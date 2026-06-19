# Google Ads Change Events Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a read-only MCP tool that returns Google Ads `change_event` history for a customer account.

**Architecture:** Query construction and validation live in `src/flin_google_ads_mcp/google_ads.py`. MCP request handling and response formatting live in `src/flin_google_ads_mcp/server.py`, using the existing `run_search_query` flow.

**Tech Stack:** Python 3.10+, FastMCP, google-ads client, pytest.

---

### Task 1: Query Builder

**Files:**
- Modify: `src/flin_google_ads_mcp/google_ads.py`
- Test: `tests/test_query_builders.py`

**Step 1: Write failing tests**

Add tests proving `build_change_events_query` selects `change_event` fields, filters by start/end dates, supports `resource_type` and `user_email`, orders descending, clamps limit, and rejects invalid dates/resource types.

**Step 2: Run tests**

Run: `pytest tests/test_query_builders.py -q`

Expected: fails because `build_change_events_query` does not exist.

**Step 3: Implement minimal code**

Add `ALLOWED_CHANGE_EVENT_RESOURCE_TYPES`, `normalize_change_event_resource_type`, `normalize_user_email_filter`, and `build_change_events_query`.

**Step 4: Verify**

Run: `pytest tests/test_query_builders.py -q`

Expected: pass.

### Task 2: MCP Tool

**Files:**
- Modify: `src/flin_google_ads_mcp/server.py`
- Test: `tests/test_server_tools.py`

**Step 1: Write failing tests**

Add a synthetic `change_event` row and assert `get_change_events` returns normalized event metadata, changed field paths, and old/new field values.

**Step 2: Run tests**

Run: `pytest tests/test_server_tools.py -q`

Expected: fails because `get_change_events` does not exist.

**Step 3: Implement minimal code**

Import `build_change_events_query`, add helpers for changed-field extraction, and expose `get_change_events`.

**Step 4: Verify**

Run: `pytest tests/test_server_tools.py -q`

Expected: pass.

### Task 3: Documentation and Full Verification

**Files:**
- Modify: `README.md`

**Step 1: Update docs**

Add `get_change_events` to the exposed tools list and document inputs, 30-day API window, and example usage.

**Step 2: Run full verification**

Run: `pytest -q`

Expected: pass.

Run: `python3 -m compileall src`

Expected: pass.
