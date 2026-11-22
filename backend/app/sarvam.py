"""Sarvam outbound client and call-result webhook parsing.

Guards (rule 7): CALLS_ENABLED kill switch, ALLOWED_NUMBERS allowlist, and a cap of
12 Khalasi calls per driver per hour that never applies to contact alerts.
The HTTP transport is injectable so tests never touch the network.
Python 3.9 compatible.
"""
from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Deque, Dict, List, Optional

from . import config as C
from .config import Settings, mask_phone

log = logging.getLogger("khalasi.sarvam")

OUTBOUND_URL = "https://apps.sarvam.ai/api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds"

# Hindi first lines per call_reason (Appendix A); the backend sets initial_bot_message.
INITIAL_BOT_MESSAGE: Dict[str, str] = {
    "inbound": "Ustaad! Khalasi bol raha hoon.",
    "callback": "Ustaad! Khalasi bol raha hoon. Aapki missed call aayi thi.",
    "check_in": "Ustaad! Khalasi bol raha hoon. Bas haal-chaal poochne ke liye. Kahan pahunche?",
    "silence_callback": "Ustaad! Khalasi. Aap theek ho?",
    "stopped_check": "Ustaad! Khalasi. Gaadi side mein hai? Sab theek?",
    "dark_stretch_warning": "Ustaad! Khalasi. Ek zaroori baat, aage network nahi milega.",
    "coverage_return": "Ustaad! Khalasi. Network wapas aa gaya. Sab theek?",
    "promised_stop_followup": "Ustaad! Khalasi. Dhaba nahi aaya?",
    "quiet_return": "Ustaad! Khalasi. 10 minute ho gaye. Sab theek?",
}

NUDGE_MARKERS = ("haan bolo", "bas 'haan' bolo", "bas haan bolo", "ustaad?", "ustaad!")


@dataclass
class CallRequest:
    number: str
    reason: str
    variables: Dict[str, Any]
    is_alert: bool = False
    body: Optional[Dict[str, Any]] = None


@dataclass
class CallOutcome:
    placed: bool
    blocked_reason: Optional[str] = None       # calls_disabled | not_allowed | rate_capped | http_error
    attempt_id: Optional[str] = None
    request: Optional[CallRequest] = None
    masked_number: str = ""

    @property
    def blocked(self) -> bool:
        return not self.placed


# Transport: (url, headers, json_body) -> dict response. Injectable; default uses httpx.
Transport = Callable[[str, Dict[str, str], Dict[str, Any]], Dict[str, Any]]


def httpx_transport(url: str, headers: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
    import httpx  # imported lazily so tests never need network

    resp = httpx.post(url, headers=headers, json=body, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OutboundClient:
    """Places Instant Outbound calls, or logs them when blocked / virtual."""

    def __init__(self, settings: Settings, transport: Optional[Transport] = None,
                 clock: Optional[Callable[[], datetime]] = None, virtual: Optional[bool] = None) -> None:
        self.settings = settings
        self.transport = transport or httpx_transport
        self.clock = clock or _utcnow
        self.virtual = settings.virtual if virtual is None else virtual
        self._per_driver: Dict[str, Deque[datetime]] = defaultdict(deque)
        self.log_lines: List[str] = []       # for tests and the console
        self.blocked: List[CallRequest] = []  # would-be calls that were blocked
        self.placed: List[CallRequest] = []

    # --- guards ------------------------------------------------------------
    def _allowed(self, number: str) -> bool:
        allowed = [n.strip() for n in self.settings.allowed_numbers if n.strip()]
        return number in allowed

    def _within_cap(self, driver_key: str, now: datetime) -> bool:
        q = self._per_driver[driver_key]
        cutoff = now - timedelta(hours=1)
        while q and q[0] < cutoff:
            q.popleft()
        return len(q) < C.MAX_CALLS_PER_DRIVER_PER_HOUR

    def _log(self, text: str) -> None:
        self.log_lines.append(text)
        log.info(text)

    # --- body ----------------------------------------------------------------
    def build_body(self, number: str, reason: str, variables: Dict[str, Any], is_alert: bool = False) -> Dict[str, Any]:
        s = self.settings
        app_id = s.sarvam_alert_app_id if is_alert else s.sarvam_khalasi_app_id
        app_version = s.sarvam_alert_app_version if is_alert else s.sarvam_khalasi_app_version
        body: Dict[str, Any] = {
            "app_config": {
                "app_id": app_id,
                "app_version": app_version,
                "connection_config": {
                    "connection_id": s.sarvam_connection_id,
                    "agent_phone_number": s.sarvam_agent_phone,
                },
                "agent_variables": {k: ("" if v is None else str(v)) for k, v in variables.items()},
                "app_overrides": {
                    "initial_language_name": "Hindi",
                },
            },
            "user_config": {"user_phone_number": number},
            "webhook_config": {
                "url": (s.public_base_url.rstrip("/") + "/webhooks/sarvam") if s.public_base_url else "/webhooks/sarvam",
                "metadata": {
                    "trip_id": str(variables.get("trip_id", "")),
                    "call_reason": reason,
                    "kind": "alert" if is_alert else "khalasi",
                    "alert_step": str(variables.get("alert_step", "")),
                },
            },
        }
        if not is_alert:
            body["app_config"]["app_overrides"]["initial_bot_message"] = INITIAL_BOT_MESSAGE.get(reason, INITIAL_BOT_MESSAGE["inbound"])
        return body

    # --- main entry ----------------------------------------------------------
    def place_call(self, number: str, reason: str, variables: Dict[str, Any],
                   is_alert: bool = False, driver_key: Optional[str] = None) -> CallOutcome:
        now = self.clock()
        masked = mask_phone(number)
        req = CallRequest(number=number, reason=reason, variables=dict(variables), is_alert=is_alert)
        req.body = self.build_body(number, reason, variables, is_alert)
        kind = "alert" if is_alert else "khalasi"
        driver_key = driver_key or str(variables.get("trip_id") or "driver")

        if not self.settings.calls_enabled:
            self._log("call blocked (CALLS_ENABLED=false): %s %s -> %s" % (kind, reason, masked))
            self.blocked.append(req)
            return CallOutcome(False, "calls_disabled", request=req, masked_number=masked)
        if not self._allowed(number):
            self._log("call blocked (number not in ALLOWED_NUMBERS): %s %s -> %s" % (kind, reason, masked))
            self.blocked.append(req)
            return CallOutcome(False, "not_allowed", request=req, masked_number=masked)
        if not is_alert and not self._within_cap(driver_key, now):
            self._log("call blocked (cap of %d Khalasi calls/hour for driver): %s -> %s"
                      % (C.MAX_CALLS_PER_DRIVER_PER_HOUR, reason, masked))
            self.blocked.append(req)
            return CallOutcome(False, "rate_capped", request=req, masked_number=masked)
        if not is_alert:
            self._per_driver[driver_key].append(now)

        if self.virtual:
            self._log("virtual mode: would place %s %s -> %s" % (kind, reason, masked))
            self.placed.append(req)
            return CallOutcome(True, attempt_id="virtual-%d" % len(self.placed), request=req, masked_number=masked)

        s = self.settings
        url = OUTBOUND_URL.format(org_id=s.sarvam_org_id, workspace_id=s.sarvam_workspace_id)
        headers = {"X-API-Key": s.sarvam_api_key, "Content-Type": "application/json"}
        try:
            resp = self.transport(url, headers, req.body)
        except Exception as exc:  # network error: never log secrets or full numbers
            self._log("call failed to place (%s): %s %s -> %s" % (type(exc).__name__, kind, reason, masked))
            return CallOutcome(False, "http_error", request=req, masked_number=masked)
        attempt_id = str(resp.get("attempt_id") or resp.get("id") or "")
        self._log("placed %s %s -> %s attempt=%s" % (kind, reason, masked, attempt_id or "?"))
        self.placed.append(req)
        return CallOutcome(True, attempt_id=attempt_id or None, request=req, masked_number=masked)


# --- Webhook parsing ------------------------------------------------------------
@dataclass
class ParsedWebhook:
    attempt_id: Optional[str]
    status: str                         # connected | no_answer | busy | failed
    duration_s: Optional[float]
    failure_reason: Optional[str]
    final_agent_variables: Dict[str, Any] = field(default_factory=dict)
    transcript: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ended_on_nudges: bool = False
    call_end_state: Optional[str] = None  # LLM output: console label only, never a decision input

    @property
    def trip_id(self) -> Optional[str]:
        v = self.metadata.get("trip_id")
        return str(v) if v else None

    @property
    def call_reason(self) -> Optional[str]:
        v = self.metadata.get("call_reason")
        return str(v) if v else None


STATUS_MAP = {
    "connected": "connected", "completed": "connected", "answered": "connected",
    "no_answer": "no_answer", "no-answer": "no_answer", "noanswer": "no_answer", "unanswered": "no_answer",
    "busy": "busy",
    "failed": "failed", "failure": "failed", "error": "failed", "unreachable": "failed",
}


def transcript_ends_in_nudges(transcript: List[Dict[str, Any]], nudges: int = 2) -> bool:
    """True when the last `nudges` turns are agent nudges with no user turn after them."""
    if not transcript:
        return False
    tail = transcript[-nudges:]
    if len(tail) < nudges:
        return False
    for turn in tail:
        role = str(turn.get("role", "")).lower()
        if role in ("user", "driver", "human"):
            return False
        text = str(turn.get("en_text") or turn.get("text") or turn.get("indic_text") or "").lower()
        if not any(m in text for m in NUDGE_MARKERS):
            return False
    return True


def parse_webhook(payload: Dict[str, Any]) -> ParsedWebhook:
    raw_status = str(payload.get("status") or payload.get("call_status") or "").strip().lower()
    status = STATUS_MAP.get(raw_status, "failed" if raw_status else "connected")
    duration = payload.get("duration")
    try:
        duration_s = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_s = None
    variables = payload.get("final_agent_variables") or {}
    if not isinstance(variables, dict):
        variables = {}
    transcript = payload.get("interaction_transcript") or []
    if not isinstance(transcript, list):
        transcript = []
    wc = payload.get("webhook_config") or {}
    metadata = wc.get("metadata") if isinstance(wc, dict) else None
    if not isinstance(metadata, dict):
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    attempt_id = payload.get("attempt_id") or payload.get("id")
    ces = variables.get("call_end_state")
    return ParsedWebhook(
        attempt_id=str(attempt_id) if attempt_id else None,
        status=status,
        duration_s=duration_s,
        failure_reason=payload.get("failure_reason"),
        final_agent_variables=dict(variables),
        transcript=list(transcript),
        metadata=dict(metadata),
        ended_on_nudges=transcript_ends_in_nudges(transcript),
        call_end_state=str(ces) if ces else None,
    )


def verify_signature(secret: str, raw_body: bytes, signature: Optional[str]) -> bool:
    """HMAC-SHA256 hex check. Format unverified against Sarvam docs (open question 6);
    when no secret is configured, accept."""
    if not secret:
        return True
    if not signature:
        return False
    import hashlib
    import hmac

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    sig = signature.split("=", 1)[-1].strip()
    return hmac.compare_digest(expected, sig)
