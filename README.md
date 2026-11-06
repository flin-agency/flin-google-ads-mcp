# flin-google-ads-mcp

Read-only MCP server for Google Ads, built for simple public use via `uvx`.

## Install in Claude Desktop on Mac

Download the `.mcpb` file from the [latest GitHub release](https://github.com/flin-agency/flin-google-ads-mcp/releases/latest). See the [Mac installation guide](docs/claude-desktop-mac.md) for setup, credentials and verification. The bundle requires a current Claude Desktop with MCPB UV runtime support and internet access on first launch.

See [SECURITY.md](SECURITY.md) for the security model and [review results](docs/security-review.md).

## Why this server

- Read-only by design
- No create/update/delete campaign operations
- Refresh token can be generated and stored through MCP auth tools
- Easy local testing with MCP Inspector

## Exposed MCP tools

- `health_check`
- `list_accessible_customers`
- `get_customer_clients`
- `find_customer_clients`
- `get_campaigns`
- `get_ad_groups`
- `get_ads`
- `get_insights`
- `get_conversion_insights`
- `get_keywords`
- `get_search_terms`
- `get_change_events`
- `auth_status`
- `get_auth_url`
- `save_refresh_token_from_code`
- `clear_auth_token`

`get_ads` includes RSA content fields (headlines/descriptions/paths/final URLs) when available.

`get_insights` supports:
- `campaign`
- `ad_group`
- `ad`
- `customer` (account-level metrics)
- `account` (alias of `customer`)

`get_search_terms` is backed by `search_term_view`, so it returns actual user search terms rather than configured keywords. Pass `segment_by_date=true` when you need daily search-term rows with a `date` field instead of one aggregate row per search term for the requested range.

Search-term conversion filters:

- `conversion_action_id`
- `conversion_action_name`

Search-term optional segmentation:

- `segment_by_date`

`get_change_events` is backed by the Google Ads `change_event` resource. It returns recent account changes with user, client type, changed resource, operation, changed field paths, and old/new values where the API returns them. Google Ads requires a finite `change_event.change_date_time` window within the past 30 days and a `LIMIT`; pass `start_date` and `end_date` as `YYYY-MM-DD`.

Example:

```json
{
  "tool": "get_change_events",
  "args": {
    "customer_id": "2054139041",
    "login_customer_id": "6050181535",
    "start_date": "2026-06-01",
    "end_date": "2026-06-15",
    "resource_type": "CAMPAIGN",
    "limit": 50
  }
}
```

## Conversion insights

Use `get_conversion_insights` when you need conversion-only reporting by day or conversion action, for example "which campaigns had lead conversions each day last week."

It supports the same levels as `get_insights`:
- `campaign`
- `ad_group`
- `ad`
- `customer` (account-level metrics)
- `account` (alias of `customer`)

Optional segmentation:
- `segment_by_date`
- `segment_by_conversion_action`

Optional conversion-action filters:

- `conversion_action_id`
- `conversion_action_name`

Rules:
- pass at most one of the two parameters
- `conversion_action_id` must be a Google Ads resource name such as `customers/1234567890/conversionActions/555`
- `conversion_action_name` matches `segments.conversion_action_name`
- `get_conversion_insights` returns only `metrics.conversions` and `metrics.conversions_value`

Use `get_insights` for general performance metrics such as impressions, clicks, CTR, CPC, and cost. Use `get_conversion_insights` for conversion-action or daily conversion breakdowns.

## Requirements

1. Python 3.10+
2. Node.js v25.8.1+ (only for MCP Inspector testing)
3. Google Ads API credentials:
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`

Optional:

- `GOOGLE_ADS_REFRESH_TOKEN` (backwards-compatible override; normally generated with MCP auth tools)
- `GOOGLE_ADS_AUTH_FILE` (defaults to `~/.config/flin-google-ads-mcp/auth.json`)
- `GOOGLE_ADS_OAUTH_REDIRECT_URI` (defaults to `http://127.0.0.1:8080/`)
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID`
- `GOOGLE_ADS_CUSTOMER_ID` (default customer if no `customer_id` argument is passed)
- `GOOGLE_ADS_USE_PROTO_PLUS` (`true` by default)

For MCC flows, you can also pass `login_customer_id` directly per tool call.

## Auth flow

The MCP client config no longer needs `GOOGLE_ADS_REFRESH_TOKEN`.

1. Configure `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, and `GOOGLE_ADS_CLIENT_SECRET`.
2. Run `auth_status`.
3. If it reports `missing_refresh_token`, run `get_auth_url`.
4. Open the returned Google URL, sign in, and copy the full redirected URL. A localhost connection error is expected; no callback listener is started.
5. Within 10 minutes, run `save_refresh_token_from_code` with that value in the same server session. The flow uses PKCE and validates state for full URLs.
6. Run `health_check`.

The stored refresh token is written to `~/.config/flin-google-ads-mcp/auth.json` by default and is never returned by MCP tools.

## Quick flow: "Avesco spend yesterday"

1. Find the subaccount by name under the manager:

```json
{
  "tool": "find_customer_clients",
  "args": {
    "manager_customer_id": "6050181535",
    "login_customer_id": "6050181535",
    "name_query": "Avesco",
    "direct_only": false,
    "include_hidden": false,
    "include_self": false,
    "status": "ALL",
    "limit": 50
  }
}
```

2. Use the returned `client_customer_id` with account-level insights:

```json
{
  "tool": "get_insights",
  "args": {
    "customer_id": "2054139041",
    "login_customer_id": "6050181535",
    "level": "account",
    "date_range": "YESTERDAY",
    "limit": 10
  }
}
```

## Date ranges

`get_insights`, `get_conversion_insights`, `get_keywords`, and `get_search_terms` support:

- `TODAY`
- `YESTERDAY`
- `THIS_WEEK_MON_TODAY`
- `THIS_WEEK_SUN_TODAY`
- `LAST_WEEK_MON_SUN`
- `LAST_WEEK_SUN_SAT`
- `LAST_7_DAYS`
- `LAST_14_DAYS`
- `LAST_30_DAYS`
- `LAST_60_DAYS`
- `LAST_90_DAYS`
- `THIS_MONTH`
- `LAST_MONTH`
- `CUSTOM` (requires `start_date` and `end_date` in `YYYY-MM-DD`)

## Quickstart (from source)

```bash
uv sync --extra dev
cp .env.example .env
# Fill .env values
uv run flin-google-ads-mcp
```

## Quickstart (as published package)

```bash
uvx flin-google-ads-mcp@latest
```

## Claude integration (published via uvx)

```json
{
  "mcpServers": {
    "flin-google-ads-mcp": {
      "command": "uvx",
      "args": ["flin-google-ads-mcp@latest"],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "xxx",
        "GOOGLE_ADS_CLIENT_ID": "xxx",
        "GOOGLE_ADS_CLIENT_SECRET": "xxx",
        "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "1234567890"
      }
    }
  }
}
```

## Claude integration (local development)

```json
{
  "mcpServers": {
    "flin-google-ads-mcp-local": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/nicolasg/Antigravity/flin-google-ads-mcp",
        "flin-google-ads-mcp"
      ],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "xxx",
        "GOOGLE_ADS_CLIENT_ID": "xxx",
        "GOOGLE_ADS_CLIENT_SECRET": "xxx",
        "GOOGLE_ADS_CUSTOMER_ID": "1234567890",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "0987654321"
      }
    }
  }
}
```

## How to test

Detailed guide: [docs/testing.md](docs/testing.md)
- Release checklist: [docs/release.md](docs/release.md)

Operational usage guide:
- [docs/mcp-usage-guide.md](docs/mcp-usage-guide.md)

Fast path:

```bash
uv sync --extra dev
python3 -m pytest
python3 -m compileall src
```

Then run live smoke tests with MCP Inspector (see the testing guide).

## Release on GitHub + PyPI

This repository publishes automatically with GitHub Actions:
- CI: `.github/workflows/ci.yml`
- Release: `.github/workflows/release.yml` (triggered by git tags `v*`)

### 1) Configure PyPI Trusted Publisher (one-time)

In PyPI project settings for `flin-google-ads-mcp`, add a Trusted Publisher with:

- Owner: `flin-agency`
- Repository: `flin-google-ads-mcp`
- Workflow: `release.yml`
- Environment: `pypi`

### 2) Cut a release

```bash
# bump version in pyproject.toml first, then:
git add -A
git commit -m "release: v0.1.0"
git tag v0.1.0
git push origin main --tags
```

The `Release` workflow builds, tests and publishes the Mac MCPB and Python packages to a GitHub release. PyPI publishing is a separate explicit workflow-dispatch option using OIDC. See [the release checklist](docs/release.md).

## CI

GitHub Actions validates:

- unit tests
- import/compile checks
- package build
