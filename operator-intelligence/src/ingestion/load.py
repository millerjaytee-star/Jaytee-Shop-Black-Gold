from __future__ import annotations

import csv
from pathlib import Path


def read_csv(path: str | Path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def load_raw(root: str | Path):
    root = Path(root)
    raw = root / "data" / "raw"
    return {
        "locations": read_csv(raw / "locations.csv"),
        "monthly": read_csv(raw / "monthly_operations.csv"),
        "weekly": read_csv(raw / "weekly_operations.csv"),
        "inventory": read_csv(raw / "inventory.csv"),
        "vendor": read_csv(raw / "vendor_purchases.csv"),
    }
