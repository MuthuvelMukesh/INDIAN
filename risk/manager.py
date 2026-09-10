"""Risk controls shared by backtesting and paper trading."""

from dataclasses import dataclass
from math import isfinite

from strategies.base import Action, PortfolioContext, Signal


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """Configure hard limits that prevent new risk from being taken."""

    max_quantity_per_trade: int = 100
    max_open_positions: int = 5
    max_daily_loss: float = 5_000

    def __post_init__(self) -> None:
        """Validate risk limits before they can be applied."""
        if self.max_quantity_per_trade < 1 or self.max_open_positions < 1:
            raise ValueError("position limits must be positive")
        if not isfinite(self.max_daily_loss) or self.max_daily_loss < 0:
            raise ValueError("max_daily_loss must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Explain whether a proposed signal may proceed."""

    allowed: bool
    reason: str


class RiskManager:
    """Apply position and daily-loss controls without executing orders."""

    def __init__(self, limits: RiskLimits) -> None:
        """Create a risk manager with immutable configured limits."""
        self.limits = limits
        self._session_key: str | None = None
        self._opening_equity: float | None = None

    def start_day(self, equity: float, session_key: str) -> None:
        """Set the equity baseline used by the daily circuit breaker."""
        self._validate_equity(equity)
        if not session_key:
            raise ValueError("session_key must not be empty")
        self._session_key = session_key
        self._opening_equity = equity

    def evaluate(
        self,
        signal: Signal,
        context: PortfolioContext,
        equity: float,
        session_key: str | None = None,
    ) -> RiskDecision:
        """Return a decision without mutating portfolio or order state."""
        self._validate_equity(equity)
        if signal.action is Action.HOLD:
            return RiskDecision(True, "hold does not add risk")
        if signal.quantity > self.limits.max_quantity_per_trade:
            return RiskDecision(False, "quantity exceeds max per-trade limit")
        if (
            signal.action is Action.BUY
            and signal.quantity > 0
            and not context.positions.get(signal.instrument_key, 0)
            and len([quantity for quantity in context.positions.values() if quantity > 0])
            >= self.limits.max_open_positions
        ):
            return RiskDecision(False, "max open positions reached")
        if self._same_session(session_key) and self._opening_equity is not None:
            daily_loss = self._opening_equity - equity
            if daily_loss >= self.limits.max_daily_loss:
                if signal.action is Action.BUY:
                    return RiskDecision(False, "daily loss circuit breaker is active")
        return RiskDecision(True, "risk limits passed")

    def _same_session(self, session_key: str | None) -> bool:
        """Check whether an evaluation belongs to the active risk session."""
        return session_key is not None and session_key == self._session_key

    @staticmethod
    def _validate_equity(equity: float) -> None:
        """Reject non-finite equity values at the risk boundary."""
        if not isfinite(equity):
            raise ValueError("equity must be finite")