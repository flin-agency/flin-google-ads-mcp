from __future__ import annotations

from types import SimpleNamespace

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
