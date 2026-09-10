"""Strategy-agnostic historical simulation engine."""

from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import mean, pstdev
from datetime import datetime, time, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal, Strategy
from risk.manager import RiskManager


# NSE regular equity hours are 09:15-15:30 IST: 375 minutes / 5 = 75 bars.
# Using the existing 252-session daily convention gives 75 * 252 = 18,900.
NSE_5MIN_PERIODS_PER_YEAR = 18_900
SCALPING_BROKERAGE_PER_ORDER = 20.0
SCALPING_SLIPPAGE_BPS = 10.0
IST = ZoneInfo("Asia/Kolkata")
NSE_OPEN = time(9, 15)
NSE_CLOSE = time(15, 30)


@dataclass(frozen=True, slots=True)
class Trade:
    """Record one simulated fill and its transaction costs."""

    timestamp: datetime
    instrument_key: str
    action: Action
    quantity: int
    price: float
    brokerage: float
    realized_pnl: float | None


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """Record marked-to-market portfolio value at one candle."""

    timestamp: datetime
    equity: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Summarize fills, equity, and risk-adjusted performance metrics."""

    starting_capital: float
    ending_equity: float
    trades: tuple[Trade, ...]
    equity_curve: tuple[EquityPoint, ...]
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float

    @property
    def total_return(self) -> float:
        """Return the fractional change from starting to ending equity."""
        return (self.ending_equity - self.starting_capital) / self.starting_capital


class BacktestEngine:
    """Run any strategy against candles using deterministic paper fills."""

    def __init__(
        self,
        strategy: Strategy,
        starting_capital: float = 100_000,
        brokerage_per_order: float = 20,
        slippage_bps: float = 5,
        risk_manager: RiskManager | None = None,
        periods_per_year: int = 252,
        bar_minutes: int | None = None,
    ) -> None:
        """Configure the strategy and conservative per-fill cost assumptions."""
        values = (starting_capital, brokerage_per_order, slippage_bps, periods_per_year)
        if not all(isfinite(value) for value in values):
            raise ValueError("backtest costs and capital must be finite")
        if (
            starting_capital <= 0
            or brokerage_per_order < 0
            or slippage_bps < 0
            or type(periods_per_year) is not int
            or periods_per_year < 1
            or (bar_minutes is not None and (type(bar_minutes) is not int or bar_minutes < 1))
        ):
            raise ValueError("capital must be positive and costs must be non-negative")
        self.strategy = strategy
        self.starting_capital = starting_capital
        self.brokerage_per_order = brokerage_per_order
        self.slippage_bps = slippage_bps
        self.risk_manager = risk_manager
        self.periods_per_year = periods_per_year
        self.bar_minutes = bar_minutes

    @classmethod
    def for_interval(
        cls,
        strategy: Strategy,
        interval: str,
        starting_capital: float = 100_000,
        risk_manager: RiskManager | None = None,
    ) -> "BacktestEngine":
        """Build a daily or five-minute engine with an explicit cost preset.

        Five-minute candles use a conservative 10 bps per-side slippage
        assumption because historical OHLCV data has no bid/ask spread. The
        brokerage value is the current flat per-order planning assumption;
        statutory and exchange charges are outside this simulation boundary.
        """
        if interval in {"1d", "day"}:
            return cls(
                strategy,
                starting_capital=starting_capital,
                risk_manager=risk_manager,
            )
        if interval == "5minute":
            return cls(
                strategy,
                starting_capital=starting_capital,
                brokerage_per_order=SCALPING_BROKERAGE_PER_ORDER,
                slippage_bps=SCALPING_SLIPPAGE_BPS,
                periods_per_year=NSE_5MIN_PERIODS_PER_YEAR,
                bar_minutes=5,
                risk_manager=risk_manager,
            )
        raise ValueError("no cost preset exists for this interval")

    def run(self, instrument_key: str, candles: Iterable[Candle]) -> BacktestResult:
        """Simulate signals chronologically and return an immutable report."""
        candles = tuple(candles)
        if not candles:
            raise ValueError("backtest requires at least one candle")
        if not instrument_key or "|" not in instrument_key:
            raise ValueError("instrument_key must be exchange-qualified")

        self.strategy.reset()
        cash = self.starting_capital
        positions: dict[str, int] = {}
        entry_costs: dict[str, float] = {}
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []
        context = PortfolioContext(cash=cash, positions=positions)

        pending: tuple[Signal, ...] = ()
        active_session: str | None = None
        for candle in sorted(candles, key=lambda item: item.timestamp):
            session_key = candle.timestamp.astimezone(IST).date().isoformat()
            current_equity = cash + positions.get(instrument_key, 0) * candle.open
            if self.risk_manager is not None and session_key != active_session:
                self.risk_manager.start_day(current_equity, session_key)
                active_session = session_key
            for signal in pending:
                if signal.instrument_key != instrument_key:
                    raise ValueError("signal instrument does not match backtest instrument")
                context = PortfolioContext(cash=cash, positions=positions)
                if self.risk_manager is not None:
                    decision = self.risk_manager.evaluate(
                        signal, context, current_equity, session_key
                    )
                    if not decision.allowed:
                        continue
                cash, trade = self._execute(
                    signal,
                    candle,
                    instrument_key,
                    cash,
                    positions,
                    entry_costs,
                    candle.open,
                )
                if trade is not None:
                    trades.append(trade)
            context = PortfolioContext(cash=cash, positions=positions)
            pending = tuple(self.strategy.on_data(candle, context))
            equity_curve.append(
                EquityPoint(candle.timestamp, cash + positions.get(instrument_key, 0) * candle.close)
            )

        equities = [point.equity for point in equity_curve]
        return BacktestResult(
            starting_capital=self.starting_capital,
            ending_equity=equities[-1],
            trades=tuple(trades),
            equity_curve=tuple(equity_curve),
            win_rate=self._win_rate(trades),
            max_drawdown=self._max_drawdown(equities),
            sharpe_ratio=self._sharpe_ratio(
                equity_curve, self.periods_per_year, self.bar_minutes
            ),
        )

    def _execute(
        self,
        signal: Signal,
        candle: Candle,
        instrument_key: str,
        cash: float,
        positions: dict[str, int],
        entry_costs: dict[str, float],
        execution_price: float,
    ) -> tuple[float, Trade | None]:
        """Apply one long-only signal at the next candle's opening price."""
        if signal.action is Action.HOLD or signal.quantity == 0:
            return cash, None
        direction = 1 if signal.action is Action.BUY else -1
        price = execution_price * (1 + direction * self.slippage_bps / 10_000)
        quantity = signal.quantity
        held = positions.get(instrument_key, 0)
        if signal.action is Action.BUY:
            total = price * quantity + self.brokerage_per_order
            if total > cash:
                return cash, None
            positions[instrument_key] = held + quantity
            entry_costs[instrument_key] = entry_costs.get(instrument_key, 0) + total
            return cash - total, Trade(
                timestamp=candle.timestamp,
                instrument_key=instrument_key,
                action=signal.action,
                quantity=quantity,
                price=price,
                brokerage=self.brokerage_per_order,
                realized_pnl=None,
            )

        quantity = min(quantity, held)
        if quantity == 0:
            return cash, None
        proceeds = price * quantity - self.brokerage_per_order
        if proceeds < 0:
            return cash, None
        positions[instrument_key] = held - quantity
        cost_basis = entry_costs.get(instrument_key, 0) * quantity / held
        entry_costs[instrument_key] = entry_costs.get(instrument_key, 0) - cost_basis
        realized_pnl = proceeds - cost_basis
        return cash + proceeds, Trade(
            timestamp=candle.timestamp,
            instrument_key=instrument_key,
            action=signal.action,
            quantity=quantity,
            price=price,
            brokerage=self.brokerage_per_order,
            realized_pnl=realized_pnl,
        )

    @staticmethod
    def _win_rate(trades: list[Trade]) -> float:
        """Calculate the fraction of completed exits with positive P&L."""
        exits = [trade for trade in trades if trade.realized_pnl is not None]
        return sum(trade.realized_pnl > 0 for trade in exits) / len(exits) if exits else 0.0

    @staticmethod
    def _max_drawdown(equities: list[float]) -> float:
        """Return the largest fractional peak-to-trough decline."""
        peak = equities[0]
        drawdowns = []
        for equity in equities:
            peak = max(peak, equity)
            drawdowns.append((peak - equity) / peak)
        return max(drawdowns)

    @staticmethod
    def _sharpe_ratio(
        equity_curve: list[EquityPoint], periods_per_year: int, bar_minutes: int | None
    ) -> float:
        """Annualize zero-risk-free returns for the candle frequency."""
        returns = []
        for previous, current in zip(equity_curve, equity_curve[1:]):
            elapsed = current.timestamp - previous.timestamp
            if bar_minutes is not None and (
                elapsed != timedelta(minutes=bar_minutes)
                or not _is_regular_session_timestamp(previous.timestamp)
                or not _is_regular_session_timestamp(current.timestamp)
            ):
                continue
            returns.append(current.equity / previous.equity - 1)
        deviation = pstdev(returns) if len(returns) > 1 else 0
        return sqrt(periods_per_year) * mean(returns) / deviation if deviation else 0.0


def _is_regular_session_timestamp(timestamp: datetime) -> bool:
    """Return whether a timestamp falls within regular NSE equity hours."""
    local_time = timestamp.astimezone(IST).time()
    return NSE_OPEN <= local_time < NSE_CLOSE