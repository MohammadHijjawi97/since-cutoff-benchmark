"""Load station reports exported from the ingest database."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUMNS = ["station", "ts", "temp_c", "battery"]


def load_readings(path: str | Path) -> pd.DataFrame:
    """One row per report, in time order (reports from different stations are interleaved)."""
    readings = pd.read_csv(path, usecols=COLUMNS, parse_dates=["ts"])
    readings["station"] = readings["station"].str.upper()
    return readings.sort_values("ts", kind="stable").reset_index(drop=True)
