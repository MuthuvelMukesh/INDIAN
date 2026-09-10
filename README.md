# Indian Market Algo Bot

This project is a local, zero-cost NSE market-data foundation for paper trading
and backtesting. Phase 1 is read-only: it fetches daily historical candles from
Upstox and caches them in SQLite. It cannot place live orders.

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

The implemented slices currently include the read-only data layer, strategy
contract, SMA crossover and RSI mean-reversion strategies, backtest engine,
risk controls, and paper broker. Paper-trading orchestration, SQLite trade
history, and the CLI are the next incremental phase.

## Phase 1 data-layer contract

`HistoricalQuery` identifies an exchange-qualified Upstox instrument key, date
range, and daily interval. `MarketDataService` checks SQLite first, calls the
read-only Upstox provider on a cache miss, validates and sorts candles, then
caches the result.

The suite also covers strategy contracts, next-candle-open backtest execution,
performance metrics, risk circuit breakers, and paper-broker accounting:

```bash
pytest -q
```

Live orders remain disabled. `LiveBroker.execute()` always raises
`NotImplementedError`.