from datetime import datetime, timedelta

from data_pipeline.process_discord_exports import (
    build_episodes,
    classify_flags,
    mark_near_duplicates,
    normalize_text,
    parse_attachments,
    parse_reactions,
    redact_for_model,
    searchable_text,
    summarize_clusters,
)


def message(
    key: str,
    author: str,
    content: str,
    minute: int,
    *,
    channel: str = "qa",
) -> dict:
    attachments = []
    flags = classify_flags(content, author, attachments)
    return {
        "message_key": key,
        "channel_key": channel,
        "reporter_key": author,
        "author_name": author,
        "created_at": (datetime(2026, 7, 30, 9, 0) + timedelta(minutes=minute)).isoformat(),
        "content_clean": content,
        "content_search": searchable_text(content),
        "content_model": redact_for_model(content),
        "attachments": attachments,
        "reaction_count": 0,
        "exact_normalized_hash": key,
        "same_author_duplicate_of": None,
        "episode_message_group_id": None,
        **flags,
    }


def test_normalize_and_redact_preserve_vietnamese_and_url():
    value = normalize_text("  Tôi   lỗi 😭 https://example.com/a?q=1  ")
    assert value == "Tôi lỗi 😭 https://example.com/a?q=1"
    redacted = redact_for_model("Mail a+b@vinuni.edu.vn, gọi 0912 345 678")
    assert redacted == "Mail [EMAIL_REDACTED], gọi [PHONE_REDACTED]"


def test_attachment_and_reaction_normalization():
    attachments = parse_attachments(
        "https://cdn.discordapp.com/a/error.png?ex=abc&token=secret"
    )
    assert attachments[0]["url"].endswith("token=secret")
    assert attachments[0]["canonical_url"] == "https://cdn.discordapp.com/a/error.png"
    assert attachments[0]["filename"] == "error.png"
    assert attachments[0]["extension"] == "png"
    reactions, count = parse_reactions("❤️ (2), 👀 (3)")
    assert reactions == [{"emoji": "❤️", "count": 2}, {"emoji": "👀", "count": 3}]
    assert count == 5


def test_flags_keep_acknowledgement_as_signal():
    flags = classify_flags("Cảm ơn anh, em làm được rồi", "student", [])
    assert flags["is_acknowledgement"] is True
    assert flags["is_dot_noise"] is False
    assert classify_flags("...", "student", [])["is_dot_noise"] is True


def test_same_author_duplicate_is_marked_not_deleted():
    rows = [
        message("m1", "u1", "Không nhận được GitHub invite", 0),
        message("m2", "u1", "không nhận được github invite", 2),
    ]
    mark_near_duplicates(rows)
    assert len(rows) == 2
    assert rows[1]["same_author_duplicate_of"] == "m1"


def test_different_reporters_remain_separate_but_share_painpoint_cluster():
    rows = [
        message("m1", "u1", "Mình không nhận được GitHub Org invite?", 0),
        message("m2", "coach", "Bạn kiểm tra hàng đợi invite nhé", 1),
        message("m3", "u2", "GitHub không hiện lời mời organization?", 8),
        message("m4", "coach", "Dùng ticket nếu vẫn chưa thấy invite", 9),
    ]
    episodes = build_episodes(rows)
    assert len({item["reporter_key"] for item in episodes}) == 2
    summaries = summarize_clusters(episodes, threshold=0.2)
    matching = [item for item in summaries if "GitHub" in item["painpoint_title"]]
    assert matching and matching[0]["unique_reporters"] == 2


def test_concurrent_unrelated_anchors_stay_separate():
    rows = [
        message("m1", "u1", "Em xin nghỉ học hôm nay được không?", 0),
        message("m2", "u2", "Em không nhận GitHub invite?", 0),
        message("m3", "coach", "GitHub đang trong hàng đợi invite", 1),
    ]
    episodes = build_episodes(rows)
    assert len(episodes) == 2
    assert {item["product_area"] for item in episodes} >= {"attendance", "developer_access"}
