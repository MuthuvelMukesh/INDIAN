"""Provider- and broker-independent strategy contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Mapping

from data.models import Candle


class Action(str, Enum):
    """Describe the portfolio action requested by a strategy."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class Signal:
    """Represent a strategy decision without knowing how it will be executed."""

    action: Action
    quantity: int
    reason: str
    instrument_key: str = "NSE_EQ|TEST"

    def __post_init__(self) -> None:
        """Reject malformed decisions before they reach an engine."""
        try:
            action = Action(self.action)
        except ValueError as error:
            raise ValueError("signal action must be BUY, SELL, or HOLD") from error
        object.__setattr__(self, "action", action)
        if type(self.quantity) is not int or self.quantity < 0:
            raise ValueError("signal quantity must be a non-negative integer")
        if not self.reason.strip():
            raise ValueError("signal reason must not be empty")
        if not self.instrument_key or "|" not in self.instrument_key:
            raise ValueError("signal instrument_key must be exchange-qualified")
        if action is Action.HOLD and self.quantity != 0:
            raise ValueError("HOLD signals must have zero quantity")
        if action is not Action.HOLD and self.quantity == 0:
            raise ValueError("BUY and SELL signals must have positive quantity")


@dataclass(frozen=True, slots=True)
class PortfolioContext:
    """Expose the read-only portfolio state available to a strategy."""

    cash: float
    positions: Mapping[str, int]

    def __post_init__(self) -> None:
        """Freeze position data so strategies cannot mutate engine state."""
        if not isfinite(self.cash) or self.cash < 0:
            raise ValueError("cash must be finite and non-negative")
        if any(
            type(quantity) is not int or quantity < 0
            for quantity in self.positions.values()
        ):
            raise ValueError("position quantities must be non-negative integers")
        object.__setattr__(self, "positions", MappingProxyType(dict(self.positions)))


class Strategy(ABC):
    """Define the common input/output contract for all strategies."""

    def reset(self) -> None:
        """Reset state before a new independent backtest or paper session."""
        return None

    @abstractmethod
    def on_data(self, candle: Candle, context: PortfolioContext) -> list[Signal]:
        """Return zero or more decisions for the newly received candle."""
