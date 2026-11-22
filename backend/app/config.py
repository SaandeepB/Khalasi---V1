"""Khalasi backend configuration.

All default timings from MASTER_PROMPT section 7 live here as named constants,
plus env-driven settings read from os.environ with safe defaults.
Python 3.9 compatible.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from typing import List, Optional

# --- Default timings (section 7) -------------------------------------------
NUDGE_1_S = 15                 # first "Ustaad? bas 'haan' bolo!" nudge
NUDGE_2_S = 30                 # second nudge
HANGUP_S = 40                  # Sarvam hangs up after ~40 s of silence
CALLBACK_DELAY_S = 5           # silence_callback placed ~5 s after hang-up
RETRY_DELAY_S = 30             # R4: retry silence_callback once after 30 s
FAMILY_ALERT_TARGET_S = 150    # family alerted by ~2:30 after silence began
MISSED_CALL_CALLBACK_S = 10    # R16: call back within 10 s
CHECK_IN_INTERVAL_MIN = 30     # R12: check-in every 30 min while moving
CHECK_IN_RECENT_CALL_MIN = 20  # R12: skip if any call in the last 20 min
CHECK_IN_START_HOUR = 0        # midnight ...
CHECK_IN_END_HOUR = 6          # ... to 6 am (exclusive)
PROMISE_CHECK_MIN = 10         # R10
QUIET_MIN = 10                 # R11
DARK_STRETCH_LOOKAHEAD_MIN = 20  # R8
REST_RESET_MIN = 30            # a rest of 30+ min resets the 5-hour clock
REST_DUE_H = 5                 # 5+ h since last rest => rest due
UNREACHABLE_RETRY_MIN = 2      # R6
UNREACHABLE_CAP_MIN = 10       # R6
GPS_STALE_MIN = 5              # R14
VALID_END_WINDOW_S = 30        # log_status must be within ~30 s of call end
SIM_RING_TIME_S = 25           # simulated ring time before no_answer (tests)
MAX_CALLS_PER_DRIVER_PER_HOUR = 12  # rule 7 cap (never applies to alerts)
TRANSCRIPT_RETENTION_DAYS = 30  # R17
PURGE_HOUR, PURGE_MINUTE = 6, 30  # R17: daily at 06:30
ALERT_TOKEN_TTL_H = 24

# Derived helpers
CHECK_IN_INTERVAL = timedelta(minutes=CHECK_IN_INTERVAL_MIN)
REST_DUE = timedelta(hours=REST_DUE_H)
REST_RESET = timedelta(minutes=REST_RESET_MIN)
GPS_STALE = timedelta(minutes=GPS_STALE_MIN)

try:  # zoneinfo exists on 3.9+, but tzdata may be missing on some systems
    from zoneinfo import ZoneInfo

    IST = ZoneInfo(os.environ.get("TZ", "Asia/Kolkata") or "Asia/Kolkata")
except Exception:  # pragma: no cover - fallback to fixed offset
    IST = timezone(timedelta(hours=5, minutes=30), "IST")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name: str) -> List[str]:
    raw = os.environ.get(name, "")
    return [p.strip() for p in raw.split(",") if p.strip()]


@dataclass
class Settings:
    """Env-driven settings. Safe defaults: calls disabled, virtual demo."""

    calls_enabled: bool = False
    allowed_numbers: List[str] = field(default_factory=list)
    demo_mode: str = "virtual"          # virtual | live
    demo_speed: float = 1.0             # scales engine timers in demo only
    tz: str = "Asia/Kolkata"
    tool_secret: str = ""
    public_base_url: str = ""
    entry_mode: str = "inbound"         # inbound | missed_call
    # Sarvam
    sarvam_api_key: str = ""
    sarvam_org_id: str = ""
    sarvam_workspace_id: str = ""
    sarvam_khalasi_app_id: str = ""
    sarvam_khalasi_app_version: str = ""
    sarvam_alert_app_id: str = ""
    sarvam_alert_app_version: str = ""
    sarvam_connection_id: str = ""
    sarvam_agent_phone: str = ""
    sarvam_webhook_secret: str = ""
    # Divyam (offline only)
    divyam_api_key: str = ""
    divyam_base_url: str = ""
    divyam_model: str = ""
    # SMS (optional)
    sms_provider: str = ""
    sms_api_key: str = ""
    # Seed phones
    driver_phone: str = ""
    alert_phone: str = ""
    backup_phone: str = ""
    fleet_desk_phone: str = ""
    db_path: str = "khalasi.db"

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ.get
        try:
            speed = float(e("DEMO_SPEED", "1") or "1")
        except ValueError:
            speed = 1.0
        return cls(
            calls_enabled=_env_bool("CALLS_ENABLED", False),
            allowed_numbers=_env_list("ALLOWED_NUMBERS"),
            demo_mode=(e("DEMO_MODE", "virtual") or "virtual").lower(),
            demo_speed=speed if speed > 0 else 1.0,
            tz=e("TZ", "Asia/Kolkata") or "Asia/Kolkata",
            tool_secret=e("TOOL_SECRET", "") or "",
            public_base_url=e("PUBLIC_BASE_URL", "") or "",
            entry_mode=e("ENTRY_MODE", "inbound") or "inbound",
            sarvam_api_key=e("SARVAM_API_KEY", "") or "",
            sarvam_org_id=e("SARVAM_ORG_ID", "") or "",
            sarvam_workspace_id=e("SARVAM_WORKSPACE_ID", "") or "",
            sarvam_khalasi_app_id=e("SARVAM_KHALASI_APP_ID", "") or "",
            sarvam_khalasi_app_version=e("SARVAM_KHALASI_APP_VERSION", "") or "",
            sarvam_alert_app_id=e("SARVAM_ALERT_APP_ID", "") or "",
            sarvam_alert_app_version=e("SARVAM_ALERT_APP_VERSION", "") or "",
            sarvam_connection_id=e("SARVAM_CONNECTION_ID", "") or "",
            sarvam_agent_phone=e("SARVAM_AGENT_PHONE", "") or "",
            sarvam_webhook_secret=e("SARVAM_WEBHOOK_SECRET", "") or "",
            divyam_api_key=e("DIVYAM_API_KEY", "") or "",
            divyam_base_url=e("DIVYAM_BASE_URL", "") or "",
            divyam_model=e("DIVYAM_MODEL", "") or "",
            sms_provider=e("SMS_PROVIDER", "") or "",
            sms_api_key=e("SMS_API_KEY", "") or "",
            driver_phone=e("DRIVER_PHONE", "") or "",
            alert_phone=e("ALERT_PHONE", "") or "",
            backup_phone=e("BACKUP_PHONE", "") or "",
            fleet_desk_phone=e("FLEET_DESK_PHONE", "") or "",
            db_path=e("KHALASI_DB", "khalasi.db") or "khalasi.db",
        )

    @property
    def virtual(self) -> bool:
        return self.demo_mode != "live"


def mask_phone(number: Optional[str]) -> str:
    """Never log full phone numbers: keep only the last 4 digits."""
    if not number:
        return "****"
    digits = "".join(ch for ch in str(number) if ch.isdigit())
    tail = digits[-4:] if len(digits) >= 4 else digits
    return "*" * 6 + tail


def get_settings() -> Settings:
    return Settings.from_env()
