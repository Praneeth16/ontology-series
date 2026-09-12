"""Generate the synthetic usage-event log for Ontology 101, Part 2.

Ten accounts, June 1 to Aug 28, 2026. Three accounts go silent on
purpose: Vandelay (June 20), Hooli (July 15), Wayne (July 28).
Silent days produce NO rows -- absence, not zero. Definition B has to
notice what is missing, which is the point.

Deterministic: seeded RNG, same CSV every run.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

START = date(2026, 6, 1)
END = date(2026, 8, 28)

# account -> (base daily events, user pool size, last day of activity or None)
ACCOUNTS = {
    "Acme":      (140, 46, None),
    "Globex":    (95,  31, None),
    "Stark":     (170, 58, None),
    "Umbrella":  (40,  12, None),
    "Soylent":   (35,  11, None),
    "PiedPiper": (12,   5, None),
    "Initech":   (55,  17, None),                 # lapsed contract, live usage
    "Vandelay":  (25,   8, date(2026, 6, 20)),    # gone by both definitions
    "Hooli":     (110, 38, date(2026, 7, 15)),    # active subscription, no recorded events
    "Wayne":     (30,  10, date(2026, 7, 28)),    # active subscription, no recorded events
}

rng = random.Random(42)
rows = []
d = START
while d <= END:
    weekday_factor = 0.35 if d.weekday() >= 5 else 1.0
    for account, (base, users, last_day) in ACCOUNTS.items():
        if last_day is not None and d > last_day:
            continue  # no row at all: silence, not zero
        lam = base * weekday_factor
        events = max(0, int(rng.gauss(lam, lam * 0.25)))
        if events == 0:
            continue
        active_users = min(users, max(1, int(rng.gauss(users * weekday_factor * 0.7, 2))))
        rows.append((d.isoformat(), account, events, active_users))
    d += timedelta(days=1)

with open(Path(__file__).with_name("usage_events.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "account", "events", "active_users"])
    w.writerows(rows)

print(f"{len(rows)} rows, {START} to {END}")
