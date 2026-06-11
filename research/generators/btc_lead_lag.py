"""BTC-led lead-lag generator for mid-cap alts (H-2026-06-011).

Research-stage generator for the uncovered TRENDING_BULL / diffusion regime.
Long-only, spot (deployable if it passes). Trades a mid-cap ALT: when BTC has
made a decisive recent up-move AND the alt has NOT yet caught up, goes LONG the
alt to capture the catch-up (information diffusion from BTC to under-arbitraged
alts).

Mechanism (H-2026-06-011): BTC is the price-discovery hub; new information hits
BTC first and diffuses to alts with a lag. On UNDER-ARBITRAGED mid-caps the lag
survives (thin arb capital). The counterparty is slow alt traders who react to
BTC-led moves late. Distinct from H-008 cross-sectional RANK -- this is
BTC-conditioned DIRECTIONAL diffusion.

BTC reference via a precomputed series. The per-symbol workers are isolated, so
BTC's trailing-return ("thrust") is precomputed in the PARENT
(research/data/btc_reference.py) and cached; this generator reads
``BtcThrustSeries.thrust_at(ts)`` (causal). If the cache is absent it fails closed.

ENTRY (LONG the alt) requires ALL of:
    1. BTC thrust at ts >= ``btc_thrust_threshold_pct`` / 100 (BTC up-move).
    2. The alt's OWN trailing return over the same window is BELOW BTC's thrust
       (the alt is lagging -> room to catch up).
Exit is a TRAILING ATR stop (take_profit None). The trader skips a same-direction
signal while already long, so re-emitting while still lagging is a no-op.

One-way dependency: research/ imports src/, never the reverse. Loaded via the
factory hook (DEC-2026-06-04-019). NEVER added to src/ before DSR validation.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from research.data import btc_reference
from research.data.btc_reference import BtcThrustSeries
from src.core.exceptions import SignalGenerationError
from src.core.indicators import ATR
from src.core.strategy.signals import SignalGenerator, TradingSignal
from src.data.market_data import OHLCVSeries
from src.data.models.signal import SignalDirection
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Per-process memo of the BTC thrust series (loaded once per process, incl. workers).
_BTC_THRUST: list[BtcThrustSeries | None] = []


def _btc_thrust() -> BtcThrustSeries | None:
    """Return the cached BTC thrust series (memoized, no recompute)."""
    if not _BTC_THRUST:
        loaded = btc_reference.load_cached()
        _BTC_THRUST.append(loaded)
        if loaded is None:
            logger.warning("btc_thrust_cache_missing")
    return _BTC_THRUST[0]


class BtcLeadLagGenerator(SignalGenerator):
    """Long the mid-cap alt when BTC has thrust up and the alt is still lagging.

    Required parameters:
        btc_thrust_lookback_bars, btc_thrust_threshold_pct, alt_lag_window_bars,
        atr_period, atr_stop_multiplier
    """

    @property
    def template_id(self) -> str:
        """Return the template ID this generator handles."""
        return "btc_lead_lag"

    @property
    def min_bars_required(self) -> int:
        """Return minimum bars: the alt-return lookback + ATR warmup + buffer."""
        return 60

    def generate(
        self,
        series: OHLCVSeries,
        params: dict[str, Any],
        symbol: str,
    ) -> TradingSignal | None:
        """Evaluate the BTC-led lead-lag LONG entry conditions.

        Args:
            series: Causal OHLCV window ending at the alt's decision bar.
            params: Validated strategy parameters.
            symbol: The alt trading-pair symbol.

        Returns:
            A LONG ``TradingSignal`` if all conditions hold, else None.

        Raises:
            SignalGenerationError: If indicator calculation fails.
        """
        if not self.validate_series(series, self.min_bars_required):
            return None

        try:
            lookback: int = int(params["btc_thrust_lookback_bars"])
            threshold: float = float(params["btc_thrust_threshold_pct"]) / 100.0
            atr_period: int = int(params["atr_period"])
            atr_stop_mult: float = float(params["atr_stop_multiplier"])

            # --- BTC thrust gate (causal): fail closed if unknown ---
            thrust_series = _btc_thrust()
            if thrust_series is None:
                return None
            current_ts = series[-1].timestamp
            btc_thrust = thrust_series.thrust_at(current_ts)
            if btc_thrust is None or btc_thrust < threshold:
                return None

            # --- Alt lagging: its own trailing return is below BTC's thrust ---
            closes = series.closes
            if len(closes) < lookback + 1 or closes[-1 - lookback] <= 0:
                return None
            alt_return = float(closes[-1]) / float(closes[-1 - lookback]) - 1.0
            if alt_return >= btc_thrust:
                return None   # alt has already caught up -> no diffusion edge

            # --- Risk framing via ATR (LONG: trailing stop below, no TP) ---
            atr_result = ATR(period=atr_period).calculate(series)
            atr_vals = atr_result.values[~np.isnan(atr_result.values)]
            if len(atr_vals) < 1:
                return None
            atr_curr = float(atr_vals[-1])
            if atr_curr <= 0:
                return None

            price = float(closes[-1])
            stop_loss = max(price - atr_stop_mult * atr_curr, price * 0.001)

            indicators = {
                "btc_thrust": btc_thrust,
                "alt_return": alt_return,
                "lag_gap": btc_thrust - alt_return,
                "atr": atr_curr,
            }
            # Strength scales with the lag gap (more catch-up room = stronger).
            strength = max(0.4, min(1.0, 0.4 + 0.6 * min((btc_thrust - alt_return) / threshold, 1.0)))

            return TradingSignal(
                direction=SignalDirection.LONG,
                symbol=symbol,
                price=price,
                strength=strength,
                stop_loss=stop_loss,
                take_profit=None,   # trailing stop -> ride the catch-up
                indicators=indicators,
                metadata={"trigger": "btc_lead_lag_long"},
            )

        except (ValueError, KeyError, IndexError) as exc:
            raise SignalGenerationError(
                template_id=self.template_id,
                reason=str(exc),
            ) from exc
