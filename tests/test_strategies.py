from datetime import UTC, datetime
from math import inf, nan

import pytest

from data.models import Candle
from strategies.base import Action, PortfolioContext, Signal, Strategy
from strategies.sma_crossover import SmaCrossoverStrategy


def make_candle(close: float, day: int) -> Candle:
    return Candle(
        timestamp=datetime(2024, 1, day, tzinfo=UTC),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000,
    )


def test_signal_and_context_are_immutable() -> None:
    signal = Signal(Action.BUY, quantity=2, reason="golden cross")
    context = PortfolioContext(cash=100_000, positions={})

    assert signal.action is Action.BUY
    assert context.positions == {}

    try:
        signal.quantity = 3  # type: ignore[misc]  # intentional immutability test
    except AttributeError:
        pass
    else:
        raise AssertionError("Signal must be immutable")


def test_strategy_is_an_abstract_contract() -> None:
    with pytest.raises(TypeError):
        Strategy()  # type: ignore[abstract]  # intentional abstract-contract test


@pytest.mark.parametrize(
    ("action", "quantity"),
    [("UNKNOWN", 1), (Action.BUY, 1.5), (Action.HOLD, 1), (Action.BUY, 0)],
)
def test_signal_rejects_invalid_runtime_values(
    action: Action | str, quantity: int | float
) -> None:
    with pytest.raises(ValueError):
        Signal(action, quantity, "invalid input")  # type: ignore[arg-type]


@pytest.mark.parametrize("cash", [nan, inf, -1])
def test_context_rejects_invalid_cash(cash: float) -> None:
    with pytest.raises(ValueError, match="cash"):
        PortfolioContext(cash=cash, positions={})


def test_context_rejects_invalid_position_quantity() -> None:
    with pytest.raises(ValueError, match="position quantities"):
        PortfolioContext(
            cash=100_000,
            positions={"NSE_EQ|TEST": 1.5},  # type: ignore[dict-item]
        )


def test_context_positions_are_read_only() -> None:
    context = PortfolioContext(cash=100_000, positions={})

    with pytest.raises(TypeError):
        context.positions["NSE_EQ|TEST"] = 1  # type: ignore[index]


def test_sma_crossover_buys_on_golden_cross_and_waits_for_window() -> None:
    strategy = SmaCrossoverStrategy(short_window=2, long_window=3, quantity=5)
    context = PortfolioContext(cash=100_000, positions={})

    signals = [
        strategy.on_data(make_candle(close, day), context)
        for day, close in enumerate((10, 9, 11, 12), start=1)
    ]

    assert signals[0] == []
    assert signals[1] == []
    assert signals[2] == []
    assert signals[3] == [Signal(Action.BUY, quantity=5, reason="SMA golden crossover")]


def test_sma_crossover_sells_on_death_cross_when_holding() -> None:
    strategy = SmaCrossoverStrategy(short_window=2, long_window=3, quantity=5)
    context = PortfolioContext(cash=100_000, positions={"NSE_EQ|TEST": 5})

    for day, close in enumerate((10, 9, 11, 12), start=1):
        strategy.on_data(make_candle(close, day), context)

    signal = strategy.on_data(make_candle(1, 5), context)

    assert signal == [Signal(Action.SELL, quantity=5, reason="SMA death crossover")]


def test_sma_crossover_caps_sell_quantity_to_position() -> None:
    strategy = SmaCrossoverStrategy(short_window=2, long_window=3, quantity=5)
    context = PortfolioContext(cash=100_000, positions={"NSE_EQ|TEST": 2})

    for day, close in enumerate((10, 9, 11, 12), start=1):
        strategy.on_data(make_candle(close, day), context)

    assert strategy.on_data(make_candle(1, 5), context) == [
        Signal(Action.SELL, quantity=2, reason="SMA death crossover")
    ]
