from datetime import UTC, datetime

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal
from strategies.rsi_reversion import RsiReversionStrategy


def candle(close: float, day: int) -> Candle:
    return Candle(
        datetime(2024, 1, day, tzinfo=UTC),
        close,
        close,
        close,
        close,
        1_000,
    )


def test_rsi_reversion_buys_oversold_and_sells_overbought() -> None:
    strategy = RsiReversionStrategy(period=2, quantity=3)
    empty = PortfolioContext(100_000, {})
    holding = PortfolioContext(100_000, {"NSE_EQ|TEST": 3})

    assert strategy.on_data(candle(100, 1), empty) == []
    assert strategy.on_data(candle(90, 2), empty) == []
    assert strategy.on_data(candle(80, 3), empty) == [
        Signal(Action.BUY, 3, "RSI oversold", "NSE_EQ|TEST")
    ]
    assert strategy.on_data(candle(110, 4), holding) == [
        Signal(Action.SELL, 3, "RSI overbought", "NSE_EQ|TEST")
    ]
