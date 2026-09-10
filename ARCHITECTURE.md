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

`RiskManager` is optional at the engine boundary. It can reject new risk while
allowing position-reducing exits, and it does not execute or mutate orders.

To add a strategy, implement the common strategy contract and register its name
in configuration. To add a broker later, implement the broker interface and
select it through configuration. Neither extension should require modifying
the backtest engine.