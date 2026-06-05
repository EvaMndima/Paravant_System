"""Tests confirming the PARA-02 quarantine filter is applied (DEC-2026-05-31-002).

The retrospective MUST exclude corrupt force-close trades, reusing the single
source of truth ``_is_corrupt_force_close`` from ``scripts.validation_report``.
"""
from __future__ import annotations

from research.backtest.cost_model import CostModel
from research.validation.effective_k import estimate_portfolio_k
from scripts.retrospective_dsr import analyze_strategy
from scripts.validation_report import _is_corrupt_force_close
from research.biographies.schema import StrategyStatus


def _good_trade(symbol: str, ret: float, i: int) -> dict[str, object]:
    """A clean trade with realistic prices."""
    entry = 0.10
    exit_ = entry * (1.0 + ret / 100.0)
    return {
        "symbol": symbol,
        "entry_price": entry,
        "exit_price": max(exit_, 1e-4),
        "quantity": 1000.0,
        "entry_commission": 0.05,
        "exit_commission": 0.05,
        "slippage_cost": 0.02,
        "return_pct": ret,
        "exit_time": f"2026-05-{(i % 27) + 1:02d}T00:00:00+00:00",
    }


def _corrupt_force_close(i: int) -> dict[str, object]:
    """A PARA-02-contaminated trade: BTC entry with a ratio-band exit price."""
    return {
        "symbol": "BTCUSDT",
        "entry_price": 50000.0,
        "exit_price": 1.05,  # equity/position_value ratio, not a market price
        "quantity": 0.01,
        "entry_commission": 0.5,
        "exit_commission": 0.5,
        "slippage_cost": 0.1,
        "return_pct": -99.0,
        "force_close": True,
        "exit_time": f"2026-05-{(i % 27) + 1:02d}T12:00:00+00:00",
    }


def test_corruption_signature_detected() -> None:
    """The corrupt fixture matches the quarantine signature; clean ones do not."""
    assert _is_corrupt_force_close(_corrupt_force_close(0)) is True
    assert _is_corrupt_force_close(_good_trade("DOGEUSDT", 1.0, 0)) is False


def test_analyze_strategy_quarantines_corrupt_trades() -> None:
    """analyze_strategy drops corrupt trades and counts them separately."""
    clean = [_good_trade("DOGEUSDT", 1.5, i) for i in range(20)]
    corrupt = [_corrupt_force_close(i) for i in range(3)]
    raw = clean + corrupt

    est = estimate_portfolio_k(
        hypotheses_counted=23,
        symbols_per_hypothesis_avg=5.0,
        param_combos_recorded=0,
        param_combos_estimated=1150,
    )
    result = analyze_strategy(
        "TEST",
        StrategyStatus.ACTIVE_LIVE,
        raw,
        k_estimate=est,
        variance_sr_point=0.05,
        cost_model=CostModel.v0_unverified(),
        run_id="run_test",
        run_date="2026-06-05",
    )
    # 20 clean analyzed, 3 corrupt quarantined.
    assert result.n_trades_analyzed == 20
    assert result.n_trades_quarantined == 3
    assert result.validation_entry.n_trades_quarantined == 3
    # The corrupt BTC trade must not appear in the per-symbol breakdown.
    symbols = {s.symbol for s in result.validation_entry.per_symbol_breakdown}
    assert "BTCUSDT" not in symbols
