import pytest

from flin_google_ads_mcp.google_ads import (
    build_campaign_query,
    build_ads_query,
    build_customer_clients_query,
    build_insights_query,
    build_keywords_query,
    clamp_limit,
    normalize_customer_id,
    normalize_customer_client_status,
    normalize_date_range,
    normalize_insight_level,
    normalize_status,
)


def test_normalize_customer_id_removes_separators() -> None:
    assert normalize_customer_id("123-456-7890") == "1234567890"


def test_normalize_customer_id_rejects_bad_length() -> None:
    with pytest.raises(ValueError):
        normalize_customer_id("123")


def test_normalize_status_supports_active_alias() -> None:
    assert normalize_status("active") == "ENABLED"


def test_normalize_date_range_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        normalize_date_range("LAST_365_DAYS")


def test_normalize_date_range_accepts_last_90_days() -> None:
    assert normalize_date_range("LAST_90_DAYS") == "LAST_90_DAYS"


def test_normalize_customer_client_status_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        normalize_customer_client_status("PAUSED")


def test_clamp_limit_bounds_value() -> None:
    assert clamp_limit(-1) == 50
    assert clamp_limit(9999) == 500


def test_campaign_query_contains_status_filter() -> None:
    query = build_campaign_query(status="PAUSED", limit=12)
    assert "campaign.status = PAUSED" in query
    assert "LIMIT 12" in query


def test_insights_query_level_changes_from_clause() -> None:
    campaign_query = build_insights_query(
        level="campaign", date_range="LAST_7_DAYS", limit=20
    )
    ad_query = build_insights_query(level="ad", date_range="LAST_7_DAYS", limit=20)

    assert "FROM campaign" in campaign_query
    assert "FROM ad_group_ad" in ad_query


def test_normalize_insight_level_accepts_account_alias() -> None:
    assert normalize_insight_level("account") == "customer"
    assert normalize_insight_level("customer") == "customer"


def test_insights_query_account_level_uses_customer_resource() -> None:
    query = build_insights_query(
        level="account", date_range="YESTERDAY", limit=5
    )

    assert "FROM customer" in query
    assert "customer.descriptive_name" in query
    assert "customer.currency_code" in query
    assert "segments.date DURING YESTERDAY" in query


def test_insights_query_supports_custom_date_range() -> None:
    query = build_insights_query(
        level="campaign",
        date_range="CUSTOM",
        start_date="2026-02-01",
        end_date="2026-02-28",
        limit=20,
    )
    assert "segments.date BETWEEN '2026-02-01' AND '2026-02-28'" in query


def test_insights_query_custom_date_range_requires_both_dates() -> None:
    with pytest.raises(ValueError):
        build_insights_query(
            level="campaign",
            date_range="CUSTOM",
            start_date="2026-02-01",
            end_date=None,
            limit=20,
        )


def test_customer_clients_query_includes_level_filters() -> None:
    query = build_customer_clients_query(
        status="ALL",
        direct_only=True,
        include_hidden=False,
        include_self=False,
        limit=20,
    )
    assert "FROM customer_client" in query
    assert "customer_client.level = 1" in query
    assert "customer_client.hidden = FALSE" in query


def test_keywords_query_contains_keyword_view_and_filters() -> None:
    query = build_keywords_query(
        status="ENABLED",
        date_range="LAST_30_DAYS",
        campaign_id="123-456-7890",
        ad_group_id=None,
        limit=15,
    )
    assert "FROM keyword_view" in query
    assert "ad_group_criterion.type = KEYWORD" in query
    assert "segments.date DURING LAST_30_DAYS" in query
    assert "campaign.id = 1234567890" in query
    assert "ad_group_criterion.status = ENABLED" in query


def test_keywords_query_supports_custom_date_range() -> None:
    query = build_keywords_query(
        status="ALL",
        date_range="CUSTOM",
        start_date="2026-03-01",
        end_date="2026-03-20",
        campaign_id=None,
        ad_group_id=None,
        limit=15,
    )
    assert "segments.date BETWEEN '2026-03-01' AND '2026-03-20'" in query


def test_ads_query_includes_rsa_content_fields() -> None:
    query = build_ads_query(
        status="ALL",
        campaign_id=None,
        ad_group_id=None,
        limit=10,
    )
    assert "ad_group_ad.ad.responsive_search_ad.headlines" in query
    assert "ad_group_ad.ad.responsive_search_ad.descriptions" in query
    assert "ad_group_ad.ad.final_urls" in query
