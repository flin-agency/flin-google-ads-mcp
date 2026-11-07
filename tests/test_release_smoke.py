import asyncio
from builtins import ExceptionGroup
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

spec = importlib.util.spec_from_file_location(
    "release_smoke", Path(__file__).resolve().parents[1] / "scripts/smoke_mcpb.py"
)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def test_index_propagation_is_retried_then_version_is_checked(monkeypatch):
    call = AsyncMock(
        side_effect=[
            ExceptionGroup("MCP cleanup", [smoke.ServerVersionMismatch("old")]),
            None,
        ]
    )
    monkeypatch.setattr(smoke, "smoke", call)
    monkeypatch.setattr(smoke.asyncio, "sleep", AsyncMock())
    asyncio.run(smoke.smoke_with_retry("bundle", None, "0.1.12", 2))
    assert call.await_count == 2
    assert call.call_args.args == ("bundle", None, "0.1.12")


def test_other_failures_and_persistent_mismatch_fail_release(monkeypatch):
    monkeypatch.setattr(smoke.asyncio, "sleep", AsyncMock())
    call = AsyncMock(side_effect=AssertionError("missing tool"))
    monkeypatch.setattr(smoke, "smoke", call)
    with pytest.raises(AssertionError, match="missing tool"):
        asyncio.run(smoke.smoke_with_retry("bundle", None, "0.1.12", 2))
    assert call.await_count == 1
    call = AsyncMock(side_effect=smoke.ServerVersionMismatch("old"))
    monkeypatch.setattr(smoke, "smoke", call)
    with pytest.raises(smoke.ServerVersionMismatch):
        asyncio.run(smoke.smoke_with_retry("bundle", None, "0.1.12", 2))
    assert call.await_count == 2
