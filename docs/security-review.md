# Security review — 0.1.9

Reviewed on 2026-11-06. Scope: application source, OAuth flow, query construction, credential storage, runtime dependencies, release workflows and the macOS MCPB contents. This is an engineering review with automated checks, not an independent penetration-test certification.

## Findings and fixes

| Finding | Resolution |
| --- | --- |
| OAuth authorization had no state or PKCE binding | Added random state, S256 PKCE, loopback redirect validation, ten-minute expiry and single-use pending flow |
| Token file was written before chmod, with non-atomic replacement and symlink following | Private temporary file from creation, atomic replacement, private new auth directory, no-follow reads, permission/owner checks |
| SDK exceptions could return sensitive response details to the model | Removed raw SDK/HTTP exception messages from tool responses; secret-bearing dataclass fields hidden from repr |
| ID normalization silently discarded arbitrary text; string filters accepted backslashes | Reject unexpected characters; retain documented numeric ID separators; test malformed/injection inputs |
| Existing local dependency resolution contained known advisories in nine packages | Updated runtime dependencies, raised direct dependency minimums, committed the hashed lockfile; zero known advisories in the checked Python 3.12/3.13 resolutions |
| No constrained desktop bundle or GitHub release artifact | Added explicit allowlist, deterministic MCPB, SHA-256 companion and native sensitive credential fields |
| Release permissions and action versions were not constrained | Read-only default token, write permission only for release publishing, pinned action commits, locked installs; PyPI publishing requires explicit dispatch |

## Verification

- 76 automated tests passed, including OAuth expiry/state/replay, PKCE challenge, file permissions, symlink refusal, failed-write preservation, error non-disclosure, input validation and deterministic packaging.
- The extracted MCPB was installed into a fresh environment on Apple Silicon macOS using Python 3.12. Its manifest command completed the MCP initialization handshake, advertised all 16 tools with appropriate annotations, and returned an expected missing-configuration response without using real credentials.
- Official `@anthropic-ai/mcpb` 2.1.2 manifest validation passed.
- `pip-audit` 2.10.1 reported no known vulnerabilities for the locked runtime requirements under Python 3.12 and 3.13 at review time. This is database coverage for those resolutions, not a guarantee about all platforms or future advisories.
- Python wheel and source distribution build, source compilation and actionlint workflow validation passed.
- Secret scanning of the working source and 96 text blobs from reachable Git history produced only reviewed test/example placeholders. No personal credentials are included in the MCPB allowlist.
- Bandit findings were manually reviewed: B105 matched the public token endpoint and status literals; B310 uses the constant HTTPS Google token endpoint; B608 flags GAQL string construction, whose interpolated values pass the reviewed validators. These findings are documented, not represented as a clean automated Bandit scan.

## Remaining boundaries

- Real Google consent, real account authorization and installation through the Claude Desktop UI were not exercised. `health_check` alone does not validate live access.
- Intel Mac execution was not tested locally; the UV bundle delegates architecture-specific dependency selection to the host runtime.
- Google Ads exposes a broad OAuth scope. Read-only enforcement here is in the server's available operations; a read-only Google Ads user role provides an additional boundary.
- Local auth files are plaintext with owner-only permissions. A compromised local account or host application remains outside this protection.
- The bundle is unsigned and downloads dependencies/Python on first launch. The runtime lock does not freeze the host-managed UV/Python runtime or isolated build-backend dependencies.
