from __future__ import annotations

import base64
import hashlib
import json
import socket
import threading
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from urllib.parse import parse_qs, urlencode, urlparse
from unittest.mock import Mock

import pytest

from flin_google_ads_mcp import auth, server
from flin_google_ads_mcp.config import ConfigurationError, Settings
from flin_google_ads_mcp.oauth_callback import oauth_callback


@pytest.fixture
def setup(monkeypatch, tmp_path):
    settings = Settings("dev", "client", "secret", None, None, None, True)
    path = tmp_path / "auth.json"
    monkeypatch.delenv("GOOGLE_ADS_OAUTH_REDIRECT_URI", raising=False)
    monkeypatch.setenv("GOOGLE_ADS_AUTH_FILE", str(path))
    monkeypatch.setattr(server, "load_settings", lambda: settings)
    monkeypatch.setattr(server, "missing_required_env_vars", lambda: [])
    saved = Mock()
    return settings, path, saved


def start(setup):
    settings, path, saved = setup
    url = oauth_callback.start(settings, path, saved)
    return parse_qs(urlparse(url).query)


def callback(query, suffix=None, host=None):
    redirect = urlparse(query["redirect_uri"][0])
    connection = HTTPConnection(redirect.hostname, redirect.port, timeout=5)
    try:
        target = suffix or redirect.path + "?" + urlencode(
            {"code": "one-use-code", "state": query["state"][0]}
        )
        headers = {"Host": host} if host else {}
        connection.request("GET", target, headers=headers)
        response = connection.getresponse()
        return response.status, response.read().decode(), dict(response.getheaders())
    finally:
        connection.close()


def token_endpoint(monkeypatch, query):
    def exchange(request, timeout):
        form = parse_qs(request.data.decode())
        assert form["redirect_uri"] == query["redirect_uri"]
        assert form["code"] == ["one-use-code"]
        challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(form["code_verifier"][0].encode()).digest()
            )
            .rstrip(b"=")
            .decode()
        )
        assert query["code_challenge"] == [challenge]
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        response.read.return_value = b'{"refresh_token":"private-refresh"}'
        return response

    post = Mock(side_effect=exchange)
    monkeypatch.setattr(auth, "urlopen", post)
    return post


def test_browser_callback_stores_token_without_manual_tool(setup, monkeypatch, capsys):
    query = start(setup)
    post = token_endpoint(monkeypatch, query)
    status, body, headers = callback(query)
    assert status == 200
    assert "Sign-in complete" in body
    assert "private-refresh" not in body
    assert "one-use-code" not in body
    assert headers["Cache-Control"] == "no-store"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert auth.load_stored_refresh_token(setup[1]) == "private-refresh"
    assert setup[1].stat().st_mode & 0o777 == 0o600
    setup[2].assert_called_once()
    post.assert_called_once()
    assert server.auth_status()["oauth_flow_status"] == "stored"
    assert server.auth_status()["status"] == "ready"
    assert not auth._pending_auth
    assert capsys.readouterr() == ("", "")
    with pytest.raises(OSError):
        callback(query)


@pytest.mark.parametrize(
    "suffix",
    [
        "/favicon.ico",
        "/?code=x",
        "/?code=x&state=wrong",
        "/?error=access_denied&state=wrong",
        "/?code=x&state=%C3%A4",
        "/other?code=x&state={state}",
        "/?code=x&code=y&state={state}",
        "/?code=x&state={state}&state=",
        "/?code=&state={state}",
        "/?code=x&error=bad&state={state}",
    ],
)
def test_invalid_callbacks_do_not_consume_flow(setup, monkeypatch, suffix):
    query = start(setup)
    post = token_endpoint(monkeypatch, query)
    status, _, _ = callback(query, suffix.format(state=query["state"][0]))
    assert status == 400
    post.assert_not_called()
    assert oauth_callback.status() == "waiting_for_browser"
    assert callback(query)[0] == 200


def test_foreign_host_is_rejected(setup, monkeypatch):
    query = start(setup)
    post = token_endpoint(monkeypatch, query)
    assert callback(query, host="evil.example")[0] == 400
    post.assert_not_called()
    assert oauth_callback.status() == "waiting_for_browser"


def test_consent_denied_closes_listener_without_token(setup):
    query = start(setup)
    assert callback(query, "/?error=access_denied&state=" + query["state"][0])[0] == 400
    assert oauth_callback.status() == "denied"
    assert not setup[1].exists()
    assert not auth._pending_auth
    with pytest.raises(OSError):
        callback(query)


@pytest.mark.parametrize("failure", ["network", "missing_token", "storage"])
def test_failures_are_safe_and_retryable(setup, monkeypatch, failure):
    query = start(setup)
    post = token_endpoint(monkeypatch, query)
    if failure == "network":
        post.side_effect = OSError("secret provider response")
    elif failure == "missing_token":
        response = post.side_effect(
            Mock(
                data=urlencode(
                    {
                        "redirect_uri": query["redirect_uri"][0],
                        "code": "one-use-code",
                        "code_verifier": auth._pending_auth["verifier"],
                    }
                ).encode()
            ),
            30,
        )
        response.read.return_value = b'{"access_token":"secret provider response"}'
        post.side_effect = None
        post.return_value = response
    else:
        monkeypatch.setattr(
            auth,
            "save_refresh_token",
            Mock(side_effect=OSError("secret provider response")),
        )
    status, body, _ = callback(query)
    assert status == 500
    assert "secret provider response" not in body
    assert oauth_callback.status() == "failed"
    setup[2].assert_not_called()
    assert not setup[1].exists()
    start(setup)
    assert oauth_callback.status() == "waiting_for_browser"


def test_expiry_closes_listener_and_discards_pkce(setup, monkeypatch):
    expired = threading.Event()
    expire = oauth_callback._expire

    def expire_and_signal(flow):
        expire(flow)
        expired.set()

    monkeypatch.setattr(oauth_callback, "_expire", expire_and_signal)
    monkeypatch.setattr(auth, "AUTH_TTL_SECONDS", 0.1)
    query = start(setup)
    assert expired.wait(3)
    assert oauth_callback.status() == "expired"
    assert not auth._pending_auth
    with pytest.raises(OSError):
        callback(query)


def test_restart_rejects_old_callback_and_clear_cancels_pending(setup, monkeypatch):
    old = start(setup)
    new = start(setup)
    post = token_endpoint(monkeypatch, new)
    assert callback(new, "/?code=x&state=" + old["state"][0])[0] == 400
    post.assert_not_called()
    result = server.clear_auth_token()
    assert result["ok"]
    assert oauth_callback.status() == "cancelled"
    assert not auth._pending_auth
    with pytest.raises(OSError):
        callback(new)


def test_configured_path_port_and_repeated_start(setup, monkeypatch):
    monkeypatch.setenv(
        "GOOGLE_ADS_OAUTH_REDIRECT_URI", "http://localhost:0/oauth/callback"
    )
    query = start(setup)
    uri = query["redirect_uri"][0]
    assert uri.startswith("http://127.0.0.1:") and uri.endswith("/oauth/callback")
    monkeypatch.setenv("GOOGLE_ADS_OAUTH_REDIRECT_URI", uri)
    query = start(setup)
    assert query["redirect_uri"] == [uri]
    token_endpoint(monkeypatch, query)
    assert callback(query)[0] == 200


def test_busy_configured_port_has_actionable_error(setup, monkeypatch):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        monkeypatch.setenv(
            "GOOGLE_ADS_OAUTH_REDIRECT_URI",
            f"http://127.0.0.1:{sock.getsockname()[1]}/",
        )
        with pytest.raises(ConfigurationError, match="available port"):
            start(setup)


def test_google_client_automatically_renews_expired_access_token(setup, monkeypatch):
    from google.ads.googleads import oauth2
    from flin_google_ads_mcp import google_ads

    auth.save_refresh_token("private-refresh", setup[1])
    monkeypatch.setattr(google_ads, "load_settings", lambda: setup[0])
    calls = []

    def request(url, method, body, headers, **kwargs):
        form = parse_qs(body.decode())
        assert form["grant_type"] == ["refresh_token"]
        assert form["refresh_token"] == ["private-refresh"]
        calls.append(form)
        return Mock(
            status=200,
            data=json.dumps(
                {
                    "access_token": f"access-{len(calls)}",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                }
            ).encode(),
        )

    monkeypatch.setattr(oauth2, "Request", lambda: request)
    google_ads.get_google_ads_client.cache_clear()
    try:
        client = google_ads.get_google_ads_client()
        assert client.credentials.token == "access-1"
        client.credentials.expiry = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(seconds=1)
        headers = {}
        client.credentials.before_request(
            request, "GET", "https://googleads.googleapis.com/", headers
        )
        assert headers["authorization"] == "Bearer access-2"
        assert len(calls) == 2
    finally:
        google_ads.get_google_ads_client.cache_clear()


def test_manual_fallback_uses_dynamic_redirect_and_closes_listener(setup, monkeypatch):
    query = start(setup)
    token_endpoint(monkeypatch, query)
    result = server.save_refresh_token_from_code("one-use-code")
    assert result["ok"]
    assert auth.load_stored_refresh_token(setup[1]) == "private-refresh"
    with pytest.raises(OSError):
        callback(query)


def test_server_tool_callback_clears_cached_clients(setup, monkeypatch):
    clear = Mock()
    monkeypatch.setattr(server.get_google_ads_client, "cache_clear", clear)
    result = server.get_auth_url()
    assert result["ok"]
    assert result["next_tool"] == "auth_status"
    assert result["expires_in_seconds"] == 600
    assert server.auth_status()["oauth_flow_status"] == "waiting_for_browser"
    query = parse_qs(urlparse(result["auth_url"]).query)
    token_endpoint(monkeypatch, query)
    assert callback(query)[0] == 200
    clear.assert_called_once()
    assert server.auth_status()["refresh_token_source"] == "file"


@pytest.mark.parametrize(
    "redirect",
    [
        "https://example.com/",
        "http://0.0.0.0/",
        "http://127.0.0.1:bad/",
        "http://127.0.0.1:99999/",
        "http://127.0.0.1/?code=x",
    ],
)
def test_invalid_callback_configuration_never_starts_flow(setup, monkeypatch, redirect):
    monkeypatch.setenv("GOOGLE_ADS_OAUTH_REDIRECT_URI", redirect)
    with pytest.raises(ConfigurationError):
        start(setup)
    assert oauth_callback.status() == "idle"
