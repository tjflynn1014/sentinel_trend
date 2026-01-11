from __future__ import annotations

from datetime import date, timedelta
from typing import Mapping, Sequence


def check_nonempty(prices: Mapping[date, float], asset: str) -> list[str]:
    if not prices:
        raise ValueError(f"{asset} prices are empty")
    return []


def check_monotonic_dates(prices: Mapping[date, float], asset: str) -> list[str]:
    warnings: list[str] = []
    dates = sorted(prices.keys())
    for prev, curr in zip(dates, dates[1:]):
        if curr <= prev:
            warnings.append(f"{asset} dates are not strictly increasing")
            break
    return warnings


def check_nonpositive_prices(prices: Mapping[date, float], asset: str) -> list[str]:
    warnings: list[str] = []
    if any(value <= 0 for value in prices.values()):
        warnings.append(f"{asset} has non-positive prices")
    return warnings


def check_missing_ratio(trading_days: Sequence[date]) -> list[str]:
    warnings: list[str] = []
    if not trading_days:
        return warnings
    start = min(trading_days)
    end = max(trading_days)
    expected = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            expected += 1
        current += timedelta(days=1)
    observed = len(trading_days)
    if expected > 0:
        missing_ratio = (expected - observed) / expected
        if missing_ratio > 0.06:
            warnings.append(
                "trading_days missing ratio (heuristic, includes holidays) "
                f"{missing_ratio:.2%} exceeds 6% "
                f"(observed {observed}, expected {expected})"
            )
    return warnings


def run_all_checks(
    prices_by_asset: Mapping[str, Mapping[date, float]],
    trading_days: Sequence[date],
) -> list[str]:
    warnings: list[str] = []
    for asset, prices in prices_by_asset.items():
        warnings.extend(check_nonempty(prices, asset))
        warnings.extend(check_monotonic_dates(prices, asset))
        warnings.extend(check_nonpositive_prices(prices, asset))
    warnings.extend(check_missing_ratio(trading_days))
    return warnings
