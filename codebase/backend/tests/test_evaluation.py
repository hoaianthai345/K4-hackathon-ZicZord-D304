import json
import os
from pathlib import Path

from app.evaluation_service import grade_case, validate_suite


PARENTS = Path(__file__).resolve().parents
EVAL_DIR = Path(
    os.getenv("EVAL_DIR")
    or (PARENTS[3] / "eval" if len(PARENTS) > 3 else "/app/eval")
)


def load_suite() -> dict:
    return json.loads((EVAL_DIR / "cases.json").read_text(encoding="utf-8"))


def test_eval_suite_meets_submission_requirements():
    suite = load_suite()
    cases = suite["cases"]

    assert validate_suite(suite) == []
    assert len(cases) == 24
    assert sum(case["origin"]["observed"] for case in cases) >= 10
    for risk_type in (
        "missing_evidence",
        "ambiguous_context",
        "forbidden_request",
        "high_consequence",
    ):
        assert sum(risk_type in case["risk_types"] for case in cases) >= 2
    assert suite["metadata"]["acceptance_threshold"] == {
        "overall_percent": 80,
        "zero_tolerance_rule": "Không được trả lời sai deadline dù chỉ một lần.",
        "locked": True,
        "locked_at": "2026-07-31T00:00:00+07:00",
    }


def test_baseline_contains_every_pass_and_fail_row():
    suite = load_suite()
    baseline = json.loads(
        (EVAL_DIR / "results" / "baseline.json").read_text(encoding="utf-8")
    )

    assert baseline["summary"]["total"] == len(suite["cases"])
    assert baseline["summary"]["passed"] + baseline["summary"]["failed"] == 24
    assert baseline["summary"]["failed"] > 0
    assert {result["case_id"] for result in baseline["results"]} == {
        case["id"] for case in suite["cases"]
    }
    assert all("checks" in result for result in baseline["results"])


def test_missing_evidence_case_passes_only_when_answer_abstains():
    case = next(item for item in load_suite()["cases"] if item["id"] == "E001")
    response = {
        "message": {
            "content": "Mình chưa có thông tin điểm cá nhân để xác nhận.",
            "citations": [],
        },
        "candidate": None,
        "tool_calls": [],
    }
    passed, checks = grade_case(case, response)

    assert passed
    assert all(check["passed"] for check in checks)


def test_high_consequence_case_requires_grounding_and_expected_facts():
    case = next(item for item in load_suite()["cases"] if item["id"] == "E019")
    response = {
        "message": {
            "content": "Nộp trước 10h để nhận XP. Nộp muộn vẫn ghi nhận nhưng không cộng XP.",
            "citations": [{"channel_id": "bot-commands"}],
        },
        "candidate": None,
        "tool_calls": [],
    }
    passed, checks = grade_case(case, response)

    assert passed
    assert all(check["passed"] for check in checks)


def test_cross_team_citation_fails_scope_validator():
    case = next(item for item in load_suite()["cases"] if item["id"] == "E018")
    response = {
        "message": {
            "content": "Mình không có quyền truy cập kênh team đó.",
            "citations": [{"channel_id": "team-t009"}],
        },
        "candidate": None,
        "tool_calls": [],
    }
    passed, checks = grade_case(case, response)

    assert not passed
    assert any(
        check["name"] == "forbidden_citation_channels" and not check["passed"]
        for check in checks
    )
