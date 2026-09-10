# Architecture

The project is being built incrementally around stable contracts. The current
local implementation has read-only market data, strategies, backtesting, risk
controls, and paper execution. It deliberately has no live order-placement
code.

```text
data/models.py     immutable Candle and HistoricalQuery domain objects
data/ports.py      provider and cache protocols
data/upstox.py     read-only Upstox HTTP adapter
data/cache.py      local SQLite candle cache
data/service.py    cache-first orchestration
strategies/base.py common signal and portfolio-context contract
strategies/sma_crossover.py
strategies/rsi_reversion.py
strategies/vwap_reversion.py session VWAP with IST reset
strategies/orb.py            09:15 IST opening-range breakout
strategies/bollinger.py      squeeze and momentum breakout
engine/backtest.py next-candle-open historical simulation
risk/manager.py    position and daily-loss controls
broker/base.py     order and fill contracts
broker/paper.py    in-memory paper execution
broker/live.py     disabled live-order stub
```

`MarketDataService` depends on `MarketDataProvider` and `CandleCache` protocols,
not concrete implementations. This makes the provider and storage replaceable
without changing callers. Upstox-specific URL and payload handling is isolated
to `data/upstox.py`.

The remaining phases will add these boundaries:

- `strategies/`: classes consume only `Candle` and portfolio context and return
  signals.
- `engine/`: backtest and paper-trading engines consume signals identically.
- `broker/`: `PaperBroker` is the only executable broker in v1; `LiveBroker`
  remains an explicit `NotImplementedError` stub.
- `risk/`: position limits and circuit breakers remain independent of strategy
  and broker implementations.
- `storage/`: SQLite persistence for trades, positions, equity, and runs.

The backtest engine fills signals on the next candle's opening price with
configurable slippage and brokerage. This avoids using a candle close to trade
on information the strategy only learned at that close. A strategy instance is
reset before each independent run.

`BacktestEngine.for_interval("5minute")` makes scalping assumptions explicit:
₹20 planning brokerage per order, 10 bps slippage per side because OHLCV has no
bid/ask spread, and 18,900 annual periods from 75 five-minute bars per NSE
session across 252 sessions. These are configurable planning assumptions, not
an assertion that every account pays the same final all-in charge.

`RiskManager` is optional at the engine boundary. It can reject new risk while
allowing position-reducing exits, and it does not execute or mutate orders.

Intraday strategies use `Asia/Kolkata` session boundaries. VWAP and ORB ignore
pre-open and post-close candles; the backtest risk session also uses the IST
calendar date. Five-minute Sharpe excludes transitions that are not exactly
five minutes apart, including overnight gaps.

To add a strategy, implement the common strategy contract and register its name
in configuration. To add a broker later, implement the broker interface and
select it through configuration. Neither extension should require modifying
the backtest engine.