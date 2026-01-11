"""CLI entry point for sentinel_trend."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from sentinel_trend.backtest.engine import run_backtest
from sentinel_trend.backtest.metrics import cagr, max_drawdown, volatility
from sentinel_trend.backtest.reports import write_decision_record
from sentinel_trend.strategy.trend_sma import make_trend_decisions


def _generate_weekdays(start: date, count: int) -> list[date]:
    days: list[date] = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _generate_prices(trading_days: list[date]) -> dict[str, dict[date, float]]:
    spy_prices: dict[date, float] = {}
    bil_prices: dict[date, float] = {}
    for idx, day in enumerate(trading_days):
        if idx < 260:
            spy_prices[day] = 100.0
        else:
            spy_prices[day] = 100.0 + (idx - 259) * 1.5
        bil_prices[day] = 100.0 + idx * 0.05
    return {"SPY": spy_prices, "BIL": bil_prices}


def _run_demo() -> None:
    trading_days = _generate_weekdays(date(2021, 1, 4), 756)
    prices_by_asset = _generate_prices(trading_days)
    decisions = make_trend_decisions(trading_days, prices_by_asset["SPY"])
    result = run_backtest(trading_days, prices_by_asset, decisions)
    metrics = {
        "cagr": cagr(result.equity_curve),
        "max_drawdown": max_drawdown(result.equity_curve),
        "volatility": volatility(result.equity_curve),
    }

    runs_dir = Path("runs")
    runs_dir.mkdir(parents=True, exist_ok=True)
    report_path = runs_dir / "demo_decision_record.md"
    config = {
        "assets": ["SPY", "BIL"],
        "sma_window": 200,
        "cost_bps": 5.0,
    }
    write_decision_record(str(report_path), config, result, metrics)

    print("sentinel_trend: demo run complete")
    print(f"Final value: {result.final_value:,.2f}")
    print(
        "CAGR: {:.4f} | Max Drawdown: {:.4f} | Volatility: {:.4f}".format(
            metrics["cagr"],
            metrics["max_drawdown"],
            metrics["volatility"],
        )
    )
    print(f"Decision record: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="sentinel_trend CLI")
    parser.add_argument("--demo", action="store_true", help="run demo backtest")
    args = parser.parse_args()

    if args.demo:
        _run_demo()
        return

    print("sentinel_trend: scaffold OK")
