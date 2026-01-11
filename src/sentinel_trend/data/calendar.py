from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence


def trading_days_from_prices(prices: Mapping[date, float]) -> list[date]:
    return sorted(prices.keys())


def intersect_trading_days(a: Sequence[date], b: Sequence[date]) -> list[date]:
    return sorted(set(a).intersection(b))
