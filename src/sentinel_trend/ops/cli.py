"""CLI entry point for sentinel_trend."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from sentinel_trend.backtest.engine import run_backtest
from sentinel_trend.backtest.metrics import (
    cagr,
    max_drawdown,
    turnover_avg_equity,
    turnover_initial,
    volatility,
)
from sentinel_trend.backtest.reports import write_decision_record
from sentinel_trend.data.calendar import intersect_trading_days, trading_days_from_prices
from sentinel_trend.data.qa import run_all_checks
from sentinel_trend.data.stooq import get_prices, normalize_symbol
from sentinel_trend.research.runner import compare_variants, write_research_report
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


def _run_real(force_refresh: bool) -> None:
    cache_dir = ".cache/stooq"
    spy_prices = get_prices("SPY", cache_dir=cache_dir, force_refresh=force_refresh)
    bil_prices = get_prices("BIL", cache_dir=cache_dir, force_refresh=force_refresh)

    spy_days = trading_days_from_prices(spy_prices)
    bil_days = trading_days_from_prices(bil_prices)
    trading_days = intersect_trading_days(spy_days, bil_days)
    spy_prices = {day: spy_prices[day] for day in trading_days}
    bil_prices = {day: bil_prices[day] for day in trading_days}

    decisions = make_trend_decisions(trading_days, spy_prices, window=200)
    result = run_backtest(
        trading_days,
        prices_by_asset={"SPY": spy_prices, "BIL": bil_prices},
        decisions=decisions,
        initial_value=100_000.0,
        cost_bps=5.0,
    )
    metrics = {
        "cagr": cagr(result.equity_curve),
        "max_drawdown": max_drawdown(result.equity_curve),
        "volatility": volatility(result.equity_curve),
        "turnover_initial": turnover_initial(result.trades, result.initial_value),
        "turnover_avg_equity": turnover_avg_equity(
            result.trades, result.equity_curve
        ),
        "trade_count": len(result.trades),
    }

    runs_dir = Path("runs")
    runs_dir.mkdir(parents=True, exist_ok=True)
    report_path = runs_dir / "real_decision_record.md"
    config = {
        "assets": ["SPY", "BIL"],
        "sma_window": 200,
        "cost_bps": 5.0,
    }
    write_decision_record(str(report_path), config, result, metrics)

    warnings = run_all_checks(
        {"SPY": spy_prices, "BIL": bil_prices},
        trading_days,
    )

    print("sentinel_trend: real run complete")
    print(f"Date range: {result.start_date} to {result.end_date}")
    print(f"Final value: {result.final_value:,.2f}")
    print(
        "CAGR: {:.4f} | Max Drawdown: {:.4f} | Volatility: {:.4f}".format(
            metrics["cagr"],
            metrics["max_drawdown"],
            metrics["volatility"],
        )
    )
    print(f"Turnover (initial): {metrics['turnover_initial']:.4f}")
    print(f"Turnover (avg equity): {metrics['turnover_avg_equity']:.4f}")
    print(f"Number of trades: {metrics['trade_count']}")
    print(
        "Cache files: {}, {}".format(
            Path(cache_dir) / f"{normalize_symbol('SPY')}.csv",
            Path(cache_dir) / f"{normalize_symbol('BIL')}.csv",
        )
    )
    for warning in warnings:
        print(f"QA: {warning}")
    print(f"Decision record: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="sentinel_trend CLI")
    parser.add_argument("--demo", action="store_true", help="run demo backtest")
    parser.add_argument("--real", action="store_true", help="run real backtest")
    parser.add_argument("--refresh", action="store_true", help="refresh cached data")
    parser.add_argument(
        "--agent-research",
        action="store_true",
        help="run agent research workflow",
    )
    parser.add_argument("--research", action="store_true", help="run local research")
    parser.add_argument("--cost-bps", type=float, default=5.0, help="cost in bps per side")
    args = parser.parse_args()

    if args.demo:
        _run_demo()
        return
    if args.real:
        _run_real(force_refresh=args.refresh)
        return
    if args.agent_research:
        print(
            "Agent research disabled: OpenAI API quota not configured. Use --research instead.",
            file=sys.stderr,
        )
        return
    if args.research:
        comparison = compare_variants([180, 200, 220], args.cost_bps, args.refresh)
        runs_dir = Path("runs")
        runs_dir.mkdir(parents=True, exist_ok=True)
        report_path = runs_dir / "research_report.md"
        write_research_report(str(report_path), comparison, args.cost_bps)
        verdict = "robust" if comparison["robust"] else "not robust"
        print(f"Research report: {report_path}")
        print(f"Verdict: {verdict}")
        return

    print("sentinel_trend: scaffold OK")
