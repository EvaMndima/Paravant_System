"""Strategy engine for lifecycle management and template orchestration.

The StrategyEngine is the central coordinator for:
- Creating strategies from templates with validated parameters
- Managing status transitions via a strict state machine
- Assigning/unassigning strategies to accounts
- Checking similarity against existing strategies
- Producing strategy summaries for the dashboard

Decision: DEC-2026-02-08-002 - SQLAlchemy 2.0 with Mapped[T]
Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-007 - Input validation at boundaries
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-08-010 - Lambda functions for mutable defaults
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.config.templates import TemplateManager
from src.core.exceptions import (InvalidParametersError,
                                 InvalidStatusTransitionError, StrategyError,
                                 TemplateNotFoundError)
from src.core.strategy.similarity import (ExistingStrategy, SimilarityResult,
                                          StrategyCandidate, check_similarity)
from src.data.models import (AssignmentStatus, Strategy, StrategyAssignment,
                             StrategyStatus, StrategyType)
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


# Valid status transitions in the strategy lifecycle state machine
VALID_TRANSITIONS: dict[StrategyStatus, set[StrategyStatus]] = {
    StrategyStatus.DRAFT: {StrategyStatus.BACKTEST},
    StrategyStatus.BACKTEST: {StrategyStatus.SIMULATED_PAPER, StrategyStatus.DRAFT},
    StrategyStatus.SIMULATED_PAPER: {StrategyStatus.LIVE_PAPER},
    StrategyStatus.LIVE_PAPER: {StrategyStatus.PENDING_APPROVAL},
    StrategyStatus.PENDING_APPROVAL: {StrategyStatus.LIVE, StrategyStatus.DRAFT},
    StrategyStatus.LIVE: {
        StrategyStatus.PAUSED,
        StrategyStatus.UNDERPERFORMING,
        StrategyStatus.RETIRED,
    },
    StrategyStatus.PAUSED: {StrategyStatus.LIVE, StrategyStatus.RETIRED},
    StrategyStatus.UNDERPERFORMING: {
        StrategyStatus.OPTIMIZATION,
        StrategyStatus.PAUSED,
        StrategyStatus.RETIRED,
        StrategyStatus.LIVE,
    },
    StrategyStatus.OPTIMIZATION: {
        StrategyStatus.LIVE,
        StrategyStatus.PAUSED,
        StrategyStatus.RETIRED,
    },
    StrategyStatus.RETIRED: set(),  # Terminal state
}


class StrategyEngine:
    """Central coordinator for strategy lifecycle management.

    Provides methods for creating, updating, and transitioning strategies
    through their lifecycle. Delegates template lookup and parameter
    validation to TemplateManager, and persistence to DataStore.

    Attributes:
        store: DataStore for persistence operations.
        template_manager: TemplateManager for template access.
    """

    def __init__(
        self,
        store: DataStore,
        template_manager: TemplateManager | None = None,
    ) -> None:
        """Initialize the strategy engine.

        Args:
            store: DataStore instance for database operations.
            template_manager: TemplateManager instance. Defaults to a new
                instance with the standard templates directory.
        """
        self.store = store
        self.template_manager = template_manager or TemplateManager()
        self.logger = get_logger(__name__)

    def create_strategy(
        self,
        name: str,
        template_id: str,
        params: dict[str, Any] | None = None,
        symbols: list[str] | None = None,
        description: str = "",
    ) -> tuple[Strategy, list[SimilarityResult]]:
        """Create a new strategy from a template.

        Validates the template exists, parameters are valid, and checks
        for similarity against existing strategies. The strategy starts
        in DRAFT status.

        Args:
            name: Human-readable strategy name.
            template_id: Template identifier (must exist in TemplateManager).
            params: Strategy parameters. Defaults to template defaults.
            symbols: Trading symbols. Defaults to template symbols.
            description: Optional strategy description.

        Returns:
            Tuple of (created Strategy, list of SimilarityResults).
            SimilarityResults with ``is_similar=True`` are warnings.

        Raises:
            TemplateNotFoundError: If template_id is not found.
            InvalidParametersError: If parameters fail validation.
            StrategyError: If strategy name is empty.
        """
        if not name or not name.strip():
            raise StrategyError(
                message="Strategy name cannot be empty",
                code="EMPTY_STRATEGY_NAME",
            )

        # Look up template
        try:
            template = self.template_manager.get_template(template_id)
        except ValueError:
            raise TemplateNotFoundError(template_id)

        # Resolve parameters: use provided or template defaults
        resolved_params = params if params is not None else template.get_default_parameters()

        # Validate parameters
        errors = self.template_manager.validate_parameters(template_id, resolved_params)
        if errors:
            raise InvalidParametersError(errors=errors, template_id=template_id)

        # Resolve symbols: use provided or template symbols
        resolved_symbols = symbols if symbols is not None else list(template.symbols)

        # Resolve strategy type from template type string
        strategy_type = StrategyType(template.type)

        # Create the Strategy model
        # Explicitly pass lifecycle=[] so add_lifecycle_event() works before
        # the object is persisted (SQLAlchemy column defaults only fire on INSERT)
        strategy = Strategy(
            name=name.strip(),
            description=description.strip() if description else template.description,
            type=strategy_type,
            template_id=template_id,
            template_version=template.version,
            parameters=resolved_params,
            symbols=resolved_symbols,
            status=StrategyStatus.DRAFT,
            status_reason="Created from template",
            lifecycle=[],
        )

        # Add initial lifecycle event
        strategy.add_lifecycle_event(
            from_status="none",
            to_status=StrategyStatus.DRAFT.value,
            reason="Strategy created from template",
        )

        # Check similarity against existing strategies
        existing_strategies = self.store.get_all_strategies()
        similarity_results = self._check_similarity(
            template_id=template_id,
            params=resolved_params,
            symbols=resolved_symbols,
            entry_logic=template.entry_logic,
            existing=existing_strategies,
        )

        # Persist
        saved = self.store.save_strategy(strategy)

        self.logger.info(
            "strategy_created",
            strategy_id=saved.id,
            name=saved.name,
            template_id=template_id,
            template_version=template.version,
            symbol_count=len(resolved_symbols),
            similar_count=sum(1 for r in similarity_results if r.is_similar),
        )

        return saved, similarity_results

    def update_strategy_parameters(
        self,
        strategy_id: str,
        params: dict[str, Any],
    ) -> Strategy:
        """Update parameters on an existing strategy.

        Only allowed in DRAFT or PAUSED status. Validates parameters
        against the strategy's template.

        Args:
            strategy_id: ID of the strategy to update.
            params: New parameter dictionary.

        Returns:
            Updated Strategy.

        Raises:
            StrategyError: If strategy not found or not in updatable status.
            InvalidParametersError: If parameters fail validation.
        """
        strategy = self.store.get_strategy(strategy_id)
        if strategy is None:
            raise StrategyError(
                message=f"Strategy not found: {strategy_id}",
                code="STRATEGY_NOT_FOUND",
                details={"strategy_id": strategy_id},
            )

        updatable_statuses = {StrategyStatus.DRAFT, StrategyStatus.PAUSED}
        if strategy.status not in updatable_statuses:
            raise StrategyError(
                message=(
                    f"Cannot update parameters in status '{strategy.status.value}'. "
                    f"Allowed statuses: {[s.value for s in updatable_statuses]}"
                ),
                code="STRATEGY_NOT_UPDATABLE",
                details={
                    "strategy_id": strategy_id,
                    "current_status": strategy.status.value,
                },
            )

        # Validate against template
        errors = self.template_manager.validate_parameters(strategy.template_id, params)
        if errors:
            raise InvalidParametersError(errors=errors, template_id=strategy.template_id)

        # Update via DataStore
        strategy.parameters = params
        saved = self.store.save_strategy(strategy)

        self.logger.info(
            "strategy_parameters_updated",
            strategy_id=strategy_id,
            template_id=strategy.template_id,
            param_count=len(params),
        )

        return saved

    def transition_status(
        self,
        strategy_id: str,
        new_status: StrategyStatus,
        reason: str = "",
    ) -> Strategy:
        """Transition a strategy to a new lifecycle status.

        Enforces the state machine defined in VALID_TRANSITIONS.

        Args:
            strategy_id: ID of the strategy to transition.
            new_status: Target status.
            reason: Reason for the transition.

        Returns:
            Updated Strategy with new status.

        Raises:
            StrategyError: If strategy not found.
            InvalidStatusTransitionError: If transition is invalid.
        """
        strategy = self.store.get_strategy(strategy_id)
        if strategy is None:
            raise StrategyError(
                message=f"Strategy not found: {strategy_id}",
                code="STRATEGY_NOT_FOUND",
                details={"strategy_id": strategy_id},
            )

        current = strategy.status
        allowed = VALID_TRANSITIONS.get(current, set())

        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                strategy_id=strategy_id,
                current_status=current.value,
                requested_status=new_status.value,
                details={
                    "allowed_transitions": [s.value for s in allowed],
                },
            )

        old_status = current.value
        strategy.status = new_status
        strategy.status_reason = reason or f"Transitioned to {new_status.value}"
        strategy.add_lifecycle_event(
            from_status=old_status,
            to_status=new_status.value,
            reason=reason or "Status transition",
        )

        saved = self.store.save_strategy(strategy)

        self.logger.info(
            "strategy_status_transitioned",
            strategy_id=strategy_id,
            from_status=old_status,
            to_status=new_status.value,
            reason=reason,
        )

        return saved

    def assign_strategy(
        self,
        strategy_id: str,
        account_id: str,
        symbol: str,
        timeframe: str,
        regime_filter: list[str] | None = None,
    ) -> StrategyAssignment:
        """Assign a strategy to an account for a specific symbol/timeframe.

        Args:
            strategy_id: Strategy ID to assign.
            account_id: Target account ID.
            symbol: Trading pair symbol.
            timeframe: Candle timeframe (e.g., ``1h``, ``4h``).
            regime_filter: Optional list of regimes where this assignment
                is active. Empty list means active in all regimes.

        Returns:
            Created StrategyAssignment.

        Raises:
            StrategyError: If strategy not found.
        """
        strategy = self.store.get_strategy(strategy_id)
        if strategy is None:
            raise StrategyError(
                message=f"Strategy not found: {strategy_id}",
                code="STRATEGY_NOT_FOUND",
                details={"strategy_id": strategy_id},
            )

        assignment = StrategyAssignment(
            account_id=account_id,
            strategy_id=strategy_id,
            symbol=symbol,
            timeframe=timeframe,
            status=AssignmentStatus.ACTIVE,
            regime_filter=regime_filter or [],
        )

        saved = self.store.save_assignment(assignment)

        self.logger.info(
            "strategy_assigned",
            assignment_id=saved.id,
            strategy_id=strategy_id,
            account_id=account_id,
            symbol=symbol,
            timeframe=timeframe,
        )

        return saved

    def unassign_strategy(self, assignment_id: str) -> None:
        """Unassign a strategy by setting its assignment to STOPPED.

        Args:
            assignment_id: Assignment ID to stop.

        Raises:
            StrategyError: If assignment not found.
        """
        with self.store.session() as session:
            assignment = session.get(StrategyAssignment, assignment_id)
            if assignment is None:
                raise StrategyError(
                    message=f"Assignment not found: {assignment_id}",
                    code="ASSIGNMENT_NOT_FOUND",
                    details={"assignment_id": assignment_id},
                )

            assignment.status = AssignmentStatus.STOPPED
            session.flush()

            self.logger.info(
                "strategy_unassigned",
                assignment_id=assignment_id,
                strategy_id=assignment.strategy_id,
            )

    def get_strategy_summary(self, strategy_id: str) -> dict[str, Any]:
        """Get a comprehensive summary of a strategy for the dashboard.

        Args:
            strategy_id: Strategy ID.

        Returns:
            Dictionary with strategy details, template info, and status.

        Raises:
            StrategyError: If strategy not found.
        """
        strategy = self.store.get_strategy(strategy_id)
        if strategy is None:
            raise StrategyError(
                message=f"Strategy not found: {strategy_id}",
                code="STRATEGY_NOT_FOUND",
                details={"strategy_id": strategy_id},
            )

        # Look up template info (may fail if template was removed)
        template_info: dict[str, Any] = {}
        try:
            template = self.template_manager.get_template(strategy.template_id)
            template_info = {
                "template_name": template.name,
                "template_version": template.version,
                "template_type": template.type,
                "entry_logic": template.entry_logic,
                "exit_logic": template.exit_logic,
                "recommended_for": template.recommended_for,
                "not_recommended_for": template.not_recommended_for,
            }
        except ValueError:
            template_info = {"error": f"Template '{strategy.template_id}' not found"}

        return {
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "status": strategy.status.value,
            "status_reason": strategy.status_reason,
            "type": strategy.type.value,
            "template_id": strategy.template_id,
            "template_version": strategy.template_version,
            "parameters": strategy.parameters,
            "symbols": strategy.symbols,
            "template": template_info,
            "backtest_results": strategy.backtest_results,
            "paper_results": strategy.paper_results,
            "live_results": strategy.live_results,
            "lifecycle": strategy.lifecycle,
            "created_at": (
                strategy.created_at.isoformat()
                if strategy.created_at
                else None
            ),
            "updated_at": (
                strategy.updated_at.isoformat()
                if strategy.updated_at
                else None
            ),
        }

    def get_valid_transitions(self, strategy_id: str) -> list[str]:
        """Get the valid next statuses for a strategy.

        Args:
            strategy_id: Strategy ID.

        Returns:
            List of valid status values the strategy can transition to.

        Raises:
            StrategyError: If strategy not found.
        """
        strategy = self.store.get_strategy(strategy_id)
        if strategy is None:
            raise StrategyError(
                message=f"Strategy not found: {strategy_id}",
                code="STRATEGY_NOT_FOUND",
                details={"strategy_id": strategy_id},
            )

        allowed = VALID_TRANSITIONS.get(strategy.status, set())
        return sorted(s.value for s in allowed)

    def _check_similarity(
        self,
        template_id: str,
        params: dict[str, Any],
        symbols: list[str],
        entry_logic: str,
        existing: list[Strategy],
    ) -> list[SimilarityResult]:
        """Check similarity of a new strategy against existing ones.

        Args:
            template_id: New strategy template ID.
            params: New strategy parameters.
            symbols: New strategy symbols.
            entry_logic: Template entry logic text.
            existing: List of existing Strategy models.

        Returns:
            List of SimilarityResult sorted by score descending.
        """
        candidate = StrategyCandidate(
            template_id=template_id,
            parameters=params,
            symbols=symbols,
            entry_logic=entry_logic,
        )

        existing_list: list[ExistingStrategy] = []
        for s in existing:
            # Look up entry logic from template
            ex_entry_logic = ""
            try:
                t = self.template_manager.get_template(s.template_id)
                ex_entry_logic = t.entry_logic
            except ValueError:
                pass

            existing_list.append(
                ExistingStrategy(
                    strategy_id=s.id,
                    strategy_name=s.name,
                    template_id=s.template_id,
                    parameters=s.parameters or {},
                    symbols=s.symbols or [],
                    entry_logic=ex_entry_logic,
                )
            )

        return check_similarity(candidate, existing_list)

    def check_underperformance_conditions(
        self,
        strategy: "Strategy",
    ) -> list[dict[str, Any]]:
        """Evaluate PRD §3.5 underperformance conditions against live metrics.

        Compares live performance data stored in strategy.live_results against
        backtest benchmarks from strategy.backtest_results. Tracks how long
        each failing condition has been active in live_results.underperformance_tracking.

        PRD §3.5 Triggers (all durations use calendar days):
          1. Win rate drops 15%+ below backtest for 14+ days.
          2. Sharpe ratio < 0.5 for 30+ days.
          3. Performance vs expectation < 50% for 21+ days.

        Args:
            strategy: Strategy to evaluate (must be LIVE status).

        Returns:
            List of active condition dicts. Each has keys:
            condition (str), duration_days (float), threshold_days (int).
            Empty list means no underperformance detected.
        """
        if strategy.status != StrategyStatus.LIVE:
            return []

        backtest = strategy.backtest_results or {}
        live = strategy.live_results or {}

        if not backtest or not live:
            return []

        now = datetime.now(timezone.utc)
        tracking: dict[str, Any] = live.get("underperformance_tracking", {})
        active_conditions: list[dict[str, Any]] = []

        # --- Condition 1: Win rate 15%+ below backtest for 14+ days ---
        bt_win_rate = float(backtest.get("win_rate_pct", 0.0))
        live_win_rate = float(live.get("win_rate_pct", bt_win_rate))
        win_rate_drop = bt_win_rate - live_win_rate
        if win_rate_drop >= 15.0:
            # Record when this condition was first detected
            if "low_win_rate_since" not in tracking:
                tracking["low_win_rate_since"] = now.isoformat()
            first_seen = datetime.fromisoformat(tracking["low_win_rate_since"])
            duration_days = (now - first_seen).total_seconds() / 86400.0
            if duration_days >= 14:
                active_conditions.append({
                    "condition": "low_win_rate",
                    "duration_days": round(duration_days, 1),
                    "threshold_days": 14,
                    "detail": (
                        f"Win rate {live_win_rate:.1f}% is {win_rate_drop:.1f}% below "
                        f"backtest {bt_win_rate:.1f}%"
                    ),
                })
        else:
            # Condition cleared — remove tracking entry
            tracking.pop("low_win_rate_since", None)

        # --- Condition 2: Sharpe ratio < 0.5 for 30+ days ---
        live_sharpe = float(live.get("sharpe_ratio", 1.0))
        if live_sharpe < 0.5:
            if "low_sharpe_since" not in tracking:
                tracking["low_sharpe_since"] = now.isoformat()
            first_seen = datetime.fromisoformat(tracking["low_sharpe_since"])
            duration_days = (now - first_seen).total_seconds() / 86400.0
            if duration_days >= 30:
                active_conditions.append({
                    "condition": "low_sharpe",
                    "duration_days": round(duration_days, 1),
                    "threshold_days": 30,
                    "detail": f"Sharpe ratio {live_sharpe:.3f} < 0.5 threshold",
                })
        else:
            tracking.pop("low_sharpe_since", None)

        # --- Condition 3: Expectancy < 50% of backtest for 21+ days ---
        bt_expectancy = float(backtest.get("expectancy", 0.0))
        live_expectancy = float(live.get("expectancy", bt_expectancy))
        if bt_expectancy > 0 and live_expectancy < (bt_expectancy * 0.5):
            if "low_expectancy_since" not in tracking:
                tracking["low_expectancy_since"] = now.isoformat()
            first_seen = datetime.fromisoformat(tracking["low_expectancy_since"])
            duration_days = (now - first_seen).total_seconds() / 86400.0
            if duration_days >= 21:
                active_conditions.append({
                    "condition": "low_expectancy",
                    "duration_days": round(duration_days, 1),
                    "threshold_days": 21,
                    "detail": (
                        f"Expectancy ${live_expectancy:.2f} is below 50% of "
                        f"backtest ${bt_expectancy:.2f}"
                    ),
                })
        else:
            tracking.pop("low_expectancy_since", None)

        # Persist updated tracking timestamps back to live_results
        if tracking != live.get("underperformance_tracking", {}):
            updated_live = dict(live)
            updated_live["underperformance_tracking"] = tracking
            strategy.live_results = updated_live
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(strategy, "live_results")

        return active_conditions

    def evaluate_and_apply_underperformance(
        self,
        strategy_id: str,
    ) -> bool:
        """Check and apply UNDERPERFORMING status if PRD §3.5 conditions are met.

        Loads the strategy, evaluates underperformance conditions, and
        auto-transitions to UNDERPERFORMING if any condition has been active
        for the required duration.

        Args:
            strategy_id: Strategy to evaluate.

        Returns:
            True if strategy was transitioned to UNDERPERFORMING, False otherwise.
        """
        strategy = self.store.get_strategy(strategy_id)
        if strategy is None or strategy.status != StrategyStatus.LIVE:
            return False

        conditions = self.check_underperformance_conditions(strategy)

        # Persist any updated tracking data from check_underperformance_conditions
        self.store.save_strategy(strategy)

        if not conditions:
            return False

        # Build human-readable reason
        condition_texts = [c["detail"] for c in conditions]
        reason = (
            "Auto-detected underperformance (PRD §3.5): "
            + "; ".join(condition_texts)
        )

        self.transition_status(
            strategy_id=strategy_id,
            new_status=StrategyStatus.UNDERPERFORMING,
            reason=reason,
        )

        logger.warning(
            "strategy_underperformance_auto_detected",
            strategy_id=strategy_id,
            conditions=[c["condition"] for c in conditions],
            condition_count=len(conditions),
        )

        return True
