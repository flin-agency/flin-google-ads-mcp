# Claude Desktop on macOS

1. Download `flin-google-ads-mcp-0.1.11-mac.mcpb` from the [GitHub release](https://github.com/flin-agency/flin-google-ads-mcp/releases/tag/v0.1.11).
2. Use a current Claude Desktop version supporting MCPB manifest 0.4 and the UV runtime. Open **Settings → Extensions → Advanced settings → Install Extension…** and select the file. Double-clicking the file is also supported by compatible versions.
3. Enter your own Google Ads developer token, OAuth **Desktop app** client ID and client secret. Optionally enter your manager/customer IDs and an existing refresh token.
4. Enable the extension. Claude manages Python 3.12 and checks PyPI for the newest stable compatible server release on each server start; internet access is required. This is not an offline installer.
5. If no refresh token was supplied, ask Claude to run `get_auth_url`, open the returned Google consent URL **on the same Mac**, and sign in within 10 minutes. Keep Claude and the extension running. The browser returns to a temporary local callback and shows a success message; the refresh token is saved automatically. No URL or code needs to be copied.
6. Ask Claude to run `auth_status` and `health_check`, then `list_accessible_customers` to verify real account access. Select the correct customer account and run your first report. These checks also apply when you supplied an existing refresh token.

Access tokens are refreshed automatically by the Google client using the stored refresh token, including after restarting Claude. You only need to sign in again if Google expires or revokes the refresh token. Never paste your client secret or refresh token into a chat. An existing refresh token belongs in the extension's sensitive configuration field; it takes precedence over the local token file, so remove an outdated value there before signing in again.

If sign-in is cancelled, fails, or times out, run `get_auth_url` again. `auth_status` includes `oauth_flow_status` (`waiting_for_browser`, `stored`, `denied`, `expired`, `failed`, or `cancelled`). The callback listens only on this Mac, uses an available port, and closes after completion or at the ten-minute deadline. `save_refresh_token_from_code` remains available only as a legacy manual fallback.

## What gets installed

The same launcher bundle supports Apple Silicon and Intel Macs through the host-managed Python runtime. No administrator permissions or manual Claude configuration edits are required. Credentials are entered after installation; no personal credentials are included in the download.

The bundle contains a small launcher and a separate dependency manifest. It runs `uv run --upgrade-package flin-google-ads-mcp --prerelease disallow` against PyPI, with Python 3.12. No old server source or frozen runtime lock is embedded. The repository lockfile remains in use for development and release checks. Developer tokens, client secrets and optional refresh tokens are marked sensitive in the manifest for secure storage by the host. Tokens created by the auth tools are stored separately in `~/.config/flin-google-ads-mcp/auth.json`, a local, unencrypted file accessible only to its owner (0600).

`health_check` checks configuration and client initialization; it does not prove live Google Ads access. Use `list_accessible_customers` for that final check.

## Automatic updates

Install extension 0.1.10 or newer once. Each subsequent server start checks PyPI and installs the newest stable server version compatible with Python 3.12. This happens when Claude starts the server, such as after restarting Claude or disabling and re-enabling the extension. A running session is not interrupted and does not hot-reload code. Credentials and the local auth file are preserved.

The version shown in Claude's extension settings describes the launcher. Ask for `health_check` and inspect `server_version` to see the actual running PyPI server version.

The original 0.1.9 extension runs bundled source and cannot gain this behavior from PyPI. Replace it with the current extension once. Future changes to launcher configuration, required Python runtime or host permissions may still require a new extension; normal server releases do not.

The launcher intentionally follows future stable PyPI releases rather than freezing their code and dependencies to the original bundle checksum. Only our normal PyPI package is requested; release tests verify the public PyPI installation before making each new MCPB available. If PyPI or the network is unavailable, startup may fail; there is no silent fallback to a bundled old server.

## Verify the download (optional)

Download the adjacent `.mcpb.sha256` file into the same folder, then run:

```sh
shasum -a 256 -c flin-google-ads-mcp-0.1.11-mac.mcpb.sha256
```

The checksum detects corruption; this bundle is not code-signed or notarized.

## Access and removal

Google's Ads OAuth scope is broader than read-only; this server exposes no Ads mutation tools. Use a Google Ads user with a read-only account role for least privilege. Manager and customer IDs choose accounts; they are not an access allowlist.

Disable/remove the extension in Claude settings. `clear_auth_token` deletes only the file-based token; it does not revoke Google authorization or remove a refresh token supplied in extension settings. Remove that field separately and revoke access in your Google account when needed.

## References

- [Official MCPB format and UV runtime](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md)
- [Claude Desktop local server installation](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)

- [UV package-specific upgrades and cache refresh](https://docs.astral.sh/uv/reference/cli/#uv-run)
