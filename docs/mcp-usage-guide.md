# MCP Usage Guide

Use this guide when operating `flin-google-ads-mcp` from Claude or MCP Inspector.

Start with `connection_status`: this only reads local configuration and token presence. A token means `auth_status=unknown`, not verified access. Use `connection_status(check_live=true)` for an explicit status-only Google Ads API check, then `list_accessible_customers` to choose the account. Existing `health_check` and `auth_status` retain their original fields and are not account-access proofs.

## Recommended call order

1. Run `connection_status`
2. If it reports `unauthenticated`, run `get_auth_url`, complete Google consent in a browser on the same computer, and wait for the success message (the token is stored automatically)
3. Run `connection_status(check_live=true)`
4. Run `list_accessible_customers`
5. If working with an MCC, run `get_customer_clients` first
6. If you need a specific client by name, run `find_customer_clients`
7. For subaccounts, always pass:
- `customer_id` (client account)
- `login_customer_id` (manager account)
8. Then run data tools:
- `get_campaigns`
- `get_ads`
- `get_keywords`
- `get_search_terms`
- `get_insights`

For account-level spend totals, use `get_insights` with:
- `level=account` (or `level=customer`)
- `date_range=YESTERDAY` (or another supported range)

For metrics tools (`get_keywords`, `get_search_terms`, `get_insights`), use either a preset `date_range` or `date_range=CUSTOM` with `start_date` + `end_date`.

For daily search-term attribution, call `get_search_terms` with `segment_by_date=true`; each row then includes the actual `date` returned by Google Ads for that search term and metric segment.

## MCC and subaccount rules

- `list_accessible_customers` does not validate manager-header behavior for all operations.
- `get_customer_clients` is the correct source for account hierarchy.
- `find_customer_clients` is the fastest way to resolve a client ID from `descriptive_name`.
- `USER_PERMISSION_DENIED` on subaccount calls is usually:
- wrong `login_customer_id`
- missing OAuth rights
- inactive manager-client link

## Common error handling

`missing_configuration`:
- One or more required env vars are missing in MCP config.

`missing_auth` / `missing_refresh_token`:
- The refresh token is not in env and no local auth file exists yet.
- Run `get_auth_url`, complete Google consent on the same computer, then run `auth_status` after the browser confirms success. No code or URL copying is needed.

`USER_PERMISSION_DENIED`:
- Check the `customer_id` and `login_customer_id` pairing.
- Confirm OAuth user has access to both manager and client account.
- Confirm the account link is active in Google Ads UI.

`tool not loaded yet`:
- Restart Claude.
- Reload tools, then call again.

## Output quality checklist

- Always state which `customer_id` and `login_customer_id` were used.
- Do not infer account ownership from numeric IDs only.
- Use `descriptive_name` from `get_customer_clients`/`find_customer_clients` for identity claims.
- Do not label an account as empty before checking both:
- `get_campaigns` with `status=ALL`
- `get_insights` for a recent date range
