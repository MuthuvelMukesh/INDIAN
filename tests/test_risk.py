from strategies.base import Action, PortfolioContext, Signal
from risk.manager import RiskLimits, RiskManager


def test_risk_rejects_oversized_trade() -> None:
    manager = RiskManager(RiskLimits(max_quantity_per_trade=10))
    decision = manager.evaluate(
        Signal(Action.BUY, 11, "entry"),
        PortfolioContext(cash=100_000, positions={}),
        equity=100_000,
    )

    assert not decision.allowed
    assert "quantity" in decision.reason


def test_risk_rejects_new_symbol_at_open_position_limit() -> None:
    manager = RiskManager(RiskLimits(max_open_positions=1))
    decision = manager.evaluate(
        Signal(Action.BUY, 1, "entry"),
        PortfolioContext(cash=100_000, positions={"NSE_EQ|OTHER": 1}),
        equity=100_000,
    )

    assert not decision.allowed
    assert "open positions" in decision.reason


def test_risk_circuit_breaker_halts_trades_after_daily_loss() -> None:
    manager = RiskManager(RiskLimits(max_daily_loss=500))
    manager.start_day(equity=100_000, session_key="2024-01-01")

    decision = manager.evaluate(
        Signal(Action.BUY, 1, "entry"),
        PortfolioContext(cash=99_000, positions={}),
        equity=99_400,
        session_key="2024-01-01",
    )

    assert not decision.allowed
    assert "daily loss" in decision.reason


def test_risk_allows_reducing_a_position_after_circuit_breaker() -> None:
    manager = RiskManager(RiskLimits(max_daily_loss=500))
    manager.start_day(equity=100_000, session_key="2024-01-01")

    decision = manager.evaluate(
        Signal(Action.SELL, 1, "exit"),
        PortfolioContext(cash=99_000, positions={"NSE_EQ|TEST": 2}),
        equity=99_400,
        session_key="2024-01-01",
    )

    assert decision.allowed