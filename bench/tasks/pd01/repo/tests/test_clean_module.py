import app.clean


def test_has_clean_orders():
    assert callable(app.clean.clean_orders)
