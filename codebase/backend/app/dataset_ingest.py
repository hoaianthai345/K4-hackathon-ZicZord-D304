from argparse import ArgumentParser
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg.types.json import Jsonb

from .config import settings
from .database import SCHEMA_SQL


CHANNEL_SCOPE = {
    "common": "cohort:K4",
    "qa": "cohort:K4",
    "bot-commands": "cohort:K4",
}
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def localized_timestamp(value: str | None) -> datetime | None:
    """Treat crawler timestamps without an offset as Vietnam local time."""
    if not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=VIETNAM_TZ)


def import_processed(processed_dir: Path) -> dict:
    if not settings.database_url:
        raise RuntimeError("Thiếu DATABASE_URL.")
    messages = read_jsonl(processed_dir / "messages_clean.jsonl")
    episodes = read_jsonl(processed_dir / "issue_episodes.jsonl")
    painpoints = read_jsonl(processed_dir / "painpoint_summary.jsonl")
    with psycopg.connect(settings.database_url, autocommit=True) as connection:
        connection.execute(SCHEMA_SQL)
        with connection.transaction():
            cursor = connection.cursor()
            cursor.executemany(
                """
                INSERT INTO discord_messages (
                    message_key, source_file, source_sheet, source_row, channel_key,
                    scope_key, reporter_key, author_name, created_at, content_original,
                    content_clean, content_search, content_model, flags, attachments,
                    reactions, reaction_count, same_author_duplicate_of,
                    episode_message_group_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (message_key) DO UPDATE SET
                    created_at = EXCLUDED.created_at,
                    content_clean = EXCLUDED.content_clean,
                    content_search = EXCLUDED.content_search,
                    content_model = EXCLUDED.content_model,
                    flags = EXCLUDED.flags,
                    attachments = EXCLUDED.attachments,
                    reactions = EXCLUDED.reactions,
                    reaction_count = EXCLUDED.reaction_count,
                    same_author_duplicate_of = EXCLUDED.same_author_duplicate_of,
                    episode_message_group_id = EXCLUDED.episode_message_group_id
                """,
                [
                    (
                        row["message_key"], row["source_file"], row["source_sheet"],
                        row["source_row"], row["channel_key"],
                        CHANNEL_SCOPE.get(row["channel_key"], "cohort:K4"),
                        row["reporter_key"], row.get("author_name"),
                        localized_timestamp(row.get("created_at")),
                        row["content_original"], row["content_clean"], row["content_search"],
                        row["content_model"], Jsonb({key: row[key] for key in (
                            "is_dot_noise", "is_greeting", "is_acknowledgement", "is_bot",
                            "is_question", "is_problem", "has_attachment", "is_attachment_only",
                        )}), Jsonb(row["attachments"]), Jsonb(row["reactions"]),
                        row["reaction_count"], row.get("same_author_duplicate_of"),
                        row.get("episode_message_group_id"),
                    )
                    for row in messages
                ],
            )
            cursor.executemany(
                """
                INSERT INTO issue_episodes (
                    episode_id, reporter_key, channel_key, scope_key, start_time, end_time,
                    canonical_problem, product_area, entities, answer_summary,
                    resolution_status, time_to_first_answer, attachment_summary,
                    reaction_count, source_rows, confidence, painpoint_cluster_id, payload
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (episode_id) DO UPDATE SET
                    start_time = EXCLUDED.start_time,
                    end_time = EXCLUDED.end_time,
                    canonical_problem = EXCLUDED.canonical_problem,
                    answer_summary = EXCLUDED.answer_summary,
                    resolution_status = EXCLUDED.resolution_status,
                    painpoint_cluster_id = EXCLUDED.painpoint_cluster_id,
                    payload = EXCLUDED.payload
                """,
                [
                    (
                        row["episode_id"], row["reporter_key"], row["channel_key"],
                        CHANNEL_SCOPE.get(row["channel_key"], "cohort:K4"),
                        localized_timestamp(row.get("start_time")),
                        localized_timestamp(row.get("end_time")),
                        row["canonical_problem"],
                        row["product_area"], Jsonb(row["entities"]), row.get("answer_summary"),
                        row["resolution_status"], row.get("time_to_first_answer"),
                        Jsonb(row["attachment_summary"]), row["reaction_count"],
                        Jsonb(row["source_rows"]), row["confidence"],
                        row.get("painpoint_cluster_id"), Jsonb(row),
                    )
                    for row in episodes
                ],
            )
            cursor.executemany(
                """
                INSERT INTO painpoint_summary (
                    painpoint_cluster_id, painpoint_title, scope_key, episode_count,
                    unique_reporters, first_seen, last_seen, unresolved_rate,
                    median_time_to_first_answer, representative_examples,
                    known_resolution, affected_area, evidence_rows, payload
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (painpoint_cluster_id) DO UPDATE SET
                    first_seen = EXCLUDED.first_seen,
                    last_seen = EXCLUDED.last_seen,
                    painpoint_title = EXCLUDED.painpoint_title,
                    episode_count = EXCLUDED.episode_count,
                    unique_reporters = EXCLUDED.unique_reporters,
                    unresolved_rate = EXCLUDED.unresolved_rate,
                    known_resolution = EXCLUDED.known_resolution,
                    payload = EXCLUDED.payload
                """,
                [
                    (
                        row["painpoint_cluster_id"], row["painpoint_title"], "cohort:K4",
                        row["episode_count"], row["unique_reporters"],
                        localized_timestamp(row.get("first_seen")),
                        localized_timestamp(row.get("last_seen")),
                        row["unresolved_rate"],
                        row.get("median_time_to_first_answer"),
                        Jsonb(row["representative_examples"]), row.get("known_resolution"),
                        row["affected_area"], Jsonb(row["evidence_rows"]), Jsonb(row),
                    )
                    for row in painpoints
                ],
            )
    return {
        "messages": len(messages),
        "episodes": len(episodes),
        "painpoints": len(painpoints),
    }


def main() -> None:
    parser = ArgumentParser(description="Load processed Discord datasets into PostgreSQL.")
    parser.add_argument("--processed-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(import_processed(args.processed_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()
