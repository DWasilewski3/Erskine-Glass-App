"""Pricing formulas matching Erskine_and_Sons_Master.xlsm."""

from __future__ import annotations

import math
from typing import Any


def _num(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _lookup_price(items: list[dict], name: Any, blank_price: float) -> float:
    if name is None or str(name).strip() == "":
        return blank_price
    key = str(name).strip().lower()
    for item in items:
        if str(item.get("name", "")).strip().lower() == key:
            return _num(item.get("price"), 0.0)
    return 0.0


def line_sqft(width: Any, height: Any, qty: Any) -> float:
    """Excel: IF((ROUNDUP((W*H)/144,0)*Qty)<4, 4, ROUNDUP((W*H)/144,0)*Qty)."""
    w = _num(width)
    h = _num(height)
    q = _num(qty)
    if w <= 0 or h <= 0 or q <= 0:
        return 0.0
    per_piece = math.ceil((w * h) / 144.0)
    return max(4.0, per_piece * q)


def line_total(
    sqft: float,
    glass_type: Any,
    grid: Any,
    catalog: dict,
) -> float:
    """Excel: SqFt * (glass_price + grid_price) * TFee * Factor * Mup.

    Blank Type uses glass price 1. Blank Grid uses 0.
    Spacer / Color / VERT / HORI do not affect the total.
    """
    if sqft <= 0:
        return 0.0
    glass_price = _lookup_price(catalog.get("glass_types", []), glass_type, 1.0)
    grid_price = _lookup_price(catalog.get("grids", []), grid, 0.0)
    m = catalog.get("multipliers") or {}
    tfee = _num(m.get("tfee"), 1.0)
    factor = _num(m.get("factor"), 1.0)
    mup = _num(m.get("mup"), 1.0)
    return round(sqft * (glass_price + grid_price) * tfee * factor * mup, 2)


def price_line(line: dict, catalog: dict) -> dict:
    out = dict(line)
    sqft = line_sqft(line.get("width"), line.get("height"), line.get("qty"))
    total = line_total(sqft, line.get("type"), line.get("grid"), catalog)
    out["sqft"] = sqft
    out["total"] = total
    return out


def price_quote(payload: dict, catalog: dict) -> dict:
    lines = [price_line(line, catalog) for line in payload.get("lines") or []]
    qty_total = sum(_num(line.get("qty")) for line in lines)
    sqft_total = sum(_num(line.get("sqft")) for line in lines)
    grand_total = round(sum(_num(line.get("total")) for line in lines), 2)
    result = dict(payload)
    result["lines"] = lines
    result["qty_total"] = qty_total
    result["sqft_total"] = sqft_total
    result["grand_total"] = grand_total
    return result
