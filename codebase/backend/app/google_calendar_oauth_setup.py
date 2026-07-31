import json
import os
from pathlib import Path

from google.auth.transport.requests import AuthorizedSession
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import settings
from .google_calendar import CALENDAR_SCOPE


def _required_path(path: Path | None, label: str) -> Path:
    if not path or not path.is_file():
        raise RuntimeError(f"{label} không tồn tại: {path or '(chưa cấu hình)'}")
    return path


def _save_credentials(path: Path, credentials, organizer_email: str) -> None:
    payload = json.loads(credentials.to_json())
    payload["organizer_email"] = organizer_email
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def main() -> None:
    if settings.google_calendar_auth_mode != "oauth":
        raise RuntimeError(
            "Đặt GOOGLE_CALENDAR_AUTH_MODE=oauth trước khi kết nối."
        )
    organizer_email = settings.google_calendar_organizer_email
    if not organizer_email:
        raise RuntimeError(
            "Thiếu GOOGLE_CALENDAR_ORGANIZER_EMAIL trong backend."
        )
    client_file = _required_path(
        settings.google_calendar_oauth_client_file,
        "OAuth client JSON",
    )
    token_file = settings.google_calendar_oauth_token_file
    if not token_file:
        raise RuntimeError(
            "Thiếu GOOGLE_CALENDAR_OAUTH_TOKEN_FILE trong backend."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_file),
        scopes=[CALENDAR_SCOPE],
        autogenerate_code_verifier=True,
    )
    credentials = flow.run_local_server(
        host="localhost",
        bind_addr="0.0.0.0",
        port=settings.google_calendar_oauth_port,
        open_browser=False,
        authorization_prompt_message=(
            "\nMở URL sau trong trình duyệt và đăng nhập bằng "
            f"{organizer_email}:\n{{url}}\n"
        ),
        success_message=(
            "Đã kết nối Google Calendar thành công. "
            "Bạn có thể đóng cửa sổ này."
        ),
        access_type="offline",
        prompt="consent",
        login_hint=organizer_email,
    )
    if not credentials.refresh_token:
        raise RuntimeError(
            "Google không trả refresh_token. Hãy thu hồi quyền ứng dụng "
            "rồi chạy lại flow."
        )

    session = AuthorizedSession(credentials)
    response = session.get(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        params={"maxResults": 1},
        timeout=20,
    )
    response.raise_for_status()
    _save_credentials(token_file, credentials, organizer_email)
    print(
        "\nKết nối hoàn tất. Backend sẽ dùng "
        f"{organizer_email} làm organizer Google Calendar."
    )


if __name__ == "__main__":
    main()
