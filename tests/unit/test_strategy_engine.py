"""Unit tests for the StrategyEngine and related components.

Tests cover:
- Strategy creation from templates
- Status transition state machine
- Parameter validation and updates
- Strategy assignment/unassignment
- Similarity detection
- Market regime management
- Exception handling
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.config.templates import ParameterSpec, StrategyTemplate, TemplateManager
from src.core.exceptions import (
    InvalidParametersError,
    InvalidStatusTransitionError,
    RegimeError,
    SignalGenerationError,
    StrategyError,
    TemplateNotFoundError,
)
from src.core.strategy.engine import VALID_TRANSITIONS, StrategyEngine
from src.core.strategy.regime import (
    MarketRegime,
    REGIME_MISMATCH_SIZE_FACTOR,
    get_regime,
    get_size_factor,
    set_regime,
    should_reduce_size,
)
from src.core.strategy.similarity import (
    StrategyCandidate,
    ExistingStrategy,
    check_similarity,
    SIMILARITY_THRESHOLD,
)
from src.data.models import StrategyStatus, StrategyType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_template_manager():
    """Create a mock TemplateManager with a test template."""
    manager = MagicMock(spec=TemplateManager)

    template = StrategyTemplate(
        id="ema_trend_rsi",
        name="EMA Trend + RSI",
        version="1.0.0",
        type="trend_following",
        description="Test template",
        entry_logic="Fast EMA crosses above Slow EMA AND RSI > threshold",
        exit_logic="EMA cross-back",
        parameters=[
            ParameterSpec(
                name="fast_ema_period",
                type="int",
                min_value=5,
                max_value=50,
                default=12,
            ),
            ParameterSpec(
                name="slow_ema_period",
                type="int",
                min_value=20,
                max_value=200,
                default=26,
            ),
        ],
        recommended_for=["trending_up", "trending_down"],
        not_recommended_for=["ranging"],
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframes=["1h", "4h"],
    )

    manager.get_template.return_value = template
    manager.validate_parameters.return_value = []  # No errors
    manager.get_default_parameters.return_value = {
        "fast_ema_period": 12,
        "slow_ema_period": 26,
    }
    return manager


@pytest.fixture
def mock_store(db_engine):
    """Create a mock DataStore backed by test database."""
    from src.data.store import DataStore

    store = DataStore()
    store.engine = db_engine
    return store


@pytest.fixture
def engine(mock_store, mock_template_manager):
    """Create a StrategyEngine with mocked dependencies."""
    return StrategyEngine(store=mock_store, template_manager=mock_template_manager)


# ---------------------------------------------------------------------------
# Strategy Creation Tests
# ---------------------------------------------------------------------------


class TestStrategyCreation:
    """Tests for strategy creation."""

    def test_create_strategy_with_defaults(self, engine):
        """Test creating a strategy with default template parameters."""
        strategy, similarities = engine.create_strategy(
            name="My EMA Strategy",
            template_id="ema_trend_rsi",
        )

        assert strategy.id is not None
        assert strategy.name == "My EMA Strategy"
        assert strategy.status == StrategyStatus.DRAFT
        assert strategy.template_id == "ema_trend_rsi"
        assert strategy.template_version == "1.0.0"
        assert strategy.type == StrategyType.TREND_FOLLOWING
        assert len(strategy.lifecycle) > 0

    def test_create_strategy_with_custom_params(self, engine):
        """Test creating a strategy with custom parameters."""
        custom_params = {"fast_ema_period": 20, "slow_ema_period": 50}
        strategy, _ = engine.create_strategy(
            name="Custom EMA",
            template_id="ema_trend_rsi",
            params=custom_params,
            symbols=["BTCUSDT"],
        )

        assert strategy.parameters == custom_params
        assert strategy.symbols == ["BTCUSDT"]

    def test_create_strategy_empty_name_raises(self, engine):
        """Test that empty name raises StrategyError."""
        with pytest.raises(StrategyError, match="name cannot be empty"):
            engine.create_strategy(name="", template_id="ema_trend_rsi")

    def test_create_strategy_invalid_template_raises(self, engine, mock_template_manager):
        """Test that invalid template raises TemplateNotFoundError."""
        mock_template_manager.get_template.side_effect = ValueError("not found")

        with pytest.raises(TemplateNotFoundError):
            engine.create_strategy(name="Test", template_id="nonexistent")

    def test_create_strategy_invalid_params_raises(self, engine, mock_template_manager):
        """Test that invalid parameters raise InvalidParametersError."""
        mock_template_manager.validate_parameters.return_value = [
            "fast_ema_period must be >= 5"
        ]

        with pytest.raises(InvalidParametersError):
            engine.create_strategy(
                name="Test",
                template_id="ema_trend_rsi",
                params={"fast_ema_period": 1},
            )

    def test_create_strategy_returns_similarity_results(self, engine, mock_store):
        """Test that creating a strategy checks for similarity."""
        # Create a first strategy
        engine.create_strategy(name="First", template_id="ema_trend_rsi")

        # Create a similar one - should return similarity results
        _, similarities = engine.create_strategy(
            name="Second", template_id="ema_trend_rsi"
        )

        # Should have results for the first strategy
        assert len(similarities) >= 1


# ---------------------------------------------------------------------------
# Status Transition Tests
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    """Tests for strategy lifecycle state machine."""

    def test_valid_transitions(self, engine):
        """Test all valid forward transitions."""
        strategy, _ = engine.create_strategy(name="Test", template_id="ema_trend_rsi")
        assert strategy.status == StrategyStatus.DRAFT

        # DRAFT -> BACKTEST
        strategy = engine.transition_status(
            strategy.id, StrategyStatus.BACKTEST, "Starting backtest"
        )
        assert strategy.status == StrategyStatus.BACKTEST

        # BACKTEST -> SIMULATED_PAPER
        strategy = engine.transition_status(
            strategy.id, StrategyStatus.SIMULATED_PAPER, "Backtest passed"
        )
        assert strategy.status == StrategyStatus.SIMULATED_PAPER

        # SIMULATED_PAPER -> LIVE_PAPER
        strategy = engine.transition_status(
            strategy.id, StrategyStatus.LIVE_PAPER, "Simulation passed"
        )
        assert strategy.status == StrategyStatus.LIVE_PAPER

    def test_invalid_transition_raises(self, engine):
        """Test that invalid transitions raise InvalidStatusTransitionError."""
        strategy, _ = engine.create_strategy(name="Test", template_id="ema_trend_rsi")

        with pytest.raises(InvalidStatusTransitionError):
            # DRAFT -> LIVE is not allowed (must go through stages)
            engine.transition_status(strategy.id, StrategyStatus.LIVE)

    def test_retired_is_terminal(self, engine):
        """Test that RETIRED has no valid transitions."""
        assert VALID_TRANSITIONS[StrategyStatus.RETIRED] == set()

    def test_transition_records_lifecycle(self, engine):
        """Test that transitions are recorded in lifecycle events."""
        strategy, _ = engine.create_strategy(name="Test", template_id="ema_trend_rsi")
        initial_lifecycle_count = len(strategy.lifecycle)

        strategy = engine.transition_status(
            strategy.id, StrategyStatus.BACKTEST, "Starting"
        )

        assert len(strategy.lifecycle) > initial_lifecycle_count

    def test_transition_nonexistent_strategy_raises(self, engine):
        """Test transitioning a non-existent strategy raises StrategyError."""
        with pytest.raises(StrategyError, match="not found"):
            engine.transition_status("nonexistent_id", StrategyStatus.BACKTEST)


# ---------------------------------------------------------------------------
# Parameter Update Tests
# ---------------------------------------------------------------------------


class TestParameterUpdates:
    """Tests for strategy parameter updates."""

    def test_update_params_in_draft(self, engine):
        """Test updating parameters in DRAFT status."""
        strategy, _ = engine.create_strategy(name="Test", template_id="ema_trend_rsi")
        new_params = {"fast_ema_period": 15, "slow_ema_period": 30}

        updated = engine.update_strategy_parameters(strategy.id, new_params)
        assert updated.parameters == new_params

    def test_update_params_not_in_live_raises(self, engine):
        """Test that updating params in non-updatable status raises."""
        strategy, _ = engine.create_strategy(name="Test", template_id="ema_trend_rsi")

        # Move to BACKTEST
        engine.transition_status(strategy.id, StrategyStatus.BACKTEST)

        with pytest.raises(StrategyError, match="Cannot update parameters"):
            engine.update_strategy_parameters(
                strategy.id, {"fast_ema_period": 15}
            )


# ---------------------------------------------------------------------------
# Strategy Assignment Tests
# ---------------------------------------------------------------------------


class TestStrategyAssignment:
    """Tests for strategy assignment management."""

    def test_assign_strategy(self, engine, sample_account):
        """Test assigning a strategy to an account."""
        strategy, _ = engine.create_strategy(name="Test", template_id="ema_trend_rsi")

        assignment = engine.assign_strategy(
            strategy_id=strategy.id,
            account_id=sample_account.id,
            symbol="BTCUSDT",
            timeframe="1h",
        )

        assert assignment.id is not None
        assert assignment.strategy_id == strategy.id
        assert assignment.account_id == sample_account.id
        assert assignment.symbol == "BTCUSDT"
        assert assignment.timeframe == "1h"

    def test_unassign_strategy(self, engine, sample_account):
        """Test unassigning a strategy."""
        strategy, _ = engine.create_strategy(name="Test", template_id="ema_trend_rsi")
        assignment = engine.assign_strategy(
            strategy_id=strategy.id,
            account_id=sample_account.id,
            symbol="BTCUSDT",
            timeframe="1h",
        )

        # Should not raise
        engine.unassign_strategy(assignment.id)


# ---------------------------------------------------------------------------
# Similarity Checker Tests
# ---------------------------------------------------------------------------


class TestSimilarityChecker:
    """Tests for strategy similarity detection."""

    def test_identical_strategies_high_score(self):
        """Test that identical strategies score very high."""
        candidate = StrategyCandidate(
            template_id="ema_trend_rsi",
            parameters={"fast": 12, "slow": 26},
            symbols=["BTCUSDT"],
            entry_logic="EMA crossover",
        )

        existing = [
            ExistingStrategy(
                strategy_id="str_1",
                strategy_name="Existing",
                template_id="ema_trend_rsi",
                parameters={"fast": 12, "slow": 26},
                symbols=["BTCUSDT"],
                entry_logic="EMA crossover",
            )
        ]

        results = check_similarity(candidate, existing)
        assert len(results) == 1
        assert results[0].overall_score >= SIMILARITY_THRESHOLD
        assert results[0].is_similar is True

    def test_different_templates_low_score(self):
        """Test that different templates score lower."""
        candidate = StrategyCandidate(
            template_id="ema_trend_rsi",
            parameters={"fast": 12},
            symbols=["BTCUSDT"],
        )

        existing = [
            ExistingStrategy(
                strategy_id="str_1",
                strategy_name="Existing",
                template_id="macd_pullback",
                parameters={"macd_fast": 12},
                symbols=["ETHUSDT"],
            )
        ]

        results = check_similarity(candidate, existing)
        assert len(results) == 1
        assert results[0].overall_score < SIMILARITY_THRESHOLD
        assert results[0].is_similar is False

    def test_empty_existing_returns_empty(self):
        """Test with no existing strategies."""
        candidate = StrategyCandidate(
            template_id="test",
            parameters={},
            symbols=[],
        )
        results = check_similarity(candidate, [])
        assert results == []


# ---------------------------------------------------------------------------
# Market Regime Tests
# ---------------------------------------------------------------------------


class TestMarketRegime:
    """Tests for market regime management."""

    def test_set_and_get_regime(self, mock_store):
        """Test setting and getting a regime."""
        set_regime("BTCUSDT", MarketRegime.TRENDING_UP, mock_store)
        result = get_regime("BTCUSDT", mock_store)
        assert result == MarketRegime.TRENDING_UP

    def test_get_unknown_symbol_returns_unknown(self, mock_store):
        """Test that unknown symbol returns UNKNOWN regime."""
        result = get_regime("NONEXISTENT", mock_store)
        assert result == MarketRegime.UNKNOWN

    def test_set_regime_empty_symbol_raises(self, mock_store):
        """Test that empty symbol raises RegimeError."""
        with pytest.raises(RegimeError):
            set_regime("", MarketRegime.VOLATILE, mock_store)

    def test_should_reduce_size_on_mismatch(self, mock_store, mock_template_manager):
        """Test size reduction when regime mismatches template recommendation."""
        set_regime("BTCUSDT", MarketRegime.RANGING, mock_store)

        result = should_reduce_size(
            "ema_trend_rsi", "BTCUSDT", mock_store, mock_template_manager
        )
        # Template recommends trending_up/trending_down, but regime is ranging
        assert result is True

    def test_no_reduction_when_aligned(self, mock_store, mock_template_manager):
        """Test no size reduction when regime matches recommendation."""
        set_regime("BTCUSDT", MarketRegime.TRENDING_UP, mock_store)

        result = should_reduce_size(
            "ema_trend_rsi", "BTCUSDT", mock_store, mock_template_manager
        )
        assert result is False

    def test_no_reduction_for_unknown_regime(self, mock_store, mock_template_manager):
        """Test no reduction for UNKNOWN regime (operator hasn't classified)."""
        result = should_reduce_size(
            "ema_trend_rsi", "NEWPAIR", mock_store, mock_template_manager
        )
        assert result is False

    def test_get_size_factor(self, mock_store, mock_template_manager):
        """Test size factor calculation."""
        set_regime("BTCUSDT", MarketRegime.RANGING, mock_store)

        factor = get_size_factor(
            "ema_trend_rsi", "BTCUSDT", mock_store, mock_template_manager
        )
        assert factor == REGIME_MISMATCH_SIZE_FACTOR


# ---------------------------------------------------------------------------
# Exception Tests
# ---------------------------------------------------------------------------


class TestExceptions:
    """Tests for new exception classes."""

    def test_invalid_status_transition_error(self):
        """Test InvalidStatusTransitionError attributes."""
        error = InvalidStatusTransitionError(
            strategy_id="str_1",
            current_status="draft",
            requested_status="live",
        )
        assert error.code == "INVALID_STATUS_TRANSITION"
        assert "str_1" in error.message
        error_dict = error.to_dict()
        assert error_dict["error"]["details"]["strategy_id"] == "str_1"

    def test_regime_error(self):
        """Test RegimeError attributes."""
        error = RegimeError(symbol="BTCUSDT", reason="Test failure")
        assert error.code == "REGIME_ERROR"
        assert "BTCUSDT" in error.message

    def test_signal_generation_error(self):
        """Test SignalGenerationError attributes."""
        error = SignalGenerationError(
            strategy_id="str_1",
            template_id="ema_trend_rsi",
            reason="Insufficient data",
        )
        assert error.code == "SIGNAL_GENERATION_ERROR"
        assert "Insufficient data" in error.message


# ---------------------------------------------------------------------------
# Strategy Summary Tests
# ---------------------------------------------------------------------------


class TestStrategySummary:
    """Tests for strategy summary generation."""

    def test_get_strategy_summary(self, engine):
        """Test getting a strategy summary."""
        strategy, _ = engine.create_strategy(name="Summary Test", template_id="ema_trend_rsi")

        summary = engine.get_strategy_summary(strategy.id)

        assert summary["id"] == strategy.id
        assert summary["name"] == "Summary Test"
        assert summary["status"] == "draft"
        assert summary["template_id"] == "ema_trend_rsi"
        assert "template" in summary
        assert summary["template"]["template_name"] == "EMA Trend + RSI"

    def test_get_valid_transitions(self, engine):
        """Test getting valid transitions for a strategy."""
        strategy, _ = engine.create_strategy(name="Test", template_id="ema_trend_rsi")

        transitions = engine.get_valid_transitions(strategy.id)

        assert "backtest" in transitions
        assert "live" not in transitions  # Not directly reachable from DRAFT
