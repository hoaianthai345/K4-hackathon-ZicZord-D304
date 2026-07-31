from app.key_pool import OpenRouterKeyPool


def test_flow_order_and_rate_limit_cooldown_select_next_key():
    now = [100.0]
    pool = OpenRouterKeyPool(
        {
            "phuc": "brief-key",
            "khang": "chat-key",
            "trinh": "rag-key",
        },
        {
            "brief": ["phuc", "khang", "trinh"],
            "chat": ["khang", "trinh", "phuc"],
        },
        clock=lambda: now[0],
    )

    assert [slot.name for slot in pool.candidates("brief")] == [
        "phuc",
        "khang",
        "trinh",
    ]
    assert [slot.name for slot in pool.candidates("chat")] == [
        "khang",
        "trinh",
        "phuc",
    ]

    pool.mark_failure("khang", 429, retry_after=30)

    assert [slot.name for slot in pool.candidates("chat")] == ["trinh", "phuc"]
    assert pool.state()["khang"]["available"] is False
    now[0] += 31
    assert pool.candidates("chat")[0].name == "khang"


def test_invalid_or_empty_duplicate_keys_are_not_retried():
    pool = OpenRouterKeyPool(
        {
            "phuc": "same-key",
            "khang": "same-key",
            "trinh": "",
            "default": "fallback-key",
        },
        {"chat": ["phuc", "khang", "trinh", "default"]},
    )

    assert pool.size == 2
    assert [slot.name for slot in pool.candidates("chat")] == [
        "phuc",
        "default",
    ]


def test_exhausted_credit_key_gets_long_cooldown():
    now = [10.0]
    pool = OpenRouterKeyPool(
        {"phuc": "brief-key", "khang": "chat-key"},
        {"brief": ["phuc", "khang"]},
        clock=lambda: now[0],
    )

    pool.mark_failure("phuc", 402)

    state = pool.state()["phuc"]
    assert state["available"] is False
    assert state["cooldown_seconds"] == 6 * 60 * 60
    assert pool.candidates("brief")[0].name == "khang"
