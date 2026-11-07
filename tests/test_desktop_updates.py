"""Regression: an already installed bundle must load a new server on restart."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def _wheel(destination: Path, version: str) -> None:
    """Make a tiny offline test distribution with the real server package name."""
    distribution = f"flin_google_ads_mcp-{version}"
    info = f"{distribution}.dist-info"
    files = {
        "flin_google_ads_mcp/__init__.py": "",
        "flin_google_ads_mcp/server.py": (
            "import json, os, sys\nfrom pathlib import Path\n"
            f"def main():\n    print(json.dumps(dict(version={version!r}, customer=os.getenv('GOOGLE_ADS_CUSTOMER_ID'), token=Path(os.environ['GOOGLE_ADS_AUTH_FILE']).read_text())), flush=True)\n"
            f"    for line in sys.stdin:\n        print({version!r}, flush=True)\n"
        ),
        f"{info}/METADATA": f"Metadata-Version: 2.1\nName: flin-google-ads-mcp\nVersion: {version}\n",
        f"{info}/WHEEL": "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    files[f"{info}/RECORD"] = "".join(
        f"{path},,\n" for path in [*files, f"{info}/RECORD"]
    )
    with zipfile.ZipFile(
        destination / f"{distribution}-py3-none-any.whl", "w"
    ) as archive:
        for path, content in files.items():
            archive.writestr(path, content)


def test_existing_extension_updates_on_next_start_and_skips_prereleases(tmp_path):
    uv = shutil.which("uv")
    assert uv, "Install uv to run the desktop update integration test."
    installation = tmp_path / "installed extension"
    (installation / "desktop").mkdir(parents=True)
    shutil.copyfile(ROOT / "desktop/server.py", installation / "desktop/server.py")
    shutil.copyfile(ROOT / "desktop/pyproject.toml", installation / "pyproject.toml")
    links = tmp_path / "index"
    links.mkdir()
    manifest = json.loads((ROOT / "manifest.json").read_text())
    args = [
        arg.replace("${__dirname}", str(installation))
        for arg in manifest["server"]["mcp_config"]["args"]
    ]
    # Exercise the production launcher, using an isolated offline package source.
    args[1:1] = ["--offline", "--no-index", "--find-links", str(links)]
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("UV_", "GOOGLE_ADS_")) and key != "VIRTUAL_ENV"
    }
    env["UV_CACHE_DIR"] = str(tmp_path / "cache")
    env["UV_PYTHON_DOWNLOADS"] = "never"

    auth_file = tmp_path / "preserved-auth.json"
    auth_file.write_text('{"refresh_token":"synthetic-token"}')
    auth_file.chmod(0o600)
    original_auth = auth_file.read_bytes()
    env["GOOGLE_ADS_AUTH_FILE"] = str(auth_file)
    env["GOOGLE_ADS_CUSTOMER_ID"] = "1234567890"

    def start(offline_fallback=False):
        result = subprocess.run(
            [
                uv,
                *(
                    args
                    if not offline_fallback
                    else [
                        "run",
                        "--offline",
                        "--frozen",
                        "--no-config",
                        "--no-dev",
                        "--python",
                        "3.12",
                        "--directory",
                        str(installation),
                        "desktop/server.py",
                    ]
                ),
            ],
            env=env,
            input="",
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
        result_data = json.loads(result.stdout)
        assert result_data["customer"] == env["GOOGLE_ADS_CUSTOMER_ID"]
        assert result_data["token"] == original_auth.decode()
        return result_data["version"]

    original_launcher = (installation / "desktop/server.py").read_bytes()
    original_config = (installation / "pyproject.toml").read_bytes()
    _wheel(links, "0.1.12")
    assert start() == "0.1.12"
    running = subprocess.Popen(
        [uv, *args],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert json.loads(running.stdout.readline())["version"] == "0.1.12"
        _wheel(links, "0.1.13")
        _wheel(links, "0.1.14rc1")
        _wheel(links, "0.2.0")
        _wheel(links, "1.0.0")
        assert start() == "0.1.13"
        assert start(offline_fallback=True) == "0.1.13"
        running.stdin.write("still running\n")
        running.stdin.flush()
        assert running.stdout.readline().strip() == "0.1.12"
    finally:
        running.communicate(timeout=10)
    assert auth_file.read_bytes() == original_auth
    assert auth_file.stat().st_mode & 0o777 == 0o600
    assert (installation / "desktop/server.py").read_bytes() == original_launcher
    assert (installation / "pyproject.toml").read_bytes() == original_config
