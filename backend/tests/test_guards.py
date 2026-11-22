"""Scenarios 26-29: allowlist, kill switch, timer survives restart, 30-day purge.
Plus the per-driver call cap and webhook parsing. Fully offline."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from app import config as C
from app.config import Settings, mask_phone
from app.db import Database, purge_old_records
from app.sarvam import OutboundClient, parse_webhook, transcript_ends_in_nudges, verify_signature
from app.scheduler import Scheduler, TimerStore

NOW = datetime(2026, 11, 23, 1, 0, tzinfo=timezone.utc)


class FakeTransport:
    """Records requests; never touches the network."""

    def __init__(self) -> None:
        self.requests: List[Dict[str, Any]] = []

    def __call__(self, url: str, headers: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
        self.requests.append({"url": url, "headers": headers, "body": body})
        return {"attempt_id": "att-%d" % len(self.requests)}


def client(**kw) -> OutboundClient:
    settings = Settings(calls_enabled=kw.pop("calls_enabled", True),
                        allowed_numbers=kw.pop("allowed", ["+919999900001", "+919999900002"]),
                        demo_mode="live", sarvam_org_id="org", sarvam_workspace_id="ws",
                        sarvam_api_key="secret-key", public_base_url="https://example.test")
    transport = FakeTransport()
    c = OutboundClient(settings, transport=transport, clock=lambda: NOW, virtual=False)
    c.fake = transport  # type: ignore[attr-defined]
    return c


def test_26_number_not_in_allowed_numbers_blocked_and_logged():
    c = client()
    out = c.place_call("+919111111111", "check_in", {"trip_id": "trip-demo"})
    assert out.blocked and out.blocked_reason == "not_allowed"
    assert c.fake.requests == []
    assert any("not in ALLOWED_NUMBERS" in line for line in c.log_lines)
    # never log the full number
    assert all("9111111111" not in line for line in c.log_lines)
    assert any(line.endswith("1111") for line in c.log_lines)


def test_27_calls_disabled_no_calls_placed_actions_logged():
    c = client(calls_enabled=False)
    out = c.place_call("+919999900001", "silence_callback", {"trip_id": "trip-demo"})
    assert out.blocked and out.blocked_reason == "calls_disabled"
    assert c.fake.requests == []
    assert any("CALLS_ENABLED=false" in line and "silence_callback" in line for line in c.log_lines)
    # alerts are blocked by the kill switch too (no real family call in testing)
    out2 = c.place_call("+919999900002", "alert", {"trip_id": "trip-demo", "alert_step": "primary"}, is_alert=True)
    assert out2.blocked and c.fake.requests == []


def test_allowed_and_enabled_builds_instant_outbound_body():
    c = client()
    out = c.place_call("+919999900001", "check_in", {"trip_id": "trip-demo", "driver_name": "Raju"})
    assert out.placed and out.attempt_id == "att-1"
    body = c.fake.requests[0]["body"]
    assert body["user_config"]["user_phone_number"] == "+919999900001"
    assert body["webhook_config"]["url"] == "https://example.test/webhooks/sarvam"
    assert body["webhook_config"]["metadata"]["call_reason"] == "check_in"
    assert body["app_config"]["app_overrides"]["initial_bot_message"].startswith("Ustaad!")
    assert c.fake.requests[0]["headers"]["X-API-Key"] == "secret-key"
    assert "orgs/org/workspaces/ws/outbounds" in c.fake.requests[0]["url"]


def test_cap_12_khalasi_calls_per_driver_per_hour_never_applies_to_alerts():
    c = client()
    for i in range(C.MAX_CALLS_PER_DRIVER_PER_HOUR):
        assert c.place_call("+919999900001", "check_in", {"trip_id": "trip-demo"}).placed
    capped = c.place_call("+919999900001", "check_in", {"trip_id": "trip-demo"})
    assert capped.blocked and capped.blocked_reason == "rate_capped"
    alert = c.place_call("+919999900002", "alert", {"trip_id": "trip-demo", "alert_step": "primary"}, is_alert=True)
    assert alert.placed


def test_mask_phone():
    assert mask_phone("+919876543210") == "******3210"
    assert "98765" not in mask_phone("+919876543210")


def test_parse_webhook_maps_fields_and_detects_nudges():
    payload = {
        "attempt_id": "att-9", "status": "connected", "duration": "95",
        "final_agent_variables": {"call_end_state": "driving_alert"},
        "interaction_transcript": [
            {"role": "agent", "en_text": "How are you Ustaad?"},
            {"role": "user", "en_text": "fine"},
            {"role": "agent", "en_text": "Ustaad? Ustaad, bas 'haan' bolo!"},
            {"role": "agent", "en_text": "Ustaad! Haan bolo!"},
        ],
        "webhook_config": {"metadata": {"trip_id": "trip-demo", "call_reason": "check_in"}},
    }
    p = parse_webhook(payload)
    assert p.attempt_id == "att-9" and p.status == "connected" and p.duration_s == 95.0
    assert p.trip_id == "trip-demo" and p.call_reason == "check_in"
    assert p.ended_on_nudges is True
    assert p.call_end_state == "driving_alert"   # label only, never a decision input
    assert parse_webhook({"status": "no_answer"}).status == "no_answer"
    assert parse_webhook({"status": "busy"}).status == "busy"
    assert parse_webhook({"status": "failed", "failure_reason": "unreachable"}).status == "failed"
    assert transcript_ends_in_nudges([{"role": "agent", "en_text": "bye"}, {"role": "user", "en_text": "ok"}]) is False


def test_28_pending_callback_survives_restart(tmp_path):
    path = str(tmp_path / "timers.db")
    store = TimerStore(path)
    fire_at = NOW + timedelta(seconds=30)
    store.schedule("silence_retry", "trip-demo", fire_at)
    store.close()                       # "crash"

    store2 = TimerStore(path)            # restart re-arms from SQLite
    pending = store2.load_pending()
    assert [(t.kind, t.trip_id, t.fire_at) for t in pending] == [("silence_retry", "trip-demo", fire_at)]
    assert store2.due(NOW + timedelta(seconds=29)) == []
    assert len(store2.due(fire_at)) == 1

    fired: List[tuple] = []

    async def on_fire(kind: str, trip_id: str) -> None:
        fired.append((kind, trip_id))

    sched = Scheduler(store2, on_fire, clock=lambda: fire_at)
    n = asyncio.get_event_loop().run_until_complete(sched.fire_due())
    assert n == 1 and fired == [("silence_retry", "trip-demo")]
    assert store2.load_pending() == []  # fired exactly once
    n2 = asyncio.get_event_loop().run_until_complete(sched.fire_due())
    assert n2 == 0


def test_timer_cancel_and_reschedule_replaces():
    store = TimerStore(":memory:")
    store.schedule("check_in", "trip-demo", NOW + timedelta(minutes=30))
    store.schedule("check_in", "trip-demo", NOW + timedelta(minutes=20))
    assert len(store.load_pending()) == 1
    assert store.cancel("check_in", "trip-demo") == 1
    assert store.load_pending() == []


def test_29_transcripts_older_than_30_days_purged():
    db = Database(":memory:")
    old = NOW - timedelta(days=31)
    fresh = NOW - timedelta(days=2)
    db.store_transcript("trip-demo", "att-old", [{"role": "user", "en_text": "old"}], old)
    db.store_transcript("trip-demo", "att-new", [{"role": "user", "en_text": "new"}], fresh)
    db.store_webhook("att-old", {"status": "connected"}, old)
    db.store_webhook("att-new", {"status": "connected"}, fresh)
    result = purge_old_records(db, NOW)
    assert result == {"transcripts": 1, "webhook_payloads": 1}
    assert db.count("transcripts") == 1 and db.count("webhook_payloads") == 1
    assert purge_old_records(db, NOW) == {"transcripts": 0, "webhook_payloads": 0}


def test_care_signal_stores_flag_without_detail():
    db = Database(":memory:")
    db.record_signal("trip-demo", "care", "sensitive detail", NOW)
    row = db.conn.execute("SELECT detail FROM signals WHERE type='care'").fetchone()
    assert row["detail"] is None


def test_verify_signature_follows_sarvam_docs():
    secret = "whsec_test"
    body = b'{"status":"connected"}'
    ts = str(int(NOW.timestamp()))
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    assert verify_signature(secret, body, f"sha256={expected}", ts, now=NOW)
    # replay guard: older than five minutes
    assert not verify_signature(secret, body, f"sha256={expected}", ts, now=NOW + timedelta(minutes=6))
    # wrong secret, missing timestamp, tampered body
    assert not verify_signature("other", body, f"sha256={expected}", ts, now=NOW)
    assert not verify_signature(secret, body, f"sha256={expected}", None, now=NOW)
    assert not verify_signature(secret, body + b" ", f"sha256={expected}", ts, now=NOW)
    # no webhook config yet: accepted
    assert verify_signature("", body, None, None, now=NOW)


def test_parse_webhook_reads_start_and_end_datetime():
    p = parse_webhook({"status": "connected", "start_datetime": "2026-09-01T18:44:15Z", "end_datetime": "2026-09-01T18:44:31Z"})
    assert p.start_datetime == datetime(2026, 9, 1, 18, 44, 15, tzinfo=timezone.utc)
    assert p.end_datetime == datetime(2026, 9, 1, 18, 44, 31, tzinfo=timezone.utc)
    assert parse_webhook({"status": "connected"}).end_datetime is None
    assert parse_webhook({"status": "connected", "end_datetime": "garbage"}).end_datetime is None
