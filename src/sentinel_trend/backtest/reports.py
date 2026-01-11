from __future__ import annotations

from datetime import date
from typing import Any

from sentinel_trend.backtest.engine import BacktestResult


def _fmt_date(value: date) -> str:
    return value.isoformat()


def write_decision_record(
    path: str,
    config: dict,
    result: BacktestResult,
    metrics: dict,
) -> None:
    lines: list[str] = []
    lines.append("# Decision Record")
    lines.append("")
    lines.append("## Configuration")
    lines.append(f"- Assets: {', '.join(config.get('assets', []))}")
    lines.append(f"- SMA Window: {config.get('sma_window')}")
    lines.append(f"- Cost (bps per side): {config.get('cost_bps')}")
    lines.append(f"- Date Range: {_fmt_date(result.start_date)} to {_fmt_date(result.end_date)}")
    lines.append("")
    lines.append("## Summary Metrics")
    lines.append(f"- CAGR: {metrics.get('cagr'):.4f}")
    lines.append(f"- Max Drawdown: {metrics.get('max_drawdown'):.4f}")
    lines.append(f"- Volatility: {metrics.get('volatility'):.4f}")
    lines.append(f"- Final Value: {result.final_value:,.2f}")
    lines.append("")
    lines.append("## Trades")
    lines.append("| Date | From | To | Cost |")
    lines.append("| --- | --- | --- | --- |")
    for trade in result.trades:
        lines.append(
            f"| {_fmt_date(trade['date'])} | {trade['from_asset']} | "
            f"{trade['to_asset']} | {trade['cost_amount']:.2f} |"
        )
    lines.append("")
    lines.append("## Last 10 Equity Points")
    lines.append("| Date | Value |")
    lines.append("| --- | --- |")
    for day, value in result.equity_curve[-10:]:
        lines.append(f"| {_fmt_date(day)} | {value:,.2f} |")
    lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
