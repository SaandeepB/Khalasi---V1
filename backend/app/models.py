"""Plain dataclass models (no ORM; stdlib sqlite3 in db.py). Python 3.9 compatible."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Driver:
    id: str
    name: str
    phone: str
    language: str = "hi"
    registered: bool = True


@dataclass
class Contact:
    driver_id: str
    step: str          # primary | backup | fleet_desk
    name: str
    phone: str


@dataclass
class Trip:
    id: str
    driver_id: str
    origin: str
    destination: str
    started_at: datetime


@dataclass
class SafeStop:
    name: str
    type: str          # apna_ghar | petrol_pump | dhaba | lay_by
    route_km: float
    lat: float
    lon: float
    demo: bool = True


@dataclass
class DarkStretch:
    id: str
    name: str
    start_km: float
    lasts_min: int
    note: str = "demo data, not real coverage"


@dataclass
class ConsoleEvent:
    kind: str           # decision | signal | timer | call | alert | truck
    at: str
    text: str
    data: Dict[str, object] = field(default_factory=dict)


@dataclass
class AlertView:
    token: str
    driver_name: str
    reason: str
    step: str
    last_location: str
    last_seen_time: str
    moving: bool
    resolved: bool
    false_alarm: Optional[bool]
    expires_at: str
    headline_hi: str
    headline_en: str
    contacts: List[str] = field(default_factory=list)
