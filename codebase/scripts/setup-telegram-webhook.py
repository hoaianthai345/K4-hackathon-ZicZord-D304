#!/usr/bin/env python3
"""Register the ZicZord FastAPI endpoint as a Telegram webhook."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


WEBHOOK_PATH = "/api/connectors/telegram/webhook"
SECRET_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,256}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register the ZicZord Telegram webhook."
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Public HTTPS backend base URL.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Env file containing TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET.",
    )
    parser.add_argument("--drop-pending-updates", action="store_true")
    return parser.parse_args()


def load_env(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise RuntimeError(f"Không thấy env file: {path}.") from exc
    values: dict[str, str] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("\"'")
    return values


def telegram_call(token: str, method: str, payload: dict | None = None) -> dict:
    request = Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API trả HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Không kết nối được Telegram API: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Telegram API không trả JSON hợp lệ.") from exc
    if not isinstance(body, dict) or body.get("ok") is not True:
        description = body.get("description") if isinstance(body, dict) else body
        raise RuntimeError(f"Telegram API từ chối request: {description}")
    return body


def normalize_webhook_secret(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value.strip())[:256]


def main() -> int:
    args = parse_args()
    try:
        public_url = args.url.rstrip("/")
        parsed = urlparse(public_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise RuntimeError("--url phải là một public HTTPS URL hợp lệ.")

        env = load_env(args.env_file)
        token = env.get("TELEGRAM_BOT_TOKEN", "")
        secret = normalize_webhook_secret(env.get("TELEGRAM_WEBHOOK_SECRET", ""))
        if not token:
            raise RuntimeError(f"{args.env_file} chưa có TELEGRAM_BOT_TOKEN.")
        if not SECRET_PATTERN.fullmatch(secret):
            raise RuntimeError(
                "TELEGRAM_WEBHOOK_SECRET chỉ được gồm A-Z, a-z, 0-9, _ hoặc -."
            )

        identity = telegram_call(token, "getMe").get("result", {})
        webhook_url = f"{public_url}{WEBHOOK_PATH}"
        telegram_call(
            token,
            "setWebhook",
            {
                "url": webhook_url,
                "secret_token": secret,
                "allowed_updates": ["message"],
                "drop_pending_updates": args.drop_pending_updates,
            },
        )
        status = telegram_call(token, "getWebhookInfo").get("result", {})
        print(f"✓ Đã cấu hình @{identity.get('username', '(không rõ username)')}")
        print(f"✓ Webhook: {status.get('url', webhook_url)}")
        print(f"✓ Pending updates: {status.get('pending_update_count', 0)}")
        return 0
    except (OSError, RuntimeError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
