import pandas as pd

from app.clean import clean_orders


def frame():
    return pd.DataFrame(
        {
            "sku": [" A1 ", "B2", ""],
            "qty": [1.0, None, 3.0],
            "note": ["x ", None, "   "],
            "price": [9.5, 2.0, 1.25],
        }
    )


def test_text_columns_stripped_and_empty_to_missing():
    out = clean_orders(frame())
    assert out["sku"].iloc[0] == "A1" and out["sku"].iloc[1] == "B2"
    assert pd.isna(out["sku"].iloc[2])
    assert out["note"].iloc[0] == "x"
    assert pd.isna(out["note"].iloc[1]) and pd.isna(out["note"].iloc[2])


def test_qty_filled_and_other_columns_untouched():
    out = clean_orders(frame())
    assert out["qty"].tolist() == [1.0, 0.0, 3.0]
    assert out["price"].tolist() == [9.5, 2.0, 1.25]


def test_input_not_modified():
    df = frame()
    clean_orders(df)
    pd.testing.assert_frame_equal(df, frame())
