"""Start the extracted release through its real manifest command and speak MCP."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ServerVersionMismatch(AssertionError):
    """PyPI metadata can precede propagation through its package index."""


def _version_mismatch_only(exc: Exception) -> bool:
    if isinstance(exc, ServerVersionMismatch):
        return True
    nested = getattr(exc, "exceptions", ())
    return bool(nested) and all(_version_mismatch_only(item) for item in nested)


async def smoke_with_retry(bundle, wheel, expected_version, attempts=1):
    for attempt in range(attempts):
        try:
            await smoke(bundle, wheel, expected_version)
            return
        except Exception as exc:
            if not _version_mismatch_only(exc) or attempt + 1 == attempts:
                raise
            print("Package index returned an older server; retrying in 10 seconds.")
            await asyncio.sleep(10)


async def smoke(
    bundle: Path, wheel: Path | None = None, expected_version: str | None = None
) -> None:
    with tempfile.TemporaryDirectory(prefix="flin-mcpb-") as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(bundle) as archive:
            for name in archive.namelist():
                assert not Path(name).is_absolute() and ".." not in Path(name).parts
            archive.extractall(root)
        manifest = json.loads((root / "manifest.json").read_text())
        config = manifest["server"]["mcp_config"]
        uv = shutil.which("uv")
        assert uv, "uv required for smoke testing"
        # Do not inherit any Google Ads credentials or local auth state.
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GOOGLE_ADS_")
        }
        env["GOOGLE_ADS_AUTH_FILE"] = str(root / "test-auth.json")
        if wheel is not None:
            # Pre-publication test only: substitute the built wheel for the PyPI dependency.
            # The shipped bundle and the post-publication test keep the PyPI requirement.
            project = root / "pyproject.toml"
            import tomllib

            requirement = tomllib.loads(project.read_text())["project"]["dependencies"][
                0
            ]
            project.write_text(
                project.read_text().replace(
                    requirement, f"flin-google-ads-mcp @ {wheel.resolve().as_uri()}"
                )
            )
        env.pop("VIRTUAL_ENV", None)
        args = [arg.replace("${__dirname}", str(root)) for arg in config["args"]]
        async with stdio_client(
            StdioServerParameters(command=uv, args=args, env=env)
        ) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                health = await session.call_tool("health_check", {})
                assert not health.isError
                payload = json.loads(health.content[0].text)
                assert payload["status"] == "missing_configuration", payload
                if (
                    expected_version is not None
                    and payload["server_version"] != expected_version
                ):
                    raise ServerVersionMismatch(
                        f"Expected server {expected_version}, received {payload['server_version']}"
                    )
                result = await session.list_tools()
                tools = {tool.name: tool for tool in result.tools}
                assert len(tools) == 17, sorted(tools)
                assert tools["get_campaigns"].annotations.readOnlyHint is True
                assert tools["clear_auth_token"].annotations.destructiveHint is True
                assert tools["connection_status"].annotations.readOnlyHint is True
                status = await session.call_tool("connection_status", {})
                assert not status.isError
                status_payload = json.loads(status.content[0].text)
                assert status_payload["configuration_status"] == "incomplete"
                assert status_payload["auth_status"] == "unknown"
                assert status_payload["live_access"] == "not_checked"
                assert status_payload["server_version"] == payload["server_version"]
                print(
                    f"MCPB smoke passed: server {payload.get('server_version')}, {len(tools)} tools, safe missing-configuration response."
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--expected-version")
    parser.add_argument("--attempts", type=int, choices=range(1, 7), default=1)
    options = parser.parse_args()
    asyncio.run(
        asyncio.wait_for(
            smoke_with_retry(
                options.bundle.resolve(),
                options.wheel,
                options.expected_version,
                options.attempts,
            ),
            timeout=180,
        )
    )
