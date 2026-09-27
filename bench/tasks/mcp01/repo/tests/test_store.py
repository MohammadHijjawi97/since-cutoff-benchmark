from app.server import NOTES


def test_store_starts_empty():
    assert NOTES == {}
