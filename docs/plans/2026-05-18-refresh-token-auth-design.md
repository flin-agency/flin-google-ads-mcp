# Refresh Token Auth Design

## Goal

Remove `GOOGLE_ADS_REFRESH_TOKEN` from the required MCP client configuration while keeping the existing Google Ads read-only tools unchanged for normal use.

## Architecture

- Keep `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, and `GOOGLE_ADS_CLIENT_SECRET` as environment-backed runtime settings.
- Make `GOOGLE_ADS_REFRESH_TOKEN` optional and treat it as a backwards-compatible override.
- Add a local auth store at `~/.config/flin-google-ads-mcp/auth.json`, configurable with `GOOGLE_ADS_AUTH_FILE`.
- Resolve the refresh token in this order:
  1. `GOOGLE_ADS_REFRESH_TOKEN`
  2. stored token file
  3. structured auth/configuration error

## MCP Tools

- `auth_status()` reports whether credentials are ready and where the refresh token would be loaded from. It never returns secret values.
- `get_auth_url()` builds a Google OAuth consent URL for the Google Ads scope.
- `save_refresh_token_from_code(code)` exchanges an OAuth authorization code for a refresh token and stores it locally.
- `clear_auth_token()` deletes the stored refresh token.

## OAuth Flow

The MCP returns a Google consent URL using the configured client ID/secret and a loopback redirect URI. The user signs in, copies the `code` query parameter or the full redirected URL, and passes it to `save_refresh_token_from_code`.

## Error Handling

- Missing client/developer credentials still show as missing configuration.
- Missing refresh token shows an actionable auth message that points to `get_auth_url`.
- Token exchange failures are returned as structured errors without exposing secrets.
- Auth status responses include only booleans, source labels, and file paths.

## Testing

- Config tests verify that `GOOGLE_ADS_REFRESH_TOKEN` is no longer required.
- Auth tests cover URL generation, code extraction, token file save/load/delete, env precedence, and token exchange handling through a monkeypatched HTTP call.
- Server tool tests cover `auth_status` and missing-token health behavior.
