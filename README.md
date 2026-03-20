# flin-google-ads-mcp

Read-only MCP server for Google Ads, built for simple public use via `uvx`.

## Why this server

- Read-only by design
- No create/update/delete campaign operations
- Credentials via environment variables only
- Easy local testing with MCP Inspector

## Exposed MCP tools

- `health_check`
- `list_accessible_customers`
- `get_customer_clients`
- `get_campaigns`
- `get_ad_groups`
- `get_ads`
- `get_insights`
- `get_keywords`

`get_ads` includes RSA content fields (headlines/descriptions/paths/final URLs) when available.

## Requirements

1. Python 3.10+
2. Node.js (only for MCP Inspector testing)
3. Google Ads API credentials:
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`
- `GOOGLE_ADS_REFRESH_TOKEN`

Optional:

- `GOOGLE_ADS_LOGIN_CUSTOMER_ID`
- `GOOGLE_ADS_CUSTOMER_ID` (default customer if no `customer_id` argument is passed)
- `GOOGLE_ADS_USE_PROTO_PLUS` (`true` by default)

For MCC flows, you can also pass `login_customer_id` directly per tool call.

## Date ranges

`get_insights` and `get_keywords` support:

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
        "GOOGLE_ADS_REFRESH_TOKEN": "xxx",
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
        "GOOGLE_ADS_REFRESH_TOKEN": "xxx",
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

The `Release` workflow builds, tests, and publishes to PyPI using OIDC (no PyPI API token in GitHub secrets).

## CI

GitHub Actions validates:

- unit tests
- import/compile checks
- package build
