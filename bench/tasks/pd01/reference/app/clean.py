"""Cleaning step of the orders ETL."""

import pandas as pd


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # pandas 3: text columns use the dedicated `str` dtype, not `object`; select both.
    for col in out.select_dtypes(include=["object", "string"]).columns:
        stripped = out[col].str.strip()
        out[col] = stripped.where(stripped != "")
    # pandas 3 (Copy-on-Write): assign the result; `out[col].fillna(..., inplace=True)` would be a no-op.
    out["qty"] = out["qty"].fillna(0)
    return out
