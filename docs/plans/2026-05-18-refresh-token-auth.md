# Refresh Token Auth Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let the MCP generate and store the Google Ads refresh token locally instead of requiring it in MCP client config.

**Architecture:** Add a small auth module responsible for OAuth URL creation, token exchange, token file storage, and refresh-token resolution. Keep existing Google Ads tools using `get_google_ads_client`, but make that function resolve the refresh token from env or local storage before building the Google Ads client config.

**Tech Stack:** Python 3.10, stdlib `urllib`, FastMCP tools, pytest.

---

### Task 1: Make Refresh Token Optional In Config

**Files:**
- Modify: `src/flin_google_ads_mcp/config.py`
- Modify: `tests/test_config.py`

**Step 1: Write the failing test**

Add a test asserting that `missing_required_env_vars` does not require `GOOGLE_ADS_REFRESH_TOKEN`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -q`

Expected: FAIL because `GOOGLE_ADS_REFRESH_TOKEN` is still required.

**Step 3: Write minimal implementation**

Remove `GOOGLE_ADS_REFRESH_TOKEN` from `REQUIRED_ENV_VARS` and make `Settings.refresh_token` optional.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -q`

Expected: PASS.

### Task 2: Add Local Auth Module

**Files:**
- Create: `src/flin_google_ads_mcp/auth.py`
- Create: `tests/test_auth.py`

**Step 1: Write failing tests**

Cover OAuth URL generation, auth code extraction from raw code or redirect URL, token save/load/delete, env token precedence, and token exchange via monkeypatched `urlopen`.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_auth.py -q`

Expected: FAIL because the module does not exist yet.

**Step 3: Write minimal implementation**

Implement auth file path resolution, JSON storage, safe status payloads, OAuth URL generation, authorization-code token exchange, and refresh-token resolution.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_auth.py -q`

Expected: PASS.

### Task 3: Wire Auth Into Google Ads Client And MCP Tools

**Files:**
- Modify: `src/flin_google_ads_mcp/google_ads.py`
- Modify: `src/flin_google_ads_mcp/server.py`
- Modify: `tests/test_server_tools.py`

**Step 1: Write failing tests**

Add server tests for `auth_status`, `health_check` missing-token behavior, and refresh-token redaction.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_server_tools.py -q`

Expected: FAIL because auth tools do not exist yet.

**Step 3: Write minimal implementation**

Use auth resolution in `get_google_ads_client`. Add `auth_status`, `get_auth_url`, `save_refresh_token_from_code`, and `clear_auth_token` MCP tools.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_server_tools.py -q`

Expected: PASS.

### Task 4: Update Documentation And Verify Suite

**Files:**
- Modify: `README.md`
- Modify: `docs/testing.md`
- Modify: `docs/mcp-usage-guide.md`

**Step 1: Update docs**

Document the new auth flow, optional `GOOGLE_ADS_REFRESH_TOKEN`, and `GOOGLE_ADS_AUTH_FILE`.

**Step 2: Run full test suite**

Run: `pytest -q`

Expected: PASS.
