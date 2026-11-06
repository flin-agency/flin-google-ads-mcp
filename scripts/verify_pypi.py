"""Verify that PyPI serves the exact distributions built for this release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
import tomllib
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def verify(dist: Path = Path("dist")) -> None:
    version = tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
    distributions = [*dist.glob("*.whl"), *dist.glob("*.tar.gz")]
    if len(distributions) != 2:
        raise RuntimeError("Expected exactly one wheel and one source distribution.")
    expected = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in distributions
    }
    url = f"https://pypi.org/pypi/flin-google-ads-mcp/{version}/json"
    for attempt in range(12):
        try:
            with urlopen(url, timeout=15) as response:
                payload = json.load(response)
            actual = {
                item["filename"]: item["digests"]["sha256"] for item in payload["urls"]
            }
            if all(actual.get(name) == digest for name, digest in expected.items()):
                print(f"PyPI {version}: both published distribution hashes verified.")
                return
            if all(name in actual for name in expected):
                raise RuntimeError(
                    "Published PyPI files differ from the release artifacts."
                )
        except HTTPError as exc:
            if exc.code != 404:
                raise
        except URLError:
            if attempt == 11:
                raise
        time.sleep(5)
    raise RuntimeError("Release distributions did not become available on PyPI.")


if __name__ == "__main__":
    verify()
