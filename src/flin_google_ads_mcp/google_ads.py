from __future__ import annotations

from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import Any
import re

from .config import ConfigurationError, Settings, load_settings


ALLOWED_DATE_RANGES = {
    "TODAY",
    "YESTERDAY",
    "THIS_WEEK_MON_TODAY",
    "THIS_WEEK_SUN_TODAY",
    "LAST_WEEK_MON_SUN",
    "LAST_WEEK_SUN_SAT",
    "LAST_7_DAYS",
    "LAST_14_DAYS",
    "LAST_30_DAYS",
    "LAST_60_DAYS",
    "LAST_90_DAYS",
    "THIS_MONTH",
    "LAST_MONTH",
    "CUSTOM",
}

STATUS_ALIASES = {
    "ACTIVE": "ENABLED",
}

ALLOWED_ENTITY_STATUS = {
    "ALL",
    "ENABLED",
    "PAUSED",
    "REMOVED",
    "ACTIVE",
}

ALLOWED_INSIGHT_LEVELS = {"campaign", "ad_group", "ad", "customer", "account"}

INSIGHT_LEVEL_ALIASES = {
    "account": "customer",
}

ALLOWED_CUSTOMER_CLIENT_STATUS = {
    "ALL",
    "ENABLED",
    "SUSPENDED",
    "CANCELED",
    "CLOSED",
    "UNKNOWN",
    "UNSPECIFIED",
}


def normalize_customer_id(raw_customer_id: str) -> str:
    cleaned = re.sub(r"\D", "", raw_customer_id)
    if not cleaned:
        raise ValueError("customer_id must contain at least one digit.")
    if len(cleaned) != 10:
        raise ValueError(
            f"customer_id must be 10 digits after normalization, got {len(cleaned)}."
        )
    return cleaned


def normalize_entity_id(raw_entity_id: str) -> str:
    cleaned = re.sub(r"\D", "", raw_entity_id)
    if not cleaned:
        raise ValueError("Entity ID must contain at least one digit.")
    return cleaned


def resolve_customer_id(customer_id: str | None, settings: Settings) -> str:
    candidate = customer_id or settings.default_customer_id
    if not candidate:
        raise ConfigurationError(
            "No customer_id provided. Set GOOGLE_ADS_CUSTOMER_ID or pass customer_id to the tool."
        )
    return normalize_customer_id(candidate)


def normalize_status(status: str) -> str:
    normalized = status.strip().upper()
    normalized = STATUS_ALIASES.get(normalized, normalized)
    if normalized not in ALLOWED_ENTITY_STATUS:
        allowed = ", ".join(sorted(ALLOWED_ENTITY_STATUS))
        raise ValueError(f"Invalid status {status!r}. Allowed values: {allowed}.")
    return normalized


def normalize_date_range(date_range: str) -> str:
    normalized = date_range.strip().upper()
    if normalized not in ALLOWED_DATE_RANGES:
        allowed = ", ".join(sorted(ALLOWED_DATE_RANGES))
        raise ValueError(
            f"Invalid date_range {date_range!r}. Allowed values: {allowed}."
        )
    return normalized


def normalize_iso_date(raw_date: str) -> str:
    candidate = raw_date.strip()
    try:
        parsed = date.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(
            f"Invalid date {raw_date!r}. Expected format YYYY-MM-DD."
        ) from exc
    return parsed.isoformat()


def build_segments_date_filter(
    *,
    date_range: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    normalized_date_range = normalize_date_range(date_range)

    if normalized_date_range == "CUSTOM":
        if not start_date or not end_date:
            raise ValueError(
                "CUSTOM date_range requires both start_date and end_date."
            )

        normalized_start = normalize_iso_date(start_date)
        normalized_end = normalize_iso_date(end_date)

        if normalized_start > normalized_end:
            raise ValueError("start_date must be less than or equal to end_date.")

        return f"segments.date BETWEEN '{normalized_start}' AND '{normalized_end}'"

    if start_date or end_date:
        raise ValueError(
            "start_date/end_date can only be used when date_range is CUSTOM."
        )

    return f"segments.date DURING {normalized_date_range}"


def normalize_insight_level(level: str) -> str:
    normalized = level.strip().lower()
    if normalized not in ALLOWED_INSIGHT_LEVELS:
        allowed = ", ".join(sorted(ALLOWED_INSIGHT_LEVELS))
        raise ValueError(f"Invalid level {level!r}. Allowed values: {allowed}.")
    return INSIGHT_LEVEL_ALIASES.get(normalized, normalized)


def normalize_customer_client_status(status: str) -> str:
    normalized = status.strip().upper()
    normalized = STATUS_ALIASES.get(normalized, normalized)
    if normalized not in ALLOWED_CUSTOMER_CLIENT_STATUS:
        allowed = ", ".join(sorted(ALLOWED_CUSTOMER_CLIENT_STATUS))
        raise ValueError(f"Invalid status {status!r}. Allowed values: {allowed}.")
    return normalized


def clamp_limit(limit: int, *, default: int = 50, max_limit: int = 500) -> int:
    if limit <= 0:
        return default
    return min(limit, max_limit)


@lru_cache(maxsize=16)
def get_google_ads_client(login_customer_id: str | None = None) -> Any:
    settings = load_settings()

    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError as exc:
        raise ConfigurationError(
            "google-ads dependency is not installed. Install project dependencies first."
        ) from exc

    config_dict: dict[str, Any] = {
        "developer_token": settings.developer_token,
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "refresh_token": settings.refresh_token,
        "use_proto_plus": settings.use_proto_plus,
    }

    effective_login_customer_id = login_customer_id or settings.login_customer_id
    if effective_login_customer_id:
        config_dict["login_customer_id"] = normalize_customer_id(
            effective_login_customer_id
        )

    return GoogleAdsClient.load_from_dict(config_dict)


def list_accessible_customer_ids(login_customer_id: str | None = None) -> list[str]:
    client = get_google_ads_client(login_customer_id)
    customer_service = client.get_service("CustomerService")
    response = customer_service.list_accessible_customers()

    customer_ids: list[str] = []
    for resource_name in response.resource_names:
        if resource_name.startswith("customers/"):
            customer_ids.append(resource_name.split("/", 1)[1])
    return customer_ids


def run_search_query(
    customer_id: str, query: str, login_customer_id: str | None = None
) -> list[Any]:
    client = get_google_ads_client(login_customer_id)
    service = client.get_service("GoogleAdsService")

    request = client.get_type("SearchGoogleAdsRequest")
    request.customer_id = normalize_customer_id(customer_id)
    request.query = query

    return list(service.search(request=request))


def enum_name(value: Any) -> str:
    if hasattr(value, "name"):
        return str(value.name)
    value_str = str(value)
    if "." in value_str:
        return value_str.rsplit(".", 1)[-1]
    return value_str


def to_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def micros_to_currency(value: Any) -> float:
    return to_float(value) / 1_000_000


def format_google_ads_error(exc: Exception) -> dict[str, Any]:
    # GoogleAdsException import is intentionally dynamic to keep module import cheap for tests.
    if exc.__class__.__name__ != "GoogleAdsException":
        return {"type": exc.__class__.__name__, "message": str(exc)}

    request_id = getattr(exc, "request_id", None)
    failure = getattr(exc, "failure", None)
    errors: list[dict[str, Any]] = []

    if failure is not None and getattr(failure, "errors", None):
        for failure_error in failure.errors:
            error_code = getattr(failure_error, "error_code", None)
            errors.append(
                {
                    "message": getattr(failure_error, "message", "Unknown API error"),
                    "code": str(error_code) if error_code is not None else "UNKNOWN",
                }
            )

    return {
        "type": exc.__class__.__name__,
        "request_id": request_id,
        "errors": errors,
        "message": str(exc),
    }


def _status_filter_clause(field_name: str, status: str) -> str:
    normalized_status = normalize_status(status)
    if normalized_status == "ALL":
        return ""
    return f" AND {field_name} = {normalized_status}"


def build_campaign_query(*, status: str, limit: int) -> str:
    return (
        "SELECT campaign.id, campaign.name, campaign.status, "
        "campaign.advertising_channel_type, campaign.serving_status "
        "FROM campaign "
        "WHERE campaign.id > 0"
        f"{_status_filter_clause('campaign.status', status)} "
        "ORDER BY campaign.id DESC "
        f"LIMIT {clamp_limit(limit)}"
    )


def build_ad_group_query(
    *, status: str, campaign_id: str | None, limit: int
) -> str:
    filters = ["ad_group.id > 0"]
    if campaign_id:
        filters.append(f"campaign.id = {normalize_entity_id(campaign_id)}")

    status_filter = _status_filter_clause("ad_group.status", status)
    if status_filter:
        filters.append(status_filter.replace(" AND ", "", 1))

    where_clause = " AND ".join(filters)
    return (
        "SELECT campaign.id, campaign.name, ad_group.id, ad_group.name, "
        "ad_group.status, ad_group.type, ad_group.cpc_bid_micros "
        "FROM ad_group "
        f"WHERE {where_clause} "
        "ORDER BY ad_group.id DESC "
        f"LIMIT {clamp_limit(limit)}"
    )


def build_ads_query(
    *,
    status: str,
    campaign_id: str | None,
    ad_group_id: str | None,
    limit: int,
) -> str:
    filters = ["ad_group_ad.ad.id > 0"]
    if campaign_id:
        filters.append(f"campaign.id = {normalize_entity_id(campaign_id)}")
    if ad_group_id:
        filters.append(f"ad_group.id = {normalize_entity_id(ad_group_id)}")

    status_filter = _status_filter_clause("ad_group_ad.status", status)
    if status_filter:
        filters.append(status_filter.replace(" AND ", "", 1))

    where_clause = " AND ".join(filters)
    return (
        "SELECT campaign.id, campaign.name, ad_group.id, ad_group.name, "
        "ad_group_ad.ad.id, ad_group_ad.ad.name, ad_group_ad.ad.type, "
        "ad_group_ad.status, ad_group_ad.ad.final_urls, "
        "ad_group_ad.ad.responsive_search_ad.headlines, "
        "ad_group_ad.ad.responsive_search_ad.descriptions, "
        "ad_group_ad.ad.responsive_search_ad.path1, "
        "ad_group_ad.ad.responsive_search_ad.path2 "
        "FROM ad_group_ad "
        f"WHERE {where_clause} "
        "ORDER BY ad_group_ad.ad.id DESC "
        f"LIMIT {clamp_limit(limit)}"
    )


def build_insights_query(
    *,
    level: str,
    date_range: str,
    limit: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    normalized_level = normalize_insight_level(level)
    normalized_limit = clamp_limit(limit)
    date_filter = build_segments_date_filter(
        date_range=date_range,
        start_date=start_date,
        end_date=end_date,
    )

    metrics = (
        "metrics.impressions, metrics.clicks, metrics.ctr, metrics.average_cpc, "
        "metrics.cost_micros, metrics.conversions, metrics.conversions_value"
    )

    if normalized_level == "customer":
        return (
            "SELECT customer.id, customer.descriptive_name, customer.currency_code, "
            f"{metrics} "
            "FROM customer "
            f"WHERE {date_filter} "
            "ORDER BY metrics.impressions DESC "
            f"LIMIT {normalized_limit}"
        )

    if normalized_level == "campaign":
        return (
            "SELECT campaign.id, campaign.name, campaign.status, "
            f"{metrics} "
            "FROM campaign "
            f"WHERE {date_filter} "
            "ORDER BY metrics.impressions DESC "
            f"LIMIT {normalized_limit}"
        )

    if normalized_level == "ad_group":
        return (
            "SELECT campaign.id, campaign.name, ad_group.id, ad_group.name, "
            "ad_group.status, "
            f"{metrics} "
            "FROM ad_group "
            f"WHERE {date_filter} "
            "ORDER BY metrics.impressions DESC "
            f"LIMIT {normalized_limit}"
        )

    return (
        "SELECT campaign.id, campaign.name, ad_group.id, ad_group.name, "
        "ad_group_ad.ad.id, ad_group_ad.ad.name, ad_group_ad.status, "
        f"{metrics} "
        "FROM ad_group_ad "
        f"WHERE {date_filter} "
        "ORDER BY metrics.impressions DESC "
        f"LIMIT {normalized_limit}"
    )


def build_customer_clients_query(
    *,
    status: str,
    direct_only: bool,
    include_hidden: bool,
    include_self: bool,
    limit: int,
) -> str:
    normalized_status = normalize_customer_client_status(status)
    filters = []

    if include_self and direct_only:
        filters.append("customer_client.level <= 1")
    elif include_self:
        filters.append("customer_client.level >= 0")
    elif direct_only:
        filters.append("customer_client.level = 1")
    else:
        filters.append("customer_client.level > 0")

    if not include_hidden:
        filters.append("customer_client.hidden = FALSE")

    if normalized_status != "ALL":
        filters.append(f"customer_client.status = {normalized_status}")

    where_clause = " AND ".join(filters)
    return (
        "SELECT customer_client.client_customer, customer_client.id, "
        "customer_client.descriptive_name, customer_client.level, "
        "customer_client.manager, customer_client.hidden, "
        "customer_client.status, customer_client.currency_code, "
        "customer_client.time_zone, customer_client.test_account "
        "FROM customer_client "
        f"WHERE {where_clause} "
        "ORDER BY customer_client.level ASC, customer_client.id ASC "
        f"LIMIT {clamp_limit(limit)}"
    )


def build_keywords_query(
    *,
    status: str,
    date_range: str,
    campaign_id: str | None,
    ad_group_id: str | None,
    limit: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    normalized_status = normalize_status(status)
    date_filter = build_segments_date_filter(
        date_range=date_range,
        start_date=start_date,
        end_date=end_date,
    )

    filters = [
        "ad_group_criterion.type = KEYWORD",
        date_filter,
    ]

    if campaign_id:
        filters.append(f"campaign.id = {normalize_entity_id(campaign_id)}")
    if ad_group_id:
        filters.append(f"ad_group.id = {normalize_entity_id(ad_group_id)}")
    if normalized_status != "ALL":
        filters.append(f"ad_group_criterion.status = {normalized_status}")

    where_clause = " AND ".join(filters)
    return (
        "SELECT campaign.id, campaign.name, ad_group.id, ad_group.name, "
        "ad_group_criterion.criterion_id, ad_group_criterion.status, "
        "ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, "
        "metrics.impressions, metrics.clicks, metrics.ctr, metrics.average_cpc, "
        "metrics.cost_micros, metrics.conversions, metrics.conversions_value "
        "FROM keyword_view "
        f"WHERE {where_clause} "
        "ORDER BY metrics.impressions DESC "
        f"LIMIT {clamp_limit(limit)}"
    )
