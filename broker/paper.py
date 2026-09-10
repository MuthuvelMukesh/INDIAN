"""In-memory paper broker for local simulation."""

from datetime import datetime
from math import isfinite

from broker.base import Broker, Fill, Order


class PaperBroker(Broker):
    """Execute long-only orders against cash and in-memory positions."""

    def __init__(self, starting_cash: float, brokerage_per_order: float = 20) -> None:
        """Create a broker that never sends requests outside the process."""
        if not isfinite(starting_cash) or starting_cash < 0:
            raise ValueError("starting_cash must be finite and non-negative")
        if not isfinite(brokerage_per_order) or brokerage_per_order < 0:
            raise ValueError("brokerage_per_order must be finite and non-negative")
        self.cash = starting_cash
        self.brokerage_per_order = brokerage_per_order
        self.positions: dict[str, int] = {}
        self._cost_basis: dict[str, float] = {}

    def execute(self, order: Order) -> Fill:
        """Apply a buy or sell to local state and return the simulated fill."""
        signal = order.signal
        if signal.action.value == "HOLD":
            return Fill(signal.action, signal.instrument_key, 0, order.price, 0, None, order.timestamp)
        held = self.positions.get(signal.instrument_key, 0)
        quantity = signal.quantity if signal.action.value == "BUY" else min(signal.quantity, held)
        if quantity == 0:
            raise ValueError("order quantity is not executable")
        if signal.action.value == "BUY":
            cost = order.price * quantity + self.brokerage_per_order
            if cost > self.cash:
                raise ValueError("insufficient paper cash")
            self.cash -= cost
            self.positions[signal.instrument_key] = held + quantity
            self._cost_basis[signal.instrument_key] = self._cost_basis.get(signal.instrument_key, 0) + cost
            pnl = None
        else:
            proceeds = order.price * quantity - self.brokerage_per_order
            if proceeds < 0:
                raise ValueError("brokerage exceeds sale proceeds")
            basis = self._cost_basis[signal.instrument_key] * quantity / held
            self.cash += proceeds
            remaining = held - quantity
            if remaining:
                self.positions[signal.instrument_key] = remaining
                self._cost_basis[signal.instrument_key] -= basis
            else:
                self.positions.pop(signal.instrument_key, None)
                self._cost_basis.pop(signal.instrument_key, None)
            pnl = proceeds - basis
        return Fill(signal.action, signal.instrument_key, quantity, order.price, self.brokerage_per_order, pnl, order.timestamp)