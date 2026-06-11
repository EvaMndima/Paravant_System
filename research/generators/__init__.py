"""Research-stage strategy generators + the eval registration registry.

Research generators subclass the production ``SignalGenerator`` and are loaded
into the eval (``scripts/regime_dsr.py``) at runtime via the factory's
``register_generator`` hook (DEC-2026-06-04-019). They are NEVER added to
``src/`` before DSR validation + promotion.

One-way dependency: research/ imports src/, never the reverse (PRD 5.2).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from research.generators.funding_confirmed_trend import (
    FundingConfirmedTrendGenerator,
)
from research.generators.funding_extreme_contrarian import (
    FundingExtremeContrarianGenerator,
)
from research.generators.funding_extreme_contrarian_v2 import (
    FundingExtremeContrarianV2Generator,
)
from research.generators.etf_flow_demand import EtfFlowDemandGenerator
from research.generators.cross_sectional_momentum import (
    CrossSectionalMomentumGenerator,
)
from research.generators.btc_lead_lag import BtcLeadLagGenerator
from research.generators.coinbase_premium import CoinbasePremiumGenerator
from src.core.strategy.signals import SignalGenerator

if TYPE_CHECKING:
    from src.core.strategy.factory import SignalGeneratorFactory


@dataclass(frozen=True)
class ResearchSpec:
    """Eval-registration metadata for one research-stage generator.

    Attributes:
        research_label: The ``--strategy`` label used in regime_dsr.
        template_id: The generator's ``template_id`` (factory key).
        generator_class: The ``SignalGenerator`` subclass to register.
        params: Strategy parameters (single pre-registered combo; small K).
        symbols: Backtest universe.
        market: ``"spot"`` or ``"futures"`` execution model for regeneration.
        needs_funding: If True, the parent pre-fetches per-symbol funding into
            the research cache before any backtest worker spawns.
        needs_etf_flow: If True, the parent pre-fetches per-symbol US-spot-ETF
            net-flow history into the research cache before any worker spawns.
        needs_panel: If True, the parent precomputes the cross-symbol
            relative-strength rank panel and caches it per symbol before any
            worker spawns (uses ``rs_lookback_bars`` + ``top_k_fraction`` params).
        needs_btc_ref: If True, the parent fetches BTC 1H and precomputes the BTC
            "thrust" reference series (uses ``btc_thrust_lookback_bars``) so the
            per-alt workers can read BTC's lead causally.
        needs_coinbase: If True, the parent pre-fetches per-symbol Coinbase 1H
            prices into the research cache before any worker spawns.
    """

    research_label: str
    template_id: str
    generator_class: type[SignalGenerator]
    params: dict[str, Any]
    symbols: list[str]
    market: str
    needs_funding: bool = False
    needs_etf_flow: bool = False
    needs_panel: bool = False
    needs_btc_ref: bool = False
    needs_coinbase: bool = False


# Forward hypothesis loop registry. One entry per research-stage hypothesis.
RESEARCH_SPECS: dict[str, ResearchSpec] = {
    "FUNDING_TREND": ResearchSpec(
        research_label="FUNDING_TREND",
        template_id="funding_confirmed_trend",
        generator_class=FundingConfirmedTrendGenerator,
        params={
            "trend_ema_period": 100,
            "fast_ema_period": 20,
            "slope_lookback": 10,
            "funding_positive_threshold": 0.0,
            "funding_extreme_cap_pct_per_8h": 0.05,
            "atr_period": 14,
            "atr_stop_multiplier": 2.0,
            "risk_reward_ratio": 2.5,
        },
        symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
        market="spot",
        needs_funding=True,
    ),
    "FUNDING_CONTRARIAN": ResearchSpec(
        research_label="FUNDING_CONTRARIAN",
        template_id="funding_extreme_contrarian",
        generator_class=FundingExtremeContrarianGenerator,
        params={
            "trend_ema_period": 100,
            "fast_ema_period": 20,
            "funding_extreme_threshold_pct_per_8h": 0.05,
            "atr_period": 14,
            "atr_stop_multiplier": 2.0,
            "risk_reward_ratio": 2.0,
        },
        symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
        market="futures",   # SHORT-side: needs allow_shorts (DEC-2026-05-28-001)
        needs_funding=True,
    ),
    "FUNDING_CONTRARIAN_V2": ResearchSpec(
        research_label="FUNDING_CONTRARIAN_V2",
        template_id="funding_extreme_contrarian_v2",
        generator_class=FundingExtremeContrarianV2Generator,
        params={
            "funding_percentile_lookback_days": 90,
            "funding_percentile_threshold": 90.0,
            "breakout_lookback": 20,
            "atr_period": 14,
            "atr_stop_multiplier": 2.0,
            "risk_reward_ratio": 2.0,
        },
        symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],
        market="futures",   # SHORT-side: needs allow_shorts (DEC-2026-05-28-001)
        needs_funding=True,
    ),
    "ETF_FLOW": ResearchSpec(
        research_label="ETF_FLOW",
        template_id="etf_flow_demand",
        generator_class=EtfFlowDemandGenerator,
        params={
            "flow_lookback_days": 90,
            "flow_percentile_threshold": 80.0,
            "holding_days": 3,
            "atr_period": 14,
            "atr_stop_multiplier": 2.5,
        },
        symbols=["BTCUSDT", "ETHUSDT"],   # only BTC + ETH have US spot ETFs
        market="spot",                    # long-only; deployable
        needs_etf_flow=True,
    ),
    "XS_MOMENTUM": ResearchSpec(
        research_label="XS_MOMENTUM",
        template_id="cross_sectional_momentum",
        generator_class=CrossSectionalMomentumGenerator,
        params={
            "rs_lookback_bars": 168,        # ~7 days on 1H (panel-build)
            "top_k_fraction": 0.25,         # long the top quartile (panel-build)
            "rebalance_bars": 24,           # daily rebalance grid
            "atr_period": 14,
            "atr_stop_multiplier": 2.5,
        },
        symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"],   # narrow universe (caveat)
        market="spot",                    # long-only; deployable
        needs_panel=True,
    ),
    "BTC_LEAD_LAG": ResearchSpec(
        research_label="BTC_LEAD_LAG",
        template_id="btc_lead_lag",
        generator_class=BtcLeadLagGenerator,
        params={
            "btc_thrust_lookback_bars": 24,
            "btc_thrust_threshold_pct": 2.0,
            "alt_lag_window_bars": 6,       # reserved; entries are condition-driven in v1
            "atr_period": 14,
            "atr_stop_multiplier": 2.5,
        },
        symbols=["ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT", "ATOMUSDT"],
        market="spot",                    # long-only; deployable
        needs_btc_ref=True,
    ),
    "COINBASE_PREMIUM": ResearchSpec(
        research_label="COINBASE_PREMIUM",
        template_id="coinbase_premium",
        generator_class=CoinbasePremiumGenerator,
        params={
            "premium_lookback_days": 30,
            "premium_percentile_threshold": 80.0,
            "atr_period": 14,
            "atr_stop_multiplier": 2.5,
        },
        symbols=["BTCUSDT"],              # Coinbase premium is a BTC signal
        market="spot",                    # long-only; deployable
        needs_coinbase=True,
    ),
}


def register_research_generators(factory: "SignalGeneratorFactory") -> None:
    """Register every research generator on ``factory`` (idempotent).

    Called in BOTH the parent and inside spawned backtest workers (each builds a
    fresh ``SignalGeneratorFactory``), so a research ``template_id`` resolves in
    every process -- the spawn-worker requirement noted in DEC-2026-06-04-019.

    Args:
        factory: The signal-generator factory to register onto.
    """
    for spec in RESEARCH_SPECS.values():
        if not factory.has_generator(spec.template_id):
            factory.register_generator(spec.template_id, spec.generator_class)
