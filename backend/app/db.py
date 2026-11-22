"""Minimal SQLite storage (stdlib sqlite3): drivers, contacts, trips, calls,
raw webhook payloads, transcripts, signals, alerts; plus the R17 purge.
Python 3.9 compatible.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from . import config as C

SCHEMA = """
CREATE TABLE IF NOT EXISTS drivers (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL, language TEXT DEFAULT 'hi',
  registered INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, driver_id TEXT NOT NULL, step TEXT NOT NULL,
  name TEXT NOT NULL, phone TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS trips (
  id TEXT PRIMARY KEY, driver_id TEXT NOT NULL, origin TEXT, destination TEXT,
  started_at TEXT NOT NULL, state_json TEXT);
CREATE TABLE IF NOT EXISTS calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT, trip_id TEXT, attempt_id TEXT, reason TEXT,
  kind TEXT, placed_at TEXT, status TEXT, ended_at TEXT, log_status TEXT, log_status_at TEXT);
CREATE TABLE IF NOT EXISTS webhook_payloads (
  id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id TEXT, received_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transcripts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, trip_id TEXT, attempt_id TEXT, created_at TEXT NOT NULL,
  transcript TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, trip_id TEXT, type TEXT NOT NULL, detail TEXT, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alerts (
  token TEXT PRIMARY KEY, trip_id TEXT NOT NULL, step TEXT NOT NULL, reason TEXT NOT NULL,
  created_at TEXT NOT NULL, expires_at TEXT NOT NULL, resolved INTEGER DEFAULT 0, false_alarm INTEGER,
  last_location TEXT, last_seen_time TEXT, moving INTEGER);
"""


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # drivers / contacts / trips ------------------------------------------------
    def upsert_driver(self, driver_id: str, name: str, phone: str, language: str = "hi", registered: bool = True) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO drivers (id, name, phone, language, registered) VALUES (?, ?, ?, ?, ?)",
            (driver_id, name, phone, language, 1 if registered else 0))
        self.conn.commit()

    def set_contacts(self, driver_id: str, contacts: List[Dict[str, str]]) -> None:
        self.conn.execute("DELETE FROM contacts WHERE driver_id = ?", (driver_id,))
        for c in contacts:
            self.conn.execute("INSERT INTO contacts (driver_id, step, name, phone) VALUES (?, ?, ?, ?)",
                              (driver_id, c["step"], c["name"], c["phone"]))
        self.conn.commit()

    def contacts_for(self, driver_id: str) -> Dict[str, Dict[str, str]]:
        rows = self.conn.execute("SELECT step, name, phone FROM contacts WHERE driver_id = ?", (driver_id,)).fetchall()
        return {r["step"]: {"name": r["name"], "phone": r["phone"]} for r in rows}

    def driver_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        digits = "".join(ch for ch in phone if ch.isdigit())[-10:]
        for r in self.conn.execute("SELECT * FROM drivers").fetchall():
            if "".join(ch for ch in r["phone"] if ch.isdigit())[-10:] == digits and digits:
                return dict(r)
        return None

    def driver_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        r = self.conn.execute("SELECT * FROM drivers WHERE lower(name) = lower(?) AND registered = 1", (name,)).fetchone()
        return dict(r) if r else None

    def driver(self, driver_id: str) -> Optional[Dict[str, Any]]:
        r = self.conn.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,)).fetchone()
        return dict(r) if r else None

    def upsert_trip(self, trip_id: str, driver_id: str, origin: str, destination: str, started_at: datetime) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO trips (id, driver_id, origin, destination, started_at) VALUES (?, ?, ?, ?, ?)",
            (trip_id, driver_id, origin, destination, _iso(started_at)))
        self.conn.commit()

    def trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        r = self.conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
        return dict(r) if r else None

    def trips(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM trips").fetchall()]

    # calls / webhooks / transcripts ---------------------------------------------
    def record_call(self, trip_id: str, attempt_id: Optional[str], reason: str, kind: str, placed_at: datetime) -> int:
        cur = self.conn.execute(
            "INSERT INTO calls (trip_id, attempt_id, reason, kind, placed_at) VALUES (?, ?, ?, ?, ?)",
            (trip_id, attempt_id, reason, kind, _iso(placed_at)))
        self.conn.commit()
        return int(cur.lastrowid)

    def call_by_attempt(self, attempt_id: str) -> Optional[Dict[str, Any]]:
        r = self.conn.execute("SELECT * FROM calls WHERE attempt_id = ? ORDER BY id DESC LIMIT 1", (attempt_id,)).fetchone()
        return dict(r) if r else None

    def record_log_status(self, trip_id: str, state: str, at: datetime) -> None:
        self.conn.execute(
            "UPDATE calls SET log_status = ?, log_status_at = ? WHERE id = ("
            " SELECT id FROM calls WHERE trip_id = ? AND ended_at IS NULL ORDER BY id DESC LIMIT 1)",
            (state, _iso(at), trip_id))
        self.conn.commit()

    def last_log_status(self, trip_id: str) -> Optional[Dict[str, Any]]:
        r = self.conn.execute(
            "SELECT log_status, log_status_at FROM calls WHERE trip_id = ? AND log_status IS NOT NULL ORDER BY id DESC LIMIT 1",
            (trip_id,)).fetchone()
        return dict(r) if r else None

    def close_call(self, attempt_id: Optional[str], trip_id: Optional[str], status: str, ended_at: datetime) -> None:
        if attempt_id:
            self.conn.execute("UPDATE calls SET status = ?, ended_at = ? WHERE attempt_id = ?",
                              (status, _iso(ended_at), attempt_id))
        elif trip_id:
            self.conn.execute(
                "UPDATE calls SET status = ?, ended_at = ? WHERE id = ("
                " SELECT id FROM calls WHERE trip_id = ? AND ended_at IS NULL ORDER BY id DESC LIMIT 1)",
                (status, _iso(ended_at), trip_id))
        self.conn.commit()

    def store_webhook(self, attempt_id: Optional[str], payload: Dict[str, Any], received_at: datetime) -> int:
        cur = self.conn.execute("INSERT INTO webhook_payloads (attempt_id, received_at, payload) VALUES (?, ?, ?)",
                                (attempt_id, _iso(received_at), json.dumps(payload)))
        self.conn.commit()
        return int(cur.lastrowid)

    def store_transcript(self, trip_id: Optional[str], attempt_id: Optional[str], transcript: List[Dict[str, Any]],
                         created_at: datetime) -> int:
        cur = self.conn.execute("INSERT INTO transcripts (trip_id, attempt_id, created_at, transcript) VALUES (?, ?, ?, ?)",
                                (trip_id, attempt_id, _iso(created_at), json.dumps(transcript)))
        self.conn.commit()
        return int(cur.lastrowid)

    def count(self, table: str) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0])

    def record_signal(self, trip_id: str, type_: str, detail: Optional[str], at: datetime) -> None:
        # `care` stores a flag only: no details
        self.conn.execute("INSERT INTO signals (trip_id, type, detail, at) VALUES (?, ?, ?, ?)",
                          (trip_id, type_, None if type_ == "care" else detail, _iso(at)))
        self.conn.commit()

    # alerts ---------------------------------------------------------------------
    def create_alert(self, token: str, trip_id: str, step: str, reason: str, now: datetime,
                     last_location: str, last_seen_time: str, moving: bool) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO alerts (token, trip_id, step, reason, created_at, expires_at, resolved, "
            "last_location, last_seen_time, moving) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
            (token, trip_id, step, reason, _iso(now), _iso(now + timedelta(hours=C.ALERT_TOKEN_TTL_H)),
             last_location, last_seen_time, 1 if moving else 0))
        self.conn.commit()

    def alert(self, token: str) -> Optional[Dict[str, Any]]:
        r = self.conn.execute("SELECT * FROM alerts WHERE token = ?", (token,)).fetchone()
        return dict(r) if r else None

    def update_alert_step(self, trip_id: str, step: str) -> None:
        self.conn.execute("UPDATE alerts SET step = ? WHERE trip_id = ? AND resolved = 0", (step, trip_id))
        self.conn.commit()

    def resolve_alert(self, token: str, false_alarm: bool) -> None:
        self.conn.execute("UPDATE alerts SET resolved = 1, false_alarm = ? WHERE token = ?",
                          (1 if false_alarm else 0, token))
        self.conn.commit()

    # R17 -------------------------------------------------------------------------
    def purge_old(self, now: datetime, days: int = C.TRANSCRIPT_RETENTION_DAYS) -> Dict[str, int]:
        """Delete transcripts and raw webhook payloads older than `days`."""
        cutoff = _iso(now - timedelta(days=days))
        t = self.conn.execute("DELETE FROM transcripts WHERE created_at < ?", (cutoff,)).rowcount
        w = self.conn.execute("DELETE FROM webhook_payloads WHERE received_at < ?", (cutoff,)).rowcount
        self.conn.commit()
        return {"transcripts": int(t), "webhook_payloads": int(w)}

    def close(self) -> None:
        self.conn.close()


def purge_old_records(db: Database, now: Optional[datetime] = None, days: int = C.TRANSCRIPT_RETENTION_DAYS) -> Dict[str, int]:
    """R17 entry point: daily at 06:30, delete transcripts and raw webhook payloads older than 30 days."""
    return db.purge_old(now or datetime.now(timezone.utc), days)
