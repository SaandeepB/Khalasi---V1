"""Seed data (Appendix C, all demo data): Raju Yadav, contacts, the Nagpur -> Jhansi trip.

Phones come from env (DRIVER_PHONE, ALERT_PHONE, BACKUP_PHONE, FLEET_DESK_PHONE).
`python -m app.seed --pilot` is a stub: pilot generation belongs to Workstream 4.
Python 3.9 compatible.
"""
from __future__ import annotations

import sys
from datetime import datetime
from typing import Dict

from . import config as C
from .config import Settings
from .db import Database

DEMO_TRIP_ID = "trip-demo"
DEMO_DRIVER_ID = "drv-raju"


def trip_start_tonight(now: datetime) -> datetime:
    """19:00 IST on the demo evening (yesterday evening if it is past midnight)."""
    local = now.astimezone(C.IST) if now.tzinfo else now.replace(tzinfo=C.IST)
    start = local.replace(hour=19, minute=0, second=0, microsecond=0)
    if local.hour < 19:
        from datetime import timedelta
        start = start - timedelta(days=1)
    return start


def seed(db: Database, settings: Settings, now: datetime) -> Dict[str, str]:
    db.upsert_driver(DEMO_DRIVER_ID, "Raju Yadav", settings.driver_phone or "+910000000000", "hi", True)
    db.set_contacts(DEMO_DRIVER_ID, [
        {"step": "primary", "name": "Sunita", "phone": settings.alert_phone or "+910000000001"},
        {"step": "backup", "name": "Backup contact", "phone": settings.backup_phone or "+910000000002"},
        {"step": "fleet_desk", "name": "Fleet night desk", "phone": settings.fleet_desk_phone or "+910000000003"},
    ])
    started = trip_start_tonight(now)
    db.upsert_trip(DEMO_TRIP_ID, DEMO_DRIVER_ID, "Nagpur", "Jhansi", started)
    return {"trip_id": DEMO_TRIP_ID, "driver_id": DEMO_DRIVER_ID, "started_at": started.isoformat()}


def main(argv) -> int:
    from datetime import timezone
    settings = Settings.from_env()
    if "--pilot" in argv:
        print("pilot data generator: stub (Workstream 4). Nothing generated.")
        return 0
    db = Database(settings.db_path)
    info = seed(db, settings, datetime.now(timezone.utc))
    print("seeded demo data:", info)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
