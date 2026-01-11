from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, Mapping, Sequence


@dataclass(frozen=True)
class TrendDecision:
    signal_date: date
    trade_date: date
    spy_close: float
    sma_200: float
    target_asset: Literal["SPY", "BIL"]


def compute_sma(values: Sequence[float], window: int) -> float:
    if window <= 0:
        raise ValueError("window must be positive")
    if len(values) < window:
        raise ValueError("not enough values for window")
    return sum(values[-window:]) / window


def decide_target(spy_close: float, sma: float) -> Literal["SPY", "BIL"]:
    return "SPY" if spy_close > sma else "BIL"


def month_end_signal_dates(trading_days: Sequence[date]) -> list[date]:
    if not trading_days:
        return []

    month_ends: list[date] = []
    last_day = trading_days[0]
    last_month = (last_day.year, last_day.month)

    for day in trading_days[1:]:
        current_month = (day.year, day.month)
        if current_month != last_month:
            month_ends.append(last_day)
            last_month = current_month
        last_day = day

    month_ends.append(last_day)
    return month_ends


def next_trading_day(trading_days: Sequence[date], d: date) -> date:
    for day in trading_days:
        if day > d:
            return day
    raise ValueError("no next trading day available")


def make_trend_decisions(
    trading_days: Sequence[date],
    spy_adj_close: Mapping[date, float],
    window: int = 200,
) -> list[TrendDecision]:
    if window <= 0:
        raise ValueError("window must be positive")

    index_by_date = {day: idx for idx, day in enumerate(trading_days)}
    decisions: list[TrendDecision] = []

    for signal_date in month_end_signal_dates(trading_days):
        idx = index_by_date.get(signal_date)
        if idx is None or idx + 1 < window:
            continue
        if idx >= len(trading_days) - 1:
            continue

        window_days = trading_days[idx - window + 1 : idx + 1]
        window_values = [spy_adj_close[day] for day in window_days]
        sma = compute_sma(window_values, window)
        spy_close = spy_adj_close[signal_date]
        trade_date = next_trading_day(trading_days, signal_date)
        target = decide_target(spy_close, sma)

        decisions.append(
            TrendDecision(
                signal_date=signal_date,
                trade_date=trade_date,
                spy_close=spy_close,
                sma_200=sma,
                target_asset=target,
            )
        )

    return decisions
