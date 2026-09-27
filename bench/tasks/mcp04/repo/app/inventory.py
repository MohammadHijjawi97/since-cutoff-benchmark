"""Stock levels (in-memory for now; the real warehouse API comes later)."""

from __future__ import annotations

STOCK: dict[str, int] = {"KB-101": 7, "KB-205": 0, "MS-330": 42}


class OutOfStock(Exception):
    pass


def stock_level(sku: str) -> int:
    if sku not in STOCK:
        raise KeyError(f"unknown SKU {sku}")
    return STOCK[sku]


def reserve(sku: str, quantity: int) -> int:
    """Reserve `quantity` units of `sku`; returns the units left."""
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    available = stock_level(sku)
    if quantity > available:
        raise OutOfStock(f"only {available} units of {sku} left")
    STOCK[sku] = available - quantity
    return STOCK[sku]
