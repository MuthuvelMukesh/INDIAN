from datetime import datetime, timedelta, timezone

import pytest

from data.models import Candle
from engine.backtest import (
    NSE_5MIN_PERIODS_PER_YEAR,
    SCALPING_BROKERAGE_PER_ORDER,
    SCALPING_SLIPPAGE_BPS,
    BacktestEngine,
    EquityPoint,
)
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


def test_sharpe_annualization_scales_with_periods_per_year() -> None:
    candles = [
        make_candle(100, 1),
        make_candle(90, 2),
        make_candle(110, 3),
        make_candle(105, 4),
    ]
    daily = BacktestEngine(
        BuyThenSell(), starting_capital=10_000, periods_per_year=252
    ).run("NSE_EQ|TEST", candles)
    intraday = BacktestEngine(
        BuyThenSell(), starting_capital=10_000, periods_per_year=18_900
    ).run("NSE_EQ|TEST", candles)

    assert intraday.sharpe_ratio / daily.sharpe_ratio == pytest.approx(
        (18_900 / 252) ** 0.5
    )


def test_five_minute_preset_is_explicit() -> None:
    engine = BacktestEngine.for_interval(BuyThenSell(), "5minute")

    assert engine.periods_per_year == NSE_5MIN_PERIODS_PER_YEAR
    assert engine.brokerage_per_order == SCALPING_BROKERAGE_PER_ORDER
    assert engine.slippage_bps == SCALPING_SLIPPAGE_BPS


def test_intraday_sharpe_excludes_off_session_returns() -> None:
    strategy = BuyThenSell()
    engine = BacktestEngine(
        strategy,
        periods_per_year=18_900,
        bar_minutes=5,
    )
    regular = datetime(2024, 1, 1, 3, 45, tzinfo=timezone.utc)
    off_session = regular - timedelta(minutes=5)
    equity_curve = [
        EquityPoint(off_session, 100.0),
        EquityPoint(regular, 101.0),
    ]

    assert engine._sharpe_ratio(equity_curve, 18_900, 5) == 0.0