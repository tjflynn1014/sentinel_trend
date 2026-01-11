from __future__ import annotations

import pytest

from sentinel_trend.agents import tools


def test_compare_variants_keys(monkeypatch) -> None:
    def _stub_real_backtest(sma_window: int, cost_bps: float, refresh: bool) -> dict:
        return {
            "cagr": 0.1 + sma_window * 0.0,
            "max_drawdown": -0.2,
        }

    monkeypatch.setattr(tools, "tool_real_backtest", _stub_real_backtest)
    result = tools.tool_compare_variants([180, 200], cost_bps=5.0, refresh=False)
    assert set(result["results"].keys()) == {180, 200}


def test_compare_variants_robustness_flag(monkeypatch) -> None:
    def _stub_real_backtest(sma_window: int, cost_bps: float, refresh: bool) -> dict:
        if sma_window == 180:
            return {"cagr": 0.03, "max_drawdown": -0.10}
        return {"cagr": 0.10, "max_drawdown": -0.25}

    monkeypatch.setattr(tools, "tool_real_backtest", _stub_real_backtest)
    result = tools.tool_compare_variants([180, 200], cost_bps=5.0, refresh=False)
    assert result["robustness"]["is_robust"] is False
