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


def _btf_post_mortem() -> PostMortem:
    """BTF (bear_trend_follower) -- the canonical thin-sample overfit cautionary tale.

    DEC-2026-05-27-007: promoted on Q1 100% WR / Sharpe 2.4-3.6; May 90-day
    backtest PF 0.76 and live paper PF 0.75 (N=25) confirmed it within 1%. This
    session's regime-DSR control re-ran BTF over full history (futures, N=997)
    and found Tier D in EVERY regime (bull/bear/chop) -- no edge anywhere.
    """
    return PostMortem(
        strategy_id="BTF",
        retirement_date="2026-05-27",
        retirement_decision="DEC-2026-05-27-007",
        decision_maker="operator",
        lifecycle_summary=LifecycleSummary(
            retirement_date="2026-05-27",
            peak_classification="Q1 backtest 100% WR (sample-overfit)",
            final_classification="RETIRED -- NEVER_VALIDATED",
            cumulative_live_trades=25,  # live paper 2026-05-17..27
            final_live_pf=0.75,
        ),
        primary_cause=PrimaryCause.NEVER_VALIDATED,
        causal_analysis=(
            "BTF was promoted on Q1 2026 backtests claiming 100% win rate and "
            "Sharpe 2.4-3.6 -- numbers that were sample-overfit to a specific "
            "market structure (steep monotonic descents). When May 2026 turned "
            "choppy-bear with relief bounces, the regime BTF was built to exploit "
            "was absent: the May 90-day backtest showed basket PF 0.76 across 90 "
            "trades, and live paper confirmed PF 0.75 across 25 trades (within 1% "
            "of backtest). Per-symbol May PFs ranged 0.46-1.10; the best (AVAX "
            "1.10, SOL 1.02) were statistically indistinguishable from noise at "
            "N=16. This session's regime-conditional DSR control (full history, "
            "futures, N=997) independently confirmed Tier D in bull, bear, AND "
            "chop -- BTF has no edge in any regime. The apparent Q1 edge never "
            "existed out of sample; it was the canonical thin-sample + "
            "cost-blind overfit."
        ),
        contributing_factors=[
            "Thin-sample overfit: Q1 100% WR on a narrow market structure.",
            "Regime-structure dependence: needed steep monotonic descents, absent in choppy-bear.",
            "Promoted before rolling-window validation (DEC-2026-05-27-005) and the "
            "DSR/N>=30 gate existed -- both of which it would have failed.",
        ],
        lessons=[
            Lesson(
                lesson_id="LESS-2026-05-001",
                category="THIN_SAMPLE_OVERFIT",
                description=(
                    "A Q1 100%-WR / very-high-Sharpe result on a narrow market "
                    "structure is the #1 overfit trap. Rolling-window validation "
                    "across regimes + a DSR floor catch it; single-window backtests "
                    "do not. BTF is the canonical case the research layer was built "
                    "to prevent."
                ),
                pattern_tags=["thin-sample", "high-wr-overfit", "single-window", "regime-structure-dependent"],
                applies_to_future_hypotheses_in=["all"],
            ),
        ],
        pattern_tags=[
            "trend-follower", "bear-strategy", "short-side", "thin-sample-overfit",
            "retired-never-validated", "cost-blind", "canonical-cautionary-tale",
        ],
        similar_active_strategies=[],  # no active strategy shares BTF's short-trend design
        searchable_terms=[
            "BTF", "bear trend follower", "Q1 100% WR overfit", "PF 0.75 live",
            "thin sample", "2026 canonical cautionary tale",
        ],
        feeds_back_to=[
            "Any hypothesis citing a single-window high-WR backtest must be "
            "rolling-window + DSR validated before promotion (LESS-2026-05-001).",
            "BTF is the calibration control for the regime-DSR instrument: if it "
            "ever scores deployable, the instrument is broken.",
        ],
    )


def _no_edge_post_mortem(
    *,
    strategy_id: str,
    template_desc: str,
    causal: str,
    factors: list[str],
    lesson_id: str,
    lesson_category: str,
    lesson_desc: str,
    lesson_tags: list[str],
    pattern_tags: list[str],
    searchable: list[str],
    feeds_back: list[str],
) -> PostMortem:
    """Build a NEVER_VALIDATED post-mortem for a triage-retired strategy.

    Shared shape for the 2026-05-28 spot-wins triage retirees (DEC-2026-05-28-002):
    strategies that never showed a validatable edge in any regime.
    """
    return PostMortem(
        strategy_id=strategy_id,
        retirement_date="2026-05-28",
        retirement_decision="DEC-2026-05-28-002",
        decision_maker="operator",
        lifecycle_summary=LifecycleSummary(
            retirement_date="2026-05-28",
            peak_classification=template_desc,
            final_classification="RETIRED -- NEVER_VALIDATED",
            cumulative_live_trades=0,  # never live (kill switch OFF)
        ),
        primary_cause=PrimaryCause.NEVER_VALIDATED,
        causal_analysis=causal,
        contributing_factors=factors,
        lessons=[
            Lesson(
                lesson_id=lesson_id, category=lesson_category, description=lesson_desc,
                pattern_tags=lesson_tags, applies_to_future_hypotheses_in=["all"],
            ),
        ],
        pattern_tags=pattern_tags,
        similar_active_strategies=[],
        searchable_terms=searchable,
        feeds_back_to=feeds_back,
    )


def _cmf_post_mortem() -> PostMortem:
    """CMF (cascading_momentum_filter) -- regime misattribution, no validated edge."""
    return _no_edge_post_mortem(
        strategy_id="CMF",
        template_desc="cascading_momentum_filter (short-side momentum)",
        causal=(
            "CMF was POOR in all three bear/chop regimes it was designed for "
            "(DEC-2026-05-28-002 spot/futures rolling backtest). Its apparent "
            "trending_bull 'edge' was wrong-direction noise -- a misattribution, "
            "not a real signal -- and it depends on shorts, which had no validated "
            "edge even with shorts enabled and funding modeled. No regime in which "
            "it reliably worked."
        ),
        factors=[
            "Design intent (bear/chop momentum) failed in every bear/chop regime.",
            "Trending_bull 'edge' was wrong-direction noise (regime misattribution).",
            "Short-dependent with no validated short edge (DEC-2026-05-28-001).",
        ],
        lesson_id="LESS-2026-05-002",
        lesson_category="REGIME_MISATTRIBUTION",
        lesson_desc=(
            "An apparent edge in a regime the strategy was NOT designed for is "
            "usually wrong-direction noise, not a discovery. Verify the edge is in "
            "the hypothesized regime before re-tagging a strategy to its accidental "
            "best regime."
        ),
        lesson_tags=["regime-misattribution", "wrong-direction-noise", "short-side"],
        pattern_tags=["momentum", "short-side", "bear-strategy", "regime-misattribution", "retired-never-validated"],
        searchable=["CMF", "cascading momentum filter", "regime misattribution", "wrong direction"],
        feeds_back=["Re-tagging a strategy to its accidental best regime requires confirming the edge is real there, not noise (LESS-2026-05-002)."],
    )


def _rsi_bb_post_mortem() -> PostMortem:
    """RSI_BB (rsi_bb_mean_reversion) -- worst PF in portfolio; classic pattern, no crypto edge."""
    return _no_edge_post_mortem(
        strategy_id="RSI_BB",
        template_desc="rsi_bb_mean_reversion (classic TA mean reversion)",
        causal=(
            "RSI_BB had the worst performance in the portfolio: PF 0.06-0.41 across "
            "all four regimes in both spot and futures modes (DEC-2026-05-28-002). "
            "A textbook RSI + Bollinger-Band mean-reversion pattern simply did not "
            "carry edge on these crypto symbols/timeframe -- it was actively "
            "losing, not merely break-even."
        ),
        factors=[
            "Classic TA mean-reversion pattern with no crypto edge at this timeframe.",
            "Worst PF in the portfolio (0.06-0.41) -- consistent across regimes and modes.",
        ],
        lesson_id="LESS-2026-05-003",
        lesson_category="PATTERN_WITHOUT_EDGE",
        lesson_desc=(
            "A well-known TA pattern (RSI+BB mean reversion) being popular is not "
            "evidence it has edge. Crypto mean-reversion at 1H/4H needs its own "
            "validation; textbook patterns frequently carry zero or negative edge."
        ),
        lesson_tags=["mean-reversion", "classic-ta", "no-edge"],
        pattern_tags=["mean-reversion", "rsi", "bollinger-bands", "no-edge", "retired-never-validated"],
        searchable=["RSI_BB", "rsi bollinger mean reversion", "worst PF", "classic TA no edge"],
        feeds_back=["Textbook TA patterns get the same DSR validation as novel ones; popularity is not edge (LESS-2026-05-003)."],
    )


def _hatp_post_mortem() -> PostMortem:
    """HATP (heikin_ashi_trend_pulse) -- 231 trades, poor all regimes; Q1 claim didn't reproduce."""
    return _no_edge_post_mortem(
        strategy_id="HATP",
        template_desc="heikin_ashi_trend_pulse (Q1 backtest PF 1.40-1.70)",
        causal=(
            "HATP was promoted on a Q1 3-round backtest claiming PF 1.40-1.70, but "
            "the rolling-window backtest could not reproduce it: POOR in all four "
            "regimes across 231 trades (DEC-2026-05-28-002). The high trade count "
            "rules out a thin-sample fluke -- HATP simply has no edge; the Q1 "
            "result was overfit, the same pattern as BTF."
        ),
        factors=[
            "Q1 multi-round backtest (PF 1.40-1.70) did not reproduce out of sample.",
            "231 trades, POOR in all 4 regimes -- not thin-sample, just no edge.",
            "Heikin-Ashi recursion + pulse entries fit Q1 noise.",
        ],
        lesson_id="LESS-2026-05-004",
        lesson_category="TRADE_COUNT_IS_NOT_EDGE",
        lesson_desc=(
            "A high trade count (here 231) does NOT imply edge -- a strategy can "
            "trade frequently and still be net-negative across every regime. "
            "Volume of trades is not evidence; per-trade expectancy after costs is."
        ),
        lesson_tags=["high-trade-count", "overfit", "heikin-ashi", "no-edge"],
        pattern_tags=["heikin-ashi", "trend-pulse", "high-frequency", "overfit", "retired-never-validated"],
        searchable=["HATP", "heikin ashi trend pulse", "231 trades no edge", "Q1 did not reproduce"],
        feeds_back=["High trade count must not be mistaken for validation; require per-trade DSR after costs (LESS-2026-05-004)."],
    )


def _vrb_post_mortem() -> PostMortem:
    """VRB (volatility_regime_breakout) -- BTC-only single-window, no robust verdict."""
    return _no_edge_post_mortem(
        strategy_id="VRB",
        template_desc="volatility_regime_breakout (BTC-only)",
        causal=(
            "VRB was BTC-only with a single window per regime, so no robust verdict "
            "was possible (DEC-2026-05-28-002). Without cross-symbol breadth or "
            "multiple windows, any apparent edge could not be distinguished from a "
            "single lucky path. Retired for insufficient evidence rather than a "
            "proven negative."
        ),
        factors=[
            "Single symbol (BTC) -- no cross-symbol corroboration.",
            "Single window per regime -- no rolling-window stability evidence.",
        ],
        lesson_id="LESS-2026-05-005",
        lesson_category="INSUFFICIENT_BREADTH",
        lesson_desc=(
            "A single-symbol, single-window result cannot be validated -- there is "
            "no breadth to distinguish edge from a lucky path. Require multiple "
            "symbols and rolling windows before any verdict, positive or negative."
        ),
        lesson_tags=["single-symbol", "single-window", "insufficient-breadth"],
        pattern_tags=["volatility-breakout", "btc-only", "single-window", "insufficient-breadth", "retired-never-validated"],
        searchable=["VRB", "volatility regime breakout", "BTC only", "single window no verdict"],
        feeds_back=["No promotion or retirement verdict from a single-symbol single-window backtest; require breadth (LESS-2026-05-005)."],
    )


def _vpt_post_mortem() -> PostMortem:
    """VPT (vpt_momentum) -- PF 1.00 break-even gross; a loss after slippage."""
    return _no_edge_post_mortem(
        strategy_id="VPT",
        template_desc="vpt_momentum (BTC-only, break-even)",
        causal=(
            "VPT was break-even gross (PF 1.00 overall, BTC-only) and a net loss "
            "after realistic slippage (DEC-2026-05-28-002). A strategy that only "
            "breaks even before costs is a guaranteed loser after them -- the cost "
            "model is decisive, not a rounding detail."
        ),
        factors=[
            "PF 1.00 gross -- no margin to absorb costs.",
            "Net-negative after slippage; cost-blindness would have hidden this.",
            "BTC-only -- no breadth.",
        ],
        lesson_id="LESS-2026-05-006",
        lesson_category="COST_BLINDNESS",
        lesson_desc=(
            "Break-even gross PF (1.00) is a LOSS after costs. Cost modeling is "
            "decisive: a strategy must clear costs with margin, not merely break "
            "even before them. This is why honest per-symbol cost modeling is a "
            "first-class research primitive."
        ),
        lesson_tags=["break-even", "cost-blindness", "slippage"],
        pattern_tags=["vpt", "volume-momentum", "btc-only", "break-even", "cost-blind", "retired-never-validated"],
        searchable=["VPT", "vpt momentum", "PF 1.00 break-even", "loses after slippage"],
        feeds_back=["Break-even gross PF is a net loss; require margin over modeled costs before promotion (LESS-2026-05-006)."],
    )


# Registry of authored post-mortems (manual at v0.5; PRD Section 6.5).
POST_MORTEMS: dict[str, Callable[[], PostMortem]] = {
    "MACD_PB": _macd_pb_post_mortem,
    "BTF": _btf_post_mortem,
    "CMF": _cmf_post_mortem,
    "RSI_BB": _rsi_bb_post_mortem,
    "HATP": _hatp_post_mortem,
    "VRB": _vrb_post_mortem,
    "VPT": _vpt_post_mortem,
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
