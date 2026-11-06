"""Start the extracted release through its real manifest command and speak MCP."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke(bundle: Path) -> None:
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
        subprocess.run(
            [
                uv,
                "sync",
                "--project",
                str(root),
                "--locked",
                "--no-dev",
                "--no-editable",
                "--python",
                "3.12",
            ],
            env=env,
            check=True,
        )
        args = [arg.replace("${__dirname}", str(root)) for arg in config["args"]]
        async with stdio_client(
            StdioServerParameters(command=uv, args=args, env=env)
        ) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                result = await session.list_tools()
                tools = {tool.name: tool for tool in result.tools}
                assert len(tools) == 16, sorted(tools)
                assert tools["get_campaigns"].annotations.readOnlyHint is True
                assert tools["clear_auth_token"].annotations.destructiveHint is True
                health = await session.call_tool("health_check", {})
                assert not health.isError
                payload = json.loads(health.content[0].text)
                assert payload["status"] == "missing_configuration", payload
                print(
                    f"MCPB smoke passed: {len(tools)} tools, safe missing-configuration response."
                )


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(smoke(Path(sys.argv[1]).resolve()), timeout=180))
