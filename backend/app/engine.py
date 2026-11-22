"""Khalasi pure decision engine.

decide(state, event, now) -> (new_state, actions)

No I/O, no clocks, no randomness. The scheduler and Sarvam client carry out
the actions. Rules R1-R16 from MASTER_PROMPT section 7. Python 3.9 compatible.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Union

from . import config as C

# --- Vocabulary --------------------------------------------------------------
SAFE_STOP_TYPES = ("apna_ghar", "petrol_pump", "dhaba", "lay_by")
HIGHWAY = "highway"

# Call reasons (exact strings from Appendix A)
INBOUND = "inbound"
CALLBACK = "callback"
CHECK_IN = "check_in"
SILENCE_CALLBACK = "silence_callback"
STOPPED_CHECK = "stopped_check"
DARK_STRETCH_WARNING = "dark_stretch_warning"
COVERAGE_RETURN = "coverage_return"
PROMISED_STOP_FOLLOWUP = "promised_stop_followup"
QUIET_RETURN = "quiet_return"
CALL_REASONS = (
    INBOUND, CALLBACK, CHECK_IN, SILENCE_CALLBACK, STOPPED_CHECK,
    DARK_STRETCH_WARNING, COVERAGE_RETURN, PROMISED_STOP_FOLLOWUP, QUIET_RETURN,
)

# Alert chain
PRIMARY, BACKUP, FLEET_DESK = "primary", "backup", "fleet_desk"
FULL_CHAIN: Tuple[str, ...] = (PRIMARY, BACKUP, FLEET_DESK)
FLEET_ONLY_CHAIN: Tuple[str, ...] = (FLEET_DESK,)
NOT_ANSWERING, UNREACHABLE, NO_NETWORK = "not_answering", "unreachable", "no_network"

# Timer kinds
T_CHECK_IN = "check_in"
T_SILENCE_RETRY = "silence_retry"
T_UNREACHABLE_RETRY = "unreachable_retry"
T_PROMISED_STOP = "promised_stop_check"
T_QUIET_RETURN = "quiet_return"
T_COVERAGE_RETURN = "coverage_return"

# Driver statuses (console)
DRIVING, RESTING, TALKING, NO_RESPONSE, UNREACHABLE_ST, ALERTING = (
    "driving", "resting", "talking", "no_response", "unreachable", "alerting",
)


# --- State -------------------------------------------------------------------
@dataclass
class TripState:
    trip_id: str = "trip-demo"
    driver_name: str = "Raju"
    driver_registered: bool = True
    trip_started_at: Optional[datetime] = None
    # truck
    moving: bool = True
    stopped_at_type: Optional[str] = None     # SAFE_STOP_TYPES | "highway" | None
    stopped_at_name: Optional[str] = None
    stopped_since: Optional[datetime] = None
    last_gps_at: Optional[datetime] = None     # None => unknown => treated as moving
    last_rest_ended_at: Optional[datetime] = None
    # dark stretch (known, ahead or current)
    dark_stretch_id: Optional[str] = None
    dark_stretch_starts_at: Optional[datetime] = None
    dark_stretch_ends_at: Optional[datetime] = None
    dark_warned: Tuple[str, ...] = ()
    # calls
    status: str = DRIVING
    resting: bool = False
    in_call: bool = False
    active_call_reason: Optional[str] = None
    last_call_at: Optional[datetime] = None
    calls_placed: int = 0
    # silence / R3-R5
    silence_began_at: Optional[datetime] = None
    silence_retries: int = 0
    # unreachable / R6
    unreachable_since: Optional[datetime] = None
    unreachable_mode: Optional[str] = None     # "dark" | "moving"
    unreachable_deadline: Optional[datetime] = None
    unreachable_reason: Optional[str] = None   # call reason being retried
    unreachable_retries: int = 0
    # alert chain / R7
    alert_chain: Tuple[str, ...] = FULL_CHAIN
    alert_step: Optional[str] = None
    alert_reason: Optional[str] = None
    alert_started_at: Optional[datetime] = None
    # signals
    care_flag: bool = False
    promised_stop_at: Optional[datetime] = None
    stop_refused_stretch: Optional[str] = None
    quiet_requested_at: Optional[datetime] = None
    # timers the engine believes are pending
    pending_timers: Tuple[str, ...] = ()


# --- Events ------------------------------------------------------------------
@dataclass
class CallResult:
    status: str                                   # connected | no_answer | busy | failed
    end_state: Optional[str] = None               # from log_status, if called
    ended_on_nudges: bool = False
    log_status_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    reason: Optional[str] = None                  # call reason; defaults to active call
    call_end_state: Optional[str] = None          # Sarvam post-call variable: NEVER used
    max_length_reached: bool = False
    alert_step: Optional[str] = None              # set when this is a Khalasi Alert call result


@dataclass
class TruckUpdate:
    moving: bool = True
    stopped_at_type: Optional[str] = None
    stopped_at_name: Optional[str] = None
    gps_age_s: int = 0
    dark_stretch_id: Optional[str] = None
    dark_stretch_starts_in_min: Optional[float] = None  # negative => inside
    dark_stretch_lasts_min: Optional[float] = None
    speed_kmph: float = 0.0


@dataclass
class Signal:
    type: str
    detail: str = ""
    registered: Optional[bool] = None   # driver_swap: is the named driver registered?


@dataclass
class Timer:
    kind: str


@dataclass
class MissedCall:
    registered: bool = True


@dataclass
class AlertResolved:
    false_alarm: bool = False


@dataclass
class CallStarted:
    reason: str = INBOUND


Event = Union[CallResult, TruckUpdate, Signal, Timer, MissedCall, AlertResolved, CallStarted]


# --- Actions -----------------------------------------------------------------
@dataclass
class PlaceCall:
    reason: str
    delay_s: int = 0


@dataclass
class AlertContact:
    step: str      # primary | backup | fleet_desk
    reason: str    # not_answering | unreachable | no_network


@dataclass
class ScheduleTimer:
    kind: str
    after_s: int


@dataclass
class CancelTimer:
    kind: str


@dataclass
class LogEvent:
    text: str


@dataclass
class ConsoleFlag:
    name: str


Action = Union[PlaceCall, AlertContact, ScheduleTimer, CancelTimer, LogEvent, ConsoleFlag]


# --- Helpers -----------------------------------------------------------------
def _ist(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now
    return now.astimezone(C.IST)


def gps_stale(state: TripState, now: datetime) -> bool:
    if state.last_gps_at is None:
        return True
    return (now - state.last_gps_at) > C.GPS_STALE


def effective_moving(state: TripState, now: datetime) -> bool:
    """R14: GPS older than 5 min counts as moving, location unknown."""
    return state.moving or gps_stale(state, now)


def at_safe_stop(state: TripState, now: datetime) -> bool:
    return (not effective_moving(state, now)) and state.stopped_at_type in SAFE_STOP_TYPES


def on_highway(state: TripState, now: datetime) -> bool:
    return (not effective_moving(state, now)) and state.stopped_at_type == HIGHWAY


def minutes_since_last_rest(state: TripState, now: datetime) -> Optional[float]:
    anchor = state.last_rest_ended_at or state.trip_started_at
    if anchor is None:
        return None
    return (now - anchor).total_seconds() / 60.0


def rest_due(state: TripState, now: datetime) -> bool:
    mins = minutes_since_last_rest(state, now)
    return mins is not None and mins >= C.REST_DUE_H * 60


def in_check_in_hours(now: datetime) -> bool:
    h = _ist(now).hour
    return C.CHECK_IN_START_HOUR <= h < C.CHECK_IN_END_HOUR


def dark_stretch_in_window(state: TripState, now: datetime, minutes: float) -> bool:
    """A known stretch starts within `minutes` (or we are already inside it)."""
    if state.dark_stretch_starts_at is None or state.dark_stretch_ends_at is None:
        return False
    if now >= state.dark_stretch_ends_at:
        return False
    return (state.dark_stretch_starts_at - now) <= timedelta(minutes=minutes)


def in_or_near_dark_stretch(state: TripState, now: datetime) -> bool:
    return dark_stretch_in_window(state, now, C.DARK_STRETCH_LOOKAHEAD_MIN)


def valid_end_state(ev: CallResult, now: datetime) -> Optional[str]:
    """The log_status value counts only if the call ended within ~30 s of it.

    A transcript ending in unanswered nudges never has a valid end state.
    Sarvam's call_end_state and any LLM analysis never count.
    """
    if ev.status != "connected":
        return None
    if ev.ended_on_nudges:
        return None
    if ev.end_state not in ("parked_resting", "driving_alert"):
        return None
    if ev.log_status_at is None:
        return None
    ended_at = ev.ended_at or now
    gap = abs((ended_at - ev.log_status_at).total_seconds())
    if gap > C.VALID_END_WINDOW_S:
        return None
    return ev.end_state


def ending_label(ev: CallResult) -> str:
    return "silence" if ev.ended_on_nudges else "dropped"


class _Ctx:
    """Mutable working copy of the state plus the action list."""

    def __init__(self, state: TripState, now: datetime) -> None:
        self.s = replace(state)
        self.now = now
        self.actions: List[Action] = []

    # action emitters -------------------------------------------------------
    def log(self, text: str) -> None:
        self.actions.append(LogEvent(text))

    def flag(self, name: str) -> None:
        self.actions.append(ConsoleFlag(name))

    def schedule(self, kind: str, after_s: float) -> None:
        after = int(max(0, round(after_s)))
        if kind in self.s.pending_timers:
            self.actions.append(CancelTimer(kind))
        else:
            self.s.pending_timers = self.s.pending_timers + (kind,)
        self.actions.append(ScheduleTimer(kind, after))

    def cancel(self, kind: str) -> None:
        if kind in self.s.pending_timers:
            self.s.pending_timers = tuple(k for k in self.s.pending_timers if k != kind)
            self.actions.append(CancelTimer(kind))

    def consume_timer(self, kind: str) -> None:
        self.s.pending_timers = tuple(k for k in self.s.pending_timers if k != kind)

    def place_call(self, reason: str, delay_s: int = 0) -> None:
        self.actions.append(PlaceCall(reason, delay_s))
        self.s.active_call_reason = reason
        self.s.in_call = True
        self.s.last_call_at = self.now
        self.s.calls_placed += 1
        self.log("engine: place_call %s (delay %ss)" % (reason, delay_s))

    def start_alert_chain(self, reason: str) -> None:
        s = self.s
        if s.alert_step is not None and s.alert_step != "exhausted":
            self.log("engine: alert chain already running at %s" % s.alert_step)
            return
        chain = s.alert_chain if s.driver_registered else FLEET_ONLY_CHAIN
        step = chain[0]
        s.alert_step = step
        s.alert_reason = reason
        s.alert_started_at = self.now
        s.status = ALERTING
        self.cancel(T_SILENCE_RETRY)
        self.cancel(T_UNREACHABLE_RETRY)
        self.actions.append(AlertContact(step, reason))
        self.log("engine: alert %s -> %s" % (reason, step))

    def next_alert_step(self) -> None:
        s = self.s
        chain = s.alert_chain if s.driver_registered else FLEET_ONLY_CHAIN
        if s.alert_step not in chain:
            s.alert_step = "exhausted"
            self.log("engine: alert chain exhausted")
            self.flag("alert_chain_exhausted")
            return
        idx = chain.index(s.alert_step)
        if idx + 1 >= len(chain):
            s.alert_step = "exhausted"
            self.log("engine: alert chain exhausted (fleet desk did not answer)")
            self.flag("alert_chain_exhausted")
            return
        step = chain[idx + 1]
        s.alert_step = step
        self.actions.append(AlertContact(step, s.alert_reason or NOT_ANSWERING))
        self.log("engine: alert %s -> %s" % (s.alert_reason, step))

    def clear_unreachable(self) -> None:
        s = self.s
        s.unreachable_since = None
        s.unreachable_mode = None
        s.unreachable_deadline = None
        s.unreachable_reason = None
        s.unreachable_retries = 0
        self.cancel(T_UNREACHABLE_RETRY)

    # shared rule bodies ---------------------------------------------------
    def apply_r3(self, origin: str) -> None:
        """R3: no valid end state (or unanswered call) -> by truck state."""
        s, now = self.s, self.now
        if at_safe_stop(s, now):
            self.log("engine: R3 %s but truck at %s (%s): presume resting, no call"
                     % (origin, s.stopped_at_name or s.stopped_at_type, s.stopped_at_type))
            s.status = RESTING
            s.resting = True
            self.cancel(T_CHECK_IN)
            return
        if on_highway(s, now):
            self.log("engine: R3 %s, truck stopped on the highway: one stopped_check" % origin)
            s.status = NO_RESPONSE
            self.place_call(STOPPED_CHECK, C.CALLBACK_DELAY_S)
            return
        # moving or GPS unknown
        s.status = NO_RESPONSE
        if s.silence_began_at is None:
            s.silence_began_at = now
        s.silence_retries = 0
        self.log("engine: R3 %s while moving/GPS unknown: silence_callback" % origin)
        self.place_call(SILENCE_CALLBACK, C.CALLBACK_DELAY_S)

    def maybe_arm_check_in(self) -> None:
        s, now = self.s, self.now
        if s.resting or s.in_call or not effective_moving(s, now):
            return
        if not in_check_in_hours(now):
            return
        if T_CHECK_IN in s.pending_timers:
            return
        if s.alert_step not in (None, "exhausted"):
            return
        self.schedule(T_CHECK_IN, C.CHECK_IN_INTERVAL_MIN * 60)

    def recheck_truck_skip(self, what: str) -> bool:
        """Before any scheduled call, re-check the truck; skip at a safe stop."""
        if at_safe_stop(self.s, self.now):
            self.log("engine: %s skipped, truck at %s (%s)" % (
                what, self.s.stopped_at_name or self.s.stopped_at_type, self.s.stopped_at_type))
            return True
        return False


# --- Event handlers ------------------------------------------------------------
def _on_truck_update(c: _Ctx, ev: TruckUpdate) -> None:
    s, now = c.s, c.now
    was_moving = effective_moving(s, now)
    was_stop_type = s.stopped_at_type

    s.last_gps_at = now - timedelta(seconds=max(0, ev.gps_age_s))
    s.moving = bool(ev.moving)
    if s.moving:
        s.stopped_at_type = None
        s.stopped_at_name = None
    else:
        s.stopped_at_type = ev.stopped_at_type or HIGHWAY
        s.stopped_at_name = ev.stopped_at_name

    # dark stretch bookkeeping
    if ev.dark_stretch_starts_in_min is not None and ev.dark_stretch_lasts_min is not None:
        sid = ev.dark_stretch_id or "ds-%d" % int(
            (now + timedelta(minutes=ev.dark_stretch_starts_in_min)).timestamp() // 60)
        s.dark_stretch_id = sid
        s.dark_stretch_starts_at = now + timedelta(minutes=ev.dark_stretch_starts_in_min)
        s.dark_stretch_ends_at = s.dark_stretch_starts_at + timedelta(minutes=ev.dark_stretch_lasts_min)
    elif s.dark_stretch_ends_at is not None and now >= s.dark_stretch_ends_at:
        s.dark_stretch_id = None
        s.dark_stretch_starts_at = None
        s.dark_stretch_ends_at = None

    now_moving = effective_moving(s, now)

    # rest accounting: stay 30+ min at a known stop (or confirmed rest) => reset
    if not now_moving:
        if s.stopped_since is None or was_moving:
            s.stopped_since = now
    else:
        if s.stopped_since is not None:
            stayed = now - s.stopped_since
            counted = (was_stop_type in SAFE_STOP_TYPES) or s.resting
            if counted and stayed >= C.REST_RESET:
                s.last_rest_ended_at = now
                c.log("engine: rest of %d min counted, 5-hour clock reset" % int(stayed.total_seconds() // 60))
            elif stayed > timedelta(0):
                c.log("engine: stop of %d min did not count as rest" % int(stayed.total_seconds() // 60))
        s.stopped_since = None
        if s.resting:
            s.resting = False
            s.status = DRIVING if s.alert_step in (None, "exhausted") else s.status
            c.log("engine: truck moving again, check-ins resume")

    # R6: during any unreachable wait, a stop on the highway alerts at once
    if s.unreachable_since is not None and on_highway(s, now):
        c.log("engine: truck stopped on the highway while phone unreachable")
        c.clear_unreachable()
        c.start_alert_chain(UNREACHABLE)
        return

    # unreachable wait ends when the truck is at a safe stop
    if s.unreachable_since is not None and at_safe_stop(s, now):
        c.log("engine: truck at a safe stop, unreachable retries stopped")
        c.clear_unreachable()
        s.status = RESTING

    # R8: dark stretch warning, once per stretch
    if (s.dark_stretch_id is not None
            and s.dark_stretch_id not in s.dark_warned
            and dark_stretch_in_window(s, now, C.DARK_STRETCH_LOOKAHEAD_MIN)
            and rest_due(s, now)
            and not at_safe_stop(s, now)):
        s.dark_warned = s.dark_warned + (s.dark_stretch_id,)
        if s.in_call:
            c.log("engine: dark stretch within 20 min and rest due; truck_status tells the agent in-call")
        else:
            c.log("engine: R8 dark stretch within 20 min and 5+ h since rest")
            c.place_call(DARK_STRETCH_WARNING, 0)

    c.maybe_arm_check_in()


def _on_call_result(c: _Ctx, ev: CallResult) -> None:
    s, now = c.s, c.now

    # Khalasi Alert (family agent) call results drive the chain (R7)
    if ev.alert_step is not None:
        if ev.status == "connected":
            c.log("engine: alert contact %s reached" % ev.alert_step)
            c.flag("alert_reached_%s" % ev.alert_step)
        else:
            c.log("engine: alert contact %s %s" % (ev.alert_step, ev.status))
            c.next_alert_step()
        return

    reason = ev.reason or s.active_call_reason or INBOUND
    s.in_call = False
    s.active_call_reason = None
    s.last_call_at = ev.ended_at or now

    if ev.status == "connected":
        end = valid_end_state(ev, now)
        if end == "parked_resting":
            # R1
            s.status = RESTING
            s.resting = True
            s.silence_began_at = None
            s.silence_retries = 0
            s.stopped_since = s.stopped_since or now
            c.clear_unreachable()
            c.cancel(T_CHECK_IN)
            c.log("engine: R1 valid parked_resting: resting, check-ins paused until the truck moves")
            return
        if end == "driving_alert":
            # R2
            s.status = DRIVING
            s.resting = False
            s.silence_began_at = None
            s.silence_retries = 0
            c.clear_unreachable()
            c.log("engine: R2 valid driving_alert: driving")
            if in_check_in_hours(now):
                c.schedule(T_CHECK_IN, C.CHECK_IN_INTERVAL_MIN * 60)
            return
        # no valid end state
        label = ending_label(ev)
        if ev.max_length_reached:
            label = "dropped (max call length)"
        if ev.end_state and ev.log_status_at is not None and not ev.ended_on_nudges:
            c.log("engine: log_status %s was %d s before the end, outside the %d s window"
                  % (ev.end_state, int(abs(((ev.ended_at or now) - ev.log_status_at).total_seconds())),
                     C.VALID_END_WINDOW_S))
        if ev.call_end_state:
            c.log("engine: ignoring Sarvam call_end_state=%s (LLM output never counts)" % ev.call_end_state)
        c.log("engine: call %s ended without a valid end state: %s" % (reason, label))
        if ev.ended_on_nudges and s.silence_began_at is None:
            s.silence_began_at = (ev.ended_at or now) - timedelta(seconds=C.HANGUP_S)
        c.apply_r3("unexpected end (%s)" % label)
        return

    if ev.status in ("no_answer", "busy"):
        if reason == SILENCE_CALLBACK:
            # R4
            if s.silence_retries < 1:
                s.silence_retries += 1
                c.log("engine: R4 silence_callback %s: retry once after %d s" % (ev.status, C.RETRY_DELAY_S))
                c.schedule(T_SILENCE_RETRY, C.RETRY_DELAY_S)
            else:
                c.log("engine: R4 silence_callback %s again: alert chain" % ev.status)
                c.start_alert_chain(NOT_ANSWERING)
            return
        if reason == STOPPED_CHECK:
            c.log("engine: R3 stopped_check %s: alert chain" % ev.status)
            c.start_alert_chain(NOT_ANSWERING)
            return
        # R5: any other Khalasi call -> R3 by truck state
        c.apply_r3("%s %s" % (reason, ev.status))
        return

    if ev.status == "failed":
        _on_failed(c, reason)
        return

    c.log("engine: unknown call status %r, treated as dropped" % ev.status)
    c.apply_r3("unknown status")


def _on_failed(c: _Ctx, reason: str) -> None:
    """R6: Khalasi call failed (unreachable)."""
    s, now = c.s, c.now
    if at_safe_stop(s, now):
        c.log("engine: R6 unreachable but truck at a safe stop: no action")
        c.clear_unreachable()
        return
    if s.unreachable_since is None:
        # first failure: decide the mode
        if in_or_near_dark_stretch(s, now) and s.dark_stretch_ends_at is not None:
            s.unreachable_mode = "dark"
            s.unreachable_deadline = s.dark_stretch_ends_at + timedelta(minutes=C.UNREACHABLE_CAP_MIN)
            c.log("engine: R6 unreachable in/near a known dark stretch: retry every %d min until %s"
                  % (C.UNREACHABLE_RETRY_MIN, s.unreachable_deadline.strftime("%H:%M")))
        elif s.moving and not gps_stale(s, now):
            s.unreachable_mode = "moving"
            s.unreachable_deadline = now + timedelta(minutes=C.UNREACHABLE_CAP_MIN)
            c.log("engine: R6 unreachable while moving with fresh GPS: retry every %d min for %d min"
                  % (C.UNREACHABLE_RETRY_MIN, C.UNREACHABLE_CAP_MIN))
        else:
            c.log("engine: R6 unreachable, stopped on the highway or GPS stale: alert now")
            c.start_alert_chain(UNREACHABLE)
            return
        s.unreachable_since = now
        s.unreachable_reason = reason
        s.unreachable_retries = 0
        s.status = UNREACHABLE_ST
    # already waiting (or just started): deadline check
    if s.unreachable_deadline is not None and now >= s.unreachable_deadline:
        alert_reason = NO_NETWORK if s.unreachable_mode == "dark" else UNREACHABLE
        c.log("engine: R6 still unreachable at the deadline: alert %s" % alert_reason)
        c.clear_unreachable()
        c.start_alert_chain(alert_reason)
        return
    c.schedule(T_UNREACHABLE_RETRY, C.UNREACHABLE_RETRY_MIN * 60)


def _on_timer(c: _Ctx, ev: Timer) -> None:
    s, now = c.s, c.now
    c.consume_timer(ev.kind)
    kind = ev.kind

    if kind == T_CHECK_IN:
        if s.resting:
            c.log("engine: check-in skipped, driver resting")
            return
        if c.recheck_truck_skip("check-in"):
            return
        if not in_check_in_hours(now):
            c.log("engine: check-in skipped, outside midnight-6 am")
            return
        if s.in_call:
            c.log("engine: check-in skipped, call in progress")
            c.schedule(T_CHECK_IN, C.CHECK_IN_INTERVAL_MIN * 60)
            return
        if s.last_call_at is not None and (now - s.last_call_at) < timedelta(minutes=C.CHECK_IN_RECENT_CALL_MIN):
            wait = (s.last_call_at + C.CHECK_IN_INTERVAL - now).total_seconds()
            c.log("engine: check-in skipped, a call happened in the last %d min" % C.CHECK_IN_RECENT_CALL_MIN)
            c.schedule(T_CHECK_IN, max(60, wait))
            return
        c.place_call(CHECK_IN, 0)
        return

    if kind == T_SILENCE_RETRY:
        if c.recheck_truck_skip("silence_callback retry"):
            s.status = RESTING
            return
        c.place_call(SILENCE_CALLBACK, 0)
        return

    if kind == T_UNREACHABLE_RETRY:
        if s.unreachable_since is None:
            return
        if c.recheck_truck_skip("unreachable retry"):
            c.clear_unreachable()
            return
        if on_highway(s, now):
            c.clear_unreachable()
            c.start_alert_chain(UNREACHABLE)
            return
        if s.unreachable_deadline is not None and now >= s.unreachable_deadline:
            alert_reason = NO_NETWORK if s.unreachable_mode == "dark" else UNREACHABLE
            c.clear_unreachable()
            c.start_alert_chain(alert_reason)
            return
        s.unreachable_retries += 1
        c.place_call(s.unreachable_reason or SILENCE_CALLBACK, 0)
        return

    if kind == T_PROMISED_STOP:
        s.promised_stop_at = None
        if at_safe_stop(s, now) or s.resting:
            c.log("engine: R10 promised stop kept at %s" % (s.stopped_at_name or s.stopped_at_type))
            c.flag("promise_kept")
            return
        c.log("engine: R10 promised stop, truck still moving after %d min" % C.PROMISE_CHECK_MIN)
        c.place_call(PROMISED_STOP_FOLLOWUP, 0)
        return

    if kind == T_QUIET_RETURN:
        s.quiet_requested_at = None
        if c.recheck_truck_skip("quiet_return"):
            return
        c.place_call(QUIET_RETURN, 0)
        return

    if kind == T_COVERAGE_RETURN:
        s.stop_refused_stretch = None
        if c.recheck_truck_skip("coverage_return"):
            return
        c.place_call(COVERAGE_RETURN, 0)
        return

    c.log("engine: unknown timer %s ignored" % kind)


def _on_signal(c: _Ctx, ev: Signal) -> None:
    s, now = c.s, c.now
    t = ev.type

    if t == "care":
        # R15: flag only, no details, never reaches the fleet
        s.care_flag = True
        c.flag("care")
        return

    if t == "driver_swap":
        # R13
        if ev.registered:
            s.driver_name = ev.detail or s.driver_name
            s.driver_registered = True
            s.alert_chain = FULL_CHAIN
            c.log("engine: R13 driver swap to registered driver %s; alerts use their contacts" % s.driver_name)
            c.flag("driver_swapped")
        else:
            s.driver_name = ev.detail or "Ustaad"
            s.driver_registered = False
            s.alert_chain = FLEET_ONLY_CHAIN
            c.log("engine: R13 driver swap to unregistered driver; alerts go to the fleet night desk")
            c.flag("unregistered_driver")
        return

    if t == "promised_stop":
        # R10
        s.promised_stop_at = now
        c.log("engine: R10 promised stop, follow-up check in %d min" % C.PROMISE_CHECK_MIN)
        c.schedule(T_PROMISED_STOP, C.PROMISE_CHECK_MIN * 60)
        return

    if t == "stop_refused":
        # R9
        if s.dark_stretch_ends_at is not None and s.dark_stretch_ends_at > now:
            s.stop_refused_stretch = s.dark_stretch_id
            wait = (s.dark_stretch_ends_at - now).total_seconds()
            c.log("engine: R9 stop refused before dark stretch; coverage_return at %s"
                  % _ist(s.dark_stretch_ends_at).strftime("%H:%M"))
            c.schedule(T_COVERAGE_RETURN, wait)
        else:
            c.log("engine: stop refused (no dark stretch ahead)")
        c.flag("stop_refused")
        return

    if t == "quiet_requested":
        # R11
        s.quiet_requested_at = now
        wait = C.QUIET_MIN * 60.0
        if dark_stretch_in_window(s, now, C.QUIET_MIN) and s.dark_stretch_starts_at is not None:
            until_start = (s.dark_stretch_starts_at - now).total_seconds()
            wait = min(wait, max(60.0, until_start - 120.0))
            c.log("engine: R11 quiet requested, dark stretch within 10 min: call back sooner")
        else:
            c.log("engine: R11 quiet requested: quiet_return in %d min" % C.QUIET_MIN)
        c.schedule(T_QUIET_RETURN, wait)
        c.flag("quiet")
        return

    if t == "sleep_sign":
        c.log("engine: sleep sign: %s" % (ev.detail or ""))
        c.flag("sleep_sign")
        return

    if t == "escalation":
        c.flag("escalation_%s" % (ev.detail or "amber"))
        return

    c.log("engine: signal %s" % t)


def _on_missed_call(c: _Ctx, ev: MissedCall) -> None:
    # R16
    if ev.registered and c.s.driver_registered:
        c.log("engine: R16 missed call from registered driver: callback within %d s" % C.MISSED_CALL_CALLBACK_S)
        c.place_call(CALLBACK, min(C.MISSED_CALL_CALLBACK_S, C.CALLBACK_DELAY_S))
    else:
        c.log("engine: missed call from an unregistered number: no callback")
        c.flag("unregistered_caller")


def _on_alert_resolved(c: _Ctx, ev: AlertResolved) -> None:
    s = c.s
    s.alert_step = None
    s.alert_reason = None
    s.alert_started_at = None
    s.silence_began_at = None
    s.silence_retries = 0
    c.clear_unreachable()
    c.cancel(T_SILENCE_RETRY)
    s.status = RESTING if s.resting else DRIVING
    if ev.false_alarm:
        c.log("engine: alert resolved as a false alarm")
        c.flag("false_alarm")
    else:
        c.log("engine: alert resolved, driver safe")
        c.flag("driver_safe")


def _on_call_started(c: _Ctx, ev: CallStarted) -> None:
    s = c.s
    s.in_call = True
    s.active_call_reason = ev.reason
    s.last_call_at = c.now
    s.status = TALKING
    c.log("engine: call started (%s)" % ev.reason)


# --- Entry point ---------------------------------------------------------------
def decide(state: TripState, event: Event, now: datetime) -> Tuple[TripState, List[Action]]:
    """Pure decision function. Returns a new state and the actions to carry out."""
    c = _Ctx(state, now)
    if isinstance(event, CallResult):
        _on_call_result(c, event)
    elif isinstance(event, TruckUpdate):
        _on_truck_update(c, event)
    elif isinstance(event, Signal):
        _on_signal(c, event)
    elif isinstance(event, Timer):
        _on_timer(c, event)
    elif isinstance(event, MissedCall):
        _on_missed_call(c, event)
    elif isinstance(event, AlertResolved):
        _on_alert_resolved(c, event)
    elif isinstance(event, CallStarted):
        _on_call_started(c, event)
    else:
        c.log("engine: unknown event %r ignored" % (event,))
    return c.s, c.actions
