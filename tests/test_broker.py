from datetime import datetime, timezone

import pytest

from broker.base import Order
from broker.live import LiveBroker
from broker.paper import PaperBroker
from strategies.base import Action, Signal


def test_paper_broker_updates_cash_and_positions() -> None:
    broker = PaperBroker(starting_cash=10_000, brokerage_per_order=20)
    timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)

    buy = broker.execute(Order(Signal(Action.BUY, 10, "entry"), 100, timestamp))
    sell = broker.execute(Order(Signal(Action.SELL, 10, "exit"), 110, timestamp))

    assert buy.price == 100
    assert sell.realized_pnl == 60
    assert broker.cash == 10_060
    assert broker.positions == {}


def test_live_broker_is_explicitly_disabled() -> None:
    with pytest.raises(NotImplementedError, match="live orders"):
        LiveBroker().execute(Order(Signal(Action.BUY, 1, "blocked"), 100, datetime.now(timezone.utc)))