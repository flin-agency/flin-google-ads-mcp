from __future__ import annotations

import json
import stat
from urllib.parse import parse_qs, urlparse

import pytest

from flin_google_ads_mcp import auth
from flin_google_ads_mcp.config import ConfigurationError, Settings
from flin_google_ads_mcp.google_ads import (
    format_google_ads_error,
    normalize_customer_id,
    normalize_entity_id,
    normalize_conversion_action_name,
    normalize_user_email_filter,
)


@pytest.fixture(autouse=True)
def isolated_auth():
    auth._pending_auth.clear()
    yield
    auth._pending_auth.clear()


def settings():
    return Settings("dev", "client", "secret", None, None, None, True)


def test_oauth_requires_pending_request():
    with pytest.raises(ConfigurationError, match="get_auth_url"):
        auth.exchange_code_for_refresh_token(settings(), "code")


@pytest.mark.parametrize(
    "suffix", ["?code=x", "?code=x&state=wrong", "?code=x&code=y&state=wrong"]
)
def test_oauth_rejects_invalid_state_before_network(suffix, monkeypatch):
    auth.build_auth_url(settings())
    monkeypatch.setattr(
        auth, "urlopen", lambda *a, **kw: pytest.fail("Network must not be used")
    )
    with pytest.raises(ConfigurationError, match="mismatch"):
        auth.exchange_code_for_refresh_token(
            settings(), auth.DEFAULT_REDIRECT_URI + suffix
        )


def test_oauth_pkce_and_valid_redirect_are_single_use(monkeypatch):
    query = parse_qs(urlparse(auth.build_auth_url(settings())).query)
    assert query["code_challenge_method"] == ["S256"]

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b'{"refresh_token":"secret-token"}'

    def post(request, timeout):
        form = parse_qs(request.data.decode())
        assert len(form["code_verifier"][0]) >= 43
        return Response()

    monkeypatch.setattr(auth, "urlopen", post)
    redirect = auth.DEFAULT_REDIRECT_URI + "?code=code&state=" + query["state"][0]
    assert auth.exchange_code_for_refresh_token(settings(), redirect) == "secret-token"
    with pytest.raises(ConfigurationError, match="get_auth_url"):
        auth.exchange_code_for_refresh_token(settings(), redirect)


def test_oauth_expires(monkeypatch):
    auth.build_auth_url(settings())
    auth._pending_auth["expires"] = 0
    with pytest.raises(ConfigurationError, match="get_auth_url"):
        auth.exchange_code_for_refresh_token(settings(), "code")


@pytest.mark.parametrize(
    "uri",
    [
        "https://evil.example/callback",
        "http://127.0.0.1.evil.example/",
        "http://user@localhost/",
        "http://localhost/?x=y",
    ],
)
def test_oauth_disallows_external_redirect(uri):
    with pytest.raises(ConfigurationError, match="loopback"):
        auth.build_auth_url(settings(), uri)


def test_token_permissions_and_symlink_safety(tmp_path):
    target = tmp_path / "private" / "auth.json"
    auth.save_refresh_token("first", target)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(ConfigurationError):
        auth.save_refresh_token("second", link)
    with pytest.raises(ConfigurationError):
        auth.load_stored_refresh_token(link)
    assert auth.load_stored_refresh_token(target) == "first"
    target.chmod(0o644)
    with pytest.raises(ConfigurationError, match="0600"):
        auth.load_stored_refresh_token(target)


def test_atomic_failure_preserves_previous_token(tmp_path, monkeypatch):
    target = tmp_path / "auth.json"
    auth.save_refresh_token("first", target)

    def fail(*args):
        raise OSError("disk failure")

    monkeypatch.setattr(auth.os, "replace", fail)
    with pytest.raises(OSError):
        auth.save_refresh_token("second", target)
    assert auth.load_stored_refresh_token(target) == "first"
    assert not list(tmp_path.glob(".auth-*"))


def test_malformed_token_file(tmp_path):
    target = tmp_path / "auth.json"
    target.write_text("[]")
    target.chmod(0o600)
    with pytest.raises(ConfigurationError, match="JSON object"):
        auth.load_stored_refresh_token(target)


@pytest.mark.parametrize(
    "error", [RuntimeError("client_secret=SECRET"), ValueError("refresh_token=SECRET")]
)
def test_sdk_errors_do_not_leak_secrets(error):
    assert "SECRET" not in json.dumps(format_google_ads_error(error))


@pytest.mark.parametrize("value", ["123 OR 1=1", "１２３", "1;SELECT", "-1"])
def test_entity_ids_reject_injection_and_unicode(value):
    with pytest.raises(ValueError):
        normalize_entity_id(value)


def test_customer_ids_reject_embedded_text():
    with pytest.raises(ValueError):
        normalize_customer_id("evil1234567890")


@pytest.mark.parametrize("value", ["x' OR TRUE", "x\\", "x\ny", "x\x00y"])
def test_string_filters_reject_query_control_characters(value):
    for normalize in (normalize_conversion_action_name, normalize_user_email_filter):
        with pytest.raises(ValueError):
            normalize(value)
