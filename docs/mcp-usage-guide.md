# MCP Usage Guide

Use this guide when operating `flin-google-ads-mcp` from Claude or MCP Inspector.

## Recommended call order

1. Run `health_check`
2. Run `list_accessible_customers`
3. If working with an MCC, run `get_customer_clients` first
4. For subaccounts, always pass:
- `customer_id` (client account)
- `login_customer_id` (manager account)
5. Then run data tools:
- `get_campaigns`
- `get_ads`
- `get_keywords`
- `get_insights`

## MCC and subaccount rules

- `list_accessible_customers` does not validate manager-header behavior for all operations.
- `get_customer_clients` is the correct source for account hierarchy.
- `USER_PERMISSION_DENIED` on subaccount calls is usually:
- wrong `login_customer_id`
- missing OAuth rights
- inactive manager-client link

## Common error handling

`missing_configuration`:
- One or more required env vars are missing in MCP config.

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
- Use `descriptive_name` from `get_customer_clients` for identity claims.
- Do not label an account as empty before checking both:
- `get_campaigns` with `status=ALL`
- `get_insights` for a recent date range
