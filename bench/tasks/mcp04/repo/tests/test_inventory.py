import pytest

from app import inventory


def test_reserve_decrements(monkeypatch):
    monkeypatch.setitem(inventory.STOCK, "KB-101", 7)
    assert inventory.reserve("KB-101", 2) == 5


def test_reserve_refuses_more_than_available(monkeypatch):
    monkeypatch.setitem(inventory.STOCK, "KB-205", 0)
    with pytest.raises(inventory.OutOfStock):
        inventory.reserve("KB-205", 1)
