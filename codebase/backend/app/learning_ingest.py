from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata

import psycopg
from psycopg.types.json import Jsonb
from pypdf import PdfReader

from .database import SCHEMA_SQL


SPACE_RE = re.compile(r"\s+")
EMAIL_RE = re.compile(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[ .-]?\d){8,10}(?!\d)")
SECRET_RES = (
    re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgsk_[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAQ\.[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
)
SEGMENT_RE = re.compile(r"^\*\*\[(T\d{2}-\d{3})\]\*\*\s*(.*)$")

TRANSCRIPT_DAY_CODES = {
    "transcript-01-clean.md": "day02-problem-framing",
    "transcript-02-clean.md": "day02-success-automation",
    "transcript-03-clean.md": "day02-team-review",
    "transcript-04-clean.md": "day01-llm-foundation",
    "transcript-05-clean.md": "problem-evaluation-data",
    "transcript-06-clean.md": "transformer-attention",
}


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    return SPACE_RE.sub(" ", text).strip()


def redact_for_model(value: str) -> str:
    redacted = EMAIL_RE.sub("[EMAIL_REDACTED]", value)
    redacted = PHONE_RE.sub("[PHONE_REDACTED]", redacted)
    for pattern in SECRET_RES:
        redacted = pattern.sub("[API_KEY_REDACTED]", redacted)
    return redacted


def stable_id(*parts: object) -> str:
    value = "|".join(str(part) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def make_record(
    *,
    source_kind: str,
    source_file: str,
    source_ref: str,
    title: str,
    content: str,
    day_code: str | None = None,
    sequence_number: int | None = None,
    page_number: int | None = None,
    occurred_at: datetime | None = None,
    metadata: dict | None = None,
) -> dict:
    content_original = unicodedata.normalize("NFC", content).strip()
    content_clean = normalize_text(content_original)
    return {
        "context_id": f"lesson-{stable_id(source_kind, source_file, source_ref)}",
        "source_kind": source_kind,
        "source_file": source_file,
        "source_ref": source_ref,
        "title": normalize_text(title),
        "day_code": day_code,
        "scope_key": "cohort:K4",
        "channel_key": "lecture",
        "sequence_number": sequence_number,
        "page_number": page_number,
        "occurred_at": occurred_at,
        "content_original": content_original,
        "content_clean": content_clean,
        "content_search": content_clean.casefold(),
        "content_model": redact_for_model(content_clean),
        "metadata": metadata or {},
    }


def parse_transcript(path: Path, pack_root: Path) -> list[dict]:
    records: list[dict] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    document_title = normalize_text(lines[0].lstrip("# ")) if lines else path.stem
    section_title = document_title
    active_ref: str | None = None
    active_body: list[str] = []
    active_section = section_title

    def flush() -> None:
        nonlocal active_ref, active_body
        if not active_ref:
            return
        body = normalize_text(" ".join(active_body))
        if body:
            sequence = int(active_ref.rsplit("-", 1)[-1])
            records.append(
                make_record(
                    source_kind="transcript",
                    source_file=str(path.relative_to(pack_root)),
                    source_ref=active_ref,
                    title=f"{document_title}: {active_section}",
                    content=body,
                    day_code=TRANSCRIPT_DAY_CODES.get(path.name),
                    sequence_number=sequence,
                    metadata={
                        "citation_code": active_ref,
                        "section": active_section,
                    },
                )
            )
        active_ref = None
        active_body = []

    for line in lines:
        if line.startswith("## "):
            flush()
            section_title = normalize_text(line[3:])
            continue
        match = SEGMENT_RE.match(line)
        if match:
            flush()
            active_ref = match.group(1)
            active_section = section_title
            active_body = [match.group(2)]
            continue
        if active_ref and line.strip():
            active_body.append(line.strip())
    flush()
    return records


def parse_slides(path: Path, pack_root: Path) -> list[dict]:
    reader = PdfReader(path)
    metadata = reader.metadata
    document_title = normalize_text(metadata.title if metadata else "") or path.stem
    day_code = "day01-llm-foundation" if path.name.startswith("d1-") else "day02-problem-framing"
    records: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            content = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            content = page.extract_text() or ""
        content = normalize_text(content)
        if not content:
            continue
        records.append(
            make_record(
                source_kind="slide",
                source_file=str(path.relative_to(pack_root)),
                source_ref=f"{path.name}#page={index}",
                title=f"{document_title}: trang {index}",
                content=content,
                day_code=day_code,
                sequence_number=index,
                page_number=index,
                metadata={"document_title": document_title},
            )
        )
    return records


def parse_timestamp(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def parse_tutor_chat(path: Path, pack_root: Path) -> list[dict]:
    turns: dict[str, list[dict]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            turns[row["turn_id"]].append(row)

    records: list[dict] = []
    for turn_id, messages in turns.items():
        student = next((item for item in messages if item["role"] == "student"), None)
        tutor = next((item for item in messages if item["role"] == "tutor"), None)
        if not student or not tutor:
            continue
        question = normalize_text(student["content"])
        answer = normalize_text(tutor["content"])
        if not question or not answer:
            continue
        citations = []
        try:
            citations = json.loads(tutor.get("citations") or "[]")
        except json.JSONDecodeError:
            citations = []
        sequence = int(re.sub(r"\D", "", turn_id) or 0)
        records.append(
            make_record(
                source_kind="tutor_qa",
                source_file=str(path.relative_to(pack_root)),
                source_ref=turn_id,
                title=f"Hỏi đáp bài học: {question[:120]}",
                content=f"Câu hỏi: {question}\nCâu trả lời: {answer}",
                day_code=student.get("day_code") or None,
                sequence_number=sequence,
                occurred_at=parse_timestamp(student.get("message_created_at", "")),
                metadata={
                    "conversation_id": student.get("conversation_id"),
                    "anonymous_user_id": student.get("user_id"),
                    "student_message_id": student.get("message_id"),
                    "tutor_message_id": tutor.get("message_id"),
                    "move_used": tutor.get("move_used"),
                    "citations": citations,
                    "rating": tutor.get("rating") or student.get("rating") or None,
                },
            )
        )
    return records


def build_records(pack_root: Path) -> tuple[list[dict], dict[str, int]]:
    records: list[dict] = []
    for path in sorted((pack_root / "transcript").glob("transcript-*-clean.md")):
        records.extend(parse_transcript(path, pack_root))
    for path in sorted((pack_root / "slides").glob("*.pdf")):
        records.extend(parse_slides(path, pack_root))
    chat_path = pack_root / "chatlog" / "chat_history_anonymized_for_hackathon.csv"
    records.extend(parse_tutor_chat(chat_path, pack_root))
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        counts[record["source_kind"]] += 1
    return records, dict(counts)


UPSERT_SQL = """
INSERT INTO learning_context (
    context_id, source_kind, source_file, source_ref, title, day_code,
    scope_key, channel_key, sequence_number, page_number, occurred_at,
    content_original, content_clean, content_search, content_model, metadata
) VALUES (
    %(context_id)s, %(source_kind)s, %(source_file)s, %(source_ref)s,
    %(title)s, %(day_code)s, %(scope_key)s, %(channel_key)s,
    %(sequence_number)s, %(page_number)s, %(occurred_at)s,
    %(content_original)s, %(content_clean)s, %(content_search)s,
    %(content_model)s, %(metadata)s
)
ON CONFLICT (context_id) DO UPDATE SET
    source_kind = EXCLUDED.source_kind,
    source_file = EXCLUDED.source_file,
    source_ref = EXCLUDED.source_ref,
    title = EXCLUDED.title,
    day_code = EXCLUDED.day_code,
    scope_key = EXCLUDED.scope_key,
    channel_key = EXCLUDED.channel_key,
    sequence_number = EXCLUDED.sequence_number,
    page_number = EXCLUDED.page_number,
    occurred_at = EXCLUDED.occurred_at,
    content_original = EXCLUDED.content_original,
    content_clean = EXCLUDED.content_clean,
    content_search = EXCLUDED.content_search,
    content_model = EXCLUDED.content_model,
    metadata = EXCLUDED.metadata,
    updated_at = NOW()
"""


def ingest(pack_root: Path, database_url: str) -> dict:
    records, source_counts = build_records(pack_root)
    serializable = [
        {**record, "metadata": Jsonb(record["metadata"])}
        for record in records
    ]
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(SCHEMA_SQL)
        with connection.cursor() as cursor:
            cursor.executemany(UPSERT_SQL, serializable)
        total = connection.execute(
            "SELECT COUNT(*) FROM learning_context"
        ).fetchone()[0]
    return {
        "loaded": len(records),
        "database_total": int(total),
        "source_counts": source_counts,
        "scope_key": "cohort:K4",
        "external_embedding": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load VLearn lesson context into PostgreSQL.")
    parser.add_argument("--pack-root", type=Path, required=True)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
    )
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")
    result = ingest(args.pack_root, args.database_url)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
