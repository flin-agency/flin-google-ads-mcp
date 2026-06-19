from __future__ import annotations

from types import SimpleNamespace

from flin_google_ads_mcp.config import ConfigurationError, Settings
from flin_google_ads_mcp import server


class _EnumName:
    def __init__(self, name: str) -> None:
        self.name = name


def _customer_client_row(
    *,
    client_customer: str,
    customer_id: str,
    descriptive_name: str,
    level: int,
    status: str = "ENABLED",
    manager: bool = False,
    hidden: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        customer_client=SimpleNamespace(
            client_customer=f"customers/{client_customer}",
            id=customer_id,
            descriptive_name=descriptive_name,
            level=level,
            manager=manager,
            hidden=hidden,
            status=_EnumName(status),
            currency_code="CHF",
            time_zone="Europe/Zurich",
            test_account=False,
        )
    )


def _insights_row() -> SimpleNamespace:
    return SimpleNamespace(
        customer=SimpleNamespace(
            id="2054139041",
            descriptive_name="Avesco AG",
            currency_code="CHF",
        ),
        metrics=SimpleNamespace(
            impressions=1200,
            clicks=45,
            ctr=0.0375,
            average_cpc=875000,
            cost_micros=39375000,
            conversions=3,
            conversions_value=12500,
        ),
    )


def _search_term_row() -> SimpleNamespace:
    return SimpleNamespace(
        campaign=SimpleNamespace(id="101", name="Brand Search"),
        ad_group=SimpleNamespace(id="202", name="Brand Core"),
        search_term_view=SimpleNamespace(
            search_term="flin google ads",
            status=_EnumName("ADDED"),
        ),
        metrics=SimpleNamespace(
            impressions=800,
            clicks=32,
            ctr=0.04,
            average_cpc=625000,
            cost_micros=20000000,
            conversions=4,
            conversions_value=16000,
        ),
    )


def _conversion_insights_row() -> SimpleNamespace:
    return SimpleNamespace(
        segments=SimpleNamespace(
            date="2026-06-17",
            conversion_action="customers/2054139041/conversionActions/555",
            conversion_action_name="event_generated_lead",
        ),
        campaign=SimpleNamespace(id="101", name="Brand Search", status=_EnumName("ENABLED")),
        metrics=SimpleNamespace(
            conversions=2,
            conversions_value=8000,
        ),
    )


def _change_event_row() -> SimpleNamespace:
    return SimpleNamespace(
        change_event=SimpleNamespace(
            resource_name="customers/2054139041/changeEvents/1~2~3",
            change_date_time="2026-06-15 12:34:56.000000",
            change_resource_name="customers/2054139041/campaigns/101",
            user_email="user@example.com",
            client_type=_EnumName("GOOGLE_ADS_WEB_CLIENT"),
            change_resource_type=_EnumName("CAMPAIGN"),
            resource_change_operation=_EnumName("UPDATE"),
            changed_fields=SimpleNamespace(paths=["status", "name"]),
            old_resource=SimpleNamespace(
                campaign=SimpleNamespace(
                    status=_EnumName("PAUSED"),
                    name="Old Campaign",
                )
            ),
            new_resource=SimpleNamespace(
                campaign=SimpleNamespace(
                    status=_EnumName("ENABLED"),
                    name="New Campaign",
                )
            ),
        )
    )


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


def test_auth_status_reports_missing_refresh_token(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(server, "missing_required_env_vars", lambda: [])
    monkeypatch.setattr(server, "load_settings", lambda: _settings())
    monkeypatch.setattr(server, "get_auth_file_path", lambda: tmp_path / "auth.json")

    result = server.auth_status()

    assert result["ok"] is False
    assert result["status"] == "missing_refresh_token"
    assert result["refresh_token_source"] is None
    assert result["auth_file"] == str(tmp_path / "auth.json")
    assert result["has_stored_refresh_token"] is False
    assert "client-secret" not in str(result)


def test_get_auth_url_returns_consent_url_without_client_secret(monkeypatch) -> None:
    monkeypatch.setattr(server, "load_settings", lambda: _settings())

    result = server.get_auth_url()

    assert result["ok"] is True
    assert result["auth_url"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client-id.apps.googleusercontent.com" in result["auth_url"]
    assert "client-secret" not in result["auth_url"]


def test_save_refresh_token_from_code_stores_exchanged_token(monkeypatch, tmp_path) -> None:
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(server, "load_settings", lambda: _settings())
    monkeypatch.setattr(server, "get_auth_file_path", lambda: auth_file)
    monkeypatch.setattr(
        server,
        "exchange_code_for_refresh_token",
        lambda settings, code: "stored-refresh",
    )

    result = server.save_refresh_token_from_code("http://127.0.0.1:8080/?code=abc")

    assert result["ok"] is True
    assert result["status"] == "stored"
    assert result["auth_file"] == str(auth_file)
    assert "stored-refresh" not in str(result)


def test_health_check_reports_missing_refresh_token_as_auth_required(monkeypatch) -> None:
    monkeypatch.setattr(server, "missing_required_env_vars", lambda: [])
    monkeypatch.setattr(server, "load_settings", lambda: _settings())

    def missing_token() -> None:
        raise ConfigurationError("Missing Google Ads refresh token. Call get_auth_url.")

    monkeypatch.setattr(server, "get_google_ads_client", missing_token)

    result = server.health_check()

    assert result["ok"] is False
    assert result["status"] == "missing_auth"
    assert result["auth_tool"] == "get_auth_url"
    assert "refresh token" in result["message"]


def test_find_customer_clients_filters_case_insensitive_contains(monkeypatch) -> None:
    monkeypatch.setattr(
        server, "build_customer_clients_query", lambda **kwargs: "SELECT ..."
    )
    monkeypatch.setattr(
        server,
        "run_search_query",
        lambda customer_id, query, login_customer_id=None: [
            _customer_client_row(
                client_customer="2054139041",
                customer_id="2054139041",
                descriptive_name="Avesco AG",
                level=1,
            ),
            _customer_client_row(
                client_customer="1111111111",
                customer_id="1111111111",
                descriptive_name="Other Client",
                level=1,
            ),
            _customer_client_row(
                client_customer="2222222222",
                customer_id="2222222222",
                descriptive_name="AVESCO Parts",
                level=2,
            ),
        ],
    )

    result = server.find_customer_clients(
        manager_customer_id="6050181535",
        name_query="avEsCo",
        include_hidden=False,
        include_self=False,
        direct_only=False,
        status="ALL",
        limit=50,
    )

    assert result["ok"] is True
    assert result["manager_customer_id"] == "6050181535"
    assert result["name_query"] == "avEsCo"
    assert result["count"] == 2

    first = result["items"][0]
    assert first["client_customer_id"] == "2054139041"
    assert first["descriptive_name"] == "Avesco AG"
    assert first["level"] == 1
    assert first["status"] == "ENABLED"
    assert first["currency_code"] == "CHF"
    assert first["time_zone"] == "Europe/Zurich"


def test_get_insights_account_level_returns_account_metrics(monkeypatch) -> None:
    monkeypatch.setattr(server, "load_settings", lambda: object())
    monkeypatch.setattr(
        server, "resolve_customer_id", lambda customer_id, settings: customer_id
    )
    monkeypatch.setattr(server, "run_search_query", lambda *args, **kwargs: [_insights_row()])

    result = server.get_insights(
        customer_id="2054139041",
        level="account",
        date_range="YESTERDAY",
        limit=10,
    )

    assert result["ok"] is True
    assert result["level"] == "account"
    assert result["count"] == 1

    row = result["items"][0]
    assert row["customer_id"] == "2054139041"
    assert row["customer_name"] == "Avesco AG"
    assert row["currency_code"] == "CHF"
    assert row["metrics"]["impressions"] == 1200
    assert row["metrics"]["clicks"] == 45
    assert row["metrics"]["cost"] == 39.375


def test_get_keywords_echoes_conversion_filters(monkeypatch) -> None:
    monkeypatch.setattr(server, "load_settings", lambda: object())
    monkeypatch.setattr(
        server, "resolve_customer_id", lambda customer_id, settings: customer_id
    )
    monkeypatch.setattr(server, "build_keywords_query", lambda **kwargs: "SELECT ...")
    monkeypatch.setattr(server, "run_search_query", lambda *args, **kwargs: [])

    result = server.get_keywords(
        customer_id="2054139041",
        date_range="LAST_30_DAYS",
        conversion_action_name="event_generated_lead",
        limit=10,
    )

    assert result["ok"] is True
    assert result["conversion_action_id"] is None
    assert result["conversion_action_name"] == "event_generated_lead"


def test_get_search_terms_returns_search_term_rows(monkeypatch) -> None:
    monkeypatch.setattr(server, "load_settings", lambda: object())
    monkeypatch.setattr(
        server, "resolve_customer_id", lambda customer_id, settings: customer_id
    )
    monkeypatch.setattr(server, "build_search_terms_query", lambda **kwargs: "SELECT ...")
    monkeypatch.setattr(server, "run_search_query", lambda *args, **kwargs: [_search_term_row()])

    result = server.get_search_terms(
        customer_id="2054139041",
        date_range="LAST_30_DAYS",
        conversion_action_id="customers/2054139041/conversionActions/555",
        limit=10,
    )

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["conversion_action_id"] == "customers/2054139041/conversionActions/555"
    assert result["conversion_action_name"] is None

    row = result["items"][0]
    assert row["campaign_id"] == "101"
    assert row["campaign_name"] == "Brand Search"
    assert row["ad_group_id"] == "202"
    assert row["ad_group_name"] == "Brand Core"
    assert row["search_term"] == "flin google ads"
    assert row["status"] == "ADDED"
    assert row["metrics"]["conversions"] == 4.0


def test_get_change_events_returns_change_history_rows(monkeypatch) -> None:
    monkeypatch.setattr(server, "load_settings", lambda: object())
    monkeypatch.setattr(
        server, "resolve_customer_id", lambda customer_id, settings: customer_id
    )
    monkeypatch.setattr(server, "build_change_events_query", lambda **kwargs: "SELECT ...")
    monkeypatch.setattr(server, "run_search_query", lambda *args, **kwargs: [_change_event_row()])

    result = server.get_change_events(
        customer_id="2054139041",
        start_date="2026-06-01",
        end_date="2026-06-15",
        resource_type="campaign",
        limit=10,
    )

    assert result["ok"] is True
    assert result["customer_id"] == "2054139041"
    assert result["count"] == 1
    assert result["start_date"] == "2026-06-01"
    assert result["end_date"] == "2026-06-15"
    assert result["resource_type"] == "campaign"

    row = result["items"][0]
    assert row["resource_name"] == "customers/2054139041/changeEvents/1~2~3"
    assert row["change_date_time"] == "2026-06-15 12:34:56.000000"
    assert row["change_resource_name"] == "customers/2054139041/campaigns/101"
    assert row["user_email"] == "user@example.com"
    assert row["client_type"] == "GOOGLE_ADS_WEB_CLIENT"
    assert row["change_resource_type"] == "CAMPAIGN"
    assert row["operation"] == "UPDATE"
    assert row["changed_fields"] == ["status", "name"]
    assert row["changes"] == [
        {"field": "status", "old": "PAUSED", "new": "ENABLED"},
        {"field": "name", "old": "Old Campaign", "new": "New Campaign"},
    ]


def test_get_conversion_insights_returns_segmented_conversion_rows(monkeypatch) -> None:
    monkeypatch.setattr(server, "load_settings", lambda: object())
    monkeypatch.setattr(
        server, "resolve_customer_id", lambda customer_id, settings: customer_id
    )
    monkeypatch.setattr(
        server, "build_conversion_insights_query", lambda **kwargs: "SELECT ..."
    )
    monkeypatch.setattr(
        server, "run_search_query", lambda *args, **kwargs: [_conversion_insights_row()]
    )

    result = server.get_conversion_insights(
        customer_id="2054139041",
        level="campaign",
        date_range="CUSTOM",
        start_date="2026-06-10",
        end_date="2026-06-17",
        campaign_id="101",
        segment_by_date=True,
        segment_by_conversion_action=True,
        limit=10,
    )

    assert result["ok"] is True
    assert result["level"] == "campaign"
    assert result["segment_by_date"] is True
    assert result["segment_by_conversion_action"] is True
    assert result["count"] == 1

    row = result["items"][0]
    assert row["date"] == "2026-06-17"
    assert row["conversion_action_id"] == "customers/2054139041/conversionActions/555"
    assert row["conversion_action_name"] == "event_generated_lead"
    assert row["campaign_id"] == "101"
    assert row["campaign_name"] == "Brand Search"
    assert row["status"] == "ENABLED"
    assert row["metrics"] == {
        "conversions": 2.0,
        "conversions_value": 8000.0,
    }
