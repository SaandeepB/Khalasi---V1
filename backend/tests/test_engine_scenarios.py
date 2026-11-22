"""Scenario tests 1-25 from MASTER_PROMPT section 7, run against the pure engine.

Fully offline: no network, no clocks, no DB.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import pytest

from app import config as C
from app.engine import (
    AlertContact, AlertResolved, CallResult, CallStarted, CancelTimer, ConsoleFlag, LogEvent,
    MissedCall, PlaceCall, ScheduleTimer, Signal, Timer, TripState, TruckUpdate,
    decide, effective_moving, valid_end_state,
    SILENCE_CALLBACK, STOPPED_CHECK, CHECK_IN, CALLBACK, DARK_STRETCH_WARNING, COVERAGE_RETURN,
    PROMISED_STOP_FOLLOWUP, QUIET_RETURN, PRIMARY, BACKUP, FLEET_DESK,
    NOT_ANSWERING, UNREACHABLE, NO_NETWORK,
    T_CHECK_IN, T_SILENCE_RETRY, T_UNREACHABLE_RETRY, T_PROMISED_STOP, T_QUIET_RETURN, T_COVERAGE_RETURN,
)

IST = C.IST


def at(hh: int, mm: int = 0, ss: int = 0, day: int = 23) -> datetime:
    """IST timestamp on the demo night (22 Nov 19:00 trip start, past midnight = 23rd)."""
    return datetime(2026, 11, day, hh, mm, ss, tzinfo=IST)


TRIP_START = at(19, 0, day=22)
ONE_AM = at(1, 0)


def base_state(now: datetime, **kw) -> TripState:
    st = TripState(trip_id="trip-demo", driver_name="Raju", trip_started_at=TRIP_START,
                   moving=True, last_gps_at=now)
    for k, v in kw.items():
        setattr(st, k, v)
    return st


def calls(actions) -> List[PlaceCall]:
    return [a for a in actions if isinstance(a, PlaceCall)]


def alerts(actions) -> List[AlertContact]:
    return [a for a in actions if isinstance(a, AlertContact)]


def timers(actions, kind: Optional[str] = None) -> List[ScheduleTimer]:
    return [a for a in actions if isinstance(a, ScheduleTimer) and (kind is None or a.kind == kind)]


def flags(actions) -> List[str]:
    return [a.name for a in actions if isinstance(a, ConsoleFlag)]


def connected_ok(end_state: str, now: datetime, reason: str = "inbound") -> CallResult:
    """A call that ended 5 s after log_status: valid end state."""
    return CallResult(status="connected", end_state=end_state, log_status_at=now - timedelta(seconds=5),
                      ended_at=now, reason=reason)


def silent_end(now: datetime, reason: str = "inbound") -> CallResult:
    """Call ended in unanswered nudges, no log_status."""
    return CallResult(status="connected", end_state=None, ended_on_nudges=True, ended_at=now, reason=reason)


def truck(moving: bool = True, stop_type: Optional[str] = None, name: Optional[str] = None,
          gps_age_s: int = 10, **kw) -> TruckUpdate:
    return TruckUpdate(moving=moving, stopped_at_type=stop_type, stopped_at_name=name, gps_age_s=gps_age_s, **kw)


def stopped_at(now: datetime, stop_type: str, name: str = "Sharma Dhaba (demo)") -> TripState:
    st = base_state(now)
    st, _ = decide(st, truck(moving=False, stop_type=stop_type, name=name), now)
    return st


def run_alert_chain_to(st: TripState, now: datetime) -> Tuple[TripState, List]:
    """Drive a moving truck through silence -> callback x2 unanswered -> alert chain."""
    st, a = decide(st, silent_end(now), now)
    assert calls(a)[0].reason == SILENCE_CALLBACK
    st, a = decide(st, CallResult("no_answer", reason=SILENCE_CALLBACK), now + timedelta(seconds=30))
    st, a = decide(st, Timer(T_SILENCE_RETRY), now + timedelta(seconds=60))
    st, a = decide(st, CallResult("no_answer", reason=SILENCE_CALLBACK), now + timedelta(seconds=90))
    return st, a


# --------------------------------------------------------------------------------------
def test_01_valid_parked_resting_no_callback_checkins_paused():
    now = ONE_AM
    st = base_state(now, pending_timers=(T_CHECK_IN,))
    st, a = decide(st, connected_ok("parked_resting", now), now)
    assert calls(a) == []
    assert alerts(a) == []
    assert st.resting is True and st.status == "resting"
    assert CancelTimer(T_CHECK_IN) in a
    assert T_CHECK_IN not in st.pending_timers
    # a later check-in timer (if any survived) is skipped while resting
    st2, a2 = decide(st, Timer(T_CHECK_IN), now + timedelta(minutes=30))
    assert calls(a2) == []


def test_02_valid_driving_alert_at_1am_check_in_at_130():
    now = ONE_AM
    st = base_state(now)
    st, a = decide(st, connected_ok("driving_alert", now), now)
    t = timers(a, T_CHECK_IN)
    assert len(t) == 1 and t[0].after_s == 30 * 60
    assert (now + timedelta(seconds=t[0].after_s)) == at(1, 30)
    assert calls(a) == [] and alerts(a) == []
    assert st.resting is False and st.status == "driving"


def test_03_no_end_state_moving_silence_callback_within_5s():
    now = ONE_AM
    st = base_state(now)
    st, a = decide(st, silent_end(now), now)
    c = calls(a)
    assert len(c) == 1 and c[0].reason == SILENCE_CALLBACK and 0 <= c[0].delay_s <= C.CALLBACK_DELAY_S
    assert alerts(a) == []


def test_04_no_end_state_stopped_at_dhaba_no_call():
    now = ONE_AM
    st = stopped_at(now, "dhaba", "Sharma Dhaba (demo)")
    st, a = decide(st, silent_end(now), now)
    assert calls(a) == [] and alerts(a) == []
    assert st.resting is True


def test_05_no_end_state_stopped_on_highway_stopped_check_then_alert():
    now = ONE_AM
    st = stopped_at(now, "highway", None)
    st, a = decide(st, silent_end(now), now)
    c = calls(a)
    assert len(c) == 1 and c[0].reason == STOPPED_CHECK
    st, a = decide(st, CallResult("no_answer", reason=STOPPED_CHECK), now + timedelta(seconds=35))
    assert calls(a) == []
    assert alerts(a) == [AlertContact(PRIMARY, NOT_ANSWERING)]


def test_06_silence_callback_unanswered_twice_primary_alerted_by_230():
    """Simulated timeline: silence begins at T; nudges 15/30 s; hang-up at 40 s;
    callback 5 s later; ring 25 s -> no_answer; retry after 30 s; ring 25 s -> alert."""
    t0 = ONE_AM                                   # silence begins
    st = base_state(t0)
    hangup = t0 + timedelta(seconds=C.HANGUP_S)   # 0:40
    st, a = decide(st, silent_end(hangup), hangup)
    cb = calls(a)[0]
    assert cb.reason == SILENCE_CALLBACK
    placed1 = hangup + timedelta(seconds=cb.delay_s)                  # 0:45
    noans1 = placed1 + timedelta(seconds=C.SIM_RING_TIME_S)           # 1:10
    st, a = decide(st, CallResult("no_answer", reason=SILENCE_CALLBACK), noans1)
    assert calls(a) == [] and alerts(a) == []
    retry = timers(a, T_SILENCE_RETRY)
    assert len(retry) == 1 and retry[0].after_s == C.RETRY_DELAY_S
    fire = noans1 + timedelta(seconds=retry[0].after_s)              # 1:40
    st, a = decide(st, Timer(T_SILENCE_RETRY), fire)
    assert calls(a)[0].reason == SILENCE_CALLBACK
    noans2 = fire + timedelta(seconds=C.SIM_RING_TIME_S)             # 2:05
    st, a = decide(st, CallResult("no_answer", reason=SILENCE_CALLBACK), noans2)
    assert alerts(a) == [AlertContact(PRIMARY, NOT_ANSWERING)]
    elapsed = (noans2 - t0).total_seconds()
    assert elapsed <= C.FAMILY_ALERT_TARGET_S, "family must be alerted by ~2:30, got %ss" % elapsed
    assert st.silence_began_at == t0


def test_07_primary_no_answer_then_backup_then_fleet_desk():
    now = ONE_AM
    st, a = run_alert_chain_to(base_state(now), now)
    assert alerts(a) == [AlertContact(PRIMARY, NOT_ANSWERING)]
    st, a = decide(st, CallResult("no_answer", alert_step=PRIMARY), now + timedelta(seconds=120))
    assert alerts(a) == [AlertContact(BACKUP, NOT_ANSWERING)]
    st, a = decide(st, CallResult("no_answer", alert_step=BACKUP), now + timedelta(seconds=150))
    assert alerts(a) == [AlertContact(FLEET_DESK, NOT_ANSWERING)]
    assert st.alert_step == FLEET_DESK
    st, a = decide(st, CallResult("connected", alert_step=FLEET_DESK), now + timedelta(seconds=180))
    assert alerts(a) == []


def test_08_check_in_unanswered_while_moving_silence_callback():
    now = at(1, 30)
    st = base_state(now, last_call_at=now - timedelta(minutes=40), pending_timers=(T_CHECK_IN,))
    st, a = decide(st, Timer(T_CHECK_IN), now)
    assert calls(a) == [PlaceCall(CHECK_IN, 0)]
    st, a = decide(st, CallResult("no_answer", reason=CHECK_IN), now + timedelta(seconds=25))
    c = calls(a)
    assert len(c) == 1 and c[0].reason == SILENCE_CALLBACK
    assert alerts(a) == []


def test_09_failed_inside_dark_stretch_retries_then_no_network_after_exit_plus_10():
    now = ONE_AM
    st = base_state(now)
    # inside a 25-min stretch that started 5 min ago -> exits at 1:20
    st, _ = decide(st, truck(dark_stretch_id="ds-1", dark_stretch_starts_in_min=-5, dark_stretch_lasts_min=25), now)
    exit_at = at(1, 20)
    assert st.dark_stretch_ends_at == exit_at
    st, a = decide(st, CallResult("failed", reason=SILENCE_CALLBACK), now)
    assert alerts(a) == []
    assert timers(a, T_UNREACHABLE_RETRY) and timers(a)[0].after_s == 120
    t = now
    retries = 0
    alerted_at = None
    for _ in range(30):
        t = t + timedelta(seconds=120)
        st, a = decide(st, Timer(T_UNREACHABLE_RETRY), t)
        if alerts(a):
            alerted_at = t
            break
        assert calls(a) == [PlaceCall(SILENCE_CALLBACK, 0)]
        retries += 1
        st, a = decide(st, CallResult("failed", reason=SILENCE_CALLBACK), t)
        if alerts(a):
            alerted_at = t
            assert alerts(a) == [AlertContact(PRIMARY, NO_NETWORK)]
            break
        assert timers(a, T_UNREACHABLE_RETRY)
    assert alerted_at is not None
    assert alerted_at == exit_at + timedelta(minutes=C.UNREACHABLE_CAP_MIN)
    assert retries >= 10


def test_10_failed_moving_fresh_gps_retries_10_min_then_unreachable_or_highway_stop():
    now = ONE_AM
    st = base_state(now)
    st, _ = decide(st, truck(moving=True, gps_age_s=5), now)
    st, a = decide(st, CallResult("failed", reason=SILENCE_CALLBACK), now)
    assert alerts(a) == [] and timers(a, T_UNREACHABLE_RETRY)
    t = now
    alerted = None
    for _ in range(10):
        t = t + timedelta(seconds=120)
        st, a = decide(st, Timer(T_UNREACHABLE_RETRY), t)
        if alerts(a):
            alerted = (t, alerts(a))
            break
        assert calls(a) == [PlaceCall(SILENCE_CALLBACK, 0)]
        st, a = decide(st, CallResult("failed", reason=SILENCE_CALLBACK), t)
        if alerts(a):
            alerted = (t, alerts(a))
            break
    assert alerted is not None
    assert alerted[0] == now + timedelta(minutes=C.UNREACHABLE_CAP_MIN)
    assert alerted[1] == [AlertContact(PRIMARY, UNREACHABLE)]

    # variant: truck stops on the highway during the wait -> alert at once
    st2 = base_state(now)
    st2, _ = decide(st2, truck(moving=True, gps_age_s=5), now)
    st2, a = decide(st2, CallResult("failed", reason=SILENCE_CALLBACK), now)
    assert alerts(a) == []
    st2, a = decide(st2, truck(moving=False, stop_type="highway"), now + timedelta(minutes=3))
    assert alerts(a) == [AlertContact(PRIMARY, UNREACHABLE)]


def test_11_failed_stopped_on_highway_unreachable_at_once():
    now = ONE_AM
    st = stopped_at(now, "highway", None)
    st, a = decide(st, CallResult("failed", reason=SILENCE_CALLBACK), now)
    assert alerts(a) == [AlertContact(PRIMARY, UNREACHABLE)]
    assert timers(a, T_UNREACHABLE_RETRY) == []


def test_12_dark_stretch_ahead_5h10_since_rest_one_warning_not_repeated():
    now = at(0, 10)   # trip started 19:00 -> 5 h 10 min since rest
    st = base_state(now)
    upd = truck(dark_stretch_id="ds-2", dark_stretch_starts_in_min=15, dark_stretch_lasts_min=40)
    st, a = decide(st, upd, now)
    assert calls(a) == [PlaceCall(DARK_STRETCH_WARNING, 0)]
    st, a = decide(st, truck(dark_stretch_id="ds-2", dark_stretch_starts_in_min=14, dark_stretch_lasts_min=40),
                   now + timedelta(minutes=1))
    assert calls(a) == []


def test_13_dark_stretch_ahead_4h_since_rest_no_warning():
    now = at(23, 0, day=22)   # 4 h since 19:00
    st = base_state(now)
    st, a = decide(st, truck(dark_stretch_id="ds-2", dark_stretch_starts_in_min=15, dark_stretch_lasts_min=40), now)
    assert calls(a) == []


def test_14_stop_refused_coverage_return_at_expected_exit():
    now = at(0, 10)
    st = base_state(now)
    st, a = decide(st, truck(dark_stretch_id="ds-2", dark_stretch_starts_in_min=15, dark_stretch_lasts_min=40), now)
    st, a = decide(st, Signal("stop_refused"), now)
    t = timers(a, T_COVERAGE_RETURN)
    assert len(t) == 1 and t[0].after_s == 55 * 60    # exit at 01:05
    fire = now + timedelta(seconds=t[0].after_s)
    st, a = decide(st, Timer(T_COVERAGE_RETURN), fire)
    assert calls(a) == [PlaceCall(COVERAGE_RETURN, 0)]


def test_15_ten_minute_chai_does_not_reset_clock_35_minute_rest_does():
    t0 = at(23, 0, day=22)
    st = base_state(t0)
    st, _ = decide(st, truck(moving=False, stop_type="dhaba", name="Sharma Dhaba (demo)"), t0)
    st, _ = decide(st, truck(moving=True), t0 + timedelta(minutes=10))
    assert st.last_rest_ended_at is None
    t1 = at(23, 30, day=22)
    st, _ = decide(st, truck(moving=False, stop_type="dhaba", name="Sharma Dhaba (demo)"), t1)
    st, a = decide(st, truck(moving=True), t1 + timedelta(minutes=35))
    assert st.last_rest_ended_at == t1 + timedelta(minutes=35)
    assert any("reset" in x.text for x in a if isinstance(x, LogEvent))


def test_16_promised_stop_followup_or_kept():
    now = ONE_AM
    st = base_state(now)
    st, a = decide(st, Signal("promised_stop", "Sharma Dhaba (demo)"), now)
    t = timers(a, T_PROMISED_STOP)
    assert len(t) == 1 and t[0].after_s == 10 * 60
    later = now + timedelta(minutes=10)
    st_moving, _ = decide(st, truck(moving=True), later)
    st_moving, a = decide(st_moving, Timer(T_PROMISED_STOP), later)
    assert calls(a) == [PlaceCall(PROMISED_STOP_FOLLOWUP, 0)]
    st_stopped, _ = decide(st, truck(moving=False, stop_type="dhaba", name="Sharma Dhaba (demo)"), later)
    st_stopped, a = decide(st_stopped, Timer(T_PROMISED_STOP), later)
    assert calls(a) == []
    assert "promise_kept" in flags(a)
    assert any("kept" in x.text for x in a if isinstance(x, LogEvent))


def test_17_quiet_requested_callback_at_10_min_or_sooner_before_dark_stretch():
    now = ONE_AM
    st = base_state(now)
    st, a = decide(st, Signal("quiet_requested"), now)
    t = timers(a, T_QUIET_RETURN)
    assert len(t) == 1 and t[0].after_s == 10 * 60
    st, a = decide(st, Timer(T_QUIET_RETURN), now + timedelta(minutes=10))
    assert calls(a) == [PlaceCall(QUIET_RETURN, 0)]
    # dark stretch in 6 min -> sooner
    st2 = base_state(now)
    st2, _ = decide(st2, truck(dark_stretch_id="ds-3", dark_stretch_starts_in_min=6, dark_stretch_lasts_min=25), now)
    st2, a = decide(st2, Signal("quiet_requested"), now)
    t = timers(a, T_QUIET_RETURN)
    assert len(t) == 1 and 60 <= t[0].after_s < 6 * 60


def test_18_log_status_driving_alert_then_call_runs_on_and_ends_in_nudges():
    now = ONE_AM
    st = base_state(now)
    ev = CallResult(status="connected", end_state="driving_alert", ended_on_nudges=True,
                    log_status_at=now - timedelta(minutes=5), ended_at=now)
    assert valid_end_state(ev, now) is None
    st, a = decide(st, ev, now)
    assert calls(a) and calls(a)[0].reason == SILENCE_CALLBACK
    # even a fresh log_status does not count when the transcript ends in nudges
    ev2 = CallResult(status="connected", end_state="driving_alert", ended_on_nudges=True,
                     log_status_at=now - timedelta(seconds=10), ended_at=now)
    assert valid_end_state(ev2, now) is None


def test_19_no_log_status_but_call_end_state_driving_alert_still_calls_back():
    now = ONE_AM
    st = base_state(now)
    ev = CallResult(status="connected", end_state=None, ended_at=now, call_end_state="driving_alert")
    assert valid_end_state(ev, now) is None
    st, a = decide(st, ev, now)
    assert calls(a) and calls(a)[0].reason == SILENCE_CALLBACK
    # and a stale log_status outside the 30 s window does not count either
    ev2 = CallResult(status="connected", end_state="parked_resting",
                     log_status_at=now - timedelta(seconds=90), ended_at=now, call_end_state="parked_resting")
    assert valid_end_state(ev2, now) is None


def test_20_gps_stale_treated_as_moving():
    now = ONE_AM
    st = base_state(now)
    st, _ = decide(st, truck(moving=False, stop_type="dhaba", name="Sharma Dhaba (demo)", gps_age_s=10), now)
    assert effective_moving(st, now) is False
    later = now + timedelta(minutes=6)
    assert effective_moving(st, later) is True
    st, a = decide(st, silent_end(later), later)
    assert calls(a) and calls(a)[0].reason == SILENCE_CALLBACK
    # a fresh update that reports stale GPS is also "moving"
    st2 = base_state(now)
    st2, _ = decide(st2, truck(moving=False, stop_type="dhaba", gps_age_s=6 * 60), now)
    assert effective_moving(st2, now) is True


def test_21_max_call_length_reached_while_driving_callback():
    now = ONE_AM
    st = base_state(now)
    ev = CallResult(status="connected", end_state=None, ended_at=now, max_length_reached=True,
                    log_status_at=None, reason=CHECK_IN)
    st, a = decide(st, ev, now)
    assert calls(a) and calls(a)[0].reason == SILENCE_CALLBACK
    assert any("max call length" in x.text for x in a if isinstance(x, LogEvent))


def test_22_care_console_flag_only_nothing_reaches_fleet():
    now = ONE_AM
    st = base_state(now)
    st, a = decide(st, Signal("care", "talked about ending his life"), now)
    assert a == [ConsoleFlag("care")]
    assert st.care_flag is True
    assert alerts(a) == [] and calls(a) == []
    # no LogEvent carries the detail
    assert not any(isinstance(x, LogEvent) for x in a)


def test_23_driver_swap_registered_uses_new_contacts_unregistered_goes_to_fleet_desk():
    now = ONE_AM
    st = base_state(now)
    st, a = decide(st, Signal("driver_swap", "Mohan", registered=True), now)
    assert st.driver_name == "Mohan" and st.driver_registered is True
    st, a = run_alert_chain_to(st, now)
    assert alerts(a) == [AlertContact(PRIMARY, NOT_ANSWERING)]

    st2 = base_state(now)
    st2, a = decide(st2, Signal("driver_swap", "Unknown", registered=False), now)
    assert "unregistered_driver" in flags(a)
    assert st2.driver_registered is False
    st2, a = run_alert_chain_to(st2, now)
    assert alerts(a) == [AlertContact(FLEET_DESK, NOT_ANSWERING)]


def test_24_missed_call_from_registered_driver_callback_within_10s():
    now = ONE_AM
    st = base_state(now)
    st, a = decide(st, MissedCall(registered=True), now)
    c = calls(a)
    assert len(c) == 1 and c[0].reason == CALLBACK and c[0].delay_s <= 10
    st2, a2 = decide(base_state(now), MissedCall(registered=False), now)
    assert calls(a2) == [] and "unregistered_caller" in flags(a2)


def test_25_scheduled_call_while_stopped_at_safe_stop_skipped():
    now = at(1, 30)
    st = stopped_at(now, "petrol_pump", "HP Pump (demo)")
    for kind in (T_CHECK_IN, T_QUIET_RETURN, T_PROMISED_STOP, T_COVERAGE_RETURN, T_SILENCE_RETRY):
        s2 = TripState(**{**st.__dict__, "pending_timers": (kind,), "last_call_at": now - timedelta(hours=1)})
        s2, a = decide(s2, Timer(kind), now)
        assert calls(a) == [], "%s should be skipped at a safe stop" % kind
        assert alerts(a) == []
        assert any(("skipped" in x.text or "kept" in x.text) for x in a if isinstance(x, LogEvent))
