"""Load the ledger export and aggregate it per account and month."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUMNS = ["date", "account", "amount"]


def load_ledger(path: str | Path) -> pd.DataFrame:
    """Read the ledger CSV export (one row per posting)."""
    ledger = pd.read_csv(path, usecols=COLUMNS, parse_dates=["date"])
    ledger["account"] = ledger["account"].str.strip()
    return ledger


def monthly_pnl(ledger: pd.DataFrame) -> pd.DataFrame:
    """Account x month table of summed amounts.

    Months are "YYYY-MM" column labels; an account with no posting in a month has a missing value there.
    """
    months = ledger["date"].dt.strftime("%Y-%m")
    table = ledger.assign(month=months).pivot_table(
        index="account", columns="month", values="amount", aggfunc="sum"
    )
    table.columns.name = None
    return table.sort_index()
