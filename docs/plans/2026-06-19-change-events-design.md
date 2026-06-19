# Google Ads Change Events Design

## Goal

Expose Google Ads account change history through the read-only MCP server.

## Design

Add a `get_change_events` MCP tool backed by the Google Ads `change_event` resource. The tool stays read-only and follows the existing pattern: validation and GAQL query construction in `google_ads.py`, response shaping in `server.py`, and focused tests in `tests/test_query_builders.py` and `tests/test_server_tools.py`.

The tool accepts `customer_id`, `start_date`, `end_date`, optional `resource_type`, optional `user_email`, `limit`, and `login_customer_id`. Dates use `YYYY-MM-DD` to match existing custom-date validation. Google Ads requires a `change_event.change_date_time` filter within the past 30 days and a `LIMIT`; the server validates only date format/order locally and lets the API enforce recency.

Returned events include event resource name, change timestamp, changed resource name/type, operation, client type, user email, changed field paths, and lightweight old/new values for those changed paths when they can be extracted from the changed resource payload.

## Error Handling

Invalid dates, invalid resource types, empty user emails, and invalid limits return the existing structured MCP error payload. Google Ads API failures continue through `format_google_ads_error`.

## Testing

Unit tests cover query construction, filters, validation, and server response formatting from synthetic rows.
