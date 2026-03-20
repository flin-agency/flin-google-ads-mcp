# flin-google-ads-mcp Design (Read-only MVP)

## Goal

Ship a public MCP package (`flin-google-ads-mcp`) that can be executed with `uvx` and safely used by others for read-only Google Ads analysis.

## Architecture

- Python package with console entrypoint: `flin-google-ads-mcp`
- MCP runtime: `mcp.server.fastmcp.FastMCP` over stdio transport
- Google Ads transport: official `google-ads` Python client using OAuth credentials from env vars

## Tools (read-only)

- `health_check`
- `list_accessible_customers`
- `get_campaigns`
- `get_ad_groups`
- `get_ads`
- `get_insights`

No tool performs create/update/delete operations.

## Data flow

1. Tool call arrives via MCP stdio.
2. Server validates and resolves config/env.
3. Tool builds safe GAQL query from constrained inputs.
4. Query executes through Google Ads API.
5. Result is serialized into stable JSON payload.

## Error handling

- Missing env vars produce explicit configuration errors.
- Google Ads API failures are returned in structured error payloads.
- Limits are clamped to avoid overly expensive requests.

## Testing

- Unit tests for config validation and query builder safety.
- Local interactive testing through MCP Inspector.

## Security

- No credential storage in code.
- No write endpoints.
- Inputs constrained by allowlists for status, date ranges, and levels.
