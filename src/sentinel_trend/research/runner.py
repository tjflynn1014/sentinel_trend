from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Mapping

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


def _restrict_prices(
    prices: Mapping[date, float],
    trading_days: list[date],
) -> dict[date, float]:
    return {day: prices[day] for day in trading_days}


def run_variant(sma_window: int, cost_bps: float, refresh: bool) -> dict:
    cache_dir = ".cache/stooq"
    spy_prices = get_prices("SPY", cache_dir=cache_dir, force_refresh=refresh)
    bil_prices = get_prices("BIL", cache_dir=cache_dir, force_refresh=refresh)

    trading_days = intersect_trading_days(
        trading_days_from_prices(spy_prices),
        trading_days_from_prices(bil_prices),
    )
    spy_prices = _restrict_prices(spy_prices, trading_days)
    bil_prices = _restrict_prices(bil_prices, trading_days)

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
    record_path = runs_dir / f"real_decision_record_{sma_window}.md"
    config = {
        "assets": ["SPY", "BIL"],
        "sma_window": sma_window,
        "cost_bps": cost_bps,
    }
    write_decision_record(str(record_path), config, result, metrics)

    qa_warnings = run_all_checks(
        {"SPY": spy_prices, "BIL": bil_prices},
        trading_days,
    )

    return {
        "window": sma_window,
        "date_range": _iso_range(result.start_date, result.end_date),
        "final_value": result.final_value,
        "cagr": metrics["cagr"],
        "max_drawdown": metrics["max_drawdown"],
        "volatility": metrics["volatility"],
        "turnover_initial": metrics["turnover_initial"],
        "turnover_avg_equity": metrics["turnover_avg_equity"],
        "trade_count": metrics["trade_count"],
        "qa_warnings": qa_warnings,
        "decision_record_path": str(record_path),
    }


def compare_variants(windows: list[int], cost_bps: float, refresh: bool) -> dict:
    results = [run_variant(window, cost_bps, refresh) for window in windows]
    results.sort(key=lambda item: item["window"])

    cagr_values = [item["cagr"] for item in results]
    dd_values = [item["max_drawdown"] for item in results]
    cagr_range = max(cagr_values) - min(cagr_values)
    dd_range = max(dd_values) - min(dd_values)

    reasons: list[str] = []
    if abs(cagr_range) > 0.02:
        reasons.append("CAGR range exceeds 2% absolute.")
    if abs(dd_range) > 0.05:
        reasons.append("Max drawdown range exceeds 5% absolute.")

    return {
        "results": results,
        "robust": len(reasons) == 0,
        "reasons": reasons,
    }


def write_research_report(path: str, comparison: dict, cost_bps: float) -> None:
    results = comparison["results"]
    windows = [item["window"] for item in results]
    date_range = results[0]["date_range"] if results else "n/a"

    lines: list[str] = []
    lines.append("# Research Report")
    lines.append("")
    lines.append("## Configuration")
    lines.append(f"- Windows: {', '.join(str(w) for w in windows)}")
    lines.append(f"- Cost (bps per side): {cost_bps}")
    lines.append(f"- Date Range: {date_range}")
    lines.append("")
    lines.append("## Robustness Verdict")
    verdict = "robust" if comparison["robust"] else "not robust"
    lines.append(f"- Verdict: {verdict}")
    if comparison["reasons"]:
        lines.append("- Reasons:")
        for reason in comparison["reasons"]:
            lines.append(f"  - {reason}")
    lines.append("")
    lines.append("## Summary Table")
    lines.append(
        "| Window | CAGR | Max Drawdown | Volatility | Turnover (Avg Eq) | Trades | Final Value |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for item in results:
        lines.append(
            "| {window} | {cagr:.4f} | {max_drawdown:.4f} | {volatility:.4f} | "
            "{turnover_avg_equity:.4f} | {trade_count} | {final_value:,.2f} |".format(
                **item
            )
        )
    lines.append("")
    lines.append("## QA Warnings")
    for item in results:
        lines.append(f"- Window {item['window']}:")
        if item["qa_warnings"]:
            for warning in item["qa_warnings"]:
                lines.append(f"  - {warning}")
        else:
            lines.append("  - None")
    lines.append("")
    lines.append("## Decision Records")
    for item in results:
        lines.append(f"- Window {item['window']}: {item['decision_record_path']}")
    lines.append("")

    Path(path).write_text("\n".join(lines), encoding="utf-8")
