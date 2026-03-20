from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping
import os


REQUIRED_ENV_VARS = (
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN",
)


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(
        f"Invalid boolean value for {name}: {raw!r}. Use true/false."
    )


def missing_required_env_vars(env: Mapping[str, str] | None = None) -> list[str]:
    source = os.environ if env is None else env
    return [key for key in REQUIRED_ENV_VARS if not source.get(key)]


@dataclass(frozen=True)
class Settings:
    developer_token: str
    client_id: str
    client_secret: str
    refresh_token: str
    login_customer_id: str | None
    default_customer_id: str | None
    use_proto_plus: bool


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    missing = missing_required_env_vars()
    if missing:
        missing_fmt = ", ".join(missing)
        raise ConfigurationError(
            "Missing required environment variables: "
            f"{missing_fmt}. See .env.example for a valid template."
        )

    return Settings(
        developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"].strip(),
        client_id=os.environ["GOOGLE_ADS_CLIENT_ID"].strip(),
        client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"].strip(),
        refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"].strip(),
        login_customer_id=os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        default_customer_id=os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
        use_proto_plus=_get_bool("GOOGLE_ADS_USE_PROTO_PLUS", True),
    )

