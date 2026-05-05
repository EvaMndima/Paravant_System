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
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.core.alerting.channels.telegram import TelegramChannel

logger = get_logger(__name__)


class RegimeRouter:
    """Manages PaperTradingEngine start/stop based on regime detection.

    Decision: DEC-2026-05-04-001 - Dual-EMA composite regime detection
    Decision: DEC-2026-05-04-002 - 2-consecutive-close confirmation rule

    Runs as an async background task alongside the engine tasks. Every
    check_interval seconds, re-evaluates the regime via RegimeDetector.
    On a confirmed regime flip, stops regime-inappropriate engines and
    starts regime-appropriate ones.

    Regime tags in full_config (per entry):
        "bull"  run in STRONG_BULL / PULLBACK_BULL
        "bear"  run in STRONG_BEAR / BOUNCE_BEAR
        "all"   run in any confirmed regime

    Args:
        detector: RegimeDetector for BTC daily EMA analysis.
        engine_factory: Callable[[list[str]], list[PaperTradingEngine]] that
            builds engines for the given list of template_ids.
        full_config: Merged STRATEGY_CONFIG + SUSPENDED_STRATEGY_CONFIG with
            "regime" tag on each entry ("bull", "bear", or "all").
        stop_event: asyncio.Event signalling global shutdown.
        check_interval: Seconds between regime re-checks (default 86400 = 24h).
        telegram: Optional TelegramChannel for regime flip Telegram alerts.
    """

    def __init__(
        self,
        detector: RegimeDetector,
        engine_factory: Callable[[list[str]], list[PaperTradingEngine]],
        full_config: dict[str, dict[str, Any]],
        stop_event: asyncio.Event,
        check_interval: int = 86400,
        telegram: TelegramChannel | None = None,
    ) -> None:
        self._detector = detector
        self._engine_factory = engine_factory
        self._full_config = full_config
        self._stop_event = stop_event
        self._check_interval = check_interval
        self._telegram = telegram

        self._current_regime: RegimeState = RegimeState.UNKNOWN
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

        await self._apply_regime(initial_regime)

        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=float(self._check_interval)
                )
                break
            except asyncio.TimeoutError:
                pass

            new_regime = await self._detector.get_confirmed_state()

            if new_regime == RegimeState.UNKNOWN:
                logger.info("regime_check_skipped", reason="unconfirmed")
                continue

            # UNKNOWN current regime OR macro side changed (bull <-> bear)
            regime_changed = (
                self._current_regime == RegimeState.UNKNOWN
                or new_regime.is_bull != self._current_regime.is_bull
            )

            if regime_changed:
                old_regime = self._current_regime
                logger.info(
                    "regime_flip_detected",
                    from_regime=old_regime.value,
                    to_regime=new_regime.value,
                )
                await self._apply_regime(new_regime)
                await self._send_flip_alert(old_regime, new_regime)
            else:
                logger.info(
                    "regime_unchanged",
                    current_regime=self._current_regime.value,
                    detected_regime=new_regime.value,
                )

        logger.info("regime_router_stopping")
        await self._stop_all_engines()

    def _get_template_ids_for_regime(self, regime: RegimeState) -> list[str]:
        """Return template IDs that should run for the given regime.

        Selects entries from full_config whose "regime" tag matches:
        "all" always included, "bull" only in bull regime, "bear" only in bear.

        Args:
            regime: The current confirmed regime state.

        Returns:
            Ordered list of template_id strings matching the regime.
        """
        result: list[str] = []
        for template_id, cfg in self._full_config.items():
            tag = cfg.get("regime", "all")
            if tag == "all":
                result.append(template_id)
            elif tag == "bull" and regime.is_bull:
                result.append(template_id)
            elif tag == "bear" and regime.is_bear:
                result.append(template_id)
        return result

    async def _apply_regime(self, regime: RegimeState) -> None:
        """Stop all current engines and start engines appropriate for regime.

        Args:
            regime: The newly confirmed regime state to apply.
        """
        logger.info("regime_applying", regime=regime.value)

        await self._stop_all_engines()

        template_ids = self._get_template_ids_for_regime(regime)

        if not template_ids:
            logger.warning(
                "regime_no_matching_templates",
                regime=regime.value,
            )
            self._current_regime = regime
            return

        engines = self._engine_factory(template_ids)
        self._active_engines = engines
        self._engine_tasks = [
            asyncio.create_task(engine.start()) for engine in engines
        ]
        self._current_regime = regime

        logger.info(
            "regime_engines_started",
            regime=regime.value,
            template_ids=template_ids,
            engine_count=len(engines),
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
    ) -> None:
        """Send a Telegram notification when the regime flips.

        Decision: DEC-2026-02-08-003 - Timezone-aware timestamps

        Args:
            old_regime: The previous regime state.
            new_regime: The newly confirmed regime state.
        """
        if self._telegram is None:
            return

        from src.core.alerting.manager import Alert, AlertLevel

        action = (
            "Bear strategies activated"
            if new_regime.is_bear
            else "Bull strategies activated"
        )
        msg = (
            f"Regime: {old_regime.value} -> {new_regime.value}\n"
            f"Action: {action}\n"
            f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        alert = Alert(
            level=AlertLevel.INFO,
            title=f"REGIME FLIP: {new_regime.value.upper()}",
            message=msg,
            metadata={
                "from_regime": old_regime.value,
                "to_regime": new_regime.value,
            },
        )
        try:
            await self._telegram.send(alert)
        except Exception as exc:
            logger.error(
                "regime_flip_alert_failed",
                from_regime=old_regime.value,
                to_regime=new_regime.value,
                error=str(exc),
            )
