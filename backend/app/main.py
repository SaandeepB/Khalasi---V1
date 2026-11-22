"""Khalasi FastAPI layer: the thinnest wiring around the pure engine.

Tools answer from in-memory state; the engine's actions are executed by the
scheduler (SQLite timers) and the outbound client. In virtual mode (DEMO_MODE
!= live, the default) calls are logged, never placed. Python 3.9 compatible.
"""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from . import config as C
from . import engine as E
from .config import Settings, mask_phone
from .db import Database, purge_old_records
from .sarvam import OutboundClient, parse_webhook, verify_signature
from .scheduler import Scheduler, TimerStore
from .seed import DEMO_DRIVER_ID, DEMO_TRIP_ID, seed
from .sim import TruckSim

log = logging.getLogger("khalasi")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

T_PURGE = "purge"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ist(dt: datetime) -> datetime:
    return dt.astimezone(C.IST)


class Runtime:
    """All mutable server state. One instance per process."""

    def __init__(self, settings: Optional[Settings] = None, db_path: Optional[str] = None) -> None:
        self.settings = settings or Settings.from_env()
        path = db_path or self.settings.db_path
        self.db = Database(path)
        self.timers = TimerStore(path if path == ":memory:" else path.replace(".db", "") + "-timers.db")
        self.client = OutboundClient(self.settings)   # virtual unless DEMO_MODE=live
        self.sim = TruckSim(trip_id=DEMO_TRIP_ID)
        self.states: Dict[str, E.TripState] = {}
        self.subscribers: List[asyncio.Queue] = []
        self.events: List[Dict[str, Any]] = []
        self.active_alert_token: Dict[str, str] = {}
        self.scheduler = Scheduler(self.timers, self.on_timer_fire)

    # --- bootstrap -----------------------------------------------------------
    def bootstrap(self) -> None:
        now = utcnow()
        info = seed(self.db, self.settings, now)
        started = datetime.fromisoformat(info["started_at"])
        self.sim.trip_started_at = started
        self.states[DEMO_TRIP_ID] = E.TripState(
            trip_id=DEMO_TRIP_ID, driver_name="Raju", trip_started_at=started, moving=True, last_gps_at=now,
            pending_timers=tuple(t.kind for t in self.timers.load_pending() if t.trip_id == DEMO_TRIP_ID and t.kind != T_PURGE),
        )
        pending = self.timers.load_pending()
        if pending:
            self.emit("timer", "re-armed %d pending timer(s) from SQLite after restart" % len(pending))
        if not any(t.kind == T_PURGE for t in pending):
            self.timers.schedule(T_PURGE, "system", self.next_purge_time(now))
        self.emit("system", "Khalasi backend up. mode=%s calls_enabled=%s speed=%sx" % (
            self.settings.demo_mode, self.settings.calls_enabled, self.settings.demo_speed))

    @staticmethod
    def next_purge_time(now: datetime) -> datetime:
        local = ist(now)
        t = local.replace(hour=C.PURGE_HOUR, minute=C.PURGE_MINUTE, second=0, microsecond=0)
        if t <= local:
            t = t + timedelta(days=1)
        return t.astimezone(timezone.utc)

    # --- console stream ------------------------------------------------------
    def emit(self, kind: str, text: str, **data: Any) -> None:
        ev = {"kind": kind, "at": ist(utcnow()).strftime("%H:%M:%S"), "text": text, "data": data}
        self.events.append(ev)
        self.events = self.events[-500:]
        log.info("[%s] %s", kind, text)
        for q in list(self.subscribers):
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                pass

    # --- engine plumbing -----------------------------------------------------
    def state(self, trip_id: str) -> E.TripState:
        if trip_id not in self.states:
            self.states[trip_id] = E.TripState(trip_id=trip_id, trip_started_at=utcnow(), last_gps_at=utcnow())
        return self.states[trip_id]

    def feed(self, trip_id: str, event: Any, now: Optional[datetime] = None) -> List[Any]:
        now = now or utcnow()
        state = self.state(trip_id)
        new_state, actions = E.decide(state, event, now)
        self.states[trip_id] = new_state
        self.emit("engine", "%s -> %d action(s); status=%s" % (type(event).__name__, len(actions), new_state.status),
                  event=_jsonable(event), status=new_state.status)
        self.apply_actions(trip_id, actions, now)
        return actions

    def truck_update(self, trip_id: str, now: datetime) -> E.TruckUpdate:
        self.sim.tick(now)
        return E.TruckUpdate(**self.sim.update_dict(now))

    def scaled(self, after_s: int) -> float:
        speed = self.settings.demo_speed if self.settings.virtual else 1.0
        return after_s / max(0.1, speed)

    def apply_actions(self, trip_id: str, actions: List[Any], now: datetime) -> None:
        for a in actions:
            if isinstance(a, E.LogEvent):
                self.emit("decision", a.text)
            elif isinstance(a, E.ConsoleFlag):
                self.emit("flag", a.name, flag=a.name)
            elif isinstance(a, E.ScheduleTimer):
                fire_at = now + timedelta(seconds=self.scaled(a.after_s))
                self.timers.schedule(a.kind, trip_id, fire_at)
                self.emit("timer", "scheduled %s in %ds (fires %s)" % (a.kind, int(self.scaled(a.after_s)),
                                                                        ist(fire_at).strftime("%H:%M:%S")), timer=a.kind)
            elif isinstance(a, E.CancelTimer):
                self.timers.cancel(a.kind, trip_id)
                self.emit("timer", "cancelled %s" % a.kind, timer=a.kind)
            elif isinstance(a, E.PlaceCall):
                self.place_driver_call(trip_id, a, now)
            elif isinstance(a, E.AlertContact):
                self.place_alert_call(trip_id, a, now)

    def driver_for_trip(self, trip_id: str) -> Dict[str, Any]:
        trip = self.db.trip(trip_id)
        drv = self.db.driver(trip["driver_id"]) if trip else None
        return drv or {"id": "unknown", "name": "Ustaad", "phone": "", "registered": 0}

    def place_driver_call(self, trip_id: str, a: E.PlaceCall, now: datetime) -> None:
        drv = self.driver_for_trip(trip_id)
        st = self.state(trip_id)
        contacts = self.db.contacts_for(drv["id"])
        variables = {
            "driver_name": st.driver_name or drv["name"].split(" ")[0],
            "alert_contact_name": contacts.get("primary", {}).get("name", "ghar"),
            "destination": self.sim.destination,
            "first_call_tonight": "yes" if st.calls_placed <= 1 else "no",
            "call_reason": a.reason,
            "trip_id": trip_id,
        }
        if self.settings.virtual:
            self.emit("call", "virtual: would place %s to driver %s in %ds (no call placed)" % (
                a.reason, mask_phone(drv["phone"]), a.delay_s), reason=a.reason, virtual=True)
            self.db.record_call(trip_id, "virtual-%d" % st.calls_placed, a.reason, "khalasi", now)
            return
        outcome = self.client.place_call(drv["phone"], a.reason, variables, is_alert=False, driver_key=drv["id"])
        self.db.record_call(trip_id, outcome.attempt_id, a.reason, "khalasi", now)
        self.emit("call", "%s %s -> %s%s" % ("placed" if outcome.placed else "blocked", a.reason,
                                              outcome.masked_number,
                                              "" if outcome.placed else " (%s)" % outcome.blocked_reason),
                  reason=a.reason, placed=outcome.placed)

    def place_alert_call(self, trip_id: str, a: E.AlertContact, now: datetime) -> None:
        drv = self.driver_for_trip(trip_id)
        st = self.state(trip_id)
        contacts = self.db.contacts_for(drv["id"])
        contact = contacts.get(a.step) or {"name": a.step, "phone": self.settings.fleet_desk_phone}
        token = self.active_alert_token.get(trip_id)
        if token is None or (self.db.alert(token) or {}).get("resolved"):
            token = secrets.token_urlsafe(16)
            self.active_alert_token[trip_id] = token
            self.db.create_alert(token, trip_id, a.step, a.reason, now, self.sim.location_text(),
                                 ist(st.last_gps_at or now).strftime("%H:%M"), E.effective_moving(st, now))
        else:
            self.db.update_alert_step(trip_id, a.step)
        link = (self.settings.public_base_url.rstrip("/") or "") + "/a/" + token
        variables = {
            "contact_name": contact["name"], "driver_name": st.driver_name, "alert_reason": a.reason,
            "last_location": self.sim.location_text(),
            "last_seen_time": ist(st.last_gps_at or now).strftime("%H:%M"),
            "is_fleet_desk": "yes" if a.step == "fleet_desk" else "no", "trip_id": trip_id, "alert_step": a.step,
        }
        self.emit("alert", "alert chain step %s (%s); alert page %s" % (a.step, a.reason, link),
                  step=a.step, reason=a.reason, link=link, token=token)
        if self.settings.virtual:
            self.emit("call", "virtual: would ring %s (%s) with Khalasi Alert; no call placed" % (
                contact["name"], mask_phone(contact.get("phone"))), virtual=True)
            return
        outcome = self.client.place_call(contact.get("phone", ""), "alert", variables, is_alert=True, driver_key=drv["id"])
        self.db.record_call(trip_id, outcome.attempt_id, "alert_" + a.step, "alert", now)
        self.emit("call", "%s alert -> %s" % ("placed" if outcome.placed else "blocked (%s)" % outcome.blocked_reason,
                                              outcome.masked_number))
        # SMS of the alert link: stub (no provider configured); link is shown on the console instead.

    async def on_timer_fire(self, kind: str, trip_id: str) -> None:
        now = utcnow()
        if kind == T_PURGE:
            result = purge_old_records(self.db, now)
            self.emit("system", "R17 purge: %s" % result)
            self.timers.schedule(T_PURGE, "system", self.next_purge_time(now))
            return
        self.emit("timer", "fired %s" % kind, timer=kind)
        # before any scheduled call, re-check the truck
        self.feed(trip_id, self.truck_update(trip_id, now), now)
        self.feed(trip_id, E.Timer(kind), now)


def _jsonable(obj: Any) -> Any:
    try:
        return json.loads(json.dumps(asdict(obj), default=str))
    except Exception:
        return str(obj)


runtime = Runtime()


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime.bootstrap()
    runtime.scheduler.start()
    try:
        yield
    finally:
        await runtime.scheduler.stop()


app = FastAPI(title="Khalasi backend", lifespan=lifespan)


# --- auth -------------------------------------------------------------------------
def require_tool_secret(authorization: Optional[str] = Header(default=None)) -> None:
    secret = runtime.settings.tool_secret
    if not secret:
        return  # dev mode: TOOL_SECRET unset -> open (stubbed; set TOOL_SECRET for the demo)
    if not authorization or not authorization.startswith("Bearer ") or authorization[7:].strip() != secret:
        raise HTTPException(status_code=401, detail="bad or missing bearer token")


async def body_json(request: Request) -> Dict[str, Any]:
    try:
        data = await request.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


# --- Sarvam API tools (fast, in-memory) ---------------------------------------------
@app.post("/tools/truck-status", dependencies=[Depends(require_tool_secret)])
async def truck_status(request: Request):
    body = await body_json(request)
    trip_id = str(body.get("trip_id") or DEMO_TRIP_ID)
    now = utcnow()
    status = runtime.sim.truck_status(trip_id, now)
    st = runtime.state(trip_id)
    if st.last_rest_ended_at:
        status["last_rest_ended_at"] = ist(st.last_rest_ended_at).strftime("%H:%M")
        status["minutes_since_last_rest"] = int(E.minutes_since_last_rest(st, now) or 0)
    runtime.emit("tool", "truck_status -> moving=%s stopped_at=%s" % (status["moving"], status["stopped_at"]))
    return status


@app.post("/tools/log-status", dependencies=[Depends(require_tool_secret)])
async def log_status(request: Request):
    body = await body_json(request)
    trip_id = str(body.get("trip_id") or DEMO_TRIP_ID)
    state = str(body.get("state") or "")
    if state not in ("parked_resting", "driving_alert"):
        raise HTTPException(status_code=422, detail="state must be parked_resting or driving_alert")
    now = utcnow()
    runtime.db.record_log_status(trip_id, state, now)
    runtime.emit("tool", "log_status %s" % state, state=state, trip_id=trip_id)
    return {"ok": True}


@app.post("/tools/report-signal", dependencies=[Depends(require_tool_secret)])
async def report_signal(request: Request):
    body = await body_json(request)
    trip_id = str(body.get("trip_id") or DEMO_TRIP_ID)
    type_ = str(body.get("type") or "")
    detail = str(body.get("detail") or "")
    if type_ not in ("sleep_sign", "escalation", "promised_stop", "stop_refused", "quiet_requested", "care", "driver_swap"):
        raise HTTPException(status_code=422, detail="unknown signal type")
    now = utcnow()
    runtime.db.record_signal(trip_id, type_, detail, now)
    registered = None
    if type_ == "driver_swap":
        registered = runtime.db.driver_by_name(detail) is not None
    runtime.emit("signal", type_ if type_ == "care" else "%s %s" % (type_, detail), type=type_,
                 detail="" if type_ == "care" else detail)
    runtime.feed(trip_id, E.Signal(type_, detail, registered=registered), now)
    return {"ok": True}


# --- hooks and webhooks ---------------------------------------------------------------
@app.post("/hooks/on-start")
async def on_start(request: Request):
    body = await body_json(request)
    caller = str(body.get("caller_number") or body.get("from") or body.get("user_phone_number")
                 or body.get("phone") or "")
    drv = runtime.db.driver_by_phone(caller) if caller else None
    trip_id = DEMO_TRIP_ID
    now = utcnow()
    if drv is None:
        runtime.emit("call", "inbound from unregistered caller %s" % mask_phone(caller), unregistered=True)
        runtime.emit("flag", "unregistered_caller", flag="unregistered_caller")
        return {"driver_name": "Ustaad", "alert_contact_name": "", "destination": "", "first_call_tonight": "yes",
                "call_reason": "inbound", "trip_id": ""}
    contacts = runtime.db.contacts_for(drv["id"])
    st = runtime.state(trip_id)
    runtime.feed(trip_id, E.CallStarted("inbound"), now)
    return {"driver_name": drv["name"].split(" ")[0], "alert_contact_name": contacts.get("primary", {}).get("name", ""),
            "destination": runtime.sim.destination, "first_call_tonight": "yes" if st.calls_placed == 0 else "no",
            "call_reason": "inbound", "trip_id": trip_id}


@app.post("/webhooks/sarvam")
async def sarvam_webhook(
    request: Request,
    sarvam_signature: Optional[str] = Header(default=None, alias="Sarvam-Signature"),
    sarvam_timestamp: Optional[str] = Header(default=None, alias="Sarvam-Timestamp"),
):
    raw = await request.body()
    if not verify_signature(runtime.settings.sarvam_webhook_secret, raw, sarvam_signature, sarvam_timestamp):
        raise HTTPException(status_code=401, detail="bad signature")
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")
    now = utcnow()
    parsed = parse_webhook(payload)
    runtime.db.store_webhook(parsed.attempt_id, payload, now)
    call = runtime.db.call_by_attempt(parsed.attempt_id) if parsed.attempt_id else None
    trip_id = parsed.trip_id or (call or {}).get("trip_id") or DEMO_TRIP_ID
    reason = parsed.call_reason or (call or {}).get("reason")
    if parsed.transcript:
        runtime.db.store_transcript(trip_id, parsed.attempt_id, parsed.transcript, now)
    runtime.db.close_call(parsed.attempt_id, trip_id, parsed.status, now)
    # end time: the payload's end_datetime (ISO 8601 UTC); webhook arrival only as a fallback
    ended_at = parsed.end_datetime or now
    ls = runtime.db.last_log_status(trip_id)
    log_state, log_at = None, None
    if ls and ls.get("log_status_at"):
        log_at = datetime.fromisoformat(ls["log_status_at"])
        log_state = ls["log_status"]
    alert_step = parsed.metadata.get("alert_step") or None
    if parsed.metadata.get("kind") != "alert":
        alert_step = None
    ev = E.CallResult(status=parsed.status, end_state=log_state, ended_on_nudges=parsed.ended_on_nudges,
                      log_status_at=log_at, ended_at=ended_at, reason=reason, call_end_state=parsed.call_end_state,
                      alert_step=alert_step)
    runtime.emit("call", "webhook: %s%s" % (parsed.status, " (ends in nudges)" if parsed.ended_on_nudges else ""),
                 status=parsed.status, transcript=parsed.transcript, call_end_state=parsed.call_end_state)
    runtime.feed(trip_id, runtime.truck_update(trip_id, now), now)
    runtime.feed(trip_id, ev, now)
    return {"ok": True}


@app.post("/webhooks/missed-call")
async def missed_call(request: Request):
    body = await body_json(request)
    caller = str(body.get("caller_number") or body.get("from") or body.get("phone") or "")
    drv = runtime.db.driver_by_phone(caller) if caller else None
    runtime.emit("call", "missed call from %s" % mask_phone(caller))
    runtime.feed(DEMO_TRIP_ID, E.MissedCall(registered=drv is not None), utcnow())
    return {"ok": True}


# --- console stream ---------------------------------------------------------------------
@app.get("/stream/console")
async def stream_console():
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    runtime.subscribers.append(q)

    async def gen():
        try:
            for ev in runtime.events[-50:]:
                yield "data: %s\n\n" % json.dumps(ev, default=str)
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield "data: %s\n\n" % json.dumps(ev, default=str)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            if q in runtime.subscribers:
                runtime.subscribers.remove(q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/state")
async def state_view():
    return {tid: _jsonable(st) for tid, st in runtime.states.items()}


# --- alert page -----------------------------------------------------------------------
HEADLINES = {
    "not_answering": ("{d} ji dhai minute se jawab nahi de rahe", "{d} hasn't answered for 2½ minutes"),
    "unreachable": ("{d} ji ka phone nahi lag raha.", "{d}'s phone is unreachable."),
    "no_network": ("{d} ji ka phone nahi lag raha. Shayad network nahi hai.",
                   "{d}'s phone is unreachable. He may be in a no-network stretch."),
}


@app.get("/a/{token}")
async def alert_page(token: str):
    row = runtime.db.alert(token)
    if not row:
        raise HTTPException(status_code=404, detail="unknown alert")
    if datetime.fromisoformat(row["expires_at"]) < utcnow():
        raise HTTPException(status_code=410, detail="alert link expired")
    st = runtime.state(row["trip_id"])
    hi, en = HEADLINES.get(row["reason"], HEADLINES["not_answering"])
    drv = runtime.driver_for_trip(row["trip_id"])
    return {
        "token": token, "driver_name": st.driver_name, "reason": row["reason"], "step": row["step"],
        "headline_hi": hi.format(d=st.driver_name), "headline_en": en.format(d=st.driver_name),
        "last_location": row["last_location"], "last_seen_time": row["last_seen_time"], "moving": bool(row["moving"]),
        "resolved": bool(row["resolved"]), "false_alarm": None if row["false_alarm"] is None else bool(row["false_alarm"]),
        "expires_at": row["expires_at"], "call_driver": "tel:" + (drv.get("phone") or ""), "call_112": "tel:112",
        "simulated": runtime.settings.virtual,
    }


@app.post("/a/{token}/safe")
async def alert_safe(token: str, request: Request):
    body = await body_json(request)
    row = runtime.db.alert(token)
    if not row:
        raise HTTPException(status_code=404, detail="unknown alert")
    false_alarm = bool(body.get("false_alarm", False))
    runtime.db.resolve_alert(token, false_alarm)
    runtime.feed(row["trip_id"], E.AlertResolved(false_alarm=false_alarm), utcnow())
    return {"ok": True}


# --- demo controls (virtual mode) --------------------------------------------------------
DEMO_TRUCK_MODES = {"moving": "moving", "stopped_dhaba": "stopped_dhaba", "stopped_highway": "stopped_highway",
                    "dhaba": "stopped_dhaba", "highway": "stopped_highway"}


@app.post("/demo/truck")
async def demo_truck(request: Request):
    body = await body_json(request)
    mode = DEMO_TRUCK_MODES.get(str(body.get("mode") or ""))
    if mode is None:
        raise HTTPException(status_code=422, detail="mode must be moving | stopped_dhaba | stopped_highway")
    now = utcnow()
    runtime.sim.set_mode(mode, now)
    if body.get("gps_age_s") is not None:
        runtime.sim.set_gps_age(int(body["gps_age_s"]))
    runtime.emit("truck", "truck -> %s" % mode, mode=mode)
    runtime.feed(DEMO_TRIP_ID, runtime.truck_update(DEMO_TRIP_ID, now), now)
    return {"ok": True, "truck": runtime.sim.truck_status(DEMO_TRIP_ID, now)}


@app.post("/demo/event")
async def demo_event(request: Request):
    body = await body_json(request)
    kind = str(body.get("kind") or "")
    now = utcnow()
    st = runtime.state(DEMO_TRIP_ID)
    reason = st.active_call_reason or "check_in"
    runtime.feed(DEMO_TRIP_ID, runtime.truck_update(DEMO_TRIP_ID, now), now)
    if kind == "silence":
        ev: Any = E.CallResult("connected", ended_on_nudges=True, ended_at=now, reason=reason)
    elif kind == "no_answer":
        ev = E.CallResult("no_answer", reason=reason)
    elif kind == "unreachable":
        ev = E.CallResult("failed", reason=reason)
    elif kind == "dark_stretch":
        runtime.sim.force_dark_stretch(15, 40)
        ev = runtime.truck_update(DEMO_TRIP_ID, now)
    elif kind == "chup":
        runtime.feed(DEMO_TRIP_ID, E.Signal("quiet_requested"), now)
        ev = E.CallResult("connected", end_state="driving_alert", log_status_at=now, ended_at=now, reason=reason)
    elif kind == "alert_no_answer":
        ev = E.CallResult("no_answer", alert_step=st.alert_step or "primary")
    elif kind == "resolved":
        ev = E.AlertResolved(false_alarm=bool(body.get("false_alarm", False)))
    else:
        raise HTTPException(status_code=422, detail="kind must be silence | no_answer | unreachable | dark_stretch | chup")
    runtime.emit("demo", "demo event %s" % kind, event_kind=kind)
    actions = runtime.feed(DEMO_TRIP_ID, ev, now)
    return {"ok": True, "actions": [_jsonable(a) for a in actions], "status": runtime.state(DEMO_TRIP_ID).status}


@app.get("/health")
async def health():
    return {"ok": True, "mode": runtime.settings.demo_mode, "calls_enabled": runtime.settings.calls_enabled,
            "pending_timers": len(runtime.timers.load_pending())}
