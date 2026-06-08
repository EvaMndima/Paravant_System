"""Regime-conditional backtest DSR screen (DEC-2026-06-04-014, Phase B).

Answers, BEFORE paper trading: which (strategy x regime) pairs carry a backtest
edge distinguishable from selection-bias luck? It REGENERATES per-trade data by
re-running the backtest engine (the per-trade series that justified the KEEP
promotions was never persisted -- DEC-2026-06-04-014), tags each trade with the
SubRegime active AT ENTRY (causal), then computes the Deflated Sharpe Ratio both
POOLED per strategy AND within each coarse regime bucket, producing a
strategy x regime coverage matrix.

THE FIVE GUARDS (DEC-2026-06-04-014) -- the whole point:
  1. SCREEN, not a deployment gate. Output never bypasses paper/live validation;
     ``current_classification`` is NOT touched. Only ``regime_coverage`` is written.
  2. K counts regime buckets as trials (``regime_conditional_k``): testing N
     regimes and keeping the best is cross-regime selection bias.
  3. Causal regime tagging (``research.backtest.regime_tagging``), with a runnable
     leakage self-check on the BTC-daily anchor before any verdict is trusted.
  4. Coarse buckets (bull/bear/chop); a bucket below ``MIN_BUCKET_N`` is
     DESCRIPTIVE (``is_descriptive=True``), never gating.
  5. DSR is necessary, not sufficient: a pass is a strong screen, not proof of
     live edge.

This reuses the verified statistical core (``analyze_strategy`` in
``scripts/retrospective_dsr.py``) per bucket -- the same cost model, base/
conservative split, K + variance_sr sweeps, and the INSUFFICIENT_DATA guard --
so the regime screen and the pooled retrospective cannot disagree on the math.

Data source: regenerated backtests fetch OHLCV from Binance (local access
required). Read-only against the network; writes only research artifacts.
"""
from __future__ import annotations

import argparse
import asyncio
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

import scripts.retrospective_dsr as rd
from research.backtest.cost_model import CostModel
from research.backtest.regime_tagging import (
    COARSE_BUCKETS,
    bucket_by_coarse,
    bucket_by_sub_regime,
    build_regime_timeline,
    is_labeling_causal,
    tag_trades,
)
from research.biographies.schema import (
    RegimeCoverageRun,
    RegimeDSRResult,
    StrategyBiography,
    StrategyStatus,
    Tier,
)
from research.validation.effective_k import (
    EffectiveKEstimate,
    regime_conditional_k,
    variance_sr_point_estimate,
)
from scripts.backtest_rolling import STRATEGY_PARAMS, STRATEGY_SYMBOLS
from src.brokers.binance.client import BinanceClient
from src.core.strategy.backtest import BacktestEngine
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.data.market_data import MarketDataFetcher, OHLCVSeries
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Research label -> rolling-backtest template id. The templates/params/symbols
# are the single source in scripts/backtest_rolling.py (a peer script); this map
# is the only new registry datum needed.
RESEARCH_LABEL_TO_TEMPLATE: dict[str, str] = {
    "MACD_PB": "macd_pullback",
    "BTP": "bull_trend_pullback",
    "VBB": "volume_balance_breakout",
    "SRC": "stoch_rsi_bull_cross",
    "ICVP": "ichimoku_cloud_trend",
    "BTF": "bear_trend_follower",
    "CMF": "cascading_momentum_filter",
    "RSI_BB": "rsi_bb_mean_reversion",
    "HATP": "heikin_ashi_trend_pulse",
    "VRB": "volatility_regime_breakout",
    "VPT": "vpt_momentum",
}

# Below this per-bucket N a regime cell is DESCRIPTIVE, not gating (guard #4).
# Matches the Tier B deployment N floor (DEC-2026-06-04-008): below it a regime
# verdict is shown for context but carries no weight.
MIN_BUCKET_N: int = 20

# Backtest lookback window for the O(n^2)->O(n) engine optimization
# (DEC-2026-06-04-015). 1800 bars reproduces EMA(200)-class indicators to ~1e-8,
# proven trade-identical on real data (102==102 trades, 6x faster).
DEFAULT_LOOKBACK_WINDOW: int = 1800

# Templates PROVEN window-safe by tests/unit/backtest/test_window_equivalence.py
# (bounded-lookback indicators only). Other templates run with the full history
# (lookback_window=None) because they use inception-cumulative / recursive
# indicators (e.g. vpt_momentum's running VPT, heikin_ashi recursion) OR are
# simply not yet covered by the equivalence test -- conservative by default.
WINDOW_SAFE_TEMPLATES: frozenset[str] = frozenset({
    "macd_pullback",
    "bull_trend_pullback",
    "volume_balance_breakout",
    "stoch_rsi_bull_cross",
    "ichimoku_cloud_trend",
})

# On-disk cache for regenerated trades so re-runs (fine-breakdown tweaks, K
# tuning) skip the expensive fetch+backtest entirely. NOT committed (transient).
CACHE_DIR = Path("research/.cache/regime_dsr")

# Per-strategy execution model for regeneration. SHORT-side (bear) strategies
# can only express their edge with shorts enabled, so they MUST be backtested in
# "futures" mode (allow_shorts=True + conservative funding drag, DEC-2026-05-28-001);
# in "spot" mode they produce N=0 (every short signal is suppressed) and tell us
# nothing. Long/bidirectional strategies use "spot" -- the mode they actually
# deploy in, and empirically their better mode (project finding 2026-05-28). The
# --market CLI flag overrides this map when set explicitly.
_DEFAULT_MARKET_BY_LABEL: dict[str, str] = {
    "BTF": "futures",   # bear_trend_follower -- short-side
    "CMF": "futures",   # cascading_momentum_filter -- short-side bear
    "MACD_PB": "spot",
    "BTP": "spot",
    "VBB": "spot",
    "SRC": "spot",
    "ICVP": "spot",
    "RSI_BB": "spot",
    "HATP": "spot",
    "VRB": "spot",
    "VPT": "spot",
}


def market_for_label(label: str, override: str | None = None) -> str:
    """Return the execution model to backtest ``label`` in.

    Args:
        label: Research label.
        override: Explicit ``--market`` value, or None to use the per-strategy
            default.

    Returns:
        ``"spot"`` or ``"futures"``. Short-side strategies default to
        ``"futures"`` so they can actually trade (see ``_DEFAULT_MARKET_BY_LABEL``).
    """
    if override:
        return override
    return _DEFAULT_MARKET_BY_LABEL.get(label, "spot")

# Status per label (single source: the retrospective universe).
_STATUS_BY_LABEL: dict[str, StrategyStatus] = {
    spec.strategy_id: spec.status for spec in rd.STRATEGY_UNIVERSE
}

OUTPUT_DIR = Path("docs/research/regime_dsr")


@dataclass(frozen=True)
class RegeneratedTrades:
    """Per-trade backtest data regenerated for one strategy.

    Attributes:
        label: Research label (e.g. ``MACD_PB``).
        template: Rolling-backtest template id.
        symbols: Symbols backtested.
        trades: Pooled serialized ``TradeRecord`` dicts across all symbols.
        btc_daily: BTC daily series (the causal regime anchor).
    """

    label: str
    template: str
    symbols: list[str]
    trades: list[dict[str, Any]]
    btc_daily: OHLCVSeries


@dataclass
class RegimeAnalysis:
    """Result of the regime-conditional screen for one strategy.

    Attributes:
        coverage_run: The canonical ``RegimeCoverageRun`` for the biography.
        pooled_result: The pooled (all-regime) ``AnalysisResult``.
        per_bucket_results: Per coarse-bucket ``AnalysisResult`` (for reports).
    """

    coverage_run: RegimeCoverageRun
    pooled_result: rd.AnalysisResult
    per_bucket_results: dict[str, rd.AnalysisResult] = field(default_factory=dict)


def _backtest_config(market: str) -> BacktestConfig:
    """Build the backtest config for spot (long-only) or futures (long+short).

    Args:
        market: ``"spot"`` (allow_shorts False, no funding) or ``"futures"``
            (allow_shorts True, conservative perpetual funding drag).

    Returns:
        A ``BacktestConfig``. Commission 0.1% + slippage 0.05% mean recorded
        ``return_pct`` is net of ~0.30% round-trip -- the booked cost the
        incremental-pad model subtracts the EXCESS over (DEC-2026-06-04-014).
    """
    if market == "futures":
        return BacktestConfig(
            initial_capital=10_000.0,
            commission_rate=0.001,
            slippage_rate=0.0005,
            allow_shorts=True,
            funding_rate_per_8h=0.0001,
        )
    return BacktestConfig(
        initial_capital=10_000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
        allow_shorts=False,
        funding_rate_per_8h=0.0,
    )


async def _fetch_with_retry(
    fetcher: MarketDataFetcher,
    *,
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
    retries: int = 4,
) -> OHLCVSeries:
    """Fetch OHLCV with bounded retry + backoff on TRANSIENT connection errors.

    Binance occasionally resets a connection mid-fetch (ConnectionResetError /
    requests ConnectionError) when many paginated requests arrive quickly. That
    is transient and retryable -- distinct from a regional 451 geo-block, which
    fails fast upstream (DEC-2026-06-01-003). Without this, a single reset during
    a multi-symbol regeneration aborts the whole run.

    Args:
        fetcher: The market-data fetcher.
        symbol: Trading pair.
        timeframe: Candle timeframe (e.g. ``1h``, ``1d``).
        start_date: Inclusive UTC start.
        end_date: Inclusive UTC end.
        retries: Max attempts before giving up.

    Returns:
        The fetched ``OHLCVSeries``.

    Raises:
        Exception: The last transient error if all attempts fail.
    """
    import requests.exceptions as rex

    transient = (
        rex.ConnectionError, rex.Timeout, rex.ChunkedEncodingError,
        ConnectionError, OSError,
    )
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return await fetcher.fetch_historical_ohlcv(
                symbol=symbol, timeframe=timeframe,
                start_date=start_date, end_date=end_date,
            )
        except transient as exc:
            last_exc = exc
            wait = 2.0 * attempt
            logger.warning(
                "regime_dsr_fetch_retry",
                symbol=symbol, timeframe=timeframe, attempt=attempt,
                error=str(exc), wait_s=wait,
            )
            await asyncio.sleep(wait)
    assert last_exc is not None
    raise last_exc


async def regenerate_pooled_trades(
    label: str,
    *,
    end_date: datetime,
    lookback_days: int,
    market: str = "spot",
    testnet: bool = False,
    use_cache: bool = True,
) -> RegeneratedTrades:
    """Re-run the backtest for ``label`` and pool its per-trade series.

    Fetches 1H OHLCV per symbol (with warmup) and BTC daily (the regime anchor,
    with EMA(200) warmup), runs ``BacktestEngine`` per symbol, and pools the
    serialized trade logs. Network-bound (Binance); never writes to the network.

    Performance (DEC-2026-06-04-015): window-safe templates use the engine's
    ``lookback_window`` optimization (~6x faster, trade-identical -- proven by
    tests/unit/backtest/test_window_equivalence.py). Results are cached on disk so
    re-runs skip the fetch+backtest entirely.

    Args:
        label: Research label (must be in ``RESEARCH_LABEL_TO_TEMPLATE``).
        end_date: Timezone-aware UTC end of the backtest window.
        lookback_days: Length of the analysis window in days.
        market: ``"spot"`` or ``"futures"``.
        testnet: Whether to use the Binance testnet client.
        use_cache: If True, read/write the on-disk regeneration cache.

    Returns:
        A ``RegeneratedTrades`` with pooled trades and the BTC daily anchor.

    Raises:
        KeyError: If ``label`` is unknown.
    """
    template = RESEARCH_LABEL_TO_TEMPLATE[label]
    symbols = list(STRATEGY_SYMBOLS[template])
    params = dict(STRATEGY_PARAMS[template])
    # Only PROVEN-safe templates use the windowing optimization; others run the
    # full history (conservative -- correctness over speed).
    window = DEFAULT_LOOKBACK_WINDOW if template in WINDOW_SAFE_TEMPLATES else None

    cache_path = (
        CACHE_DIR
        / f"{label}_{end_date.strftime('%Y%m%d')}_{lookback_days}d_{market}_w{window}.pkl"
    )
    if use_cache and cache_path.exists():
        with cache_path.open("rb") as fh:
            cached: RegeneratedTrades = pickle.load(fh)
        logger.info(
            "regime_dsr_cache_hit",
            label=label, path=str(cache_path), trades=len(cached.trades),
        )
        return cached

    client = BinanceClient(testnet=testnet)
    fetcher = MarketDataFetcher(client)
    engine = BacktestEngine(SignalGeneratorFactory())
    config = _backtest_config(market)

    # 1H needs ~45d warmup; BTC daily regime needs EMA(200) ~ 300d warmup so the
    # earliest trades are tagged from a warmed-up daily classifier.
    hourly_start = end_date - timedelta(days=lookback_days + 45)
    daily_start = end_date - timedelta(days=lookback_days + 300)

    btc_daily = await _fetch_with_retry(
        fetcher, symbol="BTCUSDT", timeframe="1d",
        start_date=daily_start, end_date=end_date,
    )

    pooled: list[dict[str, Any]] = []
    for symbol in symbols:
        series = await _fetch_with_retry(
            fetcher, symbol=symbol, timeframe="1h",
            start_date=hourly_start, end_date=end_date,
        )
        strategy = SimpleNamespace(
            id=f"regime_dsr_{label}_{symbol}",
            name=f"{label} {symbol}",
            template_id=template,
            parameters=params,
        )
        result = engine.run_backtest(
            strategy=strategy, series=series, config=config, lookback_window=window,
        )
        pooled.extend(t.to_dict() for t in result.trade_log)
        logger.info(
            "regime_dsr_symbol_backtested",
            label=label, symbol=symbol, trades=len(result.trade_log),
            lookback_window=window,
        )

    regen = RegeneratedTrades(
        label=label, template=template, symbols=symbols,
        trades=pooled, btc_daily=btc_daily,
    )
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with cache_path.open("wb") as fh:
            pickle.dump(regen, fh)
        logger.info("regime_dsr_cache_write", label=label, path=str(cache_path))
    return regen


def compute_regime_coverage(
    strategy_id: str,
    status: StrategyStatus,
    tagged: list[Any],
    *,
    run_id: str,
    run_date: str,
    cost_model: CostModel,
    base_k: EffectiveKEstimate,
    variance_sr_point: float,
    min_bucket_n: int = MIN_BUCKET_N,
) -> RegimeAnalysis:
    """Compute pooled + per-coarse-regime DSR for one strategy (pure; no network).

    Reuses ``analyze_strategy`` for both the pooled series and each regime bucket,
    so the cost model, base/conservative split, K + variance_sr sweeps, and the
    INSUFFICIENT_DATA guard are identical to the pooled retrospective. The regime
    buckets use ``regime_conditional_k`` (guard #2) so the per-bucket K penalizes
    cross-regime selection.

    Args:
        strategy_id: Research label.
        status: Lifecycle status.
        tagged: ``TaggedTrade`` list (trades tagged with entry regime).
        run_id: Idempotency key for this regime-DSR run.
        run_date: ``YYYY-MM-DD`` run date.
        cost_model: Cost model to apply.
        base_k: Portfolio effective-K estimate (pre regime multiplier).
        variance_sr_point: Cross-sectional Sharpe-variance point estimate.
        min_bucket_n: Per-bucket N below which a cell is descriptive, not gating.

    Returns:
        A ``RegimeAnalysis`` with the coverage run, pooled result, and per-bucket
        results.
    """
    all_trades = [tt.trade for tt in tagged]
    pooled = rd.analyze_strategy(
        strategy_id, status, all_trades,
        k_estimate=base_k, variance_sr_point=variance_sr_point,
        cost_model=cost_model, run_id=run_id, run_date=run_date,
    )

    coarse = bucket_by_coarse(tagged)
    # Guard #2: number of regime buckets actually evaluated counts as trials.
    n_buckets = max(1, len(coarse))
    regime_k = regime_conditional_k(base_k, n_buckets)

    per_bucket_results: dict[str, rd.AnalysisResult] = {}
    cells: list[RegimeDSRResult] = []
    for bucket in COARSE_BUCKETS:
        bucket_trades = coarse.get(bucket, [])
        if not bucket_trades:
            continue  # strategy never traded in this regime -> coverage gap
        res = rd.analyze_strategy(
            f"{strategy_id}::{bucket}", status, bucket_trades,
            k_estimate=regime_k, variance_sr_point=variance_sr_point,
            cost_model=cost_model, run_id=run_id, run_date=run_date,
        )
        per_bucket_results[bucket] = res
        e = res.validation_entry
        is_descriptive = (
            res.final_tier == Tier.INSUFFICIENT_DATA
            or res.n_trades_analyzed < min_bucket_n
        )
        note = "screen-only; not a deployment gate"
        if is_descriptive:
            note = (
                f"DESCRIPTIVE: N={res.n_trades_analyzed} < {min_bucket_n} "
                f"(or insufficient) -- not gating (guard #4)"
            )
        cells.append(
            RegimeDSRResult(
                regime=bucket,
                bucket_kind="coarse",
                n_trades=res.n_trades_analyzed,
                pf_adjusted=e.pf_adjusted,
                sharpe_adjusted=e.sharpe_adjusted,
                base_dsr_p_value=e.base_dsr_p_value,
                conservative_dsr_p_value=e.conservative_dsr_p_value,
                tier=res.final_tier,
                is_descriptive=is_descriptive,
                effective_k=regime_k.gating_k,
                notes=note,
            )
        )

    # Fine SubRegime breakdown -- DIAGNOSTIC ONLY (always descriptive, never
    # gating). The coarse buckets merge trending+choppy within a direction, which
    # MASKS the documented choppy-specific edge of several KEEP strategies (their
    # choppy_bear/choppy_bull edge is hidden inside the bear/bull cells alongside
    # trending losses). These fine cells expose pf_adjusted / sharpe_adjusted per
    # SubRegime -- both K-INDEPENDENT -- so "did the choppy_bear edge survive
    # honest costs" is directly visible even where per-bucket N is thin.
    for sub, sub_trades in bucket_by_sub_regime(tagged).items():
        res = rd.analyze_strategy(
            f"{strategy_id}::{sub.value}", status, sub_trades,
            k_estimate=regime_k, variance_sr_point=variance_sr_point,
            cost_model=cost_model, run_id=run_id, run_date=run_date,
        )
        e = res.validation_entry
        cells.append(
            RegimeDSRResult(
                regime=sub.value,
                bucket_kind="sub_regime",
                n_trades=res.n_trades_analyzed,
                pf_adjusted=e.pf_adjusted,
                sharpe_adjusted=e.sharpe_adjusted,
                base_dsr_p_value=e.base_dsr_p_value,
                conservative_dsr_p_value=e.conservative_dsr_p_value,
                tier=res.final_tier,
                is_descriptive=True,  # fine cells never gate (guard #4)
                effective_k=regime_k.gating_k,
                notes="DESCRIPTIVE fine SubRegime -- diagnostic only, never gating",
            )
        )

    coverage_run = RegimeCoverageRun(
        run_id=run_id,
        run_date=run_date,
        cost_model_version=cost_model.version,
        data_source="regenerated_backtest",
        is_screen_only=True,
        pooled_tier=pooled.final_tier,
        pooled_dsr_p_value=pooled.validation_entry.conservative_dsr_p_value,
        per_regime=cells,
        notes=(
            "Regime-conditional backtest DSR SCREEN (DEC-2026-06-04-014). "
            "NOT a deployment gate; paper/live validation still required. "
            f"K x{n_buckets} regime buckets."
        ),
    )
    return RegimeAnalysis(
        coverage_run=coverage_run,
        pooled_result=pooled,
        per_bucket_results=per_bucket_results,
    )


def write_regime_coverage(
    coverage_run: RegimeCoverageRun,
    strategy_id: str,
    status: StrategyStatus,
    symbols: list[str],
) -> bool:
    """Append a regime-coverage run to a biography idempotently and persist it.

    Writes ONLY ``regime_coverage`` -- never ``current_classification`` (guard #1:
    the screen does not deploy or re-tier). Reuses the retrospective's biography
    path + load helpers (single source of truth).

    Args:
        coverage_run: The coverage run to record.
        strategy_id: Research label.
        status: Lifecycle status.
        symbols: Symbols to seed a new biography with.

    Returns:
        True if written; False if skipped (this ``run_id`` already recorded).
    """
    biography: StrategyBiography = rd.load_or_create_biography(
        strategy_id, status, symbols
    )
    if biography.has_regime_coverage(coverage_run.run_id):
        logger.info(
            "regime_coverage_skip_idempotent",
            strategy_id=strategy_id, run_id=coverage_run.run_id,
        )
        return False

    biography.regime_coverage.append(coverage_run)
    path = rd._biography_path(strategy_id, biography.status)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = biography.model_dump(mode="json")
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=False),
        encoding="utf-8",
    )
    logger.info(
        "regime_coverage_written",
        strategy_id=strategy_id, path=str(path),
        pooled_tier=rd._tier_label(coverage_run.pooled_tier),
        buckets=len(coverage_run.per_regime),
    )
    return True


def render_coverage_matrix_md(
    analyses: dict[str, RegimeAnalysis], run_date: str
) -> str:
    """Render the strategy x regime coverage matrix as markdown.

    Args:
        analyses: Mapping of strategy label -> ``RegimeAnalysis``.
        run_date: ``YYYY-MM-DD`` run date.

    Returns:
        A markdown document with the coverage matrix and a coverage-gap summary.
    """
    lines = [
        "# Regime-Conditional Backtest DSR -- Coverage Matrix",
        "",
        f"**Date:** {run_date}",
        "**Source:** regenerated backtest trades (DEC-2026-06-04-014)",
        "**Nature:** SCREEN, not a deployment gate -- paper/live validation still "
        "required (guard #1). DSR is necessary, not sufficient (guard #5).",
        "",
        "Cells show the per-regime final tier and N. `[desc]` marks a DESCRIPTIVE "
        f"cell (N < {MIN_BUCKET_N} or insufficient) that does NOT gate (guard #4). "
        "A blank cell means the strategy never traded in that regime (coverage gap).",
        "",
        "| Strategy | Pooled | " + " | ".join(b.upper() for b in COARSE_BUCKETS) + " |",
        "|----------|--------|" + "|".join(["------"] * len(COARSE_BUCKETS)) + "|",
    ]

    def _cell(analysis: RegimeAnalysis, bucket: str) -> str:
        for c in analysis.coverage_run.per_regime:
            if c.regime == bucket:
                tag = rd._tier_label(c.tier)
                mark = " [desc]" if c.is_descriptive else ""
                return f"{tag} (N={c.n_trades}{mark})"
        return "--"

    for label, analysis in analyses.items():
        pooled = (
            f"{rd._tier_label(analysis.coverage_run.pooled_tier)} "
            f"(N={analysis.pooled_result.n_trades_analyzed})"
        )
        row = [label, pooled] + [_cell(analysis, b) for b in COARSE_BUCKETS]
        lines.append("| " + " | ".join(row) + " |")

    # Coverage-gap summary: which regimes have NO gating (non-descriptive) Tier A/B.
    lines += ["", "## Coverage Gaps (non-descriptive Tier A/B by regime)", ""]
    for bucket in COARSE_BUCKETS:
        covered = [
            label for label, a in analyses.items()
            for c in a.coverage_run.per_regime
            if c.regime == bucket
            and not c.is_descriptive
            and c.tier in (Tier.TIER_A, Tier.TIER_B)
        ]
        if covered:
            lines.append(f"- **{bucket.upper()}**: covered by {', '.join(covered)}")
        else:
            lines.append(f"- **{bucket.upper()}**: NO gating Tier A/B coverage (GAP)")

    # Fine SubRegime breakdown -- the diagnostic the coarse table cannot show.
    # PF(adj) and Sharpe(adj) are K-INDEPENDENT, so they answer "does the
    # documented choppy edge survive honest costs" regardless of the gate.
    lines += [
        "",
        "## Fine SubRegime Breakdown (DESCRIPTIVE -- never gating)",
        "",
        "The coarse buckets merge trending+choppy within a direction, masking "
        "choppy-specific edge. These per-SubRegime cells expose where edge "
        "actually concentrates. **PF(adj) and Sharpe(adj) are K-independent**: "
        "PF(adj) > 1 with a positive Sharpe is a real (if thin) edge worth "
        "paper-trading even when the cell does not gate.",
        "",
        "| Strategy | SubRegime | N | PF(adj) | Sharpe(adj) | base DSR p |",
        "|----------|-----------|---|---------|-------------|------------|",
    ]
    for label, analysis in analyses.items():
        fine = [c for c in analysis.coverage_run.per_regime
                if c.bucket_kind == "sub_regime"]
        for c in sorted(fine, key=lambda x: x.regime):
            flag = " *" if (c.pf_adjusted > 1.0 and c.sharpe_adjusted > 0.0) else ""
            lines.append(
                f"| {label} | {c.regime}{flag} | {c.n_trades} | "
                f"{c.pf_adjusted:.2f} | {c.sharpe_adjusted:+.3f} | "
                f"{c.base_dsr_p_value:.3f} |"
            )
    lines += [
        "",
        "`*` = PF(adj) > 1 and Sharpe(adj) > 0 (a positive cost-adjusted edge in "
        "that SubRegime -- the cells worth paper-trading first).",
    ]

    lines += [
        "",
        "## Honest Caveats",
        "",
        "- This is a backtest SCREEN. Backtest edge degrades live; a pass means "
        "the pair is WORTH paper-trading, not that it will be profitable live.",
        "- Costs are v0 unverified (incremental pad over already-net returns).",
        "- Effective K includes the regime-bucket multiplier (guard #2), so "
        "per-bucket verdicts are deliberately harder to pass than the pooled one.",
        "",
    ]
    return "\n".join(lines)


def render_coverage_json(
    analyses: dict[str, RegimeAnalysis], run_date: str, cost_model_version: str
) -> dict[str, Any]:
    """Render the coverage matrix as a JSON-serializable dict.

    Args:
        analyses: Mapping of strategy label -> ``RegimeAnalysis``.
        run_date: ``YYYY-MM-DD`` run date.
        cost_model_version: Cost-model version tag.

    Returns:
        A JSON-serializable dict of the full coverage matrix.
    """
    out: dict[str, Any] = {
        "run_date": run_date,
        "cost_model_version": cost_model_version,
        "is_screen_only": True,
        "strategies": {},
    }
    for label, a in analyses.items():
        out["strategies"][label] = {
            "pooled_tier": rd._tier_label(a.coverage_run.pooled_tier),
            "pooled_dsr_p_value": a.coverage_run.pooled_dsr_p_value,
            "pooled_n": a.pooled_result.n_trades_analyzed,
            "per_regime": [
                {
                    "regime": c.regime,
                    "bucket_kind": c.bucket_kind,
                    "tier": rd._tier_label(c.tier),
                    "n_trades": c.n_trades,
                    "base_dsr_p_value": c.base_dsr_p_value,
                    "conservative_dsr_p_value": c.conservative_dsr_p_value,
                    "pf_adjusted": c.pf_adjusted,
                    "sharpe_adjusted": c.sharpe_adjusted,
                    "is_descriptive": c.is_descriptive,
                    "effective_k": c.effective_k,
                }
                for c in a.coverage_run.per_regime
            ],
        }
    return out


async def run_regime_dsr(
    labels: list[str],
    *,
    end_date: datetime,
    lookback_days: int,
    market_override: str | None = None,
    output_dir: Path,
    cost_model: CostModel | None = None,
    use_cache: bool = True,
) -> dict[str, RegimeAnalysis]:
    """Regenerate, tag, and screen all ``labels``; write biographies + reports.

    Args:
        labels: Research labels to screen.
        end_date: Timezone-aware UTC backtest window end.
        lookback_days: Analysis window length in days.
        market_override: Explicit ``"spot"``/``"futures"`` for ALL labels, or
            None to use the per-strategy default (``market_for_label``): bear
            strategies in futures, others in spot.
        output_dir: Directory for the derived coverage matrix + JSON.
        cost_model: Cost model (defaults to v0 unverified).

    Returns:
        Mapping of label -> ``RegimeAnalysis``.
    """
    model = cost_model or CostModel.v0_unverified()
    run_date = end_date.date().isoformat()
    run_id = f"regime_dsr_run_{end_date.strftime('%Y%m%d')}"
    base_k = rd.build_effective_k()

    # 1) Regenerate + causally tag every strategy (network).
    regenerated: dict[str, RegeneratedTrades] = {}
    tagged_by_label: dict[str, list[Any]] = {}
    for label in labels:
        market = market_for_label(label, market_override)
        logger.info("regime_dsr_market_selected", label=label, market=market)
        regen = await regenerate_pooled_trades(
            label, end_date=end_date, lookback_days=lookback_days, market=market,
            use_cache=use_cache,
        )
        # Guard #3: verify the regime labelling is causal on THIS BTC-daily series
        # before trusting any verdict derived from it.
        if not is_labeling_causal(regen.btc_daily):
            raise RuntimeError(
                f"Regime labelling failed the causal leakage check for {label}'s "
                f"BTC-daily anchor. Refusing to produce regime verdicts."
            )
        timeline = build_regime_timeline(regen.btc_daily)
        regenerated[label] = regen
        tagged_by_label[label] = tag_trades(regen.trades, timeline)
        logger.info(
            "regime_dsr_regenerated",
            label=label, trades=len(regen.trades),
        )

    # 2) variance_sr from the cross-section of pooled conservative Sharpes
    #    (same approach as the pooled retrospective; swept downstream).
    pooled_sharpes: list[float] = []
    for label in labels:
        status = _STATUS_BY_LABEL.get(label, StrategyStatus.ACTIVE_RESEARCH)
        probe = rd.analyze_strategy(
            label, status, [tt.trade for tt in tagged_by_label[label]],
            k_estimate=base_k, variance_sr_point=0.05,  # placeholder; only Sharpe used
            cost_model=model, run_id=run_id, run_date=run_date,
        )
        pooled_sharpes.append(probe.validation_entry.sharpe_adjusted)
    variance_sr_point = variance_sr_point_estimate(pooled_sharpes)
    logger.info(
        "regime_dsr_variance_sr_estimated",
        variance_sr_point=variance_sr_point, n_strategies=len(labels),
    )

    # 3) Per-strategy regime coverage + biography writes.
    analyses: dict[str, RegimeAnalysis] = {}
    for label in labels:
        status = _STATUS_BY_LABEL.get(label, StrategyStatus.ACTIVE_RESEARCH)
        analysis = compute_regime_coverage(
            label, status, tagged_by_label[label],
            run_id=run_id, run_date=run_date, cost_model=model,
            base_k=base_k, variance_sr_point=variance_sr_point,
        )
        analyses[label] = analysis
        write_regime_coverage(
            analysis.coverage_run, label, status, regenerated[label].symbols
        )

    # 4) Derived reports.
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"COVERAGE_MATRIX_{run_date}.md").write_text(
        render_coverage_matrix_md(analyses, run_date), encoding="utf-8"
    )
    import json
    (output_dir / f"regime_coverage_{run_date}.json").write_text(
        json.dumps(render_coverage_json(analyses, run_date, model.version), indent=2),
        encoding="utf-8",
    )
    logger.info("regime_dsr_reports_written", output_dir=str(output_dir))
    return analyses


def _use_os_trust_store() -> None:
    """Verify TLS against the OS trust store (handles proxy/AV TLS inspection).

    Some environments run a TLS-inspecting middlebox (corporate proxy, VPN, or
    antivirus HTTPS scanning) that re-signs certificates with a private root
    present only in the OS trust store, not in certifi's public bundle. There,
    ``requests`` (which uses certifi) cannot verify Binance's certificate.
    ``truststore`` routes verification through the OS store -- the trust anchors
    the machine is ALREADY configured to trust. This does NOT disable
    verification; it only changes the trust-anchor source. No-op when truststore
    is unavailable (non-inspected environments verify via certifi as usual).
    """
    try:
        import truststore

        truststore.inject_into_ssl()
        logger.info("os_trust_store_injected")
    except ImportError:
        logger.info("truststore_unavailable_using_certifi")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Argument vector (defaults to ``sys.argv``).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Regime-conditional backtest DSR screen (DEC-2026-06-04-014)."
    )
    parser.add_argument(
        "--strategy", action="append", default=None,
        help="Research label to screen (repeatable). Default: all 11.",
    )
    parser.add_argument(
        "--control-only", action="store_true",
        help="Screen only BTF (the known-bad full-history calibration control).",
    )
    parser.add_argument("--lookback-days", type=int, default=540,
                        help="Backtest window length in days (default 540).")
    parser.add_argument("--end-date", type=str, default=None,
                        help="Window end YYYY-MM-DD (default: today UTC).")
    parser.add_argument("--market", choices=["spot", "futures"], default=None,
                        help="Force execution model for ALL strategies. Default "
                             "(unset): per-strategy -- bear strategies (BTF/CMF) "
                             "in futures so shorts can fire, others in spot.")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR))
    parser.add_argument("--skip-dsr-gate", action="store_true",
                        help="Skip the DSR math verification pre-flight (NOT recommended).")
    parser.add_argument("--no-cache", action="store_true",
                        help="Ignore the on-disk regeneration cache (force fresh fetch+backtest).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Argument vector (defaults to ``sys.argv``).

    Returns:
        Process exit code (0 on success).
    """
    from src.utils.logging import setup_logging

    setup_logging(level="INFO")
    # Verify Binance TLS against the OS trust store where a proxy/AV re-signs
    # certs (DEC-2026-06-04-014 run note). Secure: changes the trust anchor
    # source, never disables verification.
    _use_os_trust_store()
    args = parse_args(argv)

    # Pre-flight: refuse to run on real data unless the DSR math is verified
    # (same gate as the retrospective -- a miscalibrated instrument is worse
    # than none).
    if not args.skip_dsr_gate:
        rd.assert_dsr_math_verified()

    if args.control_only:
        labels = ["BTF"]
    elif args.strategy:
        labels = args.strategy
    else:
        labels = list(RESEARCH_LABEL_TO_TEMPLATE.keys())

    if args.end_date:
        end_date = datetime.fromisoformat(args.end_date).replace(tzinfo=timezone.utc)
    else:
        end_date = datetime.now(timezone.utc)

    logger.info(
        "regime_dsr_start",
        labels=labels, lookback_days=args.lookback_days,
        market=args.market, end_date=end_date.isoformat(),
    )
    asyncio.run(
        run_regime_dsr(
            labels,
            end_date=end_date,
            lookback_days=args.lookback_days,
            market_override=args.market,
            output_dir=Path(args.output_dir),
            use_cache=not args.no_cache,
        )
    )
    logger.info("regime_dsr_complete", labels=labels)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
