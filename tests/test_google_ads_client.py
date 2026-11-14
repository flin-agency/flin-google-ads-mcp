"""Exercise token-free configuration with the real Google Ads SDK, offline."""

import os
from types import SimpleNamespace

import pytest
from google.ads.googleads import oauth2
from google.ads.googleads.interceptors import MetadataInterceptor
from google.auth.credentials import AnonymousCredentials

from flin_google_ads_mcp import auth, google_ads, server
from flin_google_ads_mcp.config import load_settings


@pytest.fixture(params=[None, "", "obsolete-private-token"])
def oauth_configuration(request, monkeypatch, tmp_path):
    for key in os.environ:
        if key.startswith("GOOGLE_ADS_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "private-client")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "private-secret")
    monkeypatch.setenv("GOOGLE_ADS_AUTH_FILE", str(tmp_path / "auth.json"))
    if request.param is not None:
        monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", request.param)
    load_settings.cache_clear()
    google_ads.get_google_ads_client.cache_clear()
    yield
    google_ads.get_google_ads_client.cache_clear()
    load_settings.cache_clear()


def test_local_setup_accepts_oauth_without_developer_token(oauth_configuration):
    status = server.connection_status()
    assert status["configuration_status"] == "configured"
    assert status["auth_status"] == "unauthenticated"
    assert status["live_access"] == "not_checked"
    assert server.health_check()["status"] == "missing_auth"
    assert server.auth_status()["status"] == "missing_refresh_token"
    assert "private" not in str(status)


@pytest.mark.parametrize("token_source", ["file", "env"])
@pytest.mark.parametrize("proto_plus", [True, False])
def test_sdk_omits_developer_token_and_preserves_auth_and_manager(
    oauth_configuration, monkeypatch, token_source, proto_plus
):
    monkeypatch.setenv("GOOGLE_ADS_USE_PROTO_PLUS", str(proto_plus).lower())
    monkeypatch.setenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "123-456-7890")
    if token_source == "file":
        auth.save_refresh_token("private-refresh")
        original = auth.get_auth_file_path().read_bytes()
    else:
        monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "private-refresh")

    def credentials(config):
        assert "developer_token" not in config
        assert config["client_id"] == "private-client"
        assert config["client_secret"] == "private-secret"
        assert config["refresh_token"] == "private-refresh"
        return AnonymousCredentials()

    # Only replace the OAuth network exchange; SDK configuration and gRPC
    # request metadata are the real implementation used in production.
    monkeypatch.setattr(oauth2, "get_credentials", credentials)
    for override, expected_manager in [(None, "1234567890"), ("987-654-3210", "9876543210")]:
        client = google_ads.get_google_ads_client(override)
        assert client.developer_token is None
        assert client.use_proto_plus is proto_plus
        assert client.login_customer_id == expected_manager
        assert client.get_service("CustomerService") is not None
        interceptor = MetadataInterceptor(
            developer_token=client.developer_token,
            login_customer_id=client.login_customer_id,
        )
        details = SimpleNamespace(
            method="/test", timeout=30, metadata=[], credentials=None,
            wait_for_ready=False, compression=None,
        )
        metadata = interceptor.intercept_unary_unary(
            lambda call, _: call.metadata, details, object()
        )
        assert not any(key == "developer-token" for key, _ in metadata)
        assert ("login-customer-id", expected_manager) in metadata

    if token_source == "file":
        assert auth.get_auth_file_path().read_bytes() == original
