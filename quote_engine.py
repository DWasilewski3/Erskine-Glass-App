"""Pricing formulas matching Erskine_and_Sons_Master.xlsm."""

from __future__ import annotations

import math
import re
from typing import Any


def _num(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_measure(value: Any, default: float = 0.0) -> float:
    """Accept 22, 22.5, 1/2, 22 1/2, or 22-1/2."""
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        pass
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    mixed = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*[-\s]\s*(\d+)\s*/\s*(\d+)", text)
    if mixed:
        whole, num, den = mixed.groups()
        denom = float(den)
        if denom == 0:
            return default
        whole_n = float(whole)
        sign = -1.0 if whole_n < 0 else 1.0
        return sign * (abs(whole_n) + float(num) / denom)
    frac = re.fullmatch(r"(-)?\s*(\d+)\s*/\s*(\d+)", text)
    if frac:
        sign, num, den = frac.groups()
        denom = float(den)
        if denom == 0:
            return default
        return (-1.0 if sign else 1.0) * float(num) / denom
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
    w = parse_measure(width)
    h = parse_measure(height)
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
    Color / VERT / HORI do not affect the total.
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
    out.pop("spacer", None)
    if line.get("width") not in (None, ""):
        out["width"] = parse_measure(line.get("width"))
    if line.get("height") not in (None, ""):
        out["height"] = parse_measure(line.get("height"))
    sqft = line_sqft(out.get("width"), out.get("height"), line.get("qty"))
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
