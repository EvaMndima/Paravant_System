"""Tests for the regime-conditional DSR screen core (DEC-2026-06-04-014).

These exercise the PURE statistical assembly (``compute_regime_coverage``), the
report renderers, and the idempotent biography write -- all without network. The
network regeneration (``regenerate_pooled_trades``) is a thin Binance/engine edge
not unit-tested here (mirrors ``read_pooled_trades`` in the retrospective).
"""
from __future__ import annotations

import scripts.regime_dsr as rdsr
from research.backtest.cost_model import CostModel
from research.backtest.regime_tagging import TaggedTrade
from research.biographies.schema import StrategyStatus, Tier
from research.validation.effective_k import (
    estimate_portfolio_k,
    regime_conditional_k,
)
from src.core.strategy.regime.historical_classifier import SubRegime


def _trade(symbol: str, ret: float, i: int) -> dict[str, object]:
    """Build a clean synthetic trade dict (same shape as TradeRecord.to_dict)."""
    entry = 0.10
    exit_ = max(entry * (1.0 + ret / 100.0), 1e-4)
    return {
        "symbol": symbol,
        "entry_price": entry,
        "exit_price": exit_,
        "quantity": 1000.0,
        "entry_commission": 0.02,
        "exit_commission": 0.02,
        "slippage_cost": 0.01,
        "return_pct": ret,
        "entry_time": f"2026-04-{(i % 27) + 1:02d}T{(i % 24):02d}:00:00+00:00",
        "exit_time": f"2026-05-{(i % 27) + 1:02d}T{(i % 24):02d}:00:00+00:00",
    }


def _tagged(sub: SubRegime, n: int, ret: float, symbol: str = "BTCUSDT") -> list[TaggedTrade]:
    """Build n tagged trades in one SubRegime with a fixed per-trade return."""
    from research.backtest.regime_tagging import coarse_bucket_of

    return [
        TaggedTrade(trade=_trade(symbol, ret, i), sub_regime=sub,
                    coarse_bucket=coarse_bucket_of(sub))
        for i in range(n)
    ]


def _base_k():
    return estimate_portfolio_k(
        hypotheses_counted=23, symbols_per_hypothesis_avg=5.0,
        param_combos_recorded=0, param_combos_estimated=1150,
    )


def _coverage(tagged):
    return rdsr.compute_regime_coverage(
        "TEST", StrategyStatus.ACTIVE_LIVE, tagged,
        run_id="regime_run_2026", run_date="2026-06-06",
        cost_model=CostModel.v0_unverified(),
        base_k=_base_k(), variance_sr_point=0.05,
    )


def test_pooled_plus_per_regime_buckets() -> None:
    """Pooled N is the sum; each populated coarse bucket gets its own cell."""
    tagged = (
        _tagged(SubRegime.TRENDING_BULL, 25, 1.2)
        + _tagged(SubRegime.CHOPPY_BEAR, 25, -0.5)
        + _tagged(SubRegime.RANGING, 5, 0.1)  # chop, thin -> descriptive
    )
    analysis = _coverage(tagged)
    assert analysis.pooled_result.n_trades_analyzed == 55
    assert analysis.coverage_run.is_screen_only is True
    by_regime = {c.regime: c for c in analysis.coverage_run.per_regime}
    assert set(by_regime) == {"bull", "bear", "chop"}
    assert by_regime["bull"].n_trades == 25
    assert by_regime["bear"].n_trades == 25
    assert by_regime["chop"].n_trades == 5


def test_thin_bucket_is_descriptive_not_gating() -> None:
    """A bucket below MIN_BUCKET_N is descriptive; a sub-10 bucket is INSUFFICIENT_DATA."""
    tagged = (
        _tagged(SubRegime.TRENDING_BULL, 25, 1.2)
        + _tagged(SubRegime.RANGING, 5, 0.1)
    )
    analysis = _coverage(tagged)
    chop = next(c for c in analysis.coverage_run.per_regime if c.regime == "chop")
    assert chop.is_descriptive is True
    assert chop.tier == Tier.INSUFFICIENT_DATA  # N=5 < MIN_N_FOR_CLASSIFICATION


def test_regime_k_multiplies_by_bucket_count() -> None:
    """Per-bucket effective K reflects the regime-bucket multiplier (guard #2)."""
    tagged = (
        _tagged(SubRegime.TRENDING_BULL, 25, 1.2)
        + _tagged(SubRegime.CHOPPY_BEAR, 25, -0.5)
        + _tagged(SubRegime.RANGING, 25, 0.1)
    )
    analysis = _coverage(tagged)
    expected_k = regime_conditional_k(_base_k(), 3).gating_k
    for cell in analysis.coverage_run.per_regime:
        assert cell.effective_k == expected_k
    # The regime-conditional gating K exceeds the non-regime gating K.
    assert expected_k > _base_k().gating_k


def test_coverage_does_not_touch_classification() -> None:
    """Guard #1: the screen records regime_coverage only -- never re-tiers."""
    tagged = _tagged(SubRegime.TRENDING_BULL, 25, 1.2)
    analysis = _coverage(tagged)
    # The coverage run is screen-only and carries no current_classification write.
    assert analysis.coverage_run.is_screen_only is True
    assert analysis.coverage_run.data_source == "regenerated_backtest"


def test_render_matrix_and_json() -> None:
    """Reports render with a row per strategy, gap summary, and JSON structure."""
    tagged = (
        _tagged(SubRegime.TRENDING_BULL, 25, 1.2)
        + _tagged(SubRegime.CHOPPY_BEAR, 25, -0.5)
    )
    analyses = {"TEST": _coverage(tagged)}
    md = rdsr.render_coverage_matrix_md(analyses, "2026-06-06")
    assert "Coverage Matrix" in md
    assert "TEST" in md
    assert "Coverage Gaps" in md
    assert "CHOP" in md  # chop column header present even with no chop trades

    payload = rdsr.render_coverage_json(analyses, "2026-06-06", "v0_unverified")
    assert payload["is_screen_only"] is True
    assert "TEST" in payload["strategies"]
    regimes = {c["regime"] for c in payload["strategies"]["TEST"]["per_regime"]}
    assert regimes == {"bull", "bear"}


def test_market_for_label_bear_strategies_use_futures() -> None:
    """Bear strategies default to futures (shorts must fire); others to spot."""
    assert rdsr.market_for_label("BTF") == "futures"
    assert rdsr.market_for_label("CMF") == "futures"
    assert rdsr.market_for_label("MACD_PB") == "spot"
    assert rdsr.market_for_label("ICVP") == "spot"
    # Unknown labels default to spot.
    assert rdsr.market_for_label("UNKNOWN_X") == "spot"
    # Explicit override wins over the per-strategy default.
    assert rdsr.market_for_label("BTF", override="spot") == "spot"
    assert rdsr.market_for_label("MACD_PB", override="futures") == "futures"


def test_write_regime_coverage_is_idempotent(tmp_path, monkeypatch) -> None:
    """A second write with the same run_id is a no-op (idempotent re-run)."""
    monkeypatch.setattr(rdsr.rd, "BIOGRAPHIES_DIR", tmp_path)
    tagged = _tagged(SubRegime.TRENDING_BULL, 25, 1.2)
    analysis = _coverage(tagged)
    first = rdsr.write_regime_coverage(
        analysis.coverage_run, "TEST", StrategyStatus.ACTIVE_LIVE, ["BTCUSDT"]
    )
    second = rdsr.write_regime_coverage(
        analysis.coverage_run, "TEST", StrategyStatus.ACTIVE_LIVE, ["BTCUSDT"]
    )
    assert first is True
    assert second is False
    # Exactly one coverage run persisted.
    written = list(tmp_path.rglob("TEST.yaml"))
    assert len(written) == 1
