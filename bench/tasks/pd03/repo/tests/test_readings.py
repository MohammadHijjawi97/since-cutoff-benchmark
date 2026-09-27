from pathlib import Path

import pandas as pd

from app.readings import load_readings

DATA = Path(__file__).parent / "data" / "reports.csv"


def test_columns_and_time_order():
    readings = load_readings(DATA)
    assert list(readings.columns) == ["station", "ts", "temp_c", "battery"]
    assert readings["ts"].is_monotonic_increasing
    assert list(readings.index) == [0, 1, 2, 3]


def test_station_ids_upper_case_and_missing_kept():
    readings = load_readings(DATA)
    assert readings["station"].tolist() == ["A", "B", "A", "B"]
    assert pd.isna(readings.loc[0, "temp_c"]) and pd.isna(readings.loc[3, "temp_c"])
