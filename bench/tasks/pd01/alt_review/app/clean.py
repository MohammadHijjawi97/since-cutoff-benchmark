"""Cleaning step of the orders ETL.

Reviewer's alternative answer: text columns found with `is_string_dtype` column by column, empty strings replaced
with NaN, and the fill assigned back.
"""

import numpy as np
import pandas as pd


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].str.strip().replace("", np.nan)
    out["qty"] = out["qty"].fillna(0)
    return out
