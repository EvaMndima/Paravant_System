"""Tests for the strategy-card CLI scripts/show_strategy.py (spec Section 14)."""
from __future__ import annotations

import json

import yaml

import scripts.show_strategy as ss


def _write_bio(directory, strategy_id: str, payload: dict) -> None:
    """Write a biography YAML into ``directory/<strategy_id>.yaml``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{strategy_id}.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
    )


def _sample_bio(strategy_id: str = "MACD_PB") -> dict:
    """A minimal biography with one retrospective validation entry."""
    return {
        "strategy_id": strategy_id,
        "status": "ACTIVE_LIVE",
        "symbols": ["DOGEUSDT", "AVAXUSDT"],
        "current_classification": "TIER_B_PROVISIONAL_READY",
        "classification_history": [
            {
                "date": "2026-06-05",
                "classification": "TIER_B_PROVISIONAL_READY",
                "triggered_by": "retrospective_dsr_run_20260605",
            }
        ],
        "statistical_validation_history": [
            {
                "run_date": "2026-06-05",
                "run_id": "retrospective_dsr_run_20260605",
                "cost_model_version": "v0_unverified",
                "n_trades_analyzed": 47,
                "n_trades_quarantined": 0,
                "pf_raw": 1.62,
                "pf_adjusted": 1.43,
                "sharpe_raw": 1.34,
                "sharpe_adjusted": 1.18,
                "max_dd_pct_pooled_adjusted": 4.2,
                "effective_k": 1150,
                "gating_k_used": 2000,
                "base_dsr_p_value": 0.18,
                "conservative_dsr_p_value": 0.28,
                "dsr_p_value": 0.28,
                "base_tier": "TIER_A_FULL_READY",
                "conservative_tier": "TIER_B_PROVISIONAL_READY",
                "verdict_is_fragile": True,
                "hard_floor_status": {
                    "dsr_passed": True,
                    "max_dd_passed": True,
                    "cost_model_verified": False,
                    "leakage_check": "not_run",
                },
            }
        ],
        "decision_log": ["DEC-2026-05-28-002: Triage review - KEEP"],
    }


def test_summary_renders_without_error(tmp_path, monkeypatch, capsys) -> None:
    """Default summary view renders a known biography cleanly."""
    monkeypatch.setattr(ss, "BIOGRAPHIES_DIR", tmp_path)
    _write_bio(tmp_path / "active", "MACD_PB", _sample_bio())
    rc = ss.main(["MACD_PB", "--no-color"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Strategy: MACD_PB" in out
    assert "LATEST STATISTICAL VALIDATION" in out
    assert "TIER_B_PROVISIONAL_READY" in out
    # No ANSI escape codes when --no-color.
    assert "\033[" not in out


def test_unknown_strategy_lists_available_and_exits_2(tmp_path, monkeypatch, capsys) -> None:
    """An unknown id lists available strategies and returns exit code 2."""
    monkeypatch.setattr(ss, "BIOGRAPHIES_DIR", tmp_path)
    _write_bio(tmp_path / "active", "MACD_PB", _sample_bio())
    rc = ss.main(["NOPE", "--no-color"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "not found" in err
    assert "MACD_PB" in err


def test_json_output_is_valid(tmp_path, monkeypatch, capsys) -> None:
    """--json emits valid JSON parseable by json.loads."""
    monkeypatch.setattr(ss, "BIOGRAPHIES_DIR", tmp_path)
    _write_bio(tmp_path / "active", "MACD_PB", _sample_bio())
    rc = ss.main(["MACD_PB", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    parsed = json.loads(out)
    assert parsed["strategy_id"] == "MACD_PB"


def test_section_view(tmp_path, monkeypatch, capsys) -> None:
    """--section validation renders the statistical-validation section."""
    monkeypatch.setattr(ss, "BIOGRAPHIES_DIR", tmp_path)
    _write_bio(tmp_path / "active", "MACD_PB", _sample_bio())
    rc = ss.main(["MACD_PB", "--section", "validation", "--no-color"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "validation section" in out
    assert "conservative_dsr_p_value" in out


def test_empty_section_renders_placeholder(tmp_path, monkeypatch, capsys) -> None:
    """A section with no data renders an (empty) placeholder, not a crash."""
    monkeypatch.setattr(ss, "BIOGRAPHIES_DIR", tmp_path)
    _write_bio(tmp_path / "active", "MACD_PB", _sample_bio())
    rc = ss.main(["MACD_PB", "--section", "optimization", "--no-color"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "(empty)" in out


def test_no_argument_lists_available(tmp_path, monkeypatch, capsys) -> None:
    """With no strategy id, the CLI lists the available strategies."""
    monkeypatch.setattr(ss, "BIOGRAPHIES_DIR", tmp_path)
    _write_bio(tmp_path / "active", "MACD_PB", _sample_bio())
    _write_bio(tmp_path / "retired", "BTF", _sample_bio("BTF"))
    rc = ss.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "MACD_PB" in out
    assert "BTF" in out


def test_retired_biography_renders(tmp_path, monkeypatch, capsys) -> None:
    """A biography in retired/ is found and rendered."""
    monkeypatch.setattr(ss, "BIOGRAPHIES_DIR", tmp_path)
    bio = _sample_bio("BTF")
    bio["status"] = "RETIRED"
    _write_bio(tmp_path / "retired", "BTF", bio)
    rc = ss.main(["BTF", "--no-color"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Strategy: BTF" in out
    assert "RETIRED" in out
