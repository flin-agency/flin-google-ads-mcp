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

    assert mcp_requirement == "mcp>=1.6.0,<2"
