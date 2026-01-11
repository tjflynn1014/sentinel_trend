from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

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
from sentinel_trend.data.stooq import get_prices
from sentinel_trend.strategy.trend_sma import make_trend_decisions


def _iso_range(start: date, end: date) -> str:
    return f"{start.isoformat()} to {end.isoformat()}"


def tool_real_backtest(sma_window: int, cost_bps: float, refresh: bool) -> dict:
    cache_dir = ".cache/stooq"
    spy_prices = get_prices("SPY", cache_dir=cache_dir, force_refresh=refresh)
    bil_prices = get_prices("BIL", cache_dir=cache_dir, force_refresh=refresh)

    trading_days = intersect_trading_days(
        trading_days_from_prices(spy_prices),
        trading_days_from_prices(bil_prices),
    )
    spy_prices = {day: spy_prices[day] for day in trading_days}
    bil_prices = {day: bil_prices[day] for day in trading_days}

    decisions = make_trend_decisions(trading_days, spy_prices, window=sma_window)
    result = run_backtest(
        trading_days,
        prices_by_asset={"SPY": spy_prices, "BIL": bil_prices},
        decisions=decisions,
        initial_value=100_000.0,
        cost_bps=cost_bps,
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
    report_path = runs_dir / f"real_decision_record_{sma_window}.md"
    config = {
        "assets": ["SPY", "BIL"],
        "sma_window": sma_window,
        "cost_bps": cost_bps,
    }
    write_decision_record(str(report_path), config, result, metrics)

    qa_warnings = run_all_checks(
        {"SPY": spy_prices, "BIL": bil_prices},
        trading_days,
    )

    return {
        "date_range": _iso_range(result.start_date, result.end_date),
        "final_value": result.final_value,
        "cagr": metrics["cagr"],
        "max_drawdown": metrics["max_drawdown"],
        "volatility": metrics["volatility"],
        "turnover_initial": metrics["turnover_initial"],
        "turnover_avg_equity": metrics["turnover_avg_equity"],
        "trade_count": metrics["trade_count"],
        "path_decision_record": str(report_path),
        "qa_warnings": qa_warnings,
    }


def tool_compare_variants(
    windows: list[int],
    cost_bps: float,
    refresh: bool,
) -> dict:
    results: dict[int, dict] = {}
    for window in windows:
        results[window] = tool_real_backtest(window, cost_bps, refresh)

    cagr_values = [results[w]["cagr"] for w in windows]
    dd_values = [results[w]["max_drawdown"] for w in windows]
    cagr_range = max(cagr_values) - min(cagr_values)
    dd_range = max(dd_values) - min(dd_values)
    is_robust = not (cagr_range > 0.02 or dd_range > 0.05)

    return {
        "results": results,
        "robustness": {
            "is_robust": is_robust,
            "cagr_range": cagr_range,
            "max_drawdown_range": dd_range,
            "heuristic": "Flag if CAGR varies by >2% or max drawdown varies by >5% (absolute).",
        },
    }
