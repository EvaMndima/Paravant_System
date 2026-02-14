"""Tests for the order state machine validation.

Validates that the state machine enforces one-way transitions
as defined in PHASE_4_IMPLEMENTATION_GUIDE.md invariant #2:

PENDING -> SUBMITTED -> PARTIALLY_FILLED -> FILLED (valid)
PENDING -> SUBMITTED -> CANCELLED (valid)
PENDING -> REJECTED (valid)
FILLED -> CANCELLED (ILLEGAL - backward move)
SUBMITTED -> PENDING (ILLEGAL - backward move)
"""
from __future__ import annotations

import pytest

from src.core.exceptions import InvalidStateTransitionError
from src.core.execution.order_manager import VALID_TRANSITIONS, OrderManager


class TestValidTransitions:
    """Tests for valid state transitions."""

    @pytest.mark.parametrize(
        "current,new",
        [
            ("pending", "submitted"),
            ("pending", "rejected"),
            ("submitted", "partially_filled"),
            ("submitted", "filled"),
            ("submitted", "cancelled"),
            ("submitted", "expired"),
            ("partially_filled", "filled"),
            ("partially_filled", "cancelled"),
        ],
    )
    def test_valid_transition_allowed(self, current: str, new: str) -> None:
        """Test that valid transitions do not raise."""
        # Direct validation using the transitions dict
        assert new in VALID_TRANSITIONS.get(current, set()), (
            f"Transition {current} -> {new} should be valid"
        )


class TestInvalidTransitions:
    """Tests for invalid (backward) state transitions."""

    @pytest.mark.parametrize(
        "current,new",
        [
            # Backward moves
            ("submitted", "pending"),
            ("filled", "submitted"),
            ("filled", "pending"),
            ("filled", "cancelled"),
            ("cancelled", "submitted"),
            ("cancelled", "pending"),
            ("cancelled", "filled"),
            ("rejected", "pending"),
            ("rejected", "submitted"),
            # Same state (no-op transitions)
            ("pending", "pending"),
            ("submitted", "submitted"),
            ("filled", "filled"),
        ],
    )
    def test_invalid_transition_not_in_valid_set(
        self, current: str, new: str
    ) -> None:
        """Test that invalid transitions are not in the valid set."""
        valid_next = VALID_TRANSITIONS.get(current, set())
        assert new not in valid_next, (
            f"Transition {current} -> {new} should NOT be valid"
        )


class TestStateTransitionEnforcement:
    """Tests for the _validate_state_transition method."""

    def _make_manager(self) -> OrderManager:
        """Create an OrderManager with mock dependencies for state testing."""
        from unittest.mock import AsyncMock, MagicMock

        engine = AsyncMock()
        store = MagicMock()
        return OrderManager(
            execution_engine=engine,
            data_store=store,
        )

    def test_valid_transition_does_not_raise(self) -> None:
        """Test that a valid transition passes silently."""
        manager = self._make_manager()
        # Should not raise
        manager._validate_state_transition("pending", "submitted")

    def test_invalid_transition_raises(self) -> None:
        """Test that an invalid transition raises InvalidStateTransitionError."""
        manager = self._make_manager()
        with pytest.raises(InvalidStateTransitionError):
            manager._validate_state_transition("filled", "pending")

    def test_terminal_states_have_no_transitions(self) -> None:
        """Test that terminal states (filled, cancelled, rejected) have no valid next states."""
        for terminal_state in ("filled", "cancelled", "rejected", "expired"):
            valid_next = VALID_TRANSITIONS.get(terminal_state, set())
            assert len(valid_next) == 0, (
                f"Terminal state {terminal_state} should have no valid transitions, "
                f"but has: {valid_next}"
            )

    def test_all_states_reachable_from_pending(self) -> None:
        """Test that all terminal states are reachable from PENDING."""
        # BFS to find all reachable states from pending
        reachable: set[str] = set()
        queue = ["pending"]
        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            for next_state in VALID_TRANSITIONS.get(current, set()):
                queue.append(next_state)

        # All terminal states should be reachable
        assert "submitted" in reachable
        assert "filled" in reachable
        assert "cancelled" in reachable
        assert "rejected" in reachable
