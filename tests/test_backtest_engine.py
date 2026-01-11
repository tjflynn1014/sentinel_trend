from __future__ import annotations

from datetime import date, timedelta

import pytest

from sentinel_trend.backtest.costs import apply_cost
from sentinel_trend.backtest.engine import run_backtest
from sentinel_trend.backtest.metrics import cagr, max_drawdown, volatility
from sentinel_trend.strategy.trend_sma import TrendDecision


def generate_weekdays(start: date, count: int) -> list[date]:
    days: list[date] = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def test_apply_cost() -> None:
    assert apply_cost(100.0, 5.0) == pytest.approx(99.95)


def test_run_backtest_dates_and_costs() -> None:
    trading_days = generate_weekdays(date(2023, 1, 2), 6)
    spy_prices = {day: 100.0 + idx for idx, day in enumerate(trading_days)}
    bil_prices = {day: 100.0 for day in trading_days}
    prices_by_asset = {"SPY": spy_prices, "BIL": bil_prices}

    decisions = [
        TrendDecision(
            signal_date=trading_days[0],
            trade_date=trading_days[1],
            spy_close=100.0,
            sma_200=100.0,
            target_asset="BIL",
        ),
        TrendDecision(
            signal_date=trading_days[2],
            trade_date=trading_days[3],
            spy_close=102.0,
            sma_200=100.0,
            target_asset="SPY",
        ),
    ]

    result = run_backtest(trading_days, prices_by_asset, decisions, initial_value=100.0, cost_bps=10.0)

    dates = [d for d, _ in result.equity_curve]
    assert dates == sorted(dates)
    assert dates == trading_days[1:]

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade["from_asset"] == "BIL"
    assert trade["to_asset"] == "SPY"
    assert trade["cost_amount"] == pytest.approx(100.0 * (1 - 0.999**2))


def test_max_drawdown() -> None:
    curve = [
        (date(2023, 1, 2), 100.0),
        (date(2023, 1, 3), 120.0),
        (date(2023, 1, 4), 90.0),
        (date(2023, 1, 5), 110.0),
    ]
    assert max_drawdown(curve) == pytest.approx(-0.25)


def test_cagr_one_year_double() -> None:
    curve = [
        (date(2020, 1, 1), 100.0),
        (date(2021, 1, 1), 200.0),
    ]
    days = (curve[-1][0] - curve[0][0]).days
    years = days / 365.25
    expected = (curve[-1][1] / curve[0][1]) ** (1.0 / years) - 1.0
    assert cagr(curve) == pytest.approx(expected)


def test_volatility_constant_returns() -> None:
    curve = [
        (date(2023, 1, 2), 100.0),
        (date(2023, 1, 3), 101.0),
        (date(2023, 1, 4), 102.01),
        (date(2023, 1, 5), 103.0301),
    ]
    assert volatility(curve) == pytest.approx(0.0, abs=1e-10)
