from __future__ import annotations

from datetime import date
from math import sqrt
from typing import Sequence


def max_drawdown(equity_curve: Sequence[tuple[date, float]]) -> float:
    if not equity_curve:
        raise ValueError("equity_curve must not be empty")
    peak = equity_curve[0][1]
    max_dd = 0.0
    for _, value in equity_curve:
        if value > peak:
            peak = value
        drawdown = (value - peak) / peak
        if drawdown < max_dd:
            max_dd = drawdown
    return max_dd


def cagr(equity_curve: Sequence[tuple[date, float]]) -> float:
    if len(equity_curve) < 2:
        raise ValueError("equity_curve must have at least two points")
    start_date, start_value = equity_curve[0]
    end_date, end_value = equity_curve[-1]
    days = (end_date - start_date).days
    if days <= 0:
        raise ValueError("equity_curve must span positive time")
    years = days / 365.25
    return (end_value / start_value) ** (1.0 / years) - 1.0


def volatility(equity_curve: Sequence[tuple[date, float]]) -> float:
    if len(equity_curve) < 2:
        raise ValueError("equity_curve must have at least two points")
    returns: list[float] = []
    for idx in range(1, len(equity_curve)):
        prev = equity_curve[idx - 1][1]
        curr = equity_curve[idx][1]
        returns.append(curr / prev - 1.0)
    if not returns:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / len(returns)
    return sqrt(var) * sqrt(252.0)


def _trade_notional(trade: dict) -> float:
    if "notional_sold" in trade and "notional_bought" in trade:
        return float(trade["notional_sold"]) + float(trade["notional_bought"])
    if "value_before" in trade and "value_after_sell" in trade:
        return float(trade["value_before"]) + float(trade["value_after_sell"])
    if "pre_value" in trade:
        return float(trade["pre_value"]) * 2.0
    raise KeyError("trade does not contain notional fields")


def turnover_initial(trades: Sequence[dict], initial_value: float) -> float:
    if initial_value <= 0:
        raise ValueError("initial_value must be positive")
    total_notional = sum(_trade_notional(trade) for trade in trades)
    return total_notional / initial_value


def turnover_avg_equity(
    trades: Sequence[dict],
    equity_curve: Sequence[tuple[date, float]],
) -> float:
    if not equity_curve:
        raise ValueError("equity_curve must not be empty")
    average_equity = sum(value for _, value in equity_curve) / len(equity_curve)
    total_notional = sum(_trade_notional(trade) for trade in trades)
    return total_notional / average_equity
