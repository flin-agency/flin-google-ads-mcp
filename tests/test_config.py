from flin_google_ads_mcp.config import missing_required_env_vars


def test_missing_required_env_vars_detects_all_missing() -> None:
    missing = missing_required_env_vars(env={})
    assert "GOOGLE_ADS_DEVELOPER_TOKEN" in missing
    assert "GOOGLE_ADS_CLIENT_ID" in missing
    assert "GOOGLE_ADS_CLIENT_SECRET" in missing
    assert "GOOGLE_ADS_REFRESH_TOKEN" in missing


def test_missing_required_env_vars_with_complete_env() -> None:
    env = {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "dev",
        "GOOGLE_ADS_CLIENT_ID": "cid",
        "GOOGLE_ADS_CLIENT_SECRET": "sec",
        "GOOGLE_ADS_REFRESH_TOKEN": "rtok",
    }
    assert missing_required_env_vars(env=env) == []
