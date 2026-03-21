# Release Checklist

## One-time setup

1. Create PyPI project: `flin-google-ads-mcp`
2. Configure Trusted Publishing in PyPI:
- GitHub owner: `flin-agency`
- Repository: `flin-google-ads-mcp`
- Workflow: `release.yml`
- Environment: `pypi`
3. Ensure GitHub Actions is enabled for the repository

## Before each release

1. Update version in `pyproject.toml`
2. Run local checks:

```bash
uv sync --extra dev
python3 -m pytest
python3 -m compileall src
uv build
```

3. Commit and tag:

```bash
git add -A
git commit -m "release: vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

## After release

1. Verify GitHub workflow `Release` succeeded
2. Verify package appears on PyPI
3. Smoke test with:

```bash
uvx flin-google-ads-mcp@latest --help
```

## If history was rewritten (e.g. ID redaction)

After a force-push that rewrites `main` and tags, existing local clones must be resynced or recreated.

Recommended clean re-sync:

```bash
git fetch --all --prune --tags
git checkout main
git reset --hard origin/main
```

Alternative: re-clone the repository.
