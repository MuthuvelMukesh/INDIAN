# Indian Market Algo Bot

This project is a local, zero-cost NSE market-data foundation for paper trading
and backtesting. It fetches read-only historical candles from Upstox, supports
daily and intraday query intervals, and caches data in SQLite. It cannot place
live orders.

## Requirements

- Python 3.11 or newer
- A free Upstox developer app with market-data read access

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Never commit `.env`. It is ignored by git, and the example contains placeholders
only.

## Upstox app registration

1. Sign in at [Upstox Developer](https://upstox.com/developer/).
2. Create an API v2 application.
3. Enter a local OAuth redirect URL such as
   `http://127.0.0.1:8000/callback`.
4. Enable only read-only market-data permissions. Do not enable order-placement,
   portfolio mutation, or trading permissions.
5. Copy the API key and secret into `.env` as `UPSTOX_API_KEY` and
   `UPSTOX_API_SECRET`.
6. Store the locally obtained access token as `UPSTOX_ACCESS_TOKEN`.

The access token must never be logged, committed, or pasted into source code.
Phase 1 uses the token only for historical market data. No real-money action is
possible in this phase.

## Tests

Tests are fully offline and do not require Upstox credentials:

```bash
pytest
```

The same checks used by CI can be run locally:

```bash
ruff check .
mypy .
pytest -v
```

The implemented slices currently include the read-only data layer, strategy
contract, SMA crossover, RSI mean-reversion, VWAP reversion, ORB, and Bollinger
strategies, backtest engine, risk controls, and paper broker. Paper-trading
orchestration, SQLite trade history, and the CLI are the next incremental phase.

## Data and intraday contracts

`HistoricalQuery` identifies an exchange-qualified Upstox instrument key, date
range, and a strict supported interval: `1d`, `1minute`, `5minute`,
`30minute`, `day`, `week`, or `month`. Legacy `1d` requests are sent to the
Upstox v2 endpoint as `day`. `MarketDataService` checks SQLite first, calls the
read-only Upstox provider on a cache miss, validates and sorts candles, then
caches the result.

For backtests, `BacktestEngine.for_interval("5minute")` selects the explicit
scalping planning assumptions and 18,900 annual periods. It uses 10 bps
slippage per side because historical OHLCV does not include bid/ask spread.
VWAP and ORB evaluate only regular NSE hours, 09:15-15:30 IST. Intraday Sharpe
sampling excludes overnight gaps rather than treating them as five-minute
returns.

The suite also covers strategy contracts, next-candle-open backtest execution,
performance metrics, risk circuit breakers, and paper-broker accounting:

```bash
pytest -q
```

Live orders remain disabled. `LiveBroker.execute()` always raises
`NotImplementedError`.