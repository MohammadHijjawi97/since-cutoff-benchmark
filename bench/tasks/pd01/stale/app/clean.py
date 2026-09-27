"""Cleaning step of the orders ETL (pandas 2-era code)."""

import numpy as np
import pandas as pd


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].str.strip().replace("", np.nan)
    out["qty"].fillna(0, inplace=True)
    return out
