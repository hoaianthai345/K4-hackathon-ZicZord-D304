#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"
RESULTS_DIR = EVAL_DIR / "results"


def admin_key() -> str:
    env_path = ROOT / "codebase" / ".env"
    if not env_path.exists():
        raise RuntimeError(f"Không tìm thấy {env_path}.")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("ADMIN_API_KEY="):
            value = line.split("=", 1)[1].strip()
            if value:
                return value
    raise RuntimeError("ADMIN_API_KEY chưa được cấu hình trong codebase/.env.")


def request_json(url: str, key: str, method: str = "GET") -> dict:
    request = Request(
        url,
        method=method,
        headers={
            "Accept": "application/json",
            "X-Admin-Key": key,
        },
    )
    with urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def request_with_retry(url: str, key: str, method: str = "GET") -> dict:
    last_error: Exception | None = None
    for attempt in range(1, 5):
        try:
            return request_json(url, key, method)
        except (HTTPError, URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            if attempt < 4:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Request thất bại sau 4 lần thử: {last_error}")


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def build_result(
    suite: dict,
    overview: dict,
    run_id: str,
    started_at: datetime,
    results: list[dict],
) -> dict:
    passed = sum(result["passed"] for result in results)
    total = len(results)
    pass_rate = round(passed / total * 100, 1) if total else 0
    critical_failures = [
        result["case_id"]
        for result in results
        if result["critical"] and not result["passed"]
    ]
    threshold = suite["metadata"]["acceptance_threshold"]
    return {
        "run_id": run_id,
        "suite_id": suite["metadata"]["suite_id"],
        "suite_version": suite["metadata"]["version"],
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "provider": overview["provider"],
        "model": overview["model"],
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": pass_rate,
            "critical_failures": critical_failures,
            "meets_overall_threshold": (
                pass_rate >= float(threshold["overall_percent"])
            ),
            "meets_zero_tolerance": not critical_failures,
            "accepted": (
                pass_rate >= float(threshold["overall_percent"])
                and not critical_failures
            ),
        },
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ZicZord evaluation suite.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Lưu kết quả thành baseline lần đầu.",
    )
    args = parser.parse_args()
    baseline_path = RESULTS_DIR / "baseline.json"
    if args.baseline and baseline_path.exists():
        print(
            "Baseline đã tồn tại. Không ghi đè cam kết sau lần chạy đầu.",
            file=sys.stderr,
        )
        return 2

    try:
        suite = json.loads((EVAL_DIR / "cases.json").read_text(encoding="utf-8"))
        key = admin_key()
        api_url = args.api_url.rstrip("/")
        overview = request_with_retry(
            f"{api_url}/api/admin/evaluation",
            key,
        )
        run_id = (
            f"eval-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-"
            f"{uuid4().hex[:6]}"
        )
        started_at = datetime.now(UTC)
        partial_path = RESULTS_DIR / f"{run_id}.partial.json"
        results: list[dict] = []

        for index, case in enumerate(suite["cases"], start=1):
            print(
                f"[{index:02d}/{len(suite['cases'])}] {case['id']} {case['title']}",
                flush=True,
            )
            try:
                result = request_with_retry(
                    f"{api_url}/api/admin/evaluation/cases/{case['id']}/run",
                    key,
                    method="POST",
                )
            except RuntimeError as exc:
                result = {
                    "case_id": case["id"],
                    "title": case["title"],
                    "risk_types": case["risk_types"],
                    "critical": bool(case.get("critical")),
                    "observed": bool(case["origin"]["observed"]),
                    "input": case["input"],
                    "expected_behavior": case["expected_behavior"],
                    "passed": False,
                    "latency_ms": 0,
                    "answer": "",
                    "citations": [],
                    "tool_calls": [],
                    "provider": None,
                    "checks": [
                        {
                            "name": "execution",
                            "passed": False,
                            "detail": str(exc),
                        }
                    ],
                    "error": str(exc),
                }
            results.append(result)
            partial = build_result(
                suite,
                overview,
                run_id,
                started_at,
                results,
            )
            atomic_write(partial_path, partial)
            result_status = "ĐẠT" if result["passed"] else "CHƯA ĐẠT"
            print(
                f"         {result_status} | {result['latency_ms']} ms",
                flush=True,
            )

        payload = build_result(
            suite,
            overview,
            run_id,
            started_at,
            results,
        )
        atomic_write(RESULTS_DIR / "latest.json", payload)
        atomic_write(RESULTS_DIR / "runs" / f"{run_id}.json", payload)
        if args.baseline:
            atomic_write(baseline_path, payload)
        partial_path.unlink(missing_ok=True)
        summary = payload["summary"]
        print(
            f"Kết quả: {summary['passed']}/{summary['total']} "
            f"({summary['pass_rate']}%)."
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"Không chạy được eval: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
