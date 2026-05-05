"""Unit tests for RegimeRouter.

Uses mock PaperTradingEngine and RegimeDetector instances so no real
Binance data or running engines are needed.

Decision: DEC-2026-05-04-001 - Dual-EMA composite regime detection
Decision: DEC-2026-05-04-002 - 2-consecutive-close confirmation rule
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.strategy.paper.engine import PaperTradingEngine
from src.core.strategy.regime.detector import RegimeState
from src.core.strategy.regime.router import RegimeRouter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Minimal strategy config used across all tests.
# Three templates: one bull, one bear, one all-regime.
FULL_CONFIG: dict[str, dict[str, Any]] = {
    "bull_template": {
        "label": "BULL",
        "regime": "bull",
        "symbols": ["BTCUSDT"],
        "params": {},
    },
    "bear_template": {
        "label": "BEAR",
        "regime": "bear",
        "symbols": ["BTCUSDT"],
        "params": {},
    },
    "all_template": {
        "label": "ALL",
        "regime": "all",
        "symbols": ["BTCUSDT"],
        "params": {},
    },
}


def _make_engine(strategy_id: str) -> MagicMock:
    """Return a mock PaperTradingEngine with async start/stop."""
    engine: MagicMock = MagicMock(spec=PaperTradingEngine)
    engine.strategy_id = strategy_id
    engine.is_running = True
    engine.start = AsyncMock()
    engine.stop = AsyncMock()
    return engine


def _make_detector(states: list[RegimeState]) -> MagicMock:
    """Return a mock RegimeDetector whose get_confirmed_state() yields states in order."""
    detector = MagicMock()
    detector.get_confirmed_state = AsyncMock(side_effect=states)
    detector.detect = AsyncMock(side_effect=states)
    return detector


def _make_factory(
    engines_per_template: dict[str, MagicMock],
) -> Callable[[list[str]], list[PaperTradingEngine]]:
    """Return an engine factory that maps template_ids to pre-built mock engines."""
    captured_calls: list[list[str]] = []

    def factory(template_ids: list[str]) -> list[PaperTradingEngine]:
        captured_calls.append(list(template_ids))
        return [engines_per_template[tid] for tid in template_ids if tid in engines_per_template]

    factory.calls = captured_calls  # type: ignore[attr-defined]
    return factory


def _make_router(
    detector: MagicMock,
    factory: Callable[[list[str]], list[PaperTradingEngine]],
    stop_event: asyncio.Event,
    *,
    check_interval: int = 1,  # 1s default keeps tests fast when event is set
) -> RegimeRouter:
    return RegimeRouter(
        detector=detector,  # type: ignore[arg-type]
        engine_factory=factory,
        full_config=FULL_CONFIG,
        stop_event=stop_event,
        check_interval=check_interval,
        telegram=None,
    )


# ---------------------------------------------------------------------------
# Tests: _get_template_ids_for_regime (pure logic, no async)
# ---------------------------------------------------------------------------


class TestGetTemplateIdsForRegime:
    """Direct tests of the regime → template_ids mapping logic."""

    def _router(self) -> RegimeRouter:
        return RegimeRouter(
            detector=MagicMock(),
            engine_factory=lambda tids: [],
            full_config=FULL_CONFIG,
            stop_event=asyncio.Event(),
            check_interval=86400,
        )

    def test_bull_regime_returns_bull_and_all_templates(self) -> None:
        """STRONG_BULL maps to bull + all templates (not bear).

        Decision: DEC-2026-05-04-001
        """
        router = self._router()
        result = router._get_template_ids_for_regime(RegimeState.STRONG_BULL)

        assert "bull_template" in result
        assert "all_template" in result
        assert "bear_template" not in result

    def test_pullback_bull_regime_same_as_strong_bull(self) -> None:
        """PULLBACK_BULL also runs bull + all templates — same macro side."""
        router = self._router()
        result = router._get_template_ids_for_regime(RegimeState.PULLBACK_BULL)

        assert "bull_template" in result
        assert "all_template" in result
        assert "bear_template" not in result

    def test_bear_regime_returns_bear_and_all_templates(self) -> None:
        """STRONG_BEAR maps to bear + all templates (not bull).

        Decision: DEC-2026-05-04-001
        """
        router = self._router()
        result = router._get_template_ids_for_regime(RegimeState.STRONG_BEAR)

        assert "bear_template" in result
        assert "all_template" in result
        assert "bull_template" not in result

    def test_bounce_bear_regime_same_as_strong_bear(self) -> None:
        """BOUNCE_BEAR also runs bear + all templates — same macro side."""
        router = self._router()
        result = router._get_template_ids_for_regime(RegimeState.BOUNCE_BEAR)

        assert "bear_template" in result
        assert "all_template" in result
        assert "bull_template" not in result

    def test_unknown_regime_returns_only_all_templates(self) -> None:
        """UNKNOWN runs only 'all' templates — no bull or bear commitment."""
        router = self._router()
        result = router._get_template_ids_for_regime(RegimeState.UNKNOWN)

        assert "all_template" in result
        assert "bull_template" not in result
        assert "bear_template" not in result

    def test_ordering_matches_config_insertion_order(self) -> None:
        """Template IDs are returned in FULL_CONFIG insertion order."""
        router = self._router()
        bull_result = router._get_template_ids_for_regime(RegimeState.STRONG_BULL)
        # bull_template comes before all_template in FULL_CONFIG
        bull_idx = bull_result.index("bull_template")
        all_idx = bull_result.index("all_template")
        assert bull_idx < all_idx


# ---------------------------------------------------------------------------
# Tests: initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    """get_active_engines() and get_current_regime() before run() is called."""

    def test_active_engines_empty_before_run(self) -> None:
        router = RegimeRouter(
            detector=MagicMock(),
            engine_factory=lambda tids: [],
            full_config=FULL_CONFIG,
            stop_event=asyncio.Event(),
            check_interval=86400,
        )
        assert router.get_active_engines() == []

    def test_current_regime_unknown_before_run(self) -> None:
        router = RegimeRouter(
            detector=MagicMock(),
            engine_factory=lambda tids: [],
            full_config=FULL_CONFIG,
            stop_event=asyncio.Event(),
            check_interval=86400,
        )
        assert router.get_current_regime() == RegimeState.UNKNOWN


# ---------------------------------------------------------------------------
# Tests: run() — bull startup
# ---------------------------------------------------------------------------


class TestRunBullStartup:
    """Tests for run() when initial regime is bull."""

    @pytest.mark.asyncio
    async def test_bull_templates_start_on_strong_bull(self) -> None:
        """run() starts bull + all engines when initial regime is STRONG_BULL.

        Decision: DEC-2026-05-04-001 — only bull-appropriate strategies activate.
        """
        bull_engine = _make_engine("bull_session")
        all_engine = _make_engine("all_session")
        engines: dict[str, MagicMock] = {
            "bull_template": bull_engine,
            "all_template": all_engine,
        }

        stop_event = asyncio.Event()
        # Confirmed state: STRONG_BULL on startup, then stop before next check
        detector = _make_detector([RegimeState.STRONG_BULL])
        factory = _make_factory(engines)
        router = _make_router(detector, factory, stop_event)

        # Set stop_event immediately after startup so the loop exits cleanly
        async def run_and_stop() -> None:
            task = asyncio.create_task(router.run())
            # Allow startup to complete (one event loop tick per await)
            await asyncio.sleep(0.05)
            stop_event.set()
            await asyncio.wait_for(task, timeout=5.0)

        await run_and_stop()

        assert router.get_current_regime() == RegimeState.STRONG_BULL

        # Factory must have been called with bull + all templates
        assert len(factory.calls) >= 1
        assert "bull_template" in factory.calls[0]
        assert "all_template" in factory.calls[0]
        assert "bear_template" not in factory.calls[0]

    @pytest.mark.asyncio
    async def test_bear_templates_do_not_start_in_bull_regime(self) -> None:
        """Bear engines must NOT be started when regime is STRONG_BULL."""
        bear_engine = _make_engine("bear_session")
        engines: dict[str, MagicMock] = {"bear_template": bear_engine}

        stop_event = asyncio.Event()
        detector = _make_detector([RegimeState.STRONG_BULL])
        factory = _make_factory(engines)
        router = _make_router(detector, factory, stop_event)

        async def run_and_stop() -> None:
            task = asyncio.create_task(router.run())
            await asyncio.sleep(0.05)
            stop_event.set()
            await asyncio.wait_for(task, timeout=5.0)

        await run_and_stop()

        # bear_engine.start() should never have been called
        bear_engine.start.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: run() — bear startup
# ---------------------------------------------------------------------------


class TestRunBearStartup:
    """Tests for run() when initial regime is bear."""

    @pytest.mark.asyncio
    async def test_bear_templates_start_on_strong_bear(self) -> None:
        """run() starts bear + all engines when initial regime is STRONG_BEAR.

        Decision: DEC-2026-05-04-001
        """
        bear_engine = _make_engine("bear_session")
        all_engine = _make_engine("all_session")
        engines: dict[str, MagicMock] = {
            "bear_template": bear_engine,
            "all_template": all_engine,
        }

        stop_event = asyncio.Event()
        detector = _make_detector([RegimeState.STRONG_BEAR])
        factory = _make_factory(engines)
        router = _make_router(detector, factory, stop_event)

        async def run_and_stop() -> None:
            task = asyncio.create_task(router.run())
            await asyncio.sleep(0.05)
            stop_event.set()
            await asyncio.wait_for(task, timeout=5.0)

        await run_and_stop()

        assert router.get_current_regime() == RegimeState.STRONG_BEAR
        assert len(factory.calls) >= 1
        assert "bear_template" in factory.calls[0]
        assert "all_template" in factory.calls[0]
        assert "bull_template" not in factory.calls[0]

    @pytest.mark.asyncio
    async def test_bull_templates_do_not_start_in_bear_regime(self) -> None:
        """Bull engines must NOT be started when regime is STRONG_BEAR."""
        bull_engine = _make_engine("bull_session")
        engines: dict[str, MagicMock] = {"bull_template": bull_engine}

        stop_event = asyncio.Event()
        detector = _make_detector([RegimeState.STRONG_BEAR])
        factory = _make_factory(engines)
        router = _make_router(detector, factory, stop_event)

        async def run_and_stop() -> None:
            task = asyncio.create_task(router.run())
            await asyncio.sleep(0.05)
            stop_event.set()
            await asyncio.wait_for(task, timeout=5.0)

        await run_and_stop()

        bull_engine.start.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: regime flip
# ---------------------------------------------------------------------------


class TestRegimeFlip:
    """Tests that a confirmed regime change stops old engines and starts new ones."""

    @pytest.mark.asyncio
    async def test_flip_from_bull_to_bear_stops_bull_starts_bear(self) -> None:
        """On BULL->BEAR flip: bull engines stopped, bear engines started.

        Decision: DEC-2026-05-04-002 — 2-bar confirmation already handled
        by detector; router acts on whatever state get_confirmed_state() returns.
        """
        bull_engine = _make_engine("bull_session")
        bear_engine = _make_engine("bear_session")
        all_engine_1 = _make_engine("all_session_1")
        all_engine_2 = _make_engine("all_session_2")

        # First factory call (bull startup) → bull + all_1
        # Second factory call (bear flip)   → bear + all_2
        call_results: list[list[MagicMock]] = [
            [bull_engine, all_engine_1],
            [bear_engine, all_engine_2],
        ]
        call_index = 0
        captured_template_ids: list[list[str]] = []

        def engine_factory(template_ids: list[str]) -> list[PaperTradingEngine]:
            nonlocal call_index
            captured_template_ids.append(list(template_ids))
            result = call_results[call_index] if call_index < len(call_results) else []
            call_index += 1
            return result  # type: ignore[return-value]

        stop_event = asyncio.Event()

        # Detector: first call returns STRONG_BULL (startup),
        # second call returns STRONG_BEAR (first loop iteration).
        # After that the stop_event is set so the test ends.
        call_count = 0

        async def get_confirmed_state() -> RegimeState:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return RegimeState.STRONG_BULL
            else:
                # Set stop_event so next loop iteration exits cleanly
                stop_event.set()
                return RegimeState.STRONG_BEAR

        detector = MagicMock()
        detector.get_confirmed_state = get_confirmed_state
        detector.detect = AsyncMock(return_value=RegimeState.STRONG_BULL)

        router = _make_router(
            detector, engine_factory, stop_event, check_interval=1
        )

        task = asyncio.create_task(router.run())
        await asyncio.wait_for(task, timeout=10.0)

        # Regime flipped to bear
        assert router.get_current_regime() == RegimeState.STRONG_BEAR

        # Factory was called twice: once for bull startup, once for bear flip
        assert len(captured_template_ids) == 2

        first_call, second_call = captured_template_ids
        assert "bull_template" in first_call
        assert "bear_template" not in first_call

        assert "bear_template" in second_call
        assert "bull_template" not in second_call

        # Bull engine was stopped during the flip
        bull_engine.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_flip_when_macro_side_unchanged(self) -> None:
        """STRONG_BULL -> PULLBACK_BULL: same macro side, no engine restart.

        Both are bull variants — the router should not flip because
        PULLBACK_BULL.is_bull == STRONG_BULL.is_bull.
        """
        bull_engine = _make_engine("bull_session")
        all_engine = _make_engine("all_session")
        factory_calls: list[list[str]] = []

        def engine_factory(template_ids: list[str]) -> list[PaperTradingEngine]:
            factory_calls.append(list(template_ids))
            return [bull_engine, all_engine]  # type: ignore[return-value]

        stop_event = asyncio.Event()
        call_count = 0

        async def get_confirmed_state() -> RegimeState:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return RegimeState.STRONG_BULL
            else:
                stop_event.set()
                return RegimeState.PULLBACK_BULL  # same macro side, different sub-state

        detector = MagicMock()
        detector.get_confirmed_state = get_confirmed_state
        detector.detect = AsyncMock(return_value=RegimeState.STRONG_BULL)

        router = _make_router(detector, engine_factory, stop_event, check_interval=1)
        task = asyncio.create_task(router.run())
        await asyncio.wait_for(task, timeout=10.0)

        # Engine factory called ONCE (startup only) — no second restart happened
        assert len(factory_calls) == 1

        # stop() is called exactly once during graceful shutdown, NOT once for a
        # flip and once for shutdown. If a flip had occurred, the factory would have
        # been called twice AND stop would have been called before the flip restart.
        # The single factory call above already proves no flip occurred.
        assert bull_engine.stop.call_count == 1  # shutdown cleanup only

    @pytest.mark.asyncio
    async def test_unknown_regime_during_check_does_not_flip(self) -> None:
        """UNKNOWN returned by detector during loop iteration causes no action.

        Decision: DEC-2026-05-04-002 — unconfirmed (UNKNOWN) is skipped.
        """
        bull_engine = _make_engine("bull_session")
        factory_calls: list[list[str]] = []

        def engine_factory(template_ids: list[str]) -> list[PaperTradingEngine]:
            factory_calls.append(list(template_ids))
            return [bull_engine]  # type: ignore[return-value]

        stop_event = asyncio.Event()
        call_count = 0

        async def get_confirmed_state() -> RegimeState:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return RegimeState.STRONG_BULL
            else:
                stop_event.set()
                # Confirmation failed: UNKNOWN means no action
                return RegimeState.UNKNOWN

        detector = MagicMock()
        detector.get_confirmed_state = get_confirmed_state
        detector.detect = AsyncMock(return_value=RegimeState.STRONG_BULL)

        router = _make_router(detector, engine_factory, stop_event, check_interval=1)
        task = asyncio.create_task(router.run())
        await asyncio.wait_for(task, timeout=10.0)

        # Regime stays STRONG_BULL; factory not called a second time
        assert router.get_current_regime() == RegimeState.STRONG_BULL
        assert len(factory_calls) == 1

    @pytest.mark.asyncio
    async def test_get_active_engines_reflects_current_engines(self) -> None:
        """get_active_engines() returns the engines for the current regime."""
        bull_engine = _make_engine("bull_session")
        all_engine = _make_engine("all_session")
        engines_by_template: dict[str, MagicMock] = {
            "bull_template": bull_engine,
            "all_template": all_engine,
        }

        stop_event = asyncio.Event()
        detector = _make_detector([RegimeState.STRONG_BULL])
        factory = _make_factory(engines_by_template)
        router = _make_router(detector, factory, stop_event)

        async def run_and_stop() -> None:
            task = asyncio.create_task(router.run())
            await asyncio.sleep(0.05)
            # Check active engines while running
            active = router.get_active_engines()
            assert bull_engine in active
            assert all_engine in active
            stop_event.set()
            await asyncio.wait_for(task, timeout=5.0)

        await run_and_stop()
