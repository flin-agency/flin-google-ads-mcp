"""Build a reproducible MCPB from an explicit allowlist, never the working tree."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "manifest.json",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "docs/claude-desktop-mac.md",
    "docs/security-review.md",
    "desktop/server.py",
    "src/flin_google_ads_mcp/__init__.py",
    "src/flin_google_ads_mcp/auth.py",
    "src/flin_google_ads_mcp/config.py",
    "src/flin_google_ads_mcp/google_ads.py",
    "src/flin_google_ads_mcp/server.py",
)


def build(root: Path = ROOT, output_dir: Path | None = None) -> Path:
    manifest = json.loads((root / "manifest.json").read_text())
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    if manifest["version"] != project["version"]:
        raise ValueError("Manifest and project versions differ.")
    output_dir = output_dir or root / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"flin-google-ads-mcp-{project['version']}-mac.mcpb"
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in sorted(FILES):
            path = root / name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Missing or unsafe bundle input: {name}")
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, path.read_bytes())
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".mcpb.sha256").write_text(
        f"{digest}  {destination.name}\n"
    )
    return destination


if __name__ == "__main__":
    print(build())
