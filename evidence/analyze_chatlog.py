#!/usr/bin/env python3
"""Reproducible aggregate mining for the Learning Memory problem.

The script reads the local hackathon data pack and prints aggregate counts only.
It does not copy or modify the source CSV.
"""

from __future__ import annotations

import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = (
    ROOT
    / "data"
    / "vlearn-pack"
    / "chatlog"
    / "chat_history_anonymized_for_hackathon.csv"
)

RECAP_PATTERN = re.compile(
    r"\b(tóm tắt|tóm gọn|ôn lại|ôn tập|nội dung chính|"
    r"quan trọng nhất|cần nhớ|keyword cần nhớ)\b",
    re.IGNORECASE,
)

SELF_CHECK_PATTERN = re.compile(
    r"\b(quiz|tự kiểm tra|"
    r"đánh giá.{0,50}(học xong|hiểu|nắm))\b",
    re.IGNORECASE,
)


def percentage(numerator: int, denominator: int) -> str:
    return f"{100 * numerator / denominator:.1f}%"


def main() -> None:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    students = [row for row in rows if row["role"] == "student"]
    tutors = [row for row in rows if row["role"] == "tutor"]

    by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_conversation: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_turn: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)

    for row in rows:
        by_user[row["user_id"]].append(row)
        by_conversation[row["conversation_id"]].append(row)
        by_turn[row["turn_id"]][row["role"]] = row

    user_turn_counts = {
        user_id: len({row["turn_id"] for row in user_rows})
        for user_id, user_rows in by_user.items()
    }
    user_conversation_counts = {
        user_id: len({row["conversation_id"] for row in user_rows})
        for user_id, user_rows in by_user.items()
    }
    conversation_turn_counts = {
        conversation_id: len({row["turn_id"] for row in conversation_rows})
        for conversation_id, conversation_rows in by_conversation.items()
    }

    recap_turns = [row for row in students if RECAP_PATTERN.search(row["content"])]
    self_check_turns = [
        row for row in students if SELF_CHECK_PATTERN.search(row["content"])
    ]
    recap_without_citation = sum(
        by_turn[row["turn_id"]]["tutor"]["citations"].strip() in {"", "[]"}
        for row in recap_turns
    )

    returning_users = sum(count >= 2 for count in user_turn_counts.values())
    multi_conversation_users = sum(
        count >= 2 for count in user_conversation_counts.values()
    )
    multi_turn_conversations = sum(
        count >= 2 for count in conversation_turn_counts.values()
    )
    asked_check = sum(
        row["asked_check_question"] == "True" for row in tutors
    )
    misconceptions = sum(
        row["misconceptions"].strip() not in {"", "[]"} for row in tutors
    )
    follow_ups = sum(
        row["follow_ups"].strip() not in {"", "[]"} for row in tutors
    )

    print(f"rows={len(rows)}")
    print(f"turns={len(by_turn)}")
    print(f"users={len(by_user)}")
    print(f"conversations={len(by_conversation)}")
    print(
        "users_with_2plus_turns="
        f"{returning_users}/{len(by_user)} "
        f"({percentage(returning_users, len(by_user))})"
    )
    print(
        "users_with_2plus_conversations="
        f"{multi_conversation_users}/{len(by_user)} "
        f"({percentage(multi_conversation_users, len(by_user))})"
    )
    print(
        "conversations_with_2plus_turns="
        f"{multi_turn_conversations}/{len(by_conversation)} "
        f"({percentage(multi_turn_conversations, len(by_conversation))})"
    )
    print(
        "turns_per_user="
        f"median:{statistics.median(user_turn_counts.values()):g},"
        f"mean:{statistics.mean(user_turn_counts.values()):.2f},"
        f"max:{max(user_turn_counts.values())}"
    )
    print(
        "recap_requests="
        f"{len(recap_turns)} turns/"
        f"{len({row['user_id'] for row in recap_turns})} users"
    )
    print(
        "recap_without_citation="
        f"{recap_without_citation}/{len(recap_turns)} "
        f"({percentage(recap_without_citation, len(recap_turns))})"
    )
    print(
        "explicit_self_check_requests="
        f"{len(self_check_turns)} turns/"
        f"{len({row['user_id'] for row in self_check_turns})} users"
    )
    print(
        f"asked_check_question={asked_check}/{len(tutors)} "
        f"({percentage(asked_check, len(tutors))})"
    )
    print(f"misconceptions_nonempty={misconceptions}/{len(tutors)}")
    print(f"follow_ups_nonempty={follow_ups}/{len(tutors)}")


if __name__ == "__main__":
    main()
