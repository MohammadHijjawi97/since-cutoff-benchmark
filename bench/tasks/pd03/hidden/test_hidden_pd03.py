import numpy as np
import pandas as pd

from app.gaps import fill_gaps

NAN = np.nan


def reports():
    return pd.DataFrame(
        {
            "station": ["A", "B", "A", "B", "A", "C", "B", "A", "C", "B", "A"],
            "ts": pd.date_range("2026-09-01 06:00", periods=11, freq="5min"),
            "temp_c": [NAN, NAN, 11.0, 7.5, NAN, NAN, NAN, 12.5, NAN, 8.0, NAN],
            "battery": [98.0, 91.0, 97.0, NAN, 96.0, 80.0, 90.0, 95.0, 79.0, 89.0, 94.0],
        }
    )


EXPECTED = [11.0, 7.5, 11.0, 7.5, 11.0, NAN, 7.5, 12.5, NAN, 8.0, 12.5]


def test_gaps_filled_from_the_same_station():
    out = fill_gaps(reports())
    pd.testing.assert_series_equal(
        out["temp_c"].reset_index(drop=True), pd.Series(EXPECTED, name="temp_c"), check_dtype=False
    )


def test_station_without_temperatures_stays_missing():
    out = fill_gaps(reports())
    assert out.loc[out["station"] == "C", "temp_c"].isna().all()


def test_rows_order_and_other_columns_unchanged():
    src = reports()
    out = fill_gaps(src)
    assert out.index.equals(src.index)
    assert list(out.columns) == ["station", "ts", "temp_c", "battery"]
    pd.testing.assert_frame_equal(out[["station", "ts", "battery"]], src[["station", "ts", "battery"]])


def test_input_not_modified_and_complete_frame_unchanged():
    src = reports()
    fill_gaps(src)
    pd.testing.assert_frame_equal(src, reports())
    full = reports().dropna(subset=["temp_c"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(fill_gaps(full), full)
