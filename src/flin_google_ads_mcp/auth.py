from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
import json
import os

from .config import ConfigurationError, Settings


AUTH_SCOPE = "https://www.googleapis.com/auth/adwords"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8080/"
DEFAULT_AUTH_FILE = Path("~/.config/flin-google-ads-mcp/auth.json")


@dataclass(frozen=True)
class ResolvedRefreshToken:
    value: str
    source: str


def get_auth_file_path() -> Path:
    configured = os.getenv("GOOGLE_ADS_AUTH_FILE")
    return Path(configured).expanduser() if configured else DEFAULT_AUTH_FILE.expanduser()


def get_redirect_uri() -> str:
    return os.getenv("GOOGLE_ADS_OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()


def build_auth_url(settings: Settings, redirect_uri: str | None = None) -> str:
    params = {
        "client_id": settings.client_id,
        "redirect_uri": redirect_uri or get_redirect_uri(),
        "response_type": "code",
        "scope": AUTH_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def extract_authorization_code(raw_code_or_url: str) -> str:
    candidate = raw_code_or_url.strip()
    if not candidate:
        raise ConfigurationError("Missing authorization code.")

    parsed = urlparse(candidate)
    if parsed.query:
        code = parse_qs(parsed.query).get("code", [""])[0].strip()
        if code:
            return code

    return candidate


def load_stored_refresh_token(auth_file: Path | None = None) -> str | None:
    path = auth_file or get_auth_file_path()
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Could not read auth file at {path}.") from exc

    token = payload.get("refresh_token")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def save_refresh_token(refresh_token: str, auth_file: Path | None = None) -> Path:
    token = refresh_token.strip()
    if not token:
        raise ConfigurationError("Cannot store an empty refresh token.")

    path = auth_file or get_auth_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"refresh_token": token}, indent=2) + "\n", encoding="utf-8"
    )
    path.chmod(0o600)
    return path


def clear_stored_refresh_token(auth_file: Path | None = None) -> bool:
    path = auth_file or get_auth_file_path()
    if not path.exists():
        return False
    path.unlink()
    return True


def resolve_refresh_token(
    settings: Settings, auth_file: Path | None = None
) -> ResolvedRefreshToken:
    if settings.refresh_token and settings.refresh_token.strip():
        return ResolvedRefreshToken(settings.refresh_token.strip(), "environment")

    stored = load_stored_refresh_token(auth_file=auth_file)
    if stored:
        return ResolvedRefreshToken(stored, "file")

    raise ConfigurationError(
        "Missing Google Ads refresh token. Call get_auth_url, sign in, then pass "
        "the returned authorization code or redirect URL to save_refresh_token_from_code."
    )


def exchange_code_for_refresh_token(
    settings: Settings,
    raw_code_or_url: str,
    redirect_uri: str | None = None,
) -> str:
    code = extract_authorization_code(raw_code_or_url)
    data = urlencode(
        {
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri or get_redirect_uri(),
        }
    ).encode("utf-8")
    request = Request(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload: Any = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise ConfigurationError(
            "Could not exchange authorization code for token."
        ) from exc

    refresh_token = payload.get("refresh_token") if isinstance(payload, dict) else None
    if not isinstance(refresh_token, str) or not refresh_token.strip():
        raise ConfigurationError(
            "Google did not return a refresh token. Generate a new auth URL and "
            "complete consent again."
        )
    return refresh_token.strip()
