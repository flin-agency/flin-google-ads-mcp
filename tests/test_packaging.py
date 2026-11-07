from __future__ import annotations

from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_mcp_dependency_keeps_fastmcp_compatible_major_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    mcp_requirement = next(
        dependency
        for dependency in project["dependencies"]
        if dependency.startswith("mcp")
    )

    assert mcp_requirement == "mcp>=1.30.0,<2"


def test_bundle_is_reproducible_and_contains_only_allowed_files(tmp_path):
    import hashlib
    import importlib.util
    import json
    import zipfile

    spec = importlib.util.spec_from_file_location(
        "build_mcpb", ROOT / "scripts/build_mcpb.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bundle = module.build(output_dir=tmp_path)
    first = bundle.read_bytes()
    alias = tmp_path / "flin-google-ads-mcp.mcpb"
    assert alias.read_bytes() == first
    assert (
        alias.with_suffix(".mcpb.sha256").read_text()
        == f"{hashlib.sha256(first).hexdigest()}  {alias.name}\n"
    )
    assert module.build(output_dir=tmp_path).read_bytes() == first
    assert (
        bundle.with_suffix(".mcpb.sha256")
        .read_text()
        .startswith(hashlib.sha256(first).hexdigest())
    )
    with zipfile.ZipFile(bundle) as archive:
        assert set(archive.namelist()) == set(module.FILES)
        assert archive.testzip() is None
        manifest = json.loads(archive.read("manifest.json"))
        assert "--upgrade-package" in manifest["server"]["mcp_config"]["args"]
        assert "--locked" not in manifest["server"]["mcp_config"]["args"]
        for name in ("developer_token", "client_secret", "refresh_token"):
            assert manifest["user_config"][name]["sensitive"] is True
        assert "desktop/server.py" in archive.namelist()
        assert "uv.lock" not in archive.namelist()
        assert not any(name.startswith("src/") for name in archive.namelist())
        project = tomllib.loads(archive.read("pyproject.toml").decode())
        assert project["project"]["name"] == "flin-google-ads-desktop-loader"
        assert project["project"]["dependencies"] == [
            "flin-google-ads-mcp>=0.1.12,<0.2"
        ]
