"""Truck simulator: Nagpur -> Jhansi on NH-44 (Appendix C). All demo data.

Route waypoints with approximate coordinates, demo safe stops "(demo)", two demo
dark stretches (25 and 40 min), a settable truck mode, and truck_status(trip_id)
returning exactly the section 6 JSON shape. Python 3.9 compatible.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from . import config as C
from .models import DarkStretch, SafeStop

# (name, lat, lon, km from Nagpur along NH-44) -- approximate
ROUTE: List[Tuple[str, float, float, float]] = [
    ("Nagpur", 21.1458, 79.0882, 0.0),
    ("Seoni", 22.0869, 79.5431, 130.0),
    ("Lakhnadon", 22.6010, 79.6010, 195.0),
    ("Sagar", 23.8388, 78.7378, 390.0),
    ("Lalitpur", 24.6877, 78.4117, 500.0),
    ("Jhansi", 25.4484, 78.5685, 600.0),
]

SAFE_STOPS: List[SafeStop] = [
    SafeStop("Sharma Dhaba (demo)", "dhaba", 95.0, 21.85, 79.42),
    SafeStop("HP Petrol Pump Seoni (demo)", "petrol_pump", 128.0, 22.08, 79.54),
    SafeStop("Lakhnadon Truck Lay-by (demo)", "lay_by", 198.0, 22.61, 79.60),
    SafeStop("Gupta Dhaba (demo)", "dhaba", 260.0, 23.05, 79.30),
    SafeStop("Apna Ghar (demo)", "apna_ghar", 398.0, 23.86, 78.72),
    SafeStop("Indian Oil Pump Lalitpur (demo)", "petrol_pump", 498.0, 24.68, 78.41),
    SafeStop("Yadav Dhaba (demo)", "dhaba", 560.0, 25.10, 78.50),
]

DARK_STRETCHES: List[DarkStretch] = [
    DarkStretch("ds-demo-1", "Seoni-Lakhnadon ghat (demo)", 150.0, 25),
    DarkStretch("ds-demo-2", "Sagar-Lalitpur forest (demo)", 410.0, 40),
]

MODES = ("moving", "stopped_dhaba", "stopped_highway")


@dataclass
class TruckSim:
    trip_id: str = "trip-demo"
    destination: str = "Jhansi"
    speed_kmph: float = 50.0
    mode: str = "moving"
    km: float = 340.0                       # start the demo past Sagar-ish
    trip_started_at: Optional[datetime] = None
    last_rest_ended_at: Optional[datetime] = None
    last_tick: Optional[datetime] = None
    gps_age_sec: int = 20
    stopped_stop: Optional[SafeStop] = None
    forced_dark_stretch: Optional[Tuple[int, int]] = None   # (starts_in_min, lasts_min) demo override

    def set_mode(self, mode: str, now: datetime) -> Dict[str, Any]:
        if mode not in MODES:
            raise ValueError("mode must be one of %s" % (MODES,))
        self.tick(now)
        self.mode = mode
        if mode == "stopped_dhaba":
            self.stopped_stop = self.nearest_stop()
        else:
            self.stopped_stop = None
        return self.update_dict(now)

    def set_gps_age(self, seconds: int) -> None:
        self.gps_age_sec = max(0, int(seconds))

    def force_dark_stretch(self, starts_in_min: int = 15, lasts_min: int = 40) -> None:
        self.forced_dark_stretch = (starts_in_min, lasts_min)

    def tick(self, now: datetime) -> None:
        if self.last_tick is not None and self.mode == "moving":
            hours = (now - self.last_tick).total_seconds() / 3600.0
            self.km = min(ROUTE[-1][3], self.km + self.speed_kmph * hours)
        self.last_tick = now

    # geography ------------------------------------------------------------------
    def position(self) -> Tuple[float, float]:
        for (n1, la1, lo1, k1), (n2, la2, lo2, k2) in zip(ROUTE, ROUTE[1:]):
            if k1 <= self.km <= k2:
                f = (self.km - k1) / (k2 - k1) if k2 > k1 else 0.0
                return (la1 + (la2 - la1) * f, lo1 + (lo2 - lo1) * f)
        return (ROUTE[-1][1], ROUTE[-1][2])

    def nearest_town(self) -> str:
        return min(ROUTE, key=lambda r: abs(r[3] - self.km))[0]

    def location_text(self) -> str:
        return "NH-44, %s ke paas" % self.nearest_town()

    def nearest_stop(self) -> SafeStop:
        return min(SAFE_STOPS, key=lambda s: abs(s.route_km - self.km))

    def next_safe_stop(self) -> Optional[Dict[str, Any]]:
        ahead = [s for s in SAFE_STOPS if s.route_km >= self.km - 0.5]
        if not ahead:
            return None
        s = min(ahead, key=lambda x: x.route_km)
        return {"name": s.name, "type": s.type, "km": int(round(max(0.0, s.route_km - self.km)))}

    def dark_stretch(self) -> Optional[Dict[str, Any]]:
        if self.forced_dark_stretch is not None:
            starts_in, lasts = self.forced_dark_stretch
            return {"starts_in_min": int(starts_in), "lasts_min": int(lasts)}
        speed = self.speed_kmph if self.speed_kmph > 0 else 50.0
        for ds in DARK_STRETCHES:
            end_km = ds.start_km + speed * ds.lasts_min / 60.0
            if self.km > end_km:
                continue
            starts_in = (ds.start_km - self.km) / speed * 60.0
            if starts_in <= 60:
                return {"starts_in_min": int(round(starts_in)), "lasts_min": ds.lasts_min}
        return None

    def dark_stretch_id(self) -> Optional[str]:
        if self.forced_dark_stretch is not None:
            return "ds-forced"
        d = self.dark_stretch()
        if d is None:
            return None
        speed = self.speed_kmph if self.speed_kmph > 0 else 50.0
        for ds in DARK_STRETCHES:
            if int(round((ds.start_km - self.km) / speed * 60.0)) == d["starts_in_min"]:
                return ds.id
        return None

    # status ----------------------------------------------------------------------
    def stopped_at(self) -> Optional[Dict[str, Any]]:
        if self.mode == "moving":
            return None
        if self.mode == "stopped_dhaba":
            s = self.stopped_stop or self.nearest_stop()
            return {"name": s.name, "type": s.type}
        return {"name": None, "type": "highway"}

    def minutes_since_last_rest(self, now: datetime) -> Optional[int]:
        anchor = self.last_rest_ended_at or self.trip_started_at
        if anchor is None:
            return None
        return int((now - anchor).total_seconds() // 60)

    def eta_min(self) -> int:
        speed = self.speed_kmph if self.speed_kmph > 0 else 50.0
        return int(round((ROUTE[-1][3] - self.km) / speed * 60.0))

    def truck_status(self, trip_id: str, now: Optional[datetime] = None) -> Dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        self.tick(now)
        local = now.astimezone(C.IST) if now.tzinfo else now
        moving = self.mode == "moving"
        mins = self.minutes_since_last_rest(now)
        ds = self.dark_stretch()
        risk = (0 <= local.hour < 6) or (mins is not None and mins >= C.REST_DUE_H * 60)
        return {
            "time_now": local.strftime("%H:%M"),
            "moving": moving,
            "speed_kmph": int(round(self.speed_kmph)) if moving else 0,
            "gps_age_sec": int(self.gps_age_sec),
            "stopped_at": self.stopped_at(),
            "location_text": self.location_text(),
            "trip_started_at": (self.trip_started_at.astimezone(C.IST).strftime("%H:%M")
                                if self.trip_started_at else "19:00"),
            "last_rest_ended_at": (self.last_rest_ended_at.astimezone(C.IST).strftime("%H:%M")
                                   if self.last_rest_ended_at else None),
            "minutes_since_last_rest": mins,
            "next_safe_stop": self.next_safe_stop(),
            "dark_stretch": ds,
            "destination": self.destination,
            "eta_min": self.eta_min(),
            "risk_window": bool(risk),
        }

    def update_dict(self, now: datetime) -> Dict[str, Any]:
        """Fields for an engine TruckUpdate."""
        st = self.stopped_at()
        ds = self.dark_stretch()
        return {
            "moving": self.mode == "moving",
            "stopped_at_type": st["type"] if st else None,
            "stopped_at_name": st["name"] if st else None,
            "gps_age_s": int(self.gps_age_sec),
            "dark_stretch_id": self.dark_stretch_id(),
            "dark_stretch_starts_in_min": ds["starts_in_min"] if ds else None,
            "dark_stretch_lasts_min": ds["lasts_min"] if ds else None,
            "speed_kmph": self.speed_kmph if self.mode == "moving" else 0.0,
        }
