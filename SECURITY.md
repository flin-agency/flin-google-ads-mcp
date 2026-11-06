# Security

## Scope and trust boundaries

This is a local stdio MCP server. It does not accept arbitrary GAQL or execute shell commands. During OAuth sign-in only, it starts a temporary HTTP callback listener bound to loopback; the MCP transport remains stdio. Google Ads operations are search/list only. Authentication tools create an OAuth URL, receive its browser callback, and store/delete a local refresh token; these are explicitly annotated as state-changing tools.

The Google Ads OAuth scope itself is **not read-only**. Use an account with a read-only Google Ads role. Anyone controlling the desktop user, host application or environment can use its credentials. Manager/customer parameters are not account isolation boundaries. Ads text, URLs, account names and search terms are untrusted data and must not be treated as instructions.

Google receives API requests. Requested account data is returned to the MCP host and may become part of the conversation. Change events can include user email addresses. No separate telemetry or data collection is implemented by this server.

## Controls

- OAuth S256 PKCE, random state, loopback-only redirects, a ten-minute in-memory flow and one-use token exchange. Full redirect URLs must match the current state and redirect URI; raw codes are still supported and bound by PKCE. Automatic callbacks additionally require the expected Host and path, never log requests or reflect query values, and send no-store/no-referrer/CSP headers. The listener closes after success, denial, failure, cancellation or ten minutes. A new URL replaces the previous pending flow; restart requires a new flow. Clearing credentials cancels pending sign-in.
- Token files are created privately (0600), written atomically and protected against final-component symlinks; newly created auth directories use 0700. Existing overly permissive files are rejected. Parent directories and the local user account must be trusted.
- Credentials are never intentionally returned by tools. Untrusted SDK exception bodies are suppressed. Auth-generated tokens are stored as local plaintext with owner-only permissions; optional extension credentials are marked sensitive for secure host storage.
- Query inputs use enumerations, strict numeric IDs and controlled date/string filters. Result limits are bounded.
- Reproducible desktop bundle from an explicit file allowlist; no environment files, credentials, local caches or Git metadata. The repository lockfile pins the development/release-check environment. From extension 0.1.10, the launcher intentionally resolves the newest stable compatible server release from PyPI at each startup instead of including server source or a frozen runtime lock.
- CI tests, dependency auditing, restart-update regression tests and installation-protocol smoke testing. Each tagged release publishes to PyPI automatically; published distribution hashes and a real PyPI-based extension launch are verified before GitHub assets are released. Release workflows use pinned action commits and narrowly scoped permissions.

## Reporting

Please do not put credentials, authorization codes or private account data in public issues. Use GitHub's private vulnerability reporting feature if enabled; otherwise contact the repository maintainers privately to arrange disclosure.

## Limits

Tests and vulnerability databases cannot prove absence of vulnerabilities. The bundle is unsigned and requires network access at server startup. Automated tests use synthetic credentials; live OAuth consent, real Google Ads permissions and the Claude installation UI require a user-side final check. See [the review record](docs/security-review.md).

Automatic updates trust future stable releases on the configured official PyPI package. Bundle checksums cover the launcher, not future downloaded server code. Runtime dependencies may resolve differently from the development lockfile. Updating the server does not update the extension manifest or the host-managed Python/UV runtime.
