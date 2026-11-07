# Claude Desktop on macOS

1. Download [flin-google-ads-mcp.mcpb](https://github.com/flin-agency/flin-google-ads-mcp/releases/latest/download/flin-google-ads-mcp.mcpb), for Apple Silicon M1 or newer and Intel Macs. Versioned downloads remain on the [release page](https://github.com/flin-agency/flin-google-ads-mcp/releases/latest).
2. Use a current Claude Desktop version supporting MCPB manifest 0.4 and the UV runtime. Open **Settings → Extensions → Advanced settings → Install Extension…** and select the file. Double-clicking the file is also supported by compatible versions.
3. Enter the Google Ads credentials supplied by your administrator/password manager: developer token, OAuth **Desktop app** client ID and client secret. Optionally enter your manager/customer IDs and an existing refresh token.
4. Enable the extension. Claude manages Python 3.12 and checks PyPI for the newest stable server in the starter's supported range on each server start; internet access is required. This is not an offline installer.
5. If no refresh token was supplied, ask Claude to run `get_auth_url`, open the returned Google consent URL **on the same Mac**, and sign in within 10 minutes. Keep Claude and the extension running. The browser returns to a temporary local callback and shows a success message; the refresh token is saved automatically. No URL or code needs to be copied.
6. Ask Claude to run `connection_status`, then `connection_status(check_live=true)` and `list_accessible_customers` to verify real account access. Select the correct customer account and run your first report. These checks also apply when you supplied an existing refresh token.

Access tokens are refreshed automatically by the Google client using the stored refresh token, including after restarting Claude. You only need to sign in again if Google expires or revokes the refresh token. Never paste your client secret or refresh token into a chat. An existing refresh token belongs in the extension's sensitive configuration field; it takes precedence over the local token file, so remove an outdated value there before signing in again.

If sign-in is cancelled, fails, or times out, run `get_auth_url` again. `auth_status` includes `oauth_flow_status` (`waiting_for_browser`, `stored`, `denied`, `expired`, `failed`, or `cancelled`). The callback listens only on this Mac, uses an available port, and closes after completion or at the ten-minute deadline. `save_refresh_token_from_code` remains available only as a legacy manual fallback.

## What gets installed

The same launcher bundle supports Apple Silicon and Intel Macs through the host-managed Python runtime. No administrator permissions or manual Claude configuration edits are required. Credentials are entered after installation; no personal credentials are included in the download.

The bundle contains a small launcher and a separate dependency manifest. It runs `uv run --upgrade-package flin-google-ads-mcp --prerelease disallow` against PyPI, with Python 3.12. No old server source or frozen runtime lock is embedded. The repository lockfile remains in use for development and release checks. Developer tokens, client secrets and optional refresh tokens are marked sensitive in the manifest; their storage is controlled by Claude Desktop, not encrypted by this server. Tokens created by the auth tools are stored separately in `~/.config/flin-google-ads-mcp/auth.json`, a local, unencrypted file accessible only to its owner (0600).

`connection_status` reads local configuration/token state only by default: `configuration_status` is `configured` or `incomplete`, `auth_status` is `unknown` when a token merely exists, and `live_access` is `not_checked`. No browser, Google request or token refresh occurs. An explicit `check_live=true` calls Google's accessible-customer endpoint and returns only status, never account data. Failures remain `auth_status=unknown` because API permission and authentication failures are not interchangeable.

Existing `auth_status` and `health_check` remain available. `auth_status` describes local token presence; `health_check` initializes the SDK and can refresh credentials, but neither proves account/report access. Successful live status does not guarantee access to every account; use `list_accessible_customers` and a report on the selected account.

## Automatic updates

Starter 0.1.12 uses Python 3.12 and the server range `>=0.1.12,<0.2`. Within 0.1.x we preserve the `flin_google_ads_mcp.server:main` entry point, stdio MCP transport, settings/environment keys and local auth-file format; tool additions remain backwards compatible. The 0.2 boundary is deliberately excluded because this project is pre-1.0: a future incompatible entry point, configuration or credential format requires a new starter. This is a maintained compatibility policy, not a claim that all future releases are automatically safe.

Each server start checks PyPI for the newest stable release in that range. Prereleases are excluded. Restart Claude or disable and re-enable the extension to update. Running sessions do not hot-reload; settings and the local token file are not rewritten by updates. Tests exercise restarting an existing installation, preserving synthetic settings/token data, leaving a running process untouched and rejecting 0.2/1.x and prereleases.

The version shown in Claude's extension settings describes the starter. Use `connection_status.server_version` (or the existing `health_check.server_version`) to see the actual server version.

Extensions 0.1.10/0.1.11 automatically load the new server but their installed dependency range has no upper bound. **Import the current MCPB once to apply the bounded range.** Extension 0.1.9 also requires replacement because it runs bundled source. Keep existing configuration when prompted; record your field names in your password manager before any manual removal. Normal compatible server updates need no further package import; starter/UI/runtime changes can require one.

## Network failure and fallback

The network/cache strategy is unchanged: the starter checks PyPI on every start and may fail if the index/network is unavailable. There is no hidden fallback and the installer is not offline. First restore connectivity and retry. Do not remove credentials or reauthorize to fix a package-download failure.

Advanced manual fallback, only for an installation that already started successfully and still has its lockfile, Python and dependencies cached: run the following from a terminal with the same credential environment supplied securely. It uses the already resolved installation without checking for updates; it can fail if the cache is incomplete. Return to normal online startup afterwards. This is not a Claude settings toggle.

```sh
uv run --offline --frozen --no-config --no-dev --python 3.12 --directory /path/to/installed-extension desktop/server.py
```

[Support](../SUPPORT.md) explains what to report; do not share credential files or full logs containing account data.

## Verify the download (optional)

Download the adjacent `.mcpb.sha256` file into the same folder, then run:

```sh
shasum -a 256 -c flin-google-ads-mcp.mcpb.sha256
```

The checksum detects corruption; this bundle is not code-signed or notarized.

## Access and removal

Google's Ads OAuth scope is broader than read-only; this server exposes no Ads mutation tools. Use a Google Ads user with a read-only account role for least privilege. Manager and customer IDs choose accounts; they are not an access allowlist.

Disable/remove the extension in Claude settings. `clear_auth_token` deletes only the file-based token; it does not revoke Google authorization or remove a refresh token supplied in extension settings. Remove that field separately and revoke access in your Google account when needed.

## References

- [Official MCPB format and UV runtime](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md)
- [Claude Desktop local server installation](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)

- [UV package-specific upgrades and cache refresh](https://docs.astral.sh/uv/reference/cli/#uv-run)
