Sentinel Trend

Sentinel Trend is a minimalist research scaffold for a monthly trend-following
rotation between SPY and BIL using a 200-day simple moving average signal.
It focuses on clean data plumbing and reproducible experiments first, with
paper trading and broker integrations planned later. Stooq daily Close prices
are used as a proxy (not adjusted close), for research only.

Run tests:
uv run pytest

Run the CLI:
uv run sentinel-trend

Run the real-data backtest:
uv run sentinel-trend --real
