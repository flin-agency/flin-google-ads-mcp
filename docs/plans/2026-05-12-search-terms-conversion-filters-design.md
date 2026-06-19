# Search Terms And Conversion Filters Design

## Goal

Extend the read-only Google Ads MCP with:
- a new `get_search_terms` tool backed by `search_term_view`
- optional conversion-action filters for `get_insights`, `get_keywords`, and `get_search_terms`

## API Surface

### New tool

`get_search_terms(...)` will mirror the shape of `get_keywords(...)` where practical:
- `customer_id`
- `campaign_id`
- `ad_group_id`
- `status`
- `date_range`
- `start_date`
- `end_date`
- `conversion_action_id`
- `conversion_action_name`
- `limit`
- `login_customer_id`

### New optional filter parameters

The following optional parameters will be added to:
- `get_insights`
- `get_keywords`
- `get_search_terms`

Parameters:
- `conversion_action_id: str | None = None`
- `conversion_action_name: str | None = None`

Rules:
- If neither is set, behavior remains unchanged.
- If `conversion_action_id` is set, filter exactly by conversion action id.
- If `conversion_action_name` is set, filter by conversion action name.
- If both are set, the tool returns a validation error.

## Query Design

Add centralized validation and filter construction in `google_ads.py`:
- normalize conversion-action ids with the existing numeric id style
- reject empty conversion-action names
- build a reusable conversion filter clause

GAQL strategy:
- use `segments.conversion_action` when filtering by id
- use `segments.conversion_action_name` when filtering by name

The filter builder will be reused by:
- `build_insights_query(...)`
- `build_keywords_query(...)`
- new `build_search_terms_query(...)`

## Tool Output

`get_search_terms` will return stable JSON aligned with the existing tool style:
- campaign/ad group identifiers and names
- search term text
- status fields when available from the underlying resource joins
- metrics payload via the existing `_metrics_payload(...)`

The response payload will echo:
- `date_range`
- `start_date`
- `end_date`
- `conversion_action_id`
- `conversion_action_name`

## Error Handling

Validation errors:
- reject requests that provide both conversion-action filters
- reject blank conversion-action names
- reuse normalized numeric-id validation for `conversion_action_id`

Operational errors:
- continue returning structured Google Ads errors through `_error_payload(...)`

## Testing

Add unit coverage for:
- conversion filter validation rules
- query builder output for id and name filters
- `get_search_terms` server serialization
- propagation of new response echo fields on all affected tools

## Scope Boundaries

This change does not add:
- generic arbitrary GAQL execution
- write operations
- multi-filter lists for conversion actions
