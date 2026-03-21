# Testing Guide

This guide covers how to test `flin-google-ads-mcp` from zero to production confidence.

## Test levels

1. Local static and unit tests (no Google Ads credentials needed)
2. Local MCP runtime test with Inspector (credentials required)
3. End-to-end test in Claude using `uvx`
4. CI test (GitHub Actions) on each push/PR

## 1) Local static and unit tests

Run these first on every change:

```bash
uv sync --extra dev
python3 -m pytest
python3 -m compileall src
uv build
```

What this validates:

- query builders and config validation logic
- Python syntax/import safety
- package can be built into wheel and sdist

## 2) Local MCP runtime test with Inspector

Requires Node.js v25.8.1+ (for `npx` / Inspector CLI).

### 2.1 Export credentials in your shell

```bash
export GOOGLE_ADS_DEVELOPER_TOKEN="..."
export GOOGLE_ADS_CLIENT_ID="..."
export GOOGLE_ADS_CLIENT_SECRET="..."
export GOOGLE_ADS_REFRESH_TOKEN="..."
export GOOGLE_ADS_CUSTOMER_ID="1234567890"
export GOOGLE_ADS_LOGIN_CUSTOMER_ID="1234567890"
```

### 2.2 List tools (CLI mode)

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-ads-mcp \
  --method tools/list
```

Expected:

- `health_check`
- `list_accessible_customers`
- `get_customer_clients`
- `get_campaigns`
- `get_ad_groups`
- `get_ads`
- `get_insights`
- `get_keywords`

Note: `ListAccessibleCustomers` itself ignores `login-customer-id` by Google Ads API design.

### 2.3 Health check

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-ads-mcp \
  --method tools/call \
  --tool-name health_check
```

Expected:

- `"ok": true`
- `"status": "ready"`

### 2.4 Smoke test tool calls

Accessible customers:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-ads-mcp \
  --method tools/call \
  --tool-name list_accessible_customers \
  --tool-arg limit=10
```

Campaigns:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-ads-mcp \
  --method tools/call \
  --tool-name get_campaigns \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=0987654321 \
  --tool-arg status=ALL \
  --tool-arg limit=10
```

Ads (with content):

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-ads-mcp \
  --method tools/call \
  --tool-name get_ads \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=0987654321 \
  --tool-arg status=ENABLED \
  --tool-arg limit=10
```

Expected: `content.responsive_search_ad.headlines` and `content.responsive_search_ad.descriptions` are present for RSA ads.

Customer clients under manager:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-ads-mcp \
  --method tools/call \
  --tool-name get_customer_clients \
  --tool-arg customer_id=0987654321 \
  --tool-arg login_customer_id=0987654321 \
  --tool-arg direct_only=true \
  --tool-arg include_hidden=false \
  --tool-arg include_self=false \
  --tool-arg limit=20
```

Insights:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-ads-mcp \
  --method tools/call \
  --tool-name get_insights \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=0987654321 \
  --tool-arg level=campaign \
  --tool-arg date_range=LAST_MONTH \
  --tool-arg limit=10
```

Insights with custom date range:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-ads-mcp \
  --method tools/call \
  --tool-name get_insights \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=0987654321 \
  --tool-arg level=campaign \
  --tool-arg date_range=CUSTOM \
  --tool-arg start_date=2026-03-01 \
  --tool-arg end_date=2026-03-20 \
  --tool-arg limit=10
```

Keywords:

```bash
npx -y @modelcontextprotocol/inspector --cli \
  uv run flin-google-ads-mcp \
  --method tools/call \
  --tool-name get_keywords \
  --tool-arg customer_id=1234567890 \
  --tool-arg login_customer_id=0987654321 \
  --tool-arg date_range=LAST_90_DAYS \
  --tool-arg status=ENABLED \
  --tool-arg limit=25
```

## 3) End-to-end test in Claude (uvx)

Use this config:

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

Then ask Claude:

1. `Run health_check`
2. `List accessible customers`
3. `Get campaigns for customer 1234567890 with limit 5`
4. `Get campaign insights for last 30 days`

## 4) Common failures and fixes

`missing_configuration`:

- One or more required env vars are missing.
- Fix: compare with `.env.example`.

`PERMISSION_DENIED`:

- OAuth user/token is valid but lacks account access or API permissions.
- Fix: confirm account permissions and developer token access level.

`CUSTOMER_NOT_FOUND` or request errors:

- Wrong customer ID format or inaccessible account.
- Fix: use 10-digit ID (no `-`) and verify with `list_accessible_customers`.

## Recommended release gate

Before each release:

1. `python3 -m pytest`
2. `python3 -m compileall src`
3. `uv build`
4. Inspector smoke tests: `health_check`, `list_accessible_customers`, `get_customer_clients`, `get_campaigns`, `get_insights`, `get_keywords`
