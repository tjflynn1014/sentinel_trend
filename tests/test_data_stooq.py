from __future__ import annotations

from datetime import date

import pytest

from sentinel_trend.data import stooq


def test_normalize_symbol() -> None:
    assert stooq.normalize_symbol("spy") == "spy.us"
    assert stooq.normalize_symbol("BIL") == "bil.us"
    with pytest.raises(ValueError):
        stooq.normalize_symbol("qqq")


def test_parse_stooq_daily_csv() -> None:
    csv_text = "\n".join(
        [
            "Date,Open,High,Low,Close,Volume",
            "2023-01-03,10,11,9,10.5,100",
            "2023-01-04,10,11,9,10.6,100",
            "2023-01-05,10,11,9,10.7,100",
        ]
    )
    parsed = stooq.parse_stooq_daily_csv(csv_text)
    assert parsed[date(2023, 1, 3)] == 10.5
    assert len(parsed) == 3


def test_get_prices_uses_cache(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "stooq"
    cache_dir.mkdir()
    cache_path = cache_dir / "spy.us.csv"
    cache_path.write_text(
        "Date,Open,High,Low,Close,Volume\n2023-01-03,10,11,9,10.5,100\n",
        encoding="utf-8",
    )

    def _fail_download(symbol: str) -> str:
        raise AssertionError("download should not be called")

    monkeypatch.setattr(stooq, "download_stooq_daily_csv", _fail_download)
    prices = stooq.get_prices("SPY", cache_dir=str(cache_dir), force_refresh=False)
    assert prices[date(2023, 1, 3)] == 10.5


def test_get_prices_force_refresh(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "stooq"
    cache_dir.mkdir()

    def _download(symbol: str) -> str:
        return (
            "Date,Open,High,Low,Close,Volume\n"
            "2023-01-03,10,11,9,10.5,100\n"
        )

    monkeypatch.setattr(stooq, "download_stooq_daily_csv", _download)
    prices = stooq.get_prices("SPY", cache_dir=str(cache_dir), force_refresh=True)
    assert prices[date(2023, 1, 3)] == 10.5
