"""Reading the daily orders export."""

from pathlib import Path

import pandas as pd

COLUMNS = ["sku", "qty", "note", "price"]


def load_orders(path: str | Path) -> pd.DataFrame:
    """The orders export as a frame with the ETL's columns, in file order."""
    return pd.read_csv(path, usecols=COLUMNS)[COLUMNS]
