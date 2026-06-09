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
    """

    research_label: str
    template_id: str
    generator_class: type[SignalGenerator]
    params: dict[str, Any]
    symbols: list[str]
    market: str
    needs_funding: bool = False


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
