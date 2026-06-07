"""Integration tests for scripts/retrospective_dsr.py (spec Section 10).

Confirms: pooled (not per-symbol) DSR; base and conservative cases both reported
with the gate on the conservative one; idempotent biography re-runs; MaxDD
recomputed on the pooled cost-adjusted series; derived reports render.
"""
from __future__ import annotations

import json
import math

import pytest

import scripts.retrospective_dsr as rd
from research.backtest.cost_model import CostModel
from research.biographies.schema import StrategyStatus, Tier
from research.validation.effective_k import estimate_portfolio_k


def _trade(symbol: str, ret: float, i: int) -> dict[str, object]:
    """Build a clean synthetic trade for ``symbol`` with return ``ret``."""
    entry = 0.10
    exit_ = entry * (1.0 + ret / 100.0)
    return {
        "symbol": symbol,
        "entry_price": entry,
        "exit_price": max(exit_, 1e-4),
        "quantity": 1000.0,
        "entry_commission": 0.02,
        "exit_commission": 0.02,
        "slippage_cost": 0.01,
        "return_pct": ret,
        "exit_time": f"2026-05-{(i % 27) + 1:02d}T{(i % 24):02d}:00:00+00:00",
    }


@pytest.fixture()
def k_estimate():
    """A representative portfolio K estimate for tests."""
    return estimate_portfolio_k(
        hypotheses_counted=23,
        symbols_per_hypothesis_avg=5.0,
        param_combos_recorded=0,
        param_combos_estimated=1150,
    )


def _analyze(trades, k_estimate, variance_sr_point=0.05):
    """Helper to run analyze_strategy with common args."""
    return rd.analyze_strategy(
        "TEST",
        StrategyStatus.ACTIVE_LIVE,
        trades,
        k_estimate=k_estimate,
        variance_sr_point=variance_sr_point,
        cost_model=CostModel.v0_unverified(),
        run_id="run_2026",
        run_date="2026-06-05",
    )


def test_pooled_dsr_is_single_series_across_symbols(k_estimate) -> None:
    """DSR is computed once on the pooled series; per-symbol is descriptive only."""
    trades = [_trade("DOGEUSDT", 1.2, i) for i in range(15)]
    trades += [_trade("AVAXUSDT", 0.9, i) for i in range(15)]
    result = _analyze(trades, k_estimate)
    e = result.validation_entry
    # One pooled DSR p-value, N pooled across both symbols.
    assert e.n_trades_analyzed == 30
    assert 0.0 <= e.conservative_dsr_p_value <= 1.0
    # Two descriptive per-symbol rows, neither gating.
    symbols = {s.symbol for s in e.per_symbol_breakdown}
    assert symbols == {"DOGEUSDT", "AVAXUSDT"}


def test_base_and_conservative_both_reported_gate_on_conservative(k_estimate) -> None:
    """Both operating points are reported; the final tier resolves them."""
    trades = [_trade("DOGEUSDT", 2.0, i) for i in range(40)]
    result = _analyze(trades, k_estimate)
    e = result.validation_entry
    from research.promotion.classifier import resolve_final_tier

    expected_final, expected_fragile = resolve_final_tier(e.base_tier, e.conservative_tier)
    assert result.final_tier == expected_final
    assert e.fragility == expected_fragile
    # Conservative p-value is the gating dsr_p_value.
    assert e.dsr_p_value == e.conservative_dsr_p_value
    # The conservative case is never more optimistic than the base case.
    assert e.conservative_dsr_p_value >= e.base_dsr_p_value - 1e-9


def test_maxdd_recomputed_on_pooled_adjusted_series(k_estimate) -> None:
    """MaxDD gates on the recomputed pooled series, not a legacy figure."""
    # A run-up then a sharp drawdown.
    rets = [3.0] * 10 + [-5.0] * 5
    trades = [_trade("DOGEUSDT", r, i) for i, r in enumerate(rets)]
    result = _analyze(trades, k_estimate)
    cm = CostModel.v0_unverified()
    conservative = [
        rd.apply_cost_model(t, cm).conservative_return_pct
        for t in sorted(trades, key=lambda t: (t["exit_time"], t.get("entry_time", "")))
    ]
    expected_dd = rd._max_drawdown_pct_from_returns(conservative)
    assert math.isclose(
        result.validation_entry.max_dd_pct_pooled_adjusted, expected_dd, rel_tol=1e-9
    )
    assert expected_dd > 0.0


def test_idempotent_rerun_does_not_double_append(tmp_path, monkeypatch, k_estimate) -> None:
    """A second write with the same run_id is a no-op (spec Section 9.1)."""
    monkeypatch.setattr(rd, "BIOGRAPHIES_DIR", tmp_path)
    trades = [_trade("DOGEUSDT", 1.0, i) for i in range(25)]
    result = _analyze(trades, k_estimate)

    bio = rd.load_or_create_biography("TEST", StrategyStatus.ACTIVE_LIVE, ["DOGEUSDT"])
    wrote_first = rd.write_biography(
        bio, result, run_id="run_2026", run_date="2026-06-05", cost_model_version="v0_unverified"
    )
    assert wrote_first is True
    assert len(bio.statistical_validation_history) == 1

    # Reload from disk and attempt the same run again.
    bio2 = rd.load_or_create_biography("TEST", StrategyStatus.ACTIVE_LIVE, ["DOGEUSDT"])
    wrote_second = rd.write_biography(
        bio2, result, run_id="run_2026", run_date="2026-06-05", cost_model_version="v0_unverified"
    )
    assert wrote_second is False
    assert len(bio2.statistical_validation_history) == 1


def test_reports_render_without_error(k_estimate, tmp_path) -> None:
    """Markdown, portfolio summary, and JSON all render from results."""
    trades = [_trade("DOGEUSDT", 1.5, i) for i in range(30)]
    result = _analyze(trades, k_estimate)

    md = rd.render_strategy_markdown(result, "2026-06-05")
    assert "Retrospective DSR Analysis: TEST" in md
    assert "K sensitivity sweep" in md

    summary = rd.render_portfolio_summary([result], "2026-06-05")
    assert "Portfolio Summary" in summary
    assert "Headline Findings" in summary

    payload = rd.render_json([result], "2026-06-05", "v0_unverified")
    assert "TEST" in payload["strategies"]
    assert payload["strategies"]["TEST"]["tier"] == rd._tier_label(result.final_tier)


def test_degenerate_small_sample_does_not_crash(k_estimate) -> None:
    """A sub-2-trade sample yields the worst p-value and INSUFFICIENT_DATA.

    The DSR still computes a degenerate worst-case p (no exception), but the
    classifier now reports INSUFFICIENT_DATA rather than a reject tier: below the
    minimum N the verdict is "no data to judge", NOT "proven noise"
    (DEC-2026-06-04-014). This was the 2026-06-05 Neon-run misread the guard fixes.
    """
    result = _analyze([_trade("DOGEUSDT", 1.0, 0)], k_estimate)
    assert result.validation_entry.conservative_dsr_p_value == 1.0
    assert result.final_tier == Tier.INSUFFICIENT_DATA


def test_strategy_universe_has_eleven(k_estimate) -> None:
    """The hardcoded universe is the 5 KEEP + 6 RETIRED strategies."""
    ids = [s.strategy_id for s in rd.STRATEGY_UNIVERSE]
    assert len(ids) == 11
    assert set(["MACD_PB", "BTP", "VBB", "SRC", "ICVP"]).issubset(ids)
    assert set(["BTF", "CMF", "RSI_BB", "HATP", "VRB", "VPT"]).issubset(ids)


def test_end_to_end_run_writes_biographies_and_reports(tmp_path, monkeypatch) -> None:
    """Full run on synthetic data: biographies written, reports rendered.

    Doubles as the synthetic dry-run -- it exercises the two-pass variance_sr
    estimation, biography writes for multiple strategies (active and retired),
    and all derived report rendering, with the DB reader stubbed out.
    """
    monkeypatch.setattr(rd, "BIOGRAPHIES_DIR", tmp_path / "bios")

    def fake_reader(strategy_id: str):
        # Different return profiles per strategy, with per-trade variation, so
        # within-strategy dispersion is realistic and the cross-sectional
        # variance_sr estimate is non-degenerate.
        center = {"MACD_PB": 2.0, "BTF": -0.5}.get(strategy_id, 1.0)
        return [
            _trade("DOGEUSDT", center + (1.0 if i % 2 == 0 else -1.0), i)
            for i in range(25)
        ]

    monkeypatch.setattr(rd, "read_pooled_trades", fake_reader)

    specs = [
        rd.StrategySpec("MACD_PB", StrategyStatus.ACTIVE_LIVE, True, ["DOGEUSDT"]),
        rd.StrategySpec("BTF", StrategyStatus.RETIRED, False),
    ]
    out_dir = tmp_path / "reports"
    results = rd.run_retrospective(
        specs,
        output_dir=out_dir,
        json_only=False,
        run_id="run_e2e",
        run_date="2026-06-05",
    )
    assert len(results) == 2

    # Biographies written to the correct active/retired locations.
    assert (tmp_path / "bios" / "active" / "MACD_PB.yaml").exists()
    assert (tmp_path / "bios" / "retired" / "BTF.yaml").exists()

    # Derived reports exist and the JSON validates.
    assert (out_dir / "MACD_PB_2026-06-05.md").exists()
    assert (out_dir / "PORTFOLIO_SUMMARY_2026-06-05.md").exists()
    payload = json.loads((out_dir / "results_2026-06-05.json").read_text(encoding="utf-8"))
    assert set(payload["strategies"]) == {"MACD_PB", "BTF"}
    assert payload["portfolio_summary"]["keep_surviving_dsr"] >= 0


def test_main_runs_with_skip_gate(tmp_path, monkeypatch) -> None:
    """main() runs a single strategy with the DSR gate skipped (test path)."""
    monkeypatch.setattr(rd, "BIOGRAPHIES_DIR", tmp_path / "bios")
    monkeypatch.setattr(
        rd, "read_pooled_trades", lambda sid: [_trade("DOGEUSDT", 1.5, i) for i in range(22)]
    )
    rc = rd.main(
        ["--strategy", "MACD_PB", "--skip-dsr-gate", "--output-dir", str(tmp_path / "rep")]
    )
    assert rc == 0
    assert (tmp_path / "bios" / "active" / "MACD_PB.yaml").exists()


def test_exec_gate_raises_on_test_failure(monkeypatch) -> None:
    """The execution gate refuses to proceed if the DSR tests fail (spec 10.1)."""
    import subprocess

    class _Result:
        returncode = 1
        stdout = b"boom"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Result())
    with pytest.raises(SystemExit):
        rd.assert_dsr_math_verified()


def test_exec_gate_passes_on_success(monkeypatch) -> None:
    """The execution gate proceeds silently when the DSR tests pass."""
    import subprocess

    class _Result:
        returncode = 0
        stdout = b"ok"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Result())
    rd.assert_dsr_math_verified()  # must not raise


def test_main_unknown_strategy_exits(monkeypatch) -> None:
    """main() exits cleanly when given an unknown strategy id."""
    with pytest.raises(SystemExit):
        rd.main(["--strategy", "NOPE", "--skip-dsr-gate"])
