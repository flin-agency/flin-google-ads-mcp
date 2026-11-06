from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def isolate_oauth_callback():
    from flin_google_ads_mcp.oauth_callback import oauth_callback

    oauth_callback.cancel()
    oauth_callback._flow = None
    yield
    oauth_callback.cancel()
    oauth_callback._flow = None
