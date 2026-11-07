# Privacy

This local MCP server sends OAuth consent/token requests and read-only Google Ads API requests to Google. The temporary browser callback listens only on your computer. Requested account/report data is returned over stdio to Claude Desktop (or your chosen MCP host) and can enter chat history and the host provider's processing. Reports may contain customer/account names, ad text, search terms and change-event user email addresses. Review your host's privacy and retention settings before querying data.

The server implements no separate analytics or telemetry and does not intentionally persist reports. Startup downloads code/dependencies from PyPI; package fetching uses the host/UV cache and requires network access. GitHub distributes the installer. These services see normal network/download metadata.

Configuration comes from extension settings/environment variables. Sensitive fields are marked sensitive for the host, but this server does not promise Keychain storage or encryption. Browser-created refresh tokens are stored as **unencrypted local JSON**, owner-only permissions `0600`, at `~/.config/flin-google-ads-mcp/auth.json` (or `GOOGLE_ADS_AUTH_FILE`). They survive restarts and server updates. Access tokens and pending OAuth state are held in process memory. Default `connection_status` reads local state without a network request; `check_live=true` explicitly contacts Google and returns no account data.

To disconnect, disable the extension, remove its stored credential fields, and revoke the OAuth application's access in your Google Account's third-party connections settings. `clear_auth_token` deletes only the local token file and cancels pending sign-in; it does not revoke Google authorization or erase an environment/settings override. If the server cannot start, delete that token file manually. Removing the extension alone may leave the file and chat history behind; manage host history separately. Ask your administrator to rotate shared credentials when appropriate.

[Security details](SECURITY.md) · [Support](SUPPORT.md) · [Google privacy policy](https://policies.google.com/privacy)
