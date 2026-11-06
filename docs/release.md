# Release checklist

1. Update `pyproject.toml`, `src/flin_google_ads_mcp/__init__.py`, `manifest.json` and versioned installation links.
2. Run `uv lock`, review dependency changes and commit `uv.lock`.
3. Run the release checks:

```sh
uv sync --locked --extra dev
uv run --locked python -m pytest
uv export --locked --no-dev --no-emit-project --output-file /tmp/requirements.txt
uvx --python 3.12 pip-audit==2.10.1 -r /tmp/requirements.txt --no-deps --disable-pip
uv build
uv run --locked python scripts/build_mcpb.py
npx --yes @anthropic-ai/mcpb@2.1.2 validate manifest.json
uv run --locked python scripts/smoke_mcpb.py dist/*.mcpb
```

4. Push the reviewed commit, wait for CI on Linux and macOS, then tag that exact commit `vX.Y.Z` and push the tag.
5. The Release workflow tests the tag, builds the MCPB with checksum and Python packages, and publishes them as GitHub release assets. Verify the asset download and checksum.
6. Optionally publish to PyPI by manually running Release on that tag with `publish_pypi` selected. Tag pushes do not publish to PyPI automatically. The trusted publisher remains `flin-agency/flin-google-ads-mcp`, workflow `release.yml`, environment `pypi`.

The bundle deliberately contains only files listed in `scripts/build_mcpb.py`. Do not package the repository directory wholesale. User credentials, local caches and `.env` files must never be release assets. The bundle is unsigned, and its UV runtime downloads the locked runtime dependencies on first launch.
