from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from flin_google_ads_mcp.config import ConfigurationError, Settings


def _settings(refresh_token: str | None = None) -> Settings:
    return Settings(
        developer_token="dev",
        client_id="client-id.apps.googleusercontent.com",
        client_secret="client-secret",
        refresh_token=refresh_token,
        login_customer_id=None,
        default_customer_id=None,
        use_proto_plus=True,
    )


def test_build_auth_url_uses_offline_google_ads_scope_without_secret() -> None:
    from flin_google_ads_mcp.auth import AUTH_SCOPE, DEFAULT_REDIRECT_URI, build_auth_url

    auth_url = build_auth_url(_settings())
    parsed = urlparse(auth_url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.google.com"
    assert parsed.path == "/o/oauth2/v2/auth"
    assert query["client_id"] == ["client-id.apps.googleusercontent.com"]
    assert query["redirect_uri"] == [DEFAULT_REDIRECT_URI]
    assert query["response_type"] == ["code"]
    assert query["scope"] == [AUTH_SCOPE]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert "client-secret" not in auth_url


def test_extract_authorization_code_accepts_raw_code_and_redirect_url() -> None:
    from flin_google_ads_mcp.auth import extract_authorization_code

    assert extract_authorization_code("abc123") == "abc123"
    assert (
        extract_authorization_code("http://127.0.0.1:8080/?code=abc123&scope=x")
        == "abc123"
    )


def test_extract_authorization_code_rejects_empty_input() -> None:
    from flin_google_ads_mcp.auth import extract_authorization_code

    with pytest.raises(ConfigurationError, match="authorization code"):
        extract_authorization_code(" ")


def test_stored_refresh_token_round_trip_and_clear(tmp_path: Path) -> None:
    from flin_google_ads_mcp.auth import (
        clear_stored_refresh_token,
        load_stored_refresh_token,
        save_refresh_token,
    )

    auth_file = tmp_path / "nested" / "auth.json"

    assert load_stored_refresh_token(auth_file=auth_file) is None

    save_refresh_token("stored-refresh", auth_file=auth_file)
    assert load_stored_refresh_token(auth_file=auth_file) == "stored-refresh"

    assert clear_stored_refresh_token(auth_file=auth_file) is True
    assert load_stored_refresh_token(auth_file=auth_file) is None
    assert clear_stored_refresh_token(auth_file=auth_file) is False


def test_resolve_refresh_token_prefers_env_over_stored_file(tmp_path: Path) -> None:
    from flin_google_ads_mcp.auth import resolve_refresh_token, save_refresh_token

    auth_file = tmp_path / "auth.json"
    save_refresh_token("stored-refresh", auth_file=auth_file)

    resolved = resolve_refresh_token(
        _settings(refresh_token="env-refresh"), auth_file=auth_file
    )

    assert resolved.value == "env-refresh"
    assert resolved.source == "environment"


def test_resolve_refresh_token_uses_stored_file(tmp_path: Path) -> None:
    from flin_google_ads_mcp.auth import resolve_refresh_token, save_refresh_token

    auth_file = tmp_path / "auth.json"
    save_refresh_token("stored-refresh", auth_file=auth_file)

    resolved = resolve_refresh_token(_settings(), auth_file=auth_file)

    assert resolved.value == "stored-refresh"
    assert resolved.source == "file"


def test_resolve_refresh_token_raises_actionable_error_when_missing(tmp_path: Path) -> None:
    from flin_google_ads_mcp.auth import resolve_refresh_token

    with pytest.raises(ConfigurationError, match="get_auth_url"):
        resolve_refresh_token(_settings(), auth_file=tmp_path / "missing.json")


def test_exchange_code_for_refresh_token_posts_oauth_form(monkeypatch) -> None:
    from flin_google_ads_mcp import auth

    captured: dict[str, object] = {}

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"refresh_token": "new-refresh"}'

    def fake_urlopen(request: object, timeout: int) -> Response:
        captured["url"] = request.full_url
        captured["data"] = parse_qs(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(auth, "urlopen", fake_urlopen)

    refresh_token = auth.exchange_code_for_refresh_token(_settings(), "new-code")

    assert refresh_token == "new-refresh"
    assert captured["url"] == "https://oauth2.googleapis.com/token"
    assert captured["timeout"] == 30
    assert captured["data"] == {
        "client_id": ["client-id.apps.googleusercontent.com"],
        "client_secret": ["client-secret"],
        "code": ["new-code"],
        "grant_type": ["authorization_code"],
        "redirect_uri": [auth.DEFAULT_REDIRECT_URI],
    }
