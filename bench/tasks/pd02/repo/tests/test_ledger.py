from pathlib import Path

import pandas as pd

from app.ledger import load_ledger, monthly_pnl

DATA = Path(__file__).parent / "data" / "ledger.csv"


def test_load_ledger_parses_dates_and_strips_accounts():
    ledger = load_ledger(DATA)
    assert list(ledger.columns) == ["date", "account", "amount"]
    assert pd.api.types.is_datetime64_any_dtype(ledger["date"])
    assert ledger["account"].iloc[0] == "Revenue"


def test_monthly_pnl_sums_per_account_and_month():
    table = monthly_pnl(load_ledger(DATA))
    assert list(table.columns) == ["2026-07", "2026-08"]
    assert list(table.index) == ["Refunds", "Revenue", "Salaries", "Travel"]
    assert table.loc["Revenue", "2026-07"] == 12500.0
    assert table.loc["Salaries", "2026-08"] == -8200.0
    assert pd.isna(table.loc["Travel", "2026-07"])
