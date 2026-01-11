from __future__ import annotations

from datetime import date, timedelta

import pytest

from sentinel_trend.strategy.trend_sma import (
    TrendDecision,
    compute_sma,
    decide_target,
    make_trend_decisions,
    month_end_signal_dates,
    next_trading_day,
)


def generate_weekdays(start: date, count: int) -> list[date]:
    days: list[date] = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def test_compute_sma_happy_path() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert compute_sma(values, 2) == 3.5


def test_compute_sma_errors() -> None:
    with pytest.raises(ValueError):
        compute_sma([1.0, 2.0], 0)
    with pytest.raises(ValueError):
        compute_sma([1.0, 2.0], 3)


def test_decide_target_boundary() -> None:
    assert decide_target(100.0, 100.0) == "BIL"
    assert decide_target(101.0, 100.0) == "SPY"


def test_month_end_signal_dates() -> None:
    trading_days = [
        date(2023, 1, 30),
        date(2023, 1, 31),
        date(2023, 2, 1),
        date(2023, 2, 28),
        date(2023, 3, 1),
        date(2023, 3, 31),
    ]
    assert month_end_signal_dates(trading_days) == [
        date(2023, 1, 31),
        date(2023, 2, 28),
        date(2023, 3, 31),
    ]


def test_next_trading_day() -> None:
    trading_days = [date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 5)]
    assert next_trading_day(trading_days, date(2023, 1, 2)) == date(2023, 1, 3)
    with pytest.raises(ValueError):
        next_trading_day(trading_days, date(2023, 1, 5))


def test_make_trend_decisions() -> None:
    trading_days = generate_weekdays(date(2023, 1, 2), 270)
    prices: dict[date, float] = {}
    for idx, day in enumerate(trading_days):
        if idx < 220:
            prices[day] = 100.0
        else:
            prices[day] = 100.0 + (idx - 219) * 2.0

    decisions = make_trend_decisions(trading_days, prices, window=200)

    eligible_month_ends = [
        d
        for d in month_end_signal_dates(trading_days)
        if trading_days.index(d) + 1 >= 200 and d != trading_days[-1]
    ]
    assert len(decisions) == len(eligible_month_ends)
    assert isinstance(decisions[0], TrendDecision)
    assert decisions[0].target_asset == "BIL"
    assert decisions[-1].target_asset == "SPY"

    for decision in decisions:
        assert decision.trade_date > decision.signal_date
        assert decision.signal_date in trading_days
        assert decision.trade_date in trading_days

    first = decisions[0]
    first_idx = trading_days.index(first.signal_date)
    window_days = trading_days[first_idx - 200 + 1 : first_idx + 1]
    expected_sma = sum(prices[d] for d in window_days) / 200
    assert first.sma_200 == expected_sma
