from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .config import Settings


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS discord_messages (
    message_key TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    source_sheet TEXT,
    source_row INTEGER NOT NULL,
    channel_key TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    reporter_key TEXT NOT NULL,
    author_name TEXT,
    created_at TIMESTAMPTZ,
    content_original TEXT NOT NULL,
    content_clean TEXT NOT NULL,
    content_search TEXT NOT NULL,
    content_model TEXT NOT NULL,
    flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    attachments JSONB NOT NULL DEFAULT '[]'::jsonb,
    reactions JSONB NOT NULL DEFAULT '[]'::jsonb,
    reaction_count INTEGER NOT NULL DEFAULT 0,
    same_author_duplicate_of TEXT,
    episode_message_group_id TEXT,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE discord_messages
    ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS discord_messages_scope_time_idx
    ON discord_messages (scope_key, created_at DESC);
CREATE INDEX IF NOT EXISTS discord_messages_search_idx
    ON discord_messages USING gin (to_tsvector('simple', content_model));
CREATE INDEX IF NOT EXISTS discord_messages_enabled_idx
    ON discord_messages (is_enabled, scope_key, channel_key);

CREATE TABLE IF NOT EXISTS issue_episodes (
    episode_id TEXT PRIMARY KEY,
    reporter_key TEXT NOT NULL,
    channel_key TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    canonical_problem TEXT NOT NULL,
    product_area TEXT NOT NULL,
    entities JSONB NOT NULL DEFAULT '[]'::jsonb,
    answer_summary TEXT,
    resolution_status TEXT NOT NULL,
    time_to_first_answer INTEGER,
    attachment_summary JSONB NOT NULL DEFAULT '[]'::jsonb,
    reaction_count INTEGER NOT NULL DEFAULT 0,
    source_rows JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence REAL NOT NULL,
    painpoint_cluster_id TEXT,
    payload JSONB NOT NULL,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE issue_episodes
    ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS issue_episodes_scope_time_idx
    ON issue_episodes (scope_key, start_time DESC);

CREATE TABLE IF NOT EXISTS painpoint_summary (
    painpoint_cluster_id TEXT PRIMARY KEY,
    painpoint_title TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    episode_count INTEGER NOT NULL,
    unique_reporters INTEGER NOT NULL,
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,
    unresolved_rate REAL NOT NULL,
    median_time_to_first_answer INTEGER,
    representative_examples JSONB NOT NULL DEFAULT '[]'::jsonb,
    known_resolution TEXT,
    affected_area TEXT NOT NULL,
    evidence_rows JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE painpoint_summary
    ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE IF NOT EXISTS learning_context (
    context_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    title TEXT NOT NULL,
    day_code TEXT,
    scope_key TEXT NOT NULL DEFAULT 'cohort:K4',
    channel_key TEXT NOT NULL DEFAULT 'lecture',
    sequence_number INTEGER,
    page_number INTEGER,
    occurred_at TIMESTAMPTZ,
    content_original TEXT NOT NULL,
    content_clean TEXT NOT NULL,
    content_search TEXT NOT NULL,
    content_model TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS learning_context_scope_kind_idx
    ON learning_context (scope_key, source_kind, day_code);
CREATE INDEX IF NOT EXISTS learning_context_time_idx
    ON learning_context (occurred_at DESC)
    WHERE occurred_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS learning_context_search_idx
    ON learning_context USING gin (to_tsvector('simple', content_search));
CREATE INDEX IF NOT EXISTS learning_context_trgm_idx
    ON learning_context USING gin (content_search gin_trgm_ops);

CREATE TABLE IF NOT EXISTS learner_profiles (
    profile_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    student_id_last5 VARCHAR(5) NOT NULL UNIQUE,
    demo_user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT learner_profiles_student_id_last5_format
        CHECK (student_id_last5 ~ '^[0-9]{5}$')
);

CREATE INDEX IF NOT EXISTS learner_profiles_last_seen_idx
    ON learner_profiles (last_seen_at DESC);

CREATE TABLE IF NOT EXISTS chat_interactions (
    interaction_id TEXT PRIMARY KEY,
    profile_id TEXT REFERENCES learner_profiles(profile_id) ON DELETE SET NULL,
    demo_user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'web',
    external_user_id TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    provider TEXT NOT NULL,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    tool_calls JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE chat_interactions
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'web';
ALTER TABLE chat_interactions
    ADD COLUMN IF NOT EXISTS external_user_id TEXT;

CREATE INDEX IF NOT EXISTS chat_interactions_profile_time_idx
    ON chat_interactions (profile_id, created_at DESC);
CREATE INDEX IF NOT EXISTS chat_interactions_source_time_idx
    ON chat_interactions (source, created_at DESC);

"""


@dataclass
class DatabaseStatus:
    configured: bool
    reachable: bool | None
    messages: int
    episodes: int
    painpoints: int
    learning_contexts: int
    error: str | None = None


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.database_url)

    async def ensure_schema(self) -> None:
        if not self.settings.database_url:
            return
        try:
            async with await psycopg.AsyncConnection.connect(
                self.settings.database_url,
                autocommit=True,
            ) as connection:
                await connection.execute(SCHEMA_SQL)
            self.last_error = None
        except psycopg.Error as exc:
            self.last_error = str(exc)
            raise

    async def status(self) -> DatabaseStatus:
        if not self.settings.database_url:
            return DatabaseStatus(
                configured=False,
                reachable=None,
                messages=0,
                episodes=0,
                painpoints=0,
                learning_contexts=0,
            )
        try:
            async with await psycopg.AsyncConnection.connect(
                self.settings.database_url,
                autocommit=True,
            ) as connection:
                cursor = await connection.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM discord_messages),
                        (SELECT COUNT(*) FROM issue_episodes),
                        (SELECT COUNT(*) FROM painpoint_summary),
                        (SELECT COUNT(*) FROM learning_context)
                    """
                )
                row = await cursor.fetchone()
            self.last_error = None
            return DatabaseStatus(
                configured=True,
                reachable=True,
                messages=int(row[0]),
                episodes=int(row[1]),
                painpoints=int(row[2]),
                learning_contexts=int(row[3]),
            )
        except psycopg.Error as exc:
            self.last_error = str(exc)
            return DatabaseStatus(
                configured=True,
                reachable=False,
                messages=0,
                episodes=0,
                painpoints=0,
                learning_contexts=0,
                error=self.last_error,
            )

    async def get_learner_profile(self, profile_id: str) -> dict | None:
        if not self.settings.database_url:
            return None
        async with await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(
                """
                SELECT
                    profile_id, full_name, student_id_last5, demo_user_id,
                    created_at, updated_at, last_seen_at
                FROM learner_profiles
                WHERE profile_id = %s
                """,
                (profile_id,),
            )
            return await cursor.fetchone()

    async def upsert_learner_profile(
        self,
        *,
        profile_id: str,
        full_name: str,
        student_id_last5: str,
        demo_user_id: str,
    ) -> dict:
        if not self.settings.database_url:
            raise RuntimeError("PostgreSQL chưa được cấu hình.")
        async with await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            autocommit=True,
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(
                """
                INSERT INTO learner_profiles (
                    profile_id, full_name, student_id_last5, demo_user_id
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (student_id_last5) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    demo_user_id = EXCLUDED.demo_user_id,
                    updated_at = NOW(),
                    last_seen_at = NOW()
                RETURNING
                    profile_id, full_name, student_id_last5, demo_user_id,
                    created_at, updated_at, last_seen_at
                """,
                (profile_id, full_name, student_id_last5, demo_user_id),
            )
            profile = await cursor.fetchone()
        self.last_error = None
        return profile

    async def log_chat_interaction(
        self,
        *,
        interaction_id: str,
        profile_id: str | None,
        demo_user_id: str,
        channel_id: str,
        source: str = "web",
        external_user_id: str | None = None,
        question: str,
        answer: str,
        provider: str,
        citations: list[dict],
        tool_calls: list[dict],
    ) -> bool:
        if not self.settings.database_url:
            return False
        try:
            async with await psycopg.AsyncConnection.connect(
                self.settings.database_url,
                autocommit=True,
            ) as connection:
                await connection.execute(
                    """
                    INSERT INTO chat_interactions (
                        interaction_id, profile_id, demo_user_id, channel_id,
                        source, external_user_id, question, answer, provider,
                        citations, tool_calls
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        interaction_id,
                        profile_id,
                        demo_user_id,
                        channel_id,
                        source,
                        external_user_id,
                        question,
                        answer,
                        provider,
                        Jsonb(citations),
                        Jsonb(tool_calls),
                    ),
                )
            self.last_error = None
            return True
        except psycopg.Error as exc:
            self.last_error = str(exc)
            return False

    async def source(self, source_type: str, source_id: str) -> dict | None:
        if not self.settings.database_url:
            return None
        queries = {
            "message": """
                SELECT message_key AS source_id, 'message' AS source_type,
                    channel_key, scope_key, content_model AS content, created_at,
                    jsonb_build_object(
                        'flags', flags,
                        'attachments', attachments,
                        'reactions', reactions,
                        'reaction_count', reaction_count,
                        'source_file', source_file,
                        'source_sheet', source_sheet,
                        'source_row', source_row
                    ) AS metadata
                FROM discord_messages
                WHERE message_key = %s AND is_enabled = TRUE
            """,
            "episode": """
                SELECT episode_id AS source_id, 'episode' AS source_type,
                    channel_key, scope_key, canonical_problem AS content,
                    start_time AS created_at,
                    jsonb_build_object(
                        'product_area', product_area,
                        'entities', entities,
                        'answer_summary', answer_summary,
                        'resolution_status', resolution_status,
                        'time_to_first_answer', time_to_first_answer,
                        'source_rows', source_rows,
                        'confidence', confidence,
                        'painpoint_cluster_id', painpoint_cluster_id
                    ) AS metadata
                FROM issue_episodes
                WHERE episode_id = %s AND is_enabled = TRUE
            """,
            "painpoint": """
                SELECT painpoint_cluster_id AS source_id,
                    'painpoint' AS source_type, 'qa' AS channel_key, scope_key,
                    painpoint_title AS content, first_seen AS created_at,
                    jsonb_build_object(
                        'episode_count', episode_count,
                        'unique_reporters', unique_reporters,
                        'last_seen', last_seen,
                        'unresolved_rate', unresolved_rate,
                        'median_time_to_first_answer', median_time_to_first_answer,
                        'representative_examples', representative_examples,
                        'known_resolution', known_resolution,
                        'affected_area', affected_area,
                        'evidence_rows', evidence_rows
                    ) AS metadata
                FROM painpoint_summary
                WHERE painpoint_cluster_id = %s AND is_enabled = TRUE
            """,
            "lesson": """
                SELECT context_id AS source_id, 'lesson' AS source_type,
                    channel_key, scope_key, content_model AS content,
                    occurred_at AS created_at,
                    jsonb_build_object(
                        'source_kind', source_kind,
                        'source_file', source_file,
                        'source_ref', source_ref,
                        'title', title,
                        'day_code', day_code,
                        'sequence_number', sequence_number,
                        'page_number', page_number
                    ) || metadata AS metadata
                FROM learning_context
                WHERE context_id = %s AND is_enabled = TRUE
            """,
        }
        query = queries.get(source_type)
        if not query:
            return None
        async with await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(query, (source_id,))
            return await cursor.fetchone()

    async def search_learning(
        self,
        query: str,
        scope_keys: list[str],
        *,
        day_codes: list[str] | None = None,
        source_kinds: list[str] | None = None,
        start_time=None,
        end_time=None,
        limit: int = 6,
    ) -> list[dict]:
        if not self.settings.database_url or not scope_keys:
            return []
        normalized_query = query.strip().casefold()
        tokens = [
            "".join(character for character in token if character.isalnum())
            for token in normalized_query.split()
        ]
        tokens = [token for token in tokens if len(token) >= 3][:12]
        ts_query = " | ".join(tokens)
        async with await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(
                """
                WITH ranked AS (
                    SELECT
                        context_id AS source_id,
                        'lesson' AS source_type,
                        source_kind,
                        source_ref,
                        title,
                        day_code,
                        channel_key,
                        scope_key,
                        sequence_number,
                        page_number,
                        occurred_at AS created_at,
                        content_model AS content,
                        metadata,
                        CASE
                            WHEN %s = '' THEN 0
                            ELSE ts_rank(
                                to_tsvector('simple', unaccent(content_search)),
                                to_tsquery('simple', unaccent(%s))
                            )
                        END AS text_rank,
                        CASE
                            WHEN %s = '' THEN 0
                            ELSE word_similarity(
                                unaccent(%s),
                                unaccent(content_search)
                            )
                        END AS fuzzy_rank
                    FROM learning_context
                    WHERE is_enabled = TRUE
                        AND scope_key = ANY(%s)
                        AND (%s::text[] IS NULL OR day_code = ANY(%s))
                        AND (%s::text[] IS NULL OR source_kind = ANY(%s))
                        AND (%s::timestamptz IS NULL OR occurred_at >= %s)
                        AND (%s::timestamptz IS NULL OR occurred_at < %s)
                )
                SELECT *
                FROM ranked
                WHERE %s = ''
                    OR text_rank > 0
                    OR fuzzy_rank >= 0.12
                ORDER BY
                    CASE
                        WHEN 'event_brief' = ANY(
                            COALESCE(%s::text[], ARRAY[]::text[])
                        ) AND source_kind = 'event_brief' THEN 0
                        ELSE 1
                    END,
                    (text_rank * 4 + fuzzy_rank) DESC,
                    CASE source_kind
                        WHEN 'event_brief' THEN 1
                        WHEN 'competition_rule' THEN 2
                        WHEN 'workshop_transcript' THEN 3
                        WHEN 'transcript' THEN 4
                        WHEN 'slide' THEN 5
                        ELSE 6
                    END,
                    sequence_number NULLS LAST,
                    created_at DESC NULLS LAST
                LIMIT %s
                """,
                (
                    ts_query,
                    ts_query or "empty",
                    normalized_query,
                    normalized_query,
                    scope_keys,
                    day_codes,
                    day_codes,
                    source_kinds,
                    source_kinds,
                    start_time,
                    start_time,
                    end_time,
                    end_time,
                    normalized_query,
                    source_kinds,
                    limit,
                ),
            )
            return list(await cursor.fetchall())

    async def search_messages(
        self,
        query: str,
        scope_keys: list[str],
        *,
        channel_keys: list[str] | None = None,
        start_time=None,
        end_time=None,
        limit: int = 8,
    ) -> list[dict]:
        if not self.settings.database_url or not scope_keys:
            return []
        normalized_query = query.strip().casefold()
        tokens = [
            "".join(character for character in token if character.isalnum())
            for token in normalized_query.split()
        ]
        tokens = [token for token in tokens if len(token) >= 3][:12]
        ts_query = " | ".join(tokens)
        async with await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(
                """
                WITH ranked AS (
                    SELECT
                        message_key AS source_id,
                        'message' AS source_type,
                        channel_key,
                        scope_key,
                        created_at,
                        content_model AS content,
                        author_name,
                        reaction_count,
                        CASE
                            WHEN %s = '' THEN 0
                            ELSE ts_rank(
                                to_tsvector('simple', unaccent(content_search)),
                                to_tsquery('simple', unaccent(%s))
                            )
                        END AS text_rank,
                        CASE
                            WHEN %s = '' THEN 0
                            ELSE word_similarity(
                                unaccent(%s),
                                unaccent(content_search)
                            )
                        END AS fuzzy_rank
                    FROM discord_messages
                    WHERE is_enabled = TRUE
                        AND scope_key = ANY(%s)
                        AND (%s::text[] IS NULL OR channel_key = ANY(%s))
                        AND (%s::timestamptz IS NULL OR created_at >= %s)
                        AND (%s::timestamptz IS NULL OR created_at < %s)
                )
                SELECT
                    source_id, source_type, channel_key, scope_key,
                    created_at, content,
                    jsonb_build_object(
                        'author_name', author_name,
                        'reaction_count', reaction_count
                    ) AS metadata
                FROM ranked
                WHERE %s = ''
                    OR text_rank > 0
                    OR fuzzy_rank >= 0.12
                ORDER BY
                    (text_rank * 4 + fuzzy_rank) DESC,
                    reaction_count DESC,
                    created_at DESC NULLS LAST
                LIMIT %s
                """,
                (
                    ts_query,
                    ts_query or "empty",
                    normalized_query,
                    normalized_query,
                    scope_keys,
                    channel_keys,
                    channel_keys,
                    start_time,
                    start_time,
                    end_time,
                    end_time,
                    normalized_query,
                    limit,
                ),
            )
            return list(await cursor.fetchall())

    async def recent_messages(
        self,
        scope_keys: list[str],
        *,
        start_time,
        end_time=None,
        channel_keys: list[str] | None = None,
        limit: int = 400,
    ) -> list[dict]:
        """Return a chronological Discord window without keyword ranking."""
        if not self.settings.database_url or not scope_keys:
            return []
        async with await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(
                """
                SELECT
                    message_key AS source_id,
                    channel_key,
                    scope_key,
                    reporter_key,
                    COALESCE(NULLIF(author_name, ''), reporter_key) AS author_name,
                    created_at,
                    content_model AS content,
                    flags,
                    reaction_count
                FROM discord_messages
                WHERE is_enabled = TRUE
                    AND scope_key = ANY(%s)
                    AND created_at >= %s
                    AND (%s::timestamptz IS NULL OR created_at < %s)
                    AND (%s::text[] IS NULL OR channel_key = ANY(%s))
                    AND channel_key <> 'bot-commands'
                    AND COALESCE(flags->>'is_dot_noise', 'false') <> 'true'
                    AND COALESCE(flags->>'is_greeting', 'false') <> 'true'
                    AND COALESCE(flags->>'is_bot', 'false') <> 'true'
                ORDER BY created_at DESC, message_key DESC
                LIMIT %s
                """,
                (
                    scope_keys,
                    start_time,
                    end_time,
                    end_time,
                    channel_keys,
                    channel_keys,
                    limit,
                ),
            )
            return list(await cursor.fetchall())

    async def recent_learning_events(
        self,
        scope_keys: list[str],
        *,
        start_time,
        end_time=None,
        limit: int = 12,
    ) -> list[dict]:
        """Return official event briefs that belong to the requested time window."""
        if not self.settings.database_url or not scope_keys:
            return []
        async with await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(
                """
                SELECT
                    context_id AS source_id,
                    source_kind,
                    channel_key,
                    scope_key,
                    title,
                    occurred_at AS created_at,
                    content_model AS content,
                    metadata
                FROM learning_context
                WHERE is_enabled = TRUE
                    AND scope_key = ANY(%s)
                    AND source_kind = 'event_brief'
                    AND occurred_at >= %s
                    AND (%s::timestamptz IS NULL OR occurred_at < %s)
                ORDER BY occurred_at DESC, sequence_number
                LIMIT %s
                """,
                (scope_keys, start_time, end_time, end_time, limit),
            )
            return list(await cursor.fetchall())

    async def admin_context_overview(self) -> dict:
        if not self.settings.database_url:
            return {"total": 0, "enabled": 0, "by_type": {}, "by_scope": {}}
        async with await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(
                """
                WITH context_rows AS (
                    SELECT 'lesson' AS source_type, scope_key, is_enabled
                    FROM learning_context
                    UNION ALL
                    SELECT 'message', scope_key, is_enabled FROM discord_messages
                    UNION ALL
                    SELECT 'episode', scope_key, is_enabled FROM issue_episodes
                    UNION ALL
                    SELECT 'painpoint', scope_key, is_enabled FROM painpoint_summary
                )
                SELECT
                    (SELECT COUNT(*) FROM context_rows) AS total,
                    (
                        SELECT COUNT(*) FROM context_rows
                        WHERE is_enabled = TRUE
                    ) AS enabled,
                    (
                        SELECT COALESCE(
                            jsonb_object_agg(source_type, type_count),
                            '{}'::jsonb
                        )
                        FROM (
                            SELECT source_type, COUNT(*) AS type_count
                            FROM context_rows
                            GROUP BY source_type
                        ) grouped
                    ) AS by_type
                """
            )
            summary = await cursor.fetchone()
            scope_cursor = await connection.execute(
                """
                WITH context_rows AS (
                    SELECT scope_key FROM learning_context WHERE is_enabled = TRUE
                    UNION ALL
                    SELECT scope_key FROM discord_messages WHERE is_enabled = TRUE
                    UNION ALL
                    SELECT scope_key FROM issue_episodes WHERE is_enabled = TRUE
                    UNION ALL
                    SELECT scope_key FROM painpoint_summary WHERE is_enabled = TRUE
                )
                SELECT scope_key, COUNT(*) AS count
                FROM context_rows
                GROUP BY scope_key
                ORDER BY count DESC, scope_key
                """
            )
            scopes = await scope_cursor.fetchall()
        return {
            "total": int(summary["total"] or 0),
            "enabled": int(summary["enabled"] or 0),
            "by_type": dict(summary["by_type"] or {}),
            "by_scope": {row["scope_key"]: int(row["count"]) for row in scopes},
        }

    async def admin_list_context(
        self,
        *,
        search: str = "",
        source_type: str | None = None,
        scope_key: str | None = None,
        enabled: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        if not self.settings.database_url:
            return [], 0
        async with await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            row_factory=dict_row,
        ) as connection:
            cursor = await connection.execute(
                """
                WITH context_rows AS (
                    SELECT
                        context_id AS source_id,
                        'lesson' AS source_type,
                        source_kind,
                        title,
                        channel_key,
                        scope_key,
                        day_code,
                        page_number,
                        occurred_at AS created_at,
                        content_model AS content,
                        is_enabled
                    FROM learning_context
                    UNION ALL
                    SELECT
                        message_key,
                        'message',
                        'discord_message',
                        COALESCE(author_name, 'Discord message'),
                        channel_key,
                        scope_key,
                        NULL,
                        NULL,
                        created_at,
                        content_model,
                        is_enabled
                    FROM discord_messages
                    UNION ALL
                    SELECT
                        episode_id,
                        'episode',
                        'issue_episode',
                        canonical_problem,
                        channel_key,
                        scope_key,
                        NULL,
                        NULL,
                        start_time,
                        canonical_problem,
                        is_enabled
                    FROM issue_episodes
                    UNION ALL
                    SELECT
                        painpoint_cluster_id,
                        'painpoint',
                        'painpoint_summary',
                        painpoint_title,
                        'qa',
                        scope_key,
                        NULL,
                        NULL,
                        first_seen,
                        painpoint_title,
                        is_enabled
                    FROM painpoint_summary
                ),
                filtered AS (
                    SELECT *
                    FROM context_rows
                    WHERE (%s = '' OR title ILIKE %s OR content ILIKE %s)
                        AND (%s::text IS NULL OR source_type = %s)
                        AND (%s::text IS NULL OR scope_key = %s)
                        AND (%s::boolean IS NULL OR is_enabled = %s)
                )
                SELECT *, COUNT(*) OVER() AS total_count
                FROM filtered
                ORDER BY created_at DESC NULLS LAST, source_id
                LIMIT %s OFFSET %s
                """,
                (
                    search,
                    f"%{search}%",
                    f"%{search}%",
                    source_type,
                    source_type,
                    scope_key,
                    scope_key,
                    enabled,
                    enabled,
                    limit,
                    offset,
                ),
            )
            rows = list(await cursor.fetchall())
        total = int(rows[0]["total_count"]) if rows else 0
        for row in rows:
            row.pop("total_count", None)
        return rows, total

    async def admin_set_context_enabled(
        self,
        source_type: str,
        source_id: str,
        enabled: bool,
    ) -> bool:
        if not self.settings.database_url:
            return False
        targets = {
            "lesson": ("learning_context", "context_id"),
            "message": ("discord_messages", "message_key"),
            "episode": ("issue_episodes", "episode_id"),
            "painpoint": ("painpoint_summary", "painpoint_cluster_id"),
        }
        target = targets.get(source_type)
        if not target:
            return False
        table, identifier = target
        query = psycopg.sql.SQL(
            "UPDATE {} SET is_enabled = %s WHERE {} = %s"
        ).format(
            psycopg.sql.Identifier(table),
            psycopg.sql.Identifier(identifier),
        )
        async with await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            autocommit=True,
        ) as connection:
            cursor = await connection.execute(query, (enabled, source_id))
            return cursor.rowcount == 1
