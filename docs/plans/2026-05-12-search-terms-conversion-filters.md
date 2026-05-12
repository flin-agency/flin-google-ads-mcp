# Search Terms And Conversion Filters Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new `get_search_terms` MCP tool and optional conversion-action filters to `get_insights`, `get_keywords`, and `get_search_terms`.

**Architecture:** Keep the current constrained-query architecture. Add shared conversion-filter validation in `google_ads.py`, extend the existing query builders, add one new query builder for `search_term_view`, and expose the new behavior through `server.py` with stable JSON payloads.

**Tech Stack:** Python 3.10+, FastMCP, Google Ads API GAQL, pytest

---

### Task 1: Add query-builder tests for conversion filters

**Files:**
- Modify: `tests/test_query_builders.py`
- Modify: `src/flin_google_ads_mcp/google_ads.py`

**Step 1: Write the failing test**

```python
def test_insights_query_supports_conversion_action_id_filter() -> None:
    query = build_insights_query(
        level="campaign",
        date_range="LAST_7_DAYS",
        conversion_action_id="123456",
        limit=20,
    )
    assert "segments.conversion_action = 'customers/" in query
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_builders.py -v`
Expected: FAIL because the builder does not accept the new arguments yet.

**Step 3: Write minimal implementation**

Add validation and a reusable conversion filter builder, then thread the optional parameters through the affected query builders.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_query_builders.py -v`
Expected: PASS for the new cases.

**Step 5: Commit**

```bash
git add tests/test_query_builders.py src/flin_google_ads_mcp/google_ads.py
git commit -m "feat: add conversion action query filters"
```

### Task 2: Add failing tests for the new search-terms tool

**Files:**
- Modify: `tests/test_server_tools.py`
- Modify: `src/flin_google_ads_mcp/server.py`

**Step 1: Write the failing test**

```python
def test_get_search_terms_returns_search_term_rows(monkeypatch) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_server_tools.py -v`
Expected: FAIL because `get_search_terms` does not exist yet.

**Step 3: Write minimal implementation**

Add `build_search_terms_query(...)`, implement `get_search_terms(...)`, and serialize rows into the same response style used elsewhere.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_server_tools.py -v`
Expected: PASS for the new server-level case.

**Step 5: Commit**

```bash
git add tests/test_server_tools.py src/flin_google_ads_mcp/server.py src/flin_google_ads_mcp/google_ads.py
git commit -m "feat: add search terms tool"
```

### Task 3: Extend tool responses and docs

**Files:**
- Modify: `src/flin_google_ads_mcp/server.py`
- Modify: `README.md`

**Step 1: Write the failing test**

```python
def test_get_keywords_echoes_conversion_action_filters(monkeypatch) -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_server_tools.py -v`
Expected: FAIL because response metadata is not echoed yet.

**Step 3: Write minimal implementation**

Echo the new filter fields in responses and document the new tool and parameters.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_server_tools.py -v`
Expected: PASS for the response-shape cases.

**Step 5: Commit**

```bash
git add tests/test_server_tools.py src/flin_google_ads_mcp/server.py README.md
git commit -m "docs: document search terms and conversion filters"
```

### Task 4: Full verification

**Files:**
- Modify: `tests/test_query_builders.py`
- Modify: `tests/test_server_tools.py`
- Modify: `src/flin_google_ads_mcp/google_ads.py`
- Modify: `src/flin_google_ads_mcp/server.py`
- Modify: `README.md`

**Step 1: Run focused tests**

Run: `pytest tests/test_query_builders.py tests/test_server_tools.py -v`
Expected: PASS

**Step 2: Run broader verification**

Run: `python3 -m compileall src`
Expected: PASS

**Step 3: Review diff**

Run: `git diff -- src/flin_google_ads_mcp/google_ads.py src/flin_google_ads_mcp/server.py tests/test_query_builders.py tests/test_server_tools.py README.md`
Expected: only intended changes

**Step 4: Commit**

```bash
git add docs/plans/2026-05-12-search-terms-conversion-filters-design.md docs/plans/2026-05-12-search-terms-conversion-filters.md tests/test_query_builders.py tests/test_server_tools.py src/flin_google_ads_mcp/google_ads.py src/flin_google_ads_mcp/server.py README.md
git commit -m "feat: add search terms reporting and conversion filters"
```
