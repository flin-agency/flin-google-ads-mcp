# Support

For setup, use the [Mac guide](docs/claude-desktop-mac.md). Obtain credentials from your administrator/password manager; never paste secrets into chat or a public issue.

- Start with `connection_status`. `incomplete` means missing/invalid local configuration; `unknown` authentication with `not_checked` access is expected when a token exists but no live test ran.
- For sign-in, run `get_auth_url`, open the Google link on the same computer and finish within ten minutes. The callback saves the token automatically. If it fails/expires, run it again. A stale refresh-token field overrides a new file-based token: remove the stale field first.
- Test actual access with `connection_status(check_live=true)`, then `list_accessible_customers`. API/developer-token or account permissions can fail even after Google sign-in succeeds. Select the correct customer and, where necessary, manager account.
- Update on restart. Check `connection_status.server_version`; Claude's extension version is the starter version and can differ. Import the current package once for the bounded 0.1.x update policy or changed starter/settings.
- If a package download fails, restore network access and retry; there is no automatic offline fallback. An advanced cached-installation fallback is documented in the Mac guide. Keep credentials and settings intact.

Open a [GitHub issue](https://github.com/flin-agency/flin-google-ads-mcp/issues) with macOS version, Apple Silicon/Intel, Claude version, starter version, server version and redacted error text. Do not include tokens, client secrets, callback URLs/codes, auth files, customer IDs/names, ad data or full logs. See [SECURITY.md](SECURITY.md) for private vulnerability reporting and [PRIVACY.md](PRIVACY.md) for revocation/cleanup.
