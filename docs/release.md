# Release checklist

Every version-tag release automatically produces **both** a PyPI release and a Claude Desktop MCPB. There is no optional PyPI switch.

1. Update `pyproject.toml`, `src/flin_google_ads_mcp/__init__.py`, `manifest.json`, `desktop/pyproject.toml` (loader version) and installation instructions. Keep the starter's tested `>=0.1.12,<0.2` range unless its interface contract changes. Never expand the upper bound without compatibility checks.
2. Run `uv lock`, review dependency changes and commit `uv.lock`.
3. Run the release checks from a clean checkout:

```sh
uv sync --locked --extra dev
uv run --locked python -m pytest
uv export --locked --no-dev --no-emit-project --output-file /tmp/requirements.txt
uvx --python 3.12 pip-audit==2.10.1 -r /tmp/requirements.txt --no-deps --disable-pip
uv build
uv run --locked python scripts/build_mcpb.py
npx --yes @anthropic-ai/mcpb@2.1.2 validate manifest.json
uv run --locked python scripts/smoke_mcpb.py dist/flin-google-ads-mcp.mcpb --wheel dist/*.whl
```

4. Push the reviewed commit, check CI, tag that exact commit `vX.Y.Z` and push the tag.
5. The Release workflow performs these steps in order:
   - Test, audit and build the Python distributions and the MCPB; test startup with the built wheel before publication.
   - Publish the wheel and source distribution to PyPI using Trusted Publishing/OIDC.
   - Verify that PyPI serves exactly those distribution hashes and that the **unmodified** MCPB starts the newly published server from PyPI.
   - Publish the MCPB, its SHA-256 checksum and Python distributions as GitHub release assets.
6. A retry can be started using workflow dispatch on the same **tag**. Branch dispatches are rejected. Already published PyPI files are skipped, but their hashes must match the build artifacts. GitHub asset upload is retry-safe. Release runs are serialized.

Trusted Publisher: owner `flin-agency`, repository `flin-google-ads-mcp`, workflow `release.yml`, environment `pypi`. Do not add a manual approval requirement if releases must remain unattended.

The MCPB deliberately contains only mapped files in `scripts/build_mcpb.py`. Its root `pyproject.toml` comes from `desktop/pyproject.toml`, not the server project. No credentials, `.env`, local caches, bundled server source or runtime lockfile are shipped.

The installed launcher checks PyPI on each server start. Normal server updates require no new MCPB installation; an already running server takes the update on its next start. A new MCPB is still published with every version for new installations and launcher changes.

The builder emits both `flin-google-ads-mcp-X.Y.Z-mac.mcpb` and the byte-identical alias `flin-google-ads-mcp.mcpb`, each with a matching checksum. Use the explicit alias in smoke commands, not a wildcard that now matches two bundles. README links the existing latest alias, never a future versioned asset.

CI runs separately on `ubuntu-24.04`, `macos-15` (Apple Silicon) and `macos-15-intel`; Linux success does not establish Mac success. The smoke test extracts the package outside the source directory and calls MCP over stdio. Unit and update tests use synthetic credentials, not a real Google account. Neither CI nor that smoke test verifies the Claude installation UI or a customer's Google consent/account access.

After publishing, verify an existing installation against PyPI on restart and check that settings/token bytes are unchanged. The post-publication smoke retries briefly if PyPI's package index lags behind its release metadata; mismatches never count as a pass.
