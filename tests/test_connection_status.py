from unittest.mock import Mock

import pytest

from flin_google_ads_mcp import server
from flin_google_ads_mcp.auth import save_refresh_token
from flin_google_ads_mcp.config import Settings


@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "missing_required_env_vars", lambda: [])
    monkeypatch.setattr(
        server,
        "load_settings",
        lambda: Settings(
            "private-dev", "private-client", "private-secret", None, None, None, True
        ),
    )
    monkeypatch.setenv("GOOGLE_ADS_AUTH_FILE", str(tmp_path / "auth.json"))
    monkeypatch.setattr(
        server,
        "get_google_ads_client",
        Mock(side_effect=AssertionError("No SDK initialization")),
    )
    monkeypatch.setattr(
        server,
        "list_accessible_customer_ids",
        Mock(side_effect=AssertionError("No network")),
    )
    monkeypatch.setattr(
        server.oauth_callback,
        "start",
        Mock(side_effect=AssertionError("No browser flow")),
    )
    return tmp_path / "auth.json"


def test_incomplete_configuration_is_local(configured, monkeypatch):
    monkeypatch.setattr(
        server, "missing_required_env_vars", lambda: ["GOOGLE_ADS_CLIENT_ID"]
    )
    result = server.connection_status()
    assert result["server_version"] == server.__version__
    assert result["configuration_status"] == "incomplete"
    assert result["auth_status"] == "unknown"
    assert result["live_access"] == "not_checked"
    server.list_accessible_customer_ids.assert_not_called()


def test_missing_token_is_unauthenticated(configured):
    result = server.connection_status(check_live=True)
    assert result["configuration_status"] == "configured"
    assert result["auth_status"] == "unauthenticated"
    assert result["live_access"] == "not_checked"
    assert "get_auth_url" in result["next_step"]
    server.list_accessible_customer_ids.assert_not_called()


def test_token_presence_does_not_prove_authentication(configured):
    save_refresh_token("private-refresh", configured)
    original = configured.read_bytes()
    result = server.connection_status()
    assert result["auth_status"] == "unknown"
    assert result["live_access"] == "not_checked"
    assert configured.read_bytes() == original
    assert "private" not in str(result)
    server.list_accessible_customer_ids.assert_not_called()
    server.get_google_ads_client.assert_not_called()
    server.oauth_callback.start.assert_not_called()


def test_explicit_live_check_omits_customer_data(configured, monkeypatch):
    save_refresh_token("private-refresh", configured)
    live = Mock(return_value=["1234567890"])
    monkeypatch.setattr(server, "list_accessible_customer_ids", live)
    result = server.connection_status(check_live=True)
    live.assert_called_once_with()
    assert result["auth_status"] == "authenticated"
    assert result["live_access"] == "ok"
    assert "1234567890" not in str(result)
    assert "private" not in str(result)
    # A later default call is local again, not a cached claim of live access.
    assert server.connection_status()["live_access"] == "not_checked"
    live.assert_called_once()


def test_live_error_does_not_echo_provider_or_claim_unauthenticated(
    configured, monkeypatch
):
    save_refresh_token("private-refresh", configured)
    monkeypatch.setattr(
        server,
        "list_accessible_customer_ids",
        Mock(side_effect=RuntimeError("private-secret customer 1234567890")),
    )
    result = server.connection_status(check_live=True)
    assert result["auth_status"] == "unknown"
    assert result["live_access"] == "error"
    assert "1234567890" not in str(result)
    assert "private" not in str(result)


def test_unreadable_token_does_not_change_file_or_claim_logged_out(configured):
    configured.write_text("invalid private file")
    configured.chmod(0o600)
    result = server.connection_status()
    assert result["auth_status"] == "unknown"
    assert result["live_access"] == "not_checked"
    assert configured.read_text() == "invalid private file"


def test_invalid_account_configuration_is_incomplete(configured, monkeypatch):
    monkeypatch.setattr(
        server,
        "load_settings",
        lambda: Settings(
            "dev", "client", "secret", None, None, "invalid-private-id", True
        ),
    )
    result = server.connection_status()
    assert result["configuration_status"] == "incomplete"
    assert "invalid-private-id" not in str(result)


def test_env_override_does_not_require_reading_broken_file(configured, monkeypatch):
    configured.write_text("invalid")
    monkeypatch.setattr(
        server,
        "load_settings",
        lambda: Settings("dev", "client", "secret", "env-token", None, None, True),
    )
    result = server.connection_status()
    assert result["configuration_status"] == "configured"
    assert result["auth_status"] == "unknown"
    assert "env-token" not in str(result)
