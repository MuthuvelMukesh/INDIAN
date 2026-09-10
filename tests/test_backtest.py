from datetime import datetime, timezone

import pytest

from data.models import Candle
from engine.backtest import BacktestEngine
from strategies.base import Action, PortfolioContext, Signal, Strategy


def make_candle(close: float, day: int, open_price: float | None = None) -> Candle:
    open_price = close if open_price is None else open_price
    return Candle(
        timestamp=datetime(2024, 1, day, tzinfo=timezone.utc),
        open=open_price,
        high=close,
        low=close,
        close=close,
        volume=1_000,
    )


class BuyThenSell(Strategy):
    """Test strategy that exercises both sides of a simulated trade."""

    def __init__(self) -> None:
        self.calls = 0

    def on_data(self, candle: Candle, context: PortfolioContext) -> list[Signal]:
        self.calls += 1
        if self.calls == 1:
            return [Signal(Action.BUY, 10, "entry")]
        if self.calls == 2:
            return [Signal(Action.SELL, 10, "exit")]
        return []


def test_backtest_applies_slippage_and_brokerage_to_pnl() -> None:
    result = BacktestEngine(
        BuyThenSell(),
        starting_capital=10_000,
        brokerage_per_order=20,
        slippage_bps=100,
    ).run(
    "NSE_EQ|TEST",
    [make_candle(100, 1), make_candle(110, 2), make_candle(120, 3)],
    )

    assert result.trades[0].price == 111.1
    assert result.trades[1].price == 118.8
    assert result.ending_equity == 10_037
    assert result.trades[1].realized_pnl == 37


def test_backtest_reports_drawdown_and_win_rate() -> None:
    result = BacktestEngine(BuyThenSell(), starting_capital=10_000).run(
        "NSE_EQ|TEST",
        [make_candle(100, 1), make_candle(90, 2), make_candle(110, 3)],
    )

    assert result.total_return == pytest.approx(0.0159)
    assert result.win_rate == 1.0
    assert result.max_drawdown == pytest.approx(0.002045)
    assert len(result.equity_curve) == 3