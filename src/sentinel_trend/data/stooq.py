from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Mapping
from urllib.request import urlopen


_SYMBOL_MAP = {
    "SPY": "spy.us",
    "BIL": "bil.us",
}


def normalize_symbol(symbol: str) -> str:
    upper = symbol.upper()
    if upper not in _SYMBOL_MAP:
        raise ValueError(f"unknown symbol: {symbol}")
    return _SYMBOL_MAP[upper]


def download_stooq_daily_csv(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    url = f"https://stooq.com/q/d/l/?s={normalized}&i=d"
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def parse_stooq_daily_csv(csv_text: str) -> dict[date, float]:
    rows = csv.reader(csv_text.splitlines())
    parsed: dict[date, float] = {}
    header_seen = False
    for row in rows:
        if not row:
            continue
        if not header_seen:
            header_seen = True
            continue
        if len(row) < 5:
            continue
        date_str = row[0].strip()
        close_str = row[4].strip()
        try:
            year, month, day = (int(part) for part in date_str.split("-"))
            close = float(close_str)
        except (ValueError, TypeError):
            continue
        parsed[date(year, month, day)] = close
    return parsed


def get_prices(
    symbol: str,
    cache_dir: str = ".cache/stooq",
    force_refresh: bool = False,
) -> dict[date, float]:
    normalized = normalize_symbol(symbol)
    cache_path = Path(cache_dir) / f"{normalized}.csv"
    if cache_path.exists() and not force_refresh:
        csv_text = cache_path.read_text(encoding="utf-8")
        return parse_stooq_daily_csv(csv_text)

    csv_text = download_stooq_daily_csv(symbol)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(csv_text, encoding="utf-8")
    return parse_stooq_daily_csv(csv_text)
