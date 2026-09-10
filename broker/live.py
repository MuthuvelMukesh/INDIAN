"""Deliberately disabled live-broker placeholder."""

from broker.base import Broker, Fill, Order


class LiveBroker(Broker):
    """Reserve the future live broker boundary without enabling real orders."""

    def execute(self, order: Order) -> Fill:
        """Reject every live order until a separately reviewed implementation exists."""
        raise NotImplementedError("live orders are disabled in v1")
