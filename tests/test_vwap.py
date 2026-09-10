from datetime import datetime, timezone

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal
from strategies.vwap_reversion import VwapReversionStrategy


def candle(timestamp: datetime, close: float, volume: int = 100) -> Candle:
    return Candle(timestamp, close, close, close, close, volume)


def test_vwap_reversion_resets_at_each_ist_session() -> None:
    strategy = VwapReversionStrategy(deviation=0.01, quantity=2)
    empty = PortfolioContext(100_000, {})
    holding = PortfolioContext(100_000, {"NSE_EQ|TEST": 2})

    assert strategy.on_data(
        candle(datetime(2024, 1, 1, 3, 45, tzinfo=timezone.utc), 100), empty
    ) == []
    assert strategy.on_data(
        candle(datetime(2024, 1, 1, 3, 50, tzinfo=timezone.utc), 98), empty
    ) == [Signal(Action.BUY, 2, "VWAP oversold", "NSE_EQ|TEST")]
    assert strategy.on_data(
        candle(datetime(2024, 1, 1, 4, 0, tzinfo=timezone.utc), 102), holding
    ) == [Signal(Action.SELL, 2, "VWAP overbought", "NSE_EQ|TEST")]

    # 03:45 UTC on the next day is a new NSE session and starts a fresh VWAP.
    assert strategy.on_data(
        candle(datetime(2024, 1, 2, 3, 45, tzinfo=timezone.utc), 100), empty
    ) == []


def test_vwap_ignores_preopen_prices() -> None:
    strategy = VwapReversionStrategy(deviation=0.01, quantity=2)
    context = PortfolioContext(100_000, {})

    assert strategy.on_data(
        candle(datetime(2024, 1, 1, 3, 0, tzinfo=timezone.utc), 50, 10_000), context
    ) == []
    assert strategy.on_data(
        candle(datetime(2024, 1, 1, 3, 45, tzinfo=timezone.utc), 100), context
    ) == []