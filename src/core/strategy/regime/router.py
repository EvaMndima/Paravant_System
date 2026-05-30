"""Regime-driven engine lifecycle management.

Decision: DEC-2026-05-04-001 - Dual-EMA composite regime detection
Decision: DEC-2026-05-04-002 - 2-consecutive-close confirmation rule
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.core.strategy.paper.engine import PaperTradingEngine
from src.core.strategy.regime.detector import RegimeDetector, RegimeState
from src.core.strategy.regime.historical_classifier import SubRegime
from src.core.strategy.regime.sub_regime_detector import SubRegimeDetector
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.core.alerting.channels.telegram import TelegramChannel
    from src.data.store import DataStore

logger = get_logger(__name__)


class RegimeRouter:
    """Manages PaperTradingEngine start/stop based on regime detection.

    Decision: DEC-2026-05-04-001 - Dual-EMA composite regime detection
    Decision: DEC-2026-05-04-002 - 2-consecutive-close confirmation rule

    Runs as an async background task alongside the engine tasks. Every
    check_interval seconds, re-evaluates the regime via RegimeDetector.
    On a confirmed regime flip, stops regime-inappropriate engines and
    starts regime-appropriate ones.

    Routing logic (DEC-2026-05-28-003 — SubRegime-aware routing):

    Per-strategy config entries may now declare BOTH of these fields:
        "regime"      (legacy, coarse): "bull" / "bear" / "all"
        "regime_tags" (preferred, fine): list of SubRegime string values,
            e.g. ["choppy_bear", "trending_bear"]

    Routing precedence:
      1. If `regime_tags` is present AND non-empty AND a SubRegimeDetector
         is configured AND the current SubRegime is in regime_tags →
         activate this strategy.
      2. Else if `regime_tags` is present (non-empty) BUT current SubRegime
         is UNKNOWN or not in the list → do NOT activate (fail-closed).
      3. Else (no regime_tags OR no SubRegimeDetector) fall back to legacy
         coarse `regime` matching against RegimeState.is_bull/is_bear.

    The fail-closed posture in case (2) is intentional: better quiet
    than routing a strategy to a regime it wasn't validated for.

    Args:
        detector: RegimeDetector for BTC daily EMA analysis (coarse regime).
        engine_factory: Callable[[list[str]], list[PaperTradingEngine]] that
            builds engines for the given list of template_ids.
        full_config: Merged STRATEGY_CONFIG + SUSPENDED_STRATEGY_CONFIG with
            "regime" tag on each entry ("bull", "bear", or "all") and
            optionally "regime_tags" list for SubRegime-aware routing.
        stop_event: asyncio.Event signalling global shutdown.
        check_interval: Seconds between regime re-checks (default 86400 = 24h).
        telegram: Optional TelegramChannel for regime flip Telegram alerts.
        store: Optional DataStore for persisting the current regime state.
        sub_detector: Optional SubRegimeDetector for fine-grained routing.
            When provided, strategies with `regime_tags` use SubRegime
            matching. When omitted, only legacy `regime` field is consulted
            (preserves backward compatibility).
    """

    def __init__(
        self,
        detector: RegimeDetector,
        engine_factory: Callable[[list[str]], list[PaperTradingEngine]],
        full_config: dict[str, dict[str, Any]],
        stop_event: asyncio.Event,
        check_interval: int = 86400,
        telegram: TelegramChannel | None = None,
        store: DataStore | None = None,
        sub_detector: SubRegimeDetector | None = None,
    ) -> None:
        self._detector = detector
        self._sub_detector = sub_detector
        self._engine_factory = engine_factory
        self._full_config = full_config
        self._stop_event = stop_event
        self._check_interval = check_interval
        self._telegram = telegram
        self._store = store

        self._current_regime: RegimeState = RegimeState.UNKNOWN
        self._current_sub_regime: SubRegime = SubRegime.UNKNOWN
        self._active_engines: list[PaperTradingEngine] = []
        self._engine_tasks: list[asyncio.Task[None]] = []

    def get_active_engines(self) -> list[PaperTradingEngine]:
        """Return a snapshot of the currently running engines.

        Returns:
            List of PaperTradingEngine instances currently managed by this router.
        """
        return list(self._active_engines)

    def get_current_regime(self) -> RegimeState:
        """Return the last confirmed regime state.

        Returns:
            RegimeState (UNKNOWN if no confirmed state has been applied yet).
        """
        return self._current_regime

    def get_current_sub_regime(self) -> SubRegime:
        """Return the last confirmed SubRegime (UNKNOWN if no detector configured)."""
        return self._current_sub_regime

    async def run(self) -> None:
        """Main loop: detect regime on startup and re-check every check_interval.

        On startup: detect current regime and start appropriate engines.
        On regime flip: stop mismatched engines and start new ones.
        Sends Telegram alert on any confirmed regime change.

        Runs until stop_event is set, then stops all active engines.
        """
        logger.info(
            "regime_router_started",
            check_interval_seconds=self._check_interval,
        )

        # Startup: try confirmed state first, fall back to raw detect if UNKNOWN
        initial_regime = await self._detector.get_confirmed_state()
        if initial_regime == RegimeState.UNKNOWN:
            initial_regime = await self._detector.detect()
            if initial_regime != RegimeState.UNKNOWN:
                logger.warning(
                    "regime_confirmation_fallback_to_raw",
                    raw_regime=initial_regime.value,
                )
            else:
                logger.warning(
                    "regime_unknown_at_startup",
                    note="Starting all-regime strategies only",
                )

        initial_sub_regime = await self._detect_sub_regime_safely()
        await self._apply_regime(initial_regime, initial_sub_regime)

        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=float(self._check_interval)
                )
                break
            except asyncio.TimeoutError:
                pass

            new_regime = await self._detector.get_confirmed_state()
            new_sub_regime = await self._detect_sub_regime_safely()

            if new_regime == RegimeState.UNKNOWN:
                logger.info("regime_check_skipped", reason="unconfirmed")
                continue

            # Re-apply if EITHER coarse regime flipped OR sub_regime changed
            # (since fine-grained tags route on sub_regime).
            regime_changed = (
                self._current_regime == RegimeState.UNKNOWN
                or new_regime.is_bull != self._current_regime.is_bull
            )
            sub_regime_changed = (
                self._sub_detector is not None
                and new_sub_regime != self._current_sub_regime
            )

            if regime_changed or sub_regime_changed:
                old_regime = self._current_regime
                old_sub = self._current_sub_regime
                logger.info(
                    "regime_flip_detected",
                    from_regime=old_regime.value,
                    to_regime=new_regime.value,
                    from_sub=old_sub.value,
                    to_sub=new_sub_regime.value,
                )
                await self._apply_regime(new_regime, new_sub_regime)
                # Single alert per regime-check that consolidates BOTH
                # coarse and sub changes. Fires on either kind of change.
                await self._send_flip_alert(
                    old_regime, new_regime, old_sub, new_sub_regime,
                )
            else:
                logger.info(
                    "regime_unchanged",
                    current_regime=self._current_regime.value,
                    detected_regime=new_regime.value,
                    current_sub=self._current_sub_regime.value,
                )

        logger.info("regime_router_stopping")
        await self._stop_all_engines()

    async def _detect_sub_regime_safely(self) -> SubRegime:
        """Return current confirmed SubRegime, UNKNOWN if no detector or error."""
        if self._sub_detector is None:
            return SubRegime.UNKNOWN
        try:
            return await self._sub_detector.get_confirmed_state()
        except Exception as exc:
            logger.error(
                "sub_regime_detection_failed_in_router",
                error=str(exc),
                exc_info=True,
            )
            return SubRegime.UNKNOWN

    def _get_template_ids_for_regime(
        self,
        regime: RegimeState,
        sub_regime: SubRegime = SubRegime.UNKNOWN,
    ) -> list[str]:
        """Return template IDs that should run for the given regime.

        Per-entry routing precedence:
          1. If entry has non-empty `regime_tags` AND sub_regime is not
             UNKNOWN: include iff sub_regime.value is in regime_tags.
             (Fail-closed: if SubRegime is UNKNOWN, regime_tags-tagged
             strategies are NOT activated — better quiet than wrong.)
          2. Else fall back to legacy coarse `regime` field matching.

        Args:
            regime: The current confirmed coarse regime state.
            sub_regime: The current confirmed SubRegime. Default UNKNOWN
                means SubRegime detection wasn't available or didn't
                confirm; only legacy `regime` matching applies.

        Returns:
            Ordered list of template_id strings matching the regime.
        """
        result: list[str] = []
        for template_id, cfg in self._full_config.items():
            regime_tags = cfg.get("regime_tags")

            # Path 1: fine-grained routing via regime_tags + SubRegime.
            if regime_tags:
                # Skip observe-only strategies (paper-only, never activated
                # by router; explicitly marked for data collection).
                if cfg.get("observe_only"):
                    continue
                # Fail-closed: no confirmed sub_regime → don't activate.
                if sub_regime == SubRegime.UNKNOWN:
                    continue
                if sub_regime.value in regime_tags:
                    result.append(template_id)
                continue

            # Path 2: legacy coarse routing.
            tag = cfg.get("regime", "all")
            if tag == "all":
                result.append(template_id)
            elif tag == "bull" and regime.is_bull:
                result.append(template_id)
            elif tag == "bear" and regime.is_bear:
                result.append(template_id)
        return result

    async def _apply_regime(
        self,
        regime: RegimeState,
        sub_regime: SubRegime = SubRegime.UNKNOWN,
    ) -> None:
        """Stop all current engines and start engines appropriate for regime.

        Args:
            regime: The newly confirmed coarse regime state to apply.
            sub_regime: The newly confirmed SubRegime. Default UNKNOWN
                means SubRegime routing is disabled; only legacy `regime`
                matching applies. Strategies with `regime_tags` will NOT
                activate when sub_regime is UNKNOWN (fail-closed).
        """
        logger.info(
            "regime_applying",
            regime=regime.value,
            sub_regime=sub_regime.value,
        )

        await self._stop_all_engines()

        template_ids = self._get_template_ids_for_regime(regime, sub_regime)

        if not template_ids:
            logger.warning(
                "regime_no_matching_templates",
                regime=regime.value,
                sub_regime=sub_regime.value,
            )
            self._current_regime = regime
            self._current_sub_regime = sub_regime
            self._persist_regime_state(regime)
            return

        engines = self._engine_factory(template_ids)
        self._active_engines = engines
        self._engine_tasks = [
            asyncio.create_task(engine.start()) for engine in engines
        ]
        self._current_regime = regime
        self._current_sub_regime = sub_regime
        self._persist_regime_state(regime)

        logger.info(
            "regime_engines_started",
            regime=regime.value,
            sub_regime=sub_regime.value,
            template_ids=template_ids,
            engine_count=len(engines),
        )

    def _persist_regime_state(self, regime: RegimeState) -> None:
        """Write current regime into SystemState.circuit_breakers["auto_regime"].

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

        The API server reads this key to expose the current regime without
        requiring in-process access to the router. Pattern mirrors manual
        regime tagging in src.core.strategy.regime.manual.

        Args:
            regime: The regime state to persist.
        """
        if self._store is None:
            return

        try:
            state = self._store.get_system_state()
            cb = dict(state.circuit_breakers)
            cb["auto_regime"] = {
                "state": regime.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._store.update_system_state(circuit_breakers=cb)
            logger.info("regime_state_persisted", regime=regime.value)
        except Exception as exc:
            logger.error(
                "regime_state_persist_failed",
                regime=regime.value,
                error=str(exc),
            )

    async def _stop_all_engines(self) -> None:
        """Gracefully stop all currently active engines and await their tasks."""
        for engine in self._active_engines:
            if engine.is_running:
                try:
                    await engine.stop()
                except Exception as exc:
                    logger.error(
                        "regime_engine_stop_failed",
                        engine_id=engine.strategy_id,
                        error=str(exc),
                    )

        for task in self._engine_tasks:
            if not task.done():
                try:
                    await asyncio.wait_for(task, timeout=30.0)
                except (asyncio.TimeoutError, Exception):
                    task.cancel()

        self._active_engines = []
        self._engine_tasks = []

    async def _send_flip_alert(
        self,
        old_regime: RegimeState,
        new_regime: RegimeState,
        old_sub: SubRegime = SubRegime.UNKNOWN,
        new_sub: SubRegime = SubRegime.UNKNOWN,
    ) -> None:
        """Send a Telegram notification when regime or sub-regime flips.

        Consolidates both kinds of change into ONE alert per regime-check
        cycle. Distinguishes the alert title based on what actually changed:
          - coarse macro flipped: "REGIME FLIP: {state}"
          - sub-only change: "SUB-REGIME CHANGE: {state}"
        Includes the list of currently-active strategy template_ids so the
        operator can see the routing impact in one place.

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps
        Decision: DEC-2026-05-28-003 - SubRegime-aware routing.

        Args:
            old_regime: The previous coarse regime state.
            new_regime: The newly confirmed coarse regime state.
            old_sub: The previous SubRegime (UNKNOWN if no sub_detector).
            new_sub: The newly confirmed SubRegime (UNKNOWN if no sub_detector).
        """
        if self._telegram is None:
            return

        from src.core.alerting.manager import Alert, AlertLevel

        coarse_changed = new_regime != old_regime
        sub_changed = new_sub != old_sub

        # Title reflects what changed (coarse takes precedence in title)
        if coarse_changed:
            action = (
                "Bear strategies activated"
                if new_regime.is_bear
                else "Bull strategies activated"
            )
            title = f"REGIME FLIP: {new_regime.value.upper()}"
        else:
            # Sub-only change — same macro side, finer regime shifted
            action = f"Sub-regime now {new_sub.value}; routing updated"
            title = f"SUB-REGIME CHANGE: {new_sub.value.upper()}"

        active_ids = [eng.strategy_id for eng in self._active_engines]
        active_str = (
            ", ".join(active_ids) if active_ids else "(none — fail-closed)"
        )

        lines = [
            f"Coarse: {old_regime.value} -> {new_regime.value}"
            if coarse_changed
            else f"Coarse: {new_regime.value} (unchanged)",
        ]
        # Only include sub_regime line when sub_detector is active (else
        # both old_sub and new_sub default to UNKNOWN and would be noise).
        if self._sub_detector is not None:
            lines.append(
                f"Sub:    {old_sub.value} -> {new_sub.value}"
                if sub_changed
                else f"Sub:    {new_sub.value} (unchanged)"
            )
        lines.extend([
            f"Action: {action}",
            f"Active strategies ({len(active_ids)}): {active_str}",
            f"Time:   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        ])

        alert = Alert(
            level=AlertLevel.INFO,
            title=title,
            message="\n".join(lines),
            metadata={
                "from_regime": old_regime.value,
                "to_regime": new_regime.value,
                "from_sub": old_sub.value,
                "to_sub": new_sub.value,
                "active_count": len(active_ids),
            },
        )
        try:
            await self._telegram.send(alert)
        except Exception as exc:
            logger.error(
                "regime_flip_alert_failed",
                from_regime=old_regime.value,
                to_regime=new_regime.value,
                from_sub=old_sub.value,
                to_sub=new_sub.value,
                error=str(exc),
            )
