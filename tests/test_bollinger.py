from datetime import UTC, datetime

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal
from strategies.bollinger import BollingerSqueezeStrategy


def candle(day: int, close: float) -> Candle:
    timestamp = datetime(2024, 1, day, 3, 45, tzinfo=UTC)
    return Candle(timestamp, close, close, close, close, 100)


def test_bollinger_squeeze_trades_momentum_breakout_and_exit() -> None:
    strategy = BollingerSqueezeStrategy(period=3, squeeze_bandwidth=0.01, quantity=2)
    empty = PortfolioContext(100_000, {})
    holding = PortfolioContext(100_000, {"NSE_EQ|TEST": 2})

    assert strategy.on_data(candle(1, 100), empty) == []
    assert strategy.on_data(candle(2, 100), empty) == []
    assert strategy.on_data(candle(3, 100), empty) == []
    assert strategy.on_data(candle(4, 110), empty) == [
        Signal(Action.BUY, 2, "Bollinger upside momentum", "NSE_EQ|TEST")
    ]
    assert strategy.on_data(candle(5, 90), holding) == [
        Signal(Action.SELL, 2, "Bollinger downside momentum", "NSE_EQ|TEST")
    ]
