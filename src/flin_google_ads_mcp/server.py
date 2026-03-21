from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import ConfigurationError, load_settings, missing_required_env_vars
from .google_ads import (
    build_ad_group_query,
    build_ads_query,
    build_campaign_query,
    build_customer_clients_query,
    build_insights_query,
    build_keywords_query,
    enum_name,
    format_google_ads_error,
    get_google_ads_client,
    list_accessible_customer_ids,
    micros_to_currency,
    normalize_customer_id,
    normalize_insight_level,
    resolve_customer_id,
    run_search_query,
    to_float,
    to_int,
)


mcp = FastMCP(
    name="flin-google-ads-mcp",
    instructions=(
        "Read-only MCP server for Google Ads. "
        "No write operations are exposed."
    ),
)


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {"ok": False, "error": format_google_ads_error(exc)}


def _metrics_payload(metrics: Any) -> dict[str, Any]:
    return {
        "impressions": to_int(metrics.impressions),
        "clicks": to_int(metrics.clicks),
        "ctr": to_float(metrics.ctr),
        "average_cpc": micros_to_currency(metrics.average_cpc),
        "cost": micros_to_currency(metrics.cost_micros),
        "conversions": to_float(metrics.conversions),
        "conversions_value": to_float(metrics.conversions_value),
    }


def _customer_id_from_resource_name(resource_name: str) -> str:
    if resource_name.startswith("customers/"):
        return resource_name.split("/", 1)[1]
    return resource_name


def _asset_text_to_dict(asset: Any) -> dict[str, Any]:
    pinned = enum_name(asset.pinned_field)
    payload: dict[str, Any] = {"text": str(asset.text)}
    if pinned not in {"UNSPECIFIED", "UNKNOWN"}:
        payload["pinned_field"] = pinned
    return payload


def _extract_ad_content(ad: Any, ad_type: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "final_urls": [str(url) for url in getattr(ad, "final_urls", [])],
    }

    if ad_type == "RESPONSIVE_SEARCH_AD":
        rsa = ad.responsive_search_ad
        payload["responsive_search_ad"] = {
            "headlines": [_asset_text_to_dict(asset) for asset in rsa.headlines],
            "descriptions": [_asset_text_to_dict(asset) for asset in rsa.descriptions],
            "path1": str(rsa.path1) if str(rsa.path1) else None,
            "path2": str(rsa.path2) if str(rsa.path2) else None,
        }

    return payload


@mcp.tool()
def health_check() -> dict[str, Any]:
    """Check whether required Google Ads configuration is present and client initialization works."""
    missing = missing_required_env_vars()
    if missing:
        return {
            "ok": False,
            "status": "missing_configuration",
            "missing_env_vars": missing,
        }

    try:
        settings = load_settings()
        get_google_ads_client()
    except Exception as exc:
        return _error_payload(exc)

    return {
        "ok": True,
        "status": "ready",
        "default_customer_id": settings.default_customer_id,
        "login_customer_id": settings.login_customer_id,
    }


@mcp.tool()
def list_accessible_customers(
    limit: int = 100,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """List customer IDs accessible by the configured OAuth credentials.

    Google Ads API ignores login_customer_id for this specific operation.
    """
    try:
        customer_ids = list_accessible_customer_ids(login_customer_id=login_customer_id)
        normalized_limit = max(1, min(limit, 500))
        items = [{"customer_id": cid} for cid in customer_ids[:normalized_limit]]
        return {"ok": True, "count": len(items), "items": items}
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def get_customer_clients(
    customer_id: str | None = None,
    status: str = "ALL",
    direct_only: bool = False,
    include_hidden: bool = False,
    include_self: bool = False,
    limit: int = 100,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """List subaccounts under a manager account using the customer_client resource."""
    try:
        settings = load_settings()
        resolved_customer_id = resolve_customer_id(customer_id, settings)
        query = build_customer_clients_query(
            status=status,
            direct_only=direct_only,
            include_hidden=include_hidden,
            include_self=include_self,
            limit=limit,
        )
        rows = run_search_query(
            resolved_customer_id, query, login_customer_id=login_customer_id
        )

        items = [
            {
                "client_customer_id": _customer_id_from_resource_name(
                    str(row.customer_client.client_customer)
                ),
                "client_resource_name": str(row.customer_client.client_customer),
                "id": str(row.customer_client.id),
                "descriptive_name": str(row.customer_client.descriptive_name),
                "level": to_int(row.customer_client.level),
                "manager": bool(row.customer_client.manager),
                "hidden": bool(row.customer_client.hidden),
                "status": enum_name(row.customer_client.status),
                "currency_code": str(row.customer_client.currency_code),
                "time_zone": str(row.customer_client.time_zone),
                "test_account": bool(row.customer_client.test_account),
            }
            for row in rows
        ]

        return {
            "ok": True,
            "customer_id": resolved_customer_id,
            "count": len(items),
            "items": items,
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def find_customer_clients(
    manager_customer_id: str,
    name_query: str,
    status: str = "ALL",
    direct_only: bool = False,
    include_hidden: bool = False,
    include_self: bool = False,
    limit: int = 100,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Find subaccounts by descriptive name under a specific manager account."""
    try:
        needle = name_query.strip().lower()
        if not needle:
            raise ValueError("name_query must not be empty.")

        resolved_manager_customer_id = normalize_customer_id(manager_customer_id)
        query = build_customer_clients_query(
            status=status,
            direct_only=direct_only,
            include_hidden=include_hidden,
            include_self=include_self,
            limit=limit,
        )
        rows = run_search_query(
            resolved_manager_customer_id, query, login_customer_id=login_customer_id
        )

        items = []
        for row in rows:
            descriptive_name = str(row.customer_client.descriptive_name)
            if needle not in descriptive_name.lower():
                continue

            items.append(
                {
                    "client_customer_id": _customer_id_from_resource_name(
                        str(row.customer_client.client_customer)
                    ),
                    "descriptive_name": descriptive_name,
                    "level": to_int(row.customer_client.level),
                    "status": enum_name(row.customer_client.status),
                    "manager": bool(row.customer_client.manager),
                    "hidden": bool(row.customer_client.hidden),
                    "currency_code": str(row.customer_client.currency_code),
                    "time_zone": str(row.customer_client.time_zone),
                }
            )

        items.sort(
            key=lambda item: (
                item["level"],
                item["descriptive_name"].lower(),
                item["client_customer_id"],
            )
        )

        return {
            "ok": True,
            "manager_customer_id": resolved_manager_customer_id,
            "name_query": name_query,
            "count": len(items),
            "items": items,
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def get_campaigns(
    customer_id: str | None = None,
    status: str = "ALL",
    limit: int = 50,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Get campaigns for a customer account."""
    try:
        settings = load_settings()
        resolved_customer_id = resolve_customer_id(customer_id, settings)
        query = build_campaign_query(status=status, limit=limit)
        rows = run_search_query(
            resolved_customer_id, query, login_customer_id=login_customer_id
        )

        items = [
            {
                "campaign_id": str(row.campaign.id),
                "campaign_name": str(row.campaign.name),
                "status": enum_name(row.campaign.status),
                "channel_type": enum_name(row.campaign.advertising_channel_type),
                "serving_status": enum_name(row.campaign.serving_status),
            }
            for row in rows
        ]
        return {
            "ok": True,
            "customer_id": resolved_customer_id,
            "count": len(items),
            "items": items,
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def get_ad_groups(
    customer_id: str | None = None,
    campaign_id: str | None = None,
    status: str = "ALL",
    limit: int = 50,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Get ad groups for a customer account, optionally filtered by campaign."""
    try:
        settings = load_settings()
        resolved_customer_id = resolve_customer_id(customer_id, settings)
        query = build_ad_group_query(status=status, campaign_id=campaign_id, limit=limit)
        rows = run_search_query(
            resolved_customer_id, query, login_customer_id=login_customer_id
        )

        items = [
            {
                "campaign_id": str(row.campaign.id),
                "campaign_name": str(row.campaign.name),
                "ad_group_id": str(row.ad_group.id),
                "ad_group_name": str(row.ad_group.name),
                "status": enum_name(row.ad_group.status),
                "type": enum_name(row.ad_group.type),
                "cpc_bid": micros_to_currency(row.ad_group.cpc_bid_micros),
            }
            for row in rows
        ]
        return {
            "ok": True,
            "customer_id": resolved_customer_id,
            "count": len(items),
            "items": items,
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def get_ads(
    customer_id: str | None = None,
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    status: str = "ALL",
    limit: int = 50,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Get ads for a customer account, optionally filtered by campaign or ad group."""
    try:
        settings = load_settings()
        resolved_customer_id = resolve_customer_id(customer_id, settings)
        query = build_ads_query(
            status=status,
            campaign_id=campaign_id,
            ad_group_id=ad_group_id,
            limit=limit,
        )
        rows = run_search_query(
            resolved_customer_id, query, login_customer_id=login_customer_id
        )

        items = []
        for row in rows:
            ad_type = enum_name(row.ad_group_ad.ad.type)
            items.append(
                {
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": str(row.campaign.name),
                    "ad_group_id": str(row.ad_group.id),
                    "ad_group_name": str(row.ad_group.name),
                    "ad_id": str(row.ad_group_ad.ad.id),
                    "ad_name": str(row.ad_group_ad.ad.name),
                    "ad_type": ad_type,
                    "status": enum_name(row.ad_group_ad.status),
                    "content": _extract_ad_content(row.ad_group_ad.ad, ad_type),
                }
            )

        return {
            "ok": True,
            "customer_id": resolved_customer_id,
            "count": len(items),
            "items": items,
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def get_insights(
    customer_id: str | None = None,
    level: str = "campaign",
    date_range: str = "LAST_30_DAYS",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Get read-only performance metrics for campaign, ad_group, or ad level."""
    try:
        settings = load_settings()
        resolved_customer_id = resolve_customer_id(customer_id, settings)
        normalized_level = normalize_insight_level(level)
        query = build_insights_query(
            level=normalized_level,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        rows = run_search_query(
            resolved_customer_id, query, login_customer_id=login_customer_id
        )

        if normalized_level == "customer":
            items = [
                {
                    "customer_id": str(row.customer.id),
                    "customer_name": str(row.customer.descriptive_name),
                    "currency_code": str(row.customer.currency_code),
                    "metrics": _metrics_payload(row.metrics),
                }
                for row in rows
            ]
        elif normalized_level == "campaign":
            items = [
                {
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": str(row.campaign.name),
                    "status": enum_name(row.campaign.status),
                    "metrics": _metrics_payload(row.metrics),
                }
                for row in rows
            ]
        elif normalized_level == "ad_group":
            items = [
                {
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": str(row.campaign.name),
                    "ad_group_id": str(row.ad_group.id),
                    "ad_group_name": str(row.ad_group.name),
                    "status": enum_name(row.ad_group.status),
                    "metrics": _metrics_payload(row.metrics),
                }
                for row in rows
            ]
        else:
            items = [
                {
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": str(row.campaign.name),
                    "ad_group_id": str(row.ad_group.id),
                    "ad_group_name": str(row.ad_group.name),
                    "ad_id": str(row.ad_group_ad.ad.id),
                    "ad_name": str(row.ad_group_ad.ad.name),
                    "status": enum_name(row.ad_group_ad.status),
                    "metrics": _metrics_payload(row.metrics),
                }
                for row in rows
            ]

        return {
            "ok": True,
            "customer_id": resolved_customer_id,
            "level": level,
            "date_range": date_range,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(items),
            "items": items,
        }
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def get_keywords(
    customer_id: str | None = None,
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    status: str = "ALL",
    date_range: str = "LAST_30_DAYS",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    login_customer_id: str | None = None,
) -> dict[str, Any]:
    """Get keyword-level entities and performance metrics."""
    try:
        settings = load_settings()
        resolved_customer_id = resolve_customer_id(customer_id, settings)
        query = build_keywords_query(
            status=status,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
            campaign_id=campaign_id,
            ad_group_id=ad_group_id,
            limit=limit,
        )
        rows = run_search_query(
            resolved_customer_id, query, login_customer_id=login_customer_id
        )

        items = [
            {
                "campaign_id": str(row.campaign.id),
                "campaign_name": str(row.campaign.name),
                "ad_group_id": str(row.ad_group.id),
                "ad_group_name": str(row.ad_group.name),
                "criterion_id": str(row.ad_group_criterion.criterion_id),
                "keyword_text": str(row.ad_group_criterion.keyword.text),
                "match_type": enum_name(row.ad_group_criterion.keyword.match_type),
                "status": enum_name(row.ad_group_criterion.status),
                "metrics": _metrics_payload(row.metrics),
            }
            for row in rows
        ]

        return {
            "ok": True,
            "customer_id": resolved_customer_id,
            "date_range": date_range,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(items),
            "items": items,
        }
    except Exception as exc:
        return _error_payload(exc)


def main() -> None:
    try:
        # Validate early if env vars are missing.
        load_settings()
    except ConfigurationError:
        # Keep startup non-fatal so health_check can still report missing vars via MCP.
        pass

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
