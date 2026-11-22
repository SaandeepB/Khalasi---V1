"""Timers persisted in SQLite (stdlib sqlite3) so a restart never loses a call-back.

schedule(kind, trip_id, fire_at) / due(now) / cancel(kind, trip_id) / load_pending()
plus a small asyncio loop that fires due timers through a callback.
Python 3.9 compatible.
"""
from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, List, Optional


@dataclass
class PendingTimer:
    id: int
    kind: str
    trip_id: str
    fire_at: datetime


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


class TimerStore:
    """SQLite-backed timer table. Use ':memory:' or a path."""

    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS timers ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " kind TEXT NOT NULL, trip_id TEXT NOT NULL, fire_at TEXT NOT NULL,"
            " fired INTEGER NOT NULL DEFAULT 0)"
        )
        self.conn.commit()

    def schedule(self, kind: str, trip_id: str, fire_at: datetime) -> PendingTimer:
        # one pending timer per (kind, trip): re-scheduling replaces it
        self.cancel(kind, trip_id)
        cur = self.conn.execute(
            "INSERT INTO timers (kind, trip_id, fire_at, fired) VALUES (?, ?, ?, 0)",
            (kind, trip_id, _iso(fire_at)),
        )
        self.conn.commit()
        return PendingTimer(int(cur.lastrowid), kind, trip_id, fire_at)

    def cancel(self, kind: str, trip_id: str) -> int:
        cur = self.conn.execute(
            "DELETE FROM timers WHERE kind = ? AND trip_id = ? AND fired = 0", (kind, trip_id)
        )
        self.conn.commit()
        return cur.rowcount

    def due(self, now: datetime) -> List[PendingTimer]:
        rows = self.conn.execute(
            "SELECT id, kind, trip_id, fire_at FROM timers WHERE fired = 0 AND fire_at <= ? ORDER BY fire_at",
            (_iso(now),),
        ).fetchall()
        return [PendingTimer(r[0], r[1], r[2], _parse(r[3])) for r in rows]

    def load_pending(self) -> List[PendingTimer]:
        rows = self.conn.execute(
            "SELECT id, kind, trip_id, fire_at FROM timers WHERE fired = 0 ORDER BY fire_at"
        ).fetchall()
        return [PendingTimer(r[0], r[1], r[2], _parse(r[3])) for r in rows]

    def mark_fired(self, timer_id: int) -> None:
        self.conn.execute("UPDATE timers SET fired = 1 WHERE id = ?", (timer_id,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


class Scheduler:
    """asyncio loop: every `tick_s`, fire due timers through `on_fire(kind, trip_id)`."""

    def __init__(self, store: TimerStore, on_fire: Callable[[str, str], Awaitable[None]],
                 clock: Optional[Callable[[], datetime]] = None, tick_s: float = 0.5) -> None:
        self.store = store
        self.on_fire = on_fire
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.tick_s = tick_s
        self._task: Optional[asyncio.Task] = None
        self._stopped = asyncio.Event()

    def pending(self) -> List[PendingTimer]:
        return self.store.load_pending()

    async def fire_due(self, now: Optional[datetime] = None) -> int:
        now = now or self.clock()
        fired = 0
        for t in self.store.due(now):
            self.store.mark_fired(t.id)
            fired += 1
            await self.on_fire(t.kind, t.trip_id)
        return fired

    async def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                await self.fire_due()
            except Exception:  # keep the loop alive; the caller logs
                pass
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=self.tick_s)
            except asyncio.TimeoutError:
                pass

    def start(self) -> None:
        if self._task is None:
            self._stopped = asyncio.Event()
            self._task = asyncio.get_event_loop().create_task(self._run())

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            try:
                await self._task
            except Exception:
                pass
            self._task = None
