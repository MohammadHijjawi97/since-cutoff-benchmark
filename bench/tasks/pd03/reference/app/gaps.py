"""Repair of missing values in station reports."""

from __future__ import annotations

import pandas as pd


def fill_gaps(readings: pd.DataFrame) -> pd.DataFrame:
    out = readings.copy()
    # per station: carry the last reading forward, then fill leading gaps from the first reading
    out["temp_c"] = out.groupby("station")["temp_c"].transform(lambda s: s.ffill().bfill())
    return out
