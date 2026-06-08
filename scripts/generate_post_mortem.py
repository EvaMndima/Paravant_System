"""Generate a structured post-mortem and retire a strategy (PRD Appendix C).

Closes the full-circle lifecycle (DEC-2026-06-04-011): every retired strategy
gets a STRUCTURED, queryable post-mortem (cause, causal analysis, lessons with
pattern tags, similar active strategies, searchable terms) attached to its
biography, and the biography is moved ``active/ -> retired/`` with
``status=RETIRED``.

Per PRD Section 6.5, post-mortem CONTENT is authored manually at v0.5 (no
auto-generation yet); this module provides the MECHANISM (validate + attach +
retire + move + idempotent write) plus a registry of authored post-mortems.

CLI::

    python -m scripts.generate_post_mortem MACD_PB
    python -m scripts.generate_post_mortem --list

Research-layer script: imports from ``research/`` and ``src/`` (one-way rule).
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import yaml

import scripts.retrospective_dsr as rd
from research.biographies.schema import (
    Lesson,
    LifecycleSummary,
    PostMortem,
    PrimaryCause,
    SimilarStrategy,
    StrategyBiography,
    StrategyStatus,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


def apply_post_mortem(post_mortem: PostMortem) -> Path:
    """Attach ``post_mortem`` to its strategy's biography and RETIRE it.

    Loads the biography (from ``active/`` or ``retired/``), sets ``post_mortem``
    and ``status=RETIRED``, appends a ``decision_log`` entry, writes the biography
    under ``retired/``, and removes the ``active/`` copy if present. Idempotent:
    re-applying the same retirement decision does not duplicate the decision-log
    entry.

    Args:
        post_mortem: The fully authored, validated post-mortem.

    Returns:
        The path the retired biography was written to.

    Raises:
        FileNotFoundError: If no biography exists for the strategy.
    """
    strategy_id = post_mortem.strategy_id
    active_path = rd.BIOGRAPHIES_DIR / "active" / f"{strategy_id}.yaml"
    retired_path = rd.BIOGRAPHIES_DIR / "retired" / f"{strategy_id}.yaml"

    src = active_path if active_path.exists() else retired_path
    if not src.exists():
        raise FileNotFoundError(
            f"No biography for {strategy_id} (looked in active/ and retired/)."
        )

    bio = StrategyBiography.model_validate(
        yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    )
    bio.post_mortem = post_mortem
    bio.status = StrategyStatus.RETIRED

    decision_entry = (
        f"{post_mortem.retirement_decision}: RETIRED -- post-mortem filed "
        f"(primary_cause: {post_mortem.primary_cause.value})."
    )
    if decision_entry not in bio.decision_log:
        bio.decision_log.append(decision_entry)

    retired_path.parent.mkdir(parents=True, exist_ok=True)
    retired_path.write_text(
        yaml.safe_dump(
            bio.model_dump(mode="json"),
            sort_keys=False, default_flow_style=False, allow_unicode=False,
        ),
        encoding="utf-8",
    )
    # Move: remove the active copy once the retired copy is written.
    if active_path.exists() and active_path.resolve() != retired_path.resolve():
        active_path.unlink()

    logger.info(
        "post_mortem_filed",
        strategy_id=strategy_id, path=str(retired_path),
        primary_cause=post_mortem.primary_cause.value,
    )
    return retired_path


def _macd_pb_post_mortem() -> PostMortem:
    """Authored post-mortem for MACD_PB (DEC-2026-06-04-016/017).

    Evidence: regime-conditional DSR screen over two windows. choppy_bear was
    PF 1.97 / +0.29 Sharpe (N=8) in the ~90-day promotion era (matching the
    documented 2.33) but PF 0.76 over the full 540 days, with no positive cell in
    any regime. The edge was REAL at promotion and DECAYED with the bear/choppy ->
    bull-recovery regime shift; even at promotion it was never DSR-validated
    (best-window choppy_bear p=0.569, above the 0.30 floor, N=8 thin).
    """
    return PostMortem(
        strategy_id="MACD_PB",
        retirement_date="2026-06-08",
        retirement_decision="DEC-2026-06-04-017",
        decision_maker="operator",
        lifecycle_summary=LifecycleSummary(
            proposed_date=None,  # hypothesis_history not back-filled in biography
            first_live_deployment=None,  # never live (kill switch OFF; paper geo-blocked)
            retirement_date="2026-06-08",
            total_versions=None,
            peak_classification="KEEP (informal, PF-based; never DSR-validated)",
            final_classification="DECAYED",
            cumulative_live_pnl_pct=0.0,
            cumulative_live_trades=0,
            final_live_pf=None,
        ),
        primary_cause=PrimaryCause.REGIME_SHIFT,
        causal_analysis=(
            "MACD_PB (MACD pullback; DOGEUSDT, AVAXUSDT) was promoted to KEEP "
            "status in May 2026 on a strong choppy_bear backtest edge (PF 2.33). "
            "The regime-conditional DSR screen (DEC-2026-06-04-014) re-evaluated "
            "it over two windows. In the ~90-day promotion-era window (ending "
            "2026-05-28) choppy_bear was genuinely positive: PF 1.97, Sharpe "
            "+0.29 (N=8) -- confirming the edge was REAL at promotion, not "
            "fabricated. Over the full 540-day window (ending 2026-06-07) the "
            "same choppy_bear cell fell to PF 0.76 (Sharpe -0.12), and MACD_PB "
            "showed NO positive cost-adjusted cell in ANY regime (coarse or fine, "
            "every base DSR p >= 0.90). The edge DECAYED as the macro regime "
            "shifted from the bear/choppy conditions of early 2026 toward bull "
            "recovery: MACD_PB is a choppy_bear-fit strategy whose regime "
            "departed. Critically, even at promotion the edge was never "
            "DSR-validated -- its best-window choppy_bear p was 0.569, above the "
            "0.30 floor (N=8 thin). The strategy was real-but-fragile, and the "
            "decay confirmed the fragility the (then-absent) DSR gate would have "
            "flagged. Retired because no positive edge remains in any current "
            "regime and its single-regime concentration makes it structurally "
            "vulnerable to exactly the regime shift that occurred."
        ),
        contributing_factors=[
            "Regime shift: bear/choppy (early 2026) -> bull recovery, removing the "
            "choppy_bear conditions the strategy depends on.",
            "Single-regime concentration: edge confined to choppy_bear, with no "
            "expression in trending or bull regimes.",
            "Never DSR-validated at promotion (PF-based gate); best-window DSR "
            "p=0.569 was above the 0.30 floor.",
            "Thin sample: choppy_bear N=8 at promotion, N=14 over the full window "
            "-- wide confidence intervals throughout.",
        ],
        lessons=[
            Lesson(
                lesson_id="LESS-2026-06-001",
                category="REGIME_FIT",
                description=(
                    "Single-SubRegime edges (here choppy_bear) carry "
                    "concentration risk: when that regime exits, the edge has "
                    "nowhere to express. Weight multi-regime robustness in "
                    "promotion, or deploy strictly in-regime via the router."
                ),
                pattern_tags=["single-regime", "choppy-bear-only", "regime-dependent"],
                applies_to_future_hypotheses_in=["CHOPPY_BEAR", "TRENDING_BULL"],
            ),
            Lesson(
                lesson_id="LESS-2026-06-002",
                category="PROMOTION_RIGOR",
                description=(
                    "A PF-based promotion deployed an edge with DSR p=0.569 "
                    "(above the floor) that then decayed. Real-but-fragile edges "
                    "(positive PF but DSR p above floor) should be paper-validated "
                    "in-regime, not promoted on PF alone. The DSR gate would have "
                    "held this back."
                ),
                pattern_tags=["real-but-fragile", "dsr-above-floor", "pf-only-promotion"],
                applies_to_future_hypotheses_in=["all"],
            ),
        ],
        pattern_tags=[
            "macd-based", "pullback-entry", "choppy-bear", "single-regime",
            "regime-dependent", "retired-by-decay", "real-but-fragile",
            "never-dsr-validated",
        ],
        similar_active_strategies=[
            SimilarStrategy(
                strategy_id="VBB",
                similarity_score=0.70,
                shared_risk_factors=[
                    "Both depend on the choppy_bear regime",
                    "Both promoted in the same early-2026 bear/choppy era",
                ],
                recommended_monitoring=(
                    "VBB choppy_bear edge persists more strongly (PF 1.38 over "
                    "540d vs MACD_PB 0.76); monitor for the same decay as the bull "
                    "regime extends -- VBB is the most likely next decay subject."
                ),
            ),
            SimilarStrategy(
                strategy_id="BTP",
                similarity_score=0.55,
                shared_risk_factors=[
                    "Choppy/bear-era promotion",
                    "Edge fades in trending/bull regimes",
                ],
                recommended_monitoring="Watch BTP choppy_bear (1.40 promo -> 0.81 full).",
            ),
            SimilarStrategy(
                strategy_id="SRC",
                similarity_score=0.45,
                shared_risk_factors=["Regime-dependent edge", "Thin per-regime N"],
                recommended_monitoring="SRC choppy_bull/ranging only; choppy_bear already weak.",
            ),
        ],
        searchable_terms=[
            "MACD pullback", "choppy bear decay", "2026 regime-shift casualty",
            "real-but-fragile", "DOGE AVAX", "single-regime concentration",
        ],
        feeds_back_to=[
            "Future MACD-based / pullback hypotheses should check this post-mortem.",
            "Future single-regime (choppy_bear) hypotheses inherit the "
            "concentration-risk lesson (LESS-2026-06-001).",
            "Promotion process should DSR-gate before KEEP, not PF-only "
            "(LESS-2026-06-002).",
        ],
    )


# Registry of authored post-mortems (manual at v0.5; PRD Section 6.5).
POST_MORTEMS: dict[str, Callable[[], PostMortem]] = {
    "MACD_PB": _macd_pb_post_mortem,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Argument vector (defaults to ``sys.argv``).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="File a structured post-mortem and retire a strategy (Appendix C)."
    )
    parser.add_argument("strategy_id", nargs="?", help="Strategy to retire (e.g. MACD_PB).")
    parser.add_argument("--list", action="store_true",
                        help="List strategies with an authored post-mortem.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Argument vector (defaults to ``sys.argv``).

    Returns:
        Process exit code.
    """
    from src.utils.logging import setup_logging

    setup_logging(level="INFO")
    args = parse_args(argv)

    if args.list or not args.strategy_id:
        print("Authored post-mortems:", ", ".join(sorted(POST_MORTEMS)))
        return 0

    if args.strategy_id not in POST_MORTEMS:
        print(
            f"No authored post-mortem for {args.strategy_id}. "
            f"Available: {', '.join(sorted(POST_MORTEMS))}",
            file=sys.stderr,
        )
        return 1

    post_mortem = POST_MORTEMS[args.strategy_id]()
    path = apply_post_mortem(post_mortem)
    print(
        f"Filed post-mortem for {args.strategy_id} "
        f"(cause: {post_mortem.primary_cause.value}) -> {path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
