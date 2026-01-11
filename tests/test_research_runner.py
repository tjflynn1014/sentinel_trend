from __future__ import annotations

from sentinel_trend.research import runner


def test_compare_variants_not_robust(monkeypatch) -> None:
    def _stub_run_variant(window: int, cost_bps: float, refresh: bool) -> dict:
        if window == 180:
            return {"window": window, "cagr": 0.01, "max_drawdown": -0.10}
        if window == 200:
            return {"window": window, "cagr": 0.06, "max_drawdown": -0.30}
        return {"window": window, "cagr": 0.03, "max_drawdown": -0.15}

    monkeypatch.setattr(runner, "run_variant", _stub_run_variant)
    comparison = runner.compare_variants([180, 200, 220], cost_bps=5.0, refresh=False)
    assert comparison["robust"] is False


def test_write_research_report_contains_headers(tmp_path) -> None:
    report_path = tmp_path / "research_report.md"
    comparison = {
        "results": [
            {
                "window": 180,
                "date_range": "2020-01-01 to 2021-01-01",
                "final_value": 120_000.0,
                "cagr": 0.10,
                "max_drawdown": -0.20,
                "volatility": 0.15,
                "turnover_avg_equity": 1.2,
                "trade_count": 10,
                "qa_warnings": ["warn-a"],
                "decision_record_path": "runs/real_decision_record_180.md",
            }
        ],
        "robust": True,
        "reasons": [],
    }
    runner.write_research_report(str(report_path), comparison, cost_bps=5.0)
    content = report_path.read_text(encoding="utf-8")
    assert "| Window | CAGR | Max Drawdown | Volatility | Turnover (Avg Eq) | Trades | Final Value |" in content
    assert "Verdict: robust" in content
