"""Tests for the structured post-mortem model + retire mechanism (Appendix C)."""
from __future__ import annotations

import yaml

import scripts.generate_post_mortem as gpm
from research.biographies.schema import (
    PostMortem,
    PrimaryCause,
    StrategyBiography,
    StrategyStatus,
)


def test_post_mortem_model_round_trips() -> None:
    """A PostMortem dumps to JSON-safe primitives and re-validates identically."""
    pm = gpm._macd_pb_post_mortem()
    dumped = pm.model_dump(mode="json")
    # Enum serialized to its string value (YAML-safe).
    assert dumped["primary_cause"] == "REGIME_SHIFT"
    again = PostMortem.model_validate(dumped)
    assert again.strategy_id == "MACD_PB"
    assert again.primary_cause is PrimaryCause.REGIME_SHIFT
    assert len(again.lessons) == 2
    assert any("real-but-fragile" in t for t in again.pattern_tags)


def test_macd_pb_post_mortem_content() -> None:
    """The authored MACD_PB post-mortem captures the decay evidence + lessons."""
    pm = gpm._macd_pb_post_mortem()
    assert pm.primary_cause is PrimaryCause.REGIME_SHIFT
    assert pm.lifecycle_summary.final_classification == "DECAYED"
    assert pm.lifecycle_summary.cumulative_live_trades == 0  # never live
    assert "1.97" in pm.causal_analysis and "0.76" in pm.causal_analysis
    # The single-regime concentration + promotion-rigor lessons are present.
    cats = {lesson.category for lesson in pm.lessons}
    assert {"REGIME_FIT", "PROMOTION_RIGOR"} <= cats
    # VBB is flagged as the most-similar active strategy to monitor next.
    sims = {s.strategy_id for s in pm.similar_active_strategies}
    assert "VBB" in sims


def test_biography_with_post_mortem_validates() -> None:
    """A biography YAML carrying a post_mortem dict validates against the model."""
    bio = StrategyBiography(strategy_id="X", status=StrategyStatus.RETIRED)
    bio.post_mortem = gpm._macd_pb_post_mortem()
    data = bio.model_dump(mode="json")
    reloaded = StrategyBiography.model_validate(yaml.safe_load(yaml.safe_dump(data)))
    assert reloaded.post_mortem is not None
    assert reloaded.post_mortem.primary_cause == "REGIME_SHIFT"


def test_apply_post_mortem_retires_and_moves(tmp_path, monkeypatch) -> None:
    """apply_post_mortem sets RETIRED, writes retired/, removes active/, idempotent."""
    monkeypatch.setattr(gpm.rd, "BIOGRAPHIES_DIR", tmp_path)
    active = tmp_path / "active"
    active.mkdir(parents=True)
    seed = StrategyBiography(
        strategy_id="MACD_PB", status=StrategyStatus.ACTIVE_LIVE, symbols=["DOGEUSDT"]
    )
    (active / "MACD_PB.yaml").write_text(
        yaml.safe_dump(seed.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )

    path = gpm.apply_post_mortem(gpm._macd_pb_post_mortem())

    assert path == tmp_path / "retired" / "MACD_PB.yaml"
    assert path.exists()
    assert not (active / "MACD_PB.yaml").exists()  # moved, not copied

    retired = StrategyBiography.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
    assert retired.status == StrategyStatus.RETIRED
    assert retired.post_mortem is not None
    assert retired.post_mortem.primary_cause == "REGIME_SHIFT"
    decision_lines = [d for d in retired.decision_log if "RETIRED" in str(d)]
    assert len(decision_lines) == 1

    # Idempotent: re-applying does not duplicate the decision-log entry.
    gpm.apply_post_mortem(gpm._macd_pb_post_mortem())
    retired2 = StrategyBiography.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )
    decision_lines2 = [d for d in retired2.decision_log if "RETIRED" in str(d)]
    assert len(decision_lines2) == 1
