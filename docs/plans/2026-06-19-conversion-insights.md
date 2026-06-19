# Conversion Insights Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a dedicated conversion reporting tool that supports date and conversion-action segmentation without mixing incompatible traffic metrics.

**Architecture:** Keep the existing constrained GAQL builder pattern. Add a separate `build_conversion_insights_query(...)` for conversion-only metrics and expose it through `get_conversion_insights(...)`; leave `get_insights(...)` for general performance metrics.

**Tech Stack:** Python 3.10+, FastMCP, Google Ads API GAQL, pytest

---

### Task 1: Add Query Builder Tests

**Files:**
- Modify: `tests/test_query_builders.py`
- Modify: `src/flin_google_ads_mcp/google_ads.py`

**Step 1: Write failing tests**

Add tests proving conversion insights can:
- select `segments.date` when requested
- select conversion action fields when requested
- filter by campaign/ad group
- reject campaign/ad group filters at account level

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_query_builders.py -q`

Expected: fail because `build_conversion_insights_query` does not exist.

**Step 3: Implement minimal query builder**

Add `build_conversion_insights_query(...)` with conversion-only metrics:
- `metrics.conversions`
- `metrics.conversions_value`

**Step 4: Run tests**

Run: `pytest tests/test_query_builders.py -q`

Expected: pass.

### Task 2: Add MCP Tool Serialization

**Files:**
- Modify: `tests/test_server_tools.py`
- Modify: `src/flin_google_ads_mcp/server.py`

**Step 1: Write failing server test**

Add a fake row with campaign, date, conversion action, and conversion metrics. Assert `get_conversion_insights(...)` returns those fields.

**Step 2: Run test to verify failure**

Run: `pytest tests/test_server_tools.py -q`

Expected: fail because `get_conversion_insights` does not exist.

**Step 3: Implement minimal tool**

Wire the query builder into a new MCP tool and serialize optional segment fields only when requested.

**Step 4: Run tests**

Run: `pytest tests/test_server_tools.py -q`

Expected: pass.

### Task 3: Update Docs And Verify

**Files:**
- Modify: `README.md`
- Modify: `docs/testing.md`

**Step 1: Document the new tool**

Add `get_conversion_insights` to tool lists and explain when to use it instead of `get_insights`.

**Step 2: Run full verification**

Run: `pytest -q`

Expected: all tests pass.
