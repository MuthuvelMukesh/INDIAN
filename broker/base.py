"""Broker-neutral order and fill contracts."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from strategies.base import Action, Signal


@dataclass(frozen=True, slots=True)
class Order:
    """Describe a requested fill at a simulated or broker-provided price."""

    signal: Signal
    price: float
    timestamp: datetime

    def __post_init__(self) -> None:
        """Reject economically invalid prices before broker execution."""
        if not isfinite(self.price) or self.price <= 0:
            raise ValueError("order price must be finite and positive")


@dataclass(frozen=True, slots=True)
class Fill:
    """Record the result of executing one order."""

    action: Action
    instrument_key: str
    quantity: int
    price: float
    brokerage: float
    realized_pnl: float | None
    timestamp: datetime


class Broker:
    """Define the execution contract consumed by future engines."""

    def execute(self, order: Order) -> Fill:
        """Execute one order and return its fill record."""
        raise NotImplementedError