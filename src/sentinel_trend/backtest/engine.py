from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

from sentinel_trend.backtest.costs import apply_cost
from sentinel_trend.strategy.trend_sma import TrendDecision


@dataclass(frozen=True)
class BacktestResult:
    start_date: date
    end_date: date
    initial_value: float
    final_value: float
    equity_curve: list[tuple[date, float]]
    holdings: list[tuple[date, str]]
    trades: list[dict]


def run_backtest(
    trading_days: Sequence[date],
    prices_by_asset: Mapping[str, Mapping[date, float]],
    decisions: Sequence[TrendDecision],
    initial_value: float = 100_000.0,
    cost_bps: float = 5.0,
) -> BacktestResult:
    if not decisions:
        raise ValueError("decisions must not be empty")

    prices_spy = prices_by_asset.get("SPY")
    prices_bil = prices_by_asset.get("BIL")
    if prices_spy is None or prices_bil is None:
        raise ValueError("prices_by_asset must contain SPY and BIL")

    trade_dates = {d.trade_date for d in decisions}
    start_date = min(trade_dates)
    end_date = trading_days[-1]
    if start_date not in trading_days:
        raise ValueError("start_date not in trading_days")

    first_decision = min(decisions, key=lambda d: d.trade_date)
    current_asset = first_decision.target_asset
    value = initial_value

    trades: list[dict] = []
    equity_curve: list[tuple[date, float]] = []
    holdings: list[tuple[date, str]] = []

    prev_day: date | None = None
    for day in trading_days:
        if day < start_date:
            continue

        if prev_day is not None:
            price_map = prices_spy if current_asset == "SPY" else prices_bil
            if prev_day not in price_map or day not in price_map:
                raise ValueError("missing price for held asset")
            value *= price_map[day] / price_map[prev_day]

        if day in trade_dates:
            decision = next(d for d in decisions if d.trade_date == day)
            if decision.target_asset != current_asset:
                pre_value = value
                value = apply_cost(value, cost_bps)
                from_asset = current_asset
                current_asset = decision.target_asset
                value = apply_cost(value, cost_bps)
                cost_amount = pre_value - value
                trades.append(
                    {
                        "date": day,
                        "from_asset": from_asset,
                        "to_asset": current_asset,
                        "pre_value": pre_value,
                        "post_value": value,
                        "cost_bps": cost_bps,
                        "cost_amount": cost_amount,
                    }
                )

        equity_curve.append((day, value))
        holdings.append((day, current_asset))
        prev_day = day

    if not equity_curve:
        raise ValueError("equity_curve is empty")

    return BacktestResult(
        start_date=equity_curve[0][0],
        end_date=equity_curve[-1][0],
        initial_value=initial_value,
        final_value=equity_curve[-1][1],
        equity_curve=equity_curve,
        holdings=holdings,
        trades=trades,
    )
