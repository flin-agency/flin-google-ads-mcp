# Claude Desktop on macOS

1. Download `flin-google-ads-mcp-0.1.9-mac.mcpb` from the [GitHub release](https://github.com/flin-agency/flin-google-ads-mcp/releases/tag/v0.1.9).
2. Use a current Claude Desktop version supporting MCPB manifest 0.4 and the UV runtime. Open **Settings → Extensions → Advanced settings → Install Extension…** and select the file. Double-clicking the file is also supported by compatible versions.
3. Enter your own Google Ads developer token, OAuth **Desktop app** client ID and client secret. Optionally enter your manager/customer IDs and an existing refresh token.
4. Enable the extension. Claude manages Python 3.12 and downloads the locked dependencies on first launch; internet access is required. This is not an offline installer.
5. If no refresh token was supplied, ask Claude to run `get_auth_url`, open the Google consent URL, and sign in. Copy the **complete URL** from the browser address bar after redirection to `http://127.0.0.1:8080/`. A connection error on that page is expected: this server does not open a web listener.
6. Within 10 minutes, pass that URL to `save_refresh_token_from_code` in the same running server session. Then run `auth_status` and `health_check`.

The authorization code is short-lived and single-use, but passing it through a chat can put it in chat history. An existing refresh token can instead be entered in the extension's sensitive configuration field, avoiding token entry in chat. Never paste your client secret or refresh token into a chat.

## What gets installed

The same source bundle supports Apple Silicon and Intel Macs through the host-managed Python runtime. No administrator permissions or manual Claude configuration edits are required. Credentials are entered after installation; no personal credentials are included in the download.

The bundle uses an explicit file allowlist, a committed `uv.lock` with package hashes, and `uv run --locked`. Developer tokens, client secrets and optional refresh tokens are marked sensitive in the manifest for secure storage by the host. Tokens created by the auth tools are stored separately in `~/.config/flin-google-ads-mcp/auth.json`, a local, unencrypted file accessible only to its owner (0600).

`health_check` checks configuration and client initialization; it does not prove live Google Ads access. Use `list_accessible_customers` for that final check.

## Verify the download (optional)

Download the adjacent `.mcpb.sha256` file into the same folder, then run:

```sh
shasum -a 256 -c flin-google-ads-mcp-0.1.9-mac.mcpb.sha256
```

The checksum detects corruption; this bundle is not code-signed or notarized.

## Access and removal

Google's Ads OAuth scope is broader than read-only; this server exposes no Ads mutation tools. Use a Google Ads user with a read-only account role for least privilege. Manager and customer IDs choose accounts; they are not an access allowlist.

Disable/remove the extension in Claude settings. `clear_auth_token` deletes only the file-based token; it does not revoke Google authorization or remove a refresh token supplied in extension settings. Remove that field separately and revoke access in your Google account when needed.

## References

- [Official MCPB format and UV runtime](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md)
- [Claude Desktop local server installation](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
