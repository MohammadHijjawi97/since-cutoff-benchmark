import numpy as np
import pandas as pd

from app.report import format_for_display


def table():
    return pd.DataFrame(
        {
            "2026-07": [12500.0, -8200.0, np.nan, 0.0],
            "2026-08": [1234567.891, -634.2, 11250.5, np.nan],
        },
        index=pd.Index(["Revenue", "Salaries", "Travel", "Refunds"], name="account"),
    )


def test_accounting_style():
    out = format_for_display(table())
    assert out.loc["Revenue", "2026-07"] == "12,500.00"
    assert out.loc["Revenue", "2026-08"] == "1,234,567.89"
    assert out.loc["Salaries", "2026-07"] == "(8,200.00)"
    assert out.loc["Salaries", "2026-08"] == "(634.20)"
    assert out.loc["Travel", "2026-08"] == "11,250.50"
    assert out.loc["Refunds", "2026-07"] == "-"


def test_missing_values_become_empty_strings():
    out = format_for_display(table())
    assert out.loc["Travel", "2026-07"] == ""
    assert out.loc["Refunds", "2026-08"] == ""


def test_same_labels_and_every_cell_is_text():
    out = format_for_display(table())
    assert list(out.index) == ["Revenue", "Salaries", "Travel", "Refunds"]
    assert out.index.name == "account"
    assert list(out.columns) == ["2026-07", "2026-08"]
    assert all(isinstance(v, str) for v in out.to_numpy().ravel())


def test_integer_table_and_input_not_modified():
    src = pd.DataFrame({"2026-09": [5, -12000, 0]}, index=["A", "B", "C"])
    before = src.copy()
    out = format_for_display(src)
    assert out["2026-09"].tolist() == ["5.00", "(12,000.00)", "-"]
    pd.testing.assert_frame_equal(src, before)
    t = table()
    format_for_display(t)
    pd.testing.assert_frame_equal(t, table())
