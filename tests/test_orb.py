from datetime import UTC, datetime

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal
from strategies.orb import OpeningRangeBreakoutStrategy


def candle(hour: int, minute: int, close: float, high: float, low: float) -> Candle:
    timestamp = datetime(2024, 1, 1, hour, minute, tzinfo=UTC)
    return Candle(timestamp, close, high, low, close, 100)


def test_orb_waits_for_range_then_trades_breakout() -> None:
    strategy = OpeningRangeBreakoutStrategy(opening_minutes=10, quantity=2)
    empty = PortfolioContext(100_000, {})
    holding = PortfolioContext(100_000, {"NSE_EQ|TEST": 2})

    assert strategy.on_data(candle(3, 45, 100, 102, 99), empty) == []
    assert strategy.on_data(candle(3, 50, 101, 103, 98), empty) == []
    assert strategy.on_data(candle(3, 55, 105, 106, 104), empty) == [
        Signal(Action.BUY, 2, "ORB upside breakout", "NSE_EQ|TEST")
    ]
    assert strategy.on_data(candle(4, 0, 96, 97, 95), holding) == [
        Signal(Action.SELL, 2, "ORB downside breakout", "NSE_EQ|TEST")
    ]


def test_orb_resets_range_on_new_session() -> None:
    strategy = OpeningRangeBreakoutStrategy(opening_minutes=5)
    context = PortfolioContext(100_000, {})

    strategy.on_data(candle(3, 45, 100, 101, 99), context)
    assert strategy.on_data(candle(3, 50, 105, 106, 104), context) == [
        Signal(Action.BUY, 1, "ORB upside breakout", "NSE_EQ|TEST")
    ]

    next_day = Candle(
        datetime(2024, 1, 2, 3, 45, tzinfo=UTC),
        100,
        101,
        99,
        100,
        100,
    )
    assert strategy.on_data(next_day, context) == []


def test_orb_ignores_after_close_breakouts() -> None:
    strategy = OpeningRangeBreakoutStrategy(opening_minutes=5)
    context = PortfolioContext(100_000, {})

    strategy.on_data(candle(3, 45, 100, 101, 99), context)
    assert strategy.on_data(candle(10, 0, 110, 111, 109), context) == []
