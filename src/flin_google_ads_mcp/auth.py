from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
import base64
import hashlib
import json
import os
import secrets
import stat
import tempfile
import threading
import time

from .config import ConfigurationError, Settings


AUTH_SCOPE = "https://www.googleapis.com/auth/adwords"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8080/"
DEFAULT_AUTH_FILE = Path("~/.config/flin-google-ads-mcp/auth.json")
_pending_auth: dict[str, Any] = {}
_auth_lock = threading.Lock()
AUTH_TTL_SECONDS = 600


@dataclass(frozen=True)
class ResolvedRefreshToken:
    value: str = field(repr=False)
    source: str


def get_auth_file_path() -> Path:
    configured = os.getenv("GOOGLE_ADS_AUTH_FILE")
    return (
        Path(configured).expanduser() if configured else DEFAULT_AUTH_FILE.expanduser()
    )


def get_redirect_uri() -> str:
    return os.getenv("GOOGLE_ADS_OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()


def build_auth_url(settings: Settings, redirect_uri: str | None = None) -> str:
    redirect = redirect_uri or get_redirect_uri()
    parsed = urlparse(redirect)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ConfigurationError(
            "OAuth redirect URI must be an HTTP loopback URL without query or fragment."
        )
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(32)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    with _auth_lock:
        _pending_auth.clear()
        _pending_auth.update(
            client_id=settings.client_id,
            redirect_uri=redirect,
            verifier=verifier,
            state=state,
            expires=time.monotonic() + AUTH_TTL_SECONDS,
        )
    params = {
        "client_id": settings.client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": AUTH_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
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
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            info = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_mode & 0o077
            ):
                raise ConfigurationError(
                    "Auth file must be a regular file owned by you with permissions 0600."
                )
            payload = json.load(handle)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Could not read auth file at {path}.") from exc

    if not isinstance(payload, dict):
        raise ConfigurationError("Auth file must contain a JSON object.")
    token = payload.get("refresh_token")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def save_refresh_token(refresh_token: str, auth_file: Path | None = None) -> Path:
    token = refresh_token.strip()
    if not token:
        raise ConfigurationError("Cannot store an empty refresh token.")

    path = auth_file or get_auth_file_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ConfigurationError("Auth file must not be a symbolic link.")
    fd, temporary = tempfile.mkstemp(prefix=".auth-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"refresh_token": token}, handle)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
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
    with _auth_lock:
        pending = dict(_pending_auth)
        if not pending or pending["expires"] < time.monotonic():
            _pending_auth.clear()
            raise ConfigurationError(
                "Call get_auth_url and complete sign-in within 10 minutes in this server session."
            )
        if pending["client_id"] != settings.client_id or pending["redirect_uri"] != (
            redirect_uri or get_redirect_uri()
        ):
            raise ConfigurationError(
                "OAuth configuration changed. Call get_auth_url again."
            )
        parsed = urlparse(raw_code_or_url.strip())
        if parsed.scheme or parsed.netloc:
            expected = urlparse(pending["redirect_uri"])
            query = parse_qs(parsed.query)
            if (
                (parsed.scheme, parsed.netloc, parsed.path)
                != (expected.scheme, expected.netloc, expected.path)
                or parsed.fragment
                or len(query.get("code", [])) != 1
                or len(query.get("state", [])) != 1
                or not secrets.compare_digest(query["state"][0], pending["state"])
            ):
                raise ConfigurationError(
                    "OAuth redirect or state mismatch. Use the URL from the latest sign-in."
                )
        _pending_auth.clear()
    code = extract_authorization_code(raw_code_or_url)
    data = urlencode(
        {
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "code_verifier": pending["verifier"],
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
