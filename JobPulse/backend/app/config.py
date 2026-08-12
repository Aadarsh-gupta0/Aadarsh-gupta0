"""Runtime configuration, loaded from environment / `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="JOBPULSE_",
        extra="ignore",
    )

    # --- general -------------------------------------------------------
    env: str = "dev"
    database_url: str = f"sqlite+pysqlite:///{REPO_ROOT / 'jobpulse.db'}"
    api_key: str | None = Field(
        default=None,
        description="If set, mutating admin endpoints require the X-API-Key header.",
    )

    # --- ingestion -----------------------------------------------------
    ingest_interval_minutes: int = 30
    """How often the scheduler runs a full scrape pass."""

    http_timeout_seconds: float = 20.0
    http_max_retries: int = 3
    user_agent: str = "JobPulseBot/0.1 (+https://github.com/Aadarsh-gupta0; personal job-alert app)"
    respect_robots_txt: bool = True

    per_host_delay_seconds: float = 1.5
    """Politeness delay between two requests to the same host."""

    enabled_scrapers: list[str] = Field(
        default_factory=lambda: [
            "remoteok",
            "arbeitnow",
            "himalayas",
            "weworkremotely",
            "hn_hiring",
            "greenhouse",
            "lever",
        ]
    )

    greenhouse_boards: list[str] = Field(
        default_factory=lambda: ["figma", "canva", "razorpay", "postman", "gitlab"]
    )
    lever_boards: list[str] = Field(default_factory=lambda: ["swiggy", "netflix"])

    # --- matching ------------------------------------------------------
    match_threshold: float = 0.35
    """Minimum normalised score (0-1) before a job is stored for a profile."""

    notify_threshold: float = 0.55
    """Minimum normalised score before we send a push notification."""

    max_pushes_per_device_per_run: int = 4
    """Hard cap so a big scrape never spams the lock screen."""

    quiet_hours_start: int = 22  # 22:00 local
    quiet_hours_end: int = 7  # 07:00 local

    # --- APNs ----------------------------------------------------------
    apns_use_sandbox: bool = True
    apns_team_id: str | None = None
    apns_key_id: str | None = None
    apns_auth_key_path: Path | None = None
    apns_auth_key: str | None = Field(
        default=None, description="PEM contents of the .p8 key; alternative to the path."
    )
    apns_topic: str = "com.aadarsh.jobpulse"

    @field_validator("enabled_scrapers", "greenhouse_boards", "lever_boards", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def apns_host(self) -> str:
        return "api.sandbox.push.apple.com" if self.apns_use_sandbox else "api.push.apple.com"

    @property
    def apns_configured(self) -> bool:
        has_key = bool(self.apns_auth_key) or (
            self.apns_auth_key_path is not None and self.apns_auth_key_path.exists()
        )
        return bool(self.apns_team_id and self.apns_key_id and has_key)

    def read_apns_key(self) -> str:
        if self.apns_auth_key:
            return self.apns_auth_key
        if self.apns_auth_key_path and self.apns_auth_key_path.exists():
            return self.apns_auth_key_path.read_text()
        raise RuntimeError("No APNs auth key configured (set JOBPULSE_APNS_AUTH_KEY_PATH).")


@lru_cache
def get_settings() -> Settings:
    return Settings()
