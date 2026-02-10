"""Strategy template loading and parameter validation.

Provides Pydantic models for strategy templates and a manager class
that loads templates from YAML files in the ``config/templates/``
directory. Each template defines:

- Identification (id, name, version, type)
- Entry/exit logic descriptions
- Parameters with type, range, and default constraints
- Expected performance metrics
- Regime recommendations

Decision: DEC-2026-02-08-002 - SQLAlchemy 2.0 patterns (template_id field integration)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class ParameterSpec(BaseModel):
    """Specification for a single strategy parameter.

    Defines the type, allowed range, default value, and description
    for a strategy parameter. Used by the template manager to validate
    user-provided parameter values.

    Attributes:
        name: Parameter identifier (used as dict key).
        type: Data type of the parameter.
        min_value: Minimum allowed value (numeric types only).
        max_value: Maximum allowed value (numeric types only).
        default: Default parameter value.
        step: Suggested step size for UI sliders (numeric types).
        choices: Allowed string values (str type only).
        description: Human-readable description of the parameter.
    """

    name: str = Field(..., min_length=1, description="Parameter identifier")
    type: Literal["int", "float", "bool", "str"] = Field(
        ..., description="Parameter data type"
    )
    min_value: float | None = Field(
        default=None, alias="min", description="Minimum value (numeric)"
    )
    max_value: float | None = Field(
        default=None, alias="max", description="Maximum value (numeric)"
    )
    default: int | float | bool | str = Field(
        ..., description="Default parameter value"
    )
    step: float | None = Field(
        default=None, description="Step size for numeric parameters"
    )
    choices: list[str] | None = Field(
        default=None, description="Valid choices for string parameters"
    )
    description: str = Field(
        default="", description="Human-readable description"
    )

    model_config = {"populate_by_name": True}


class ExpectedPerformance(BaseModel):
    """Expected performance metrics for a strategy template.

    These are guideline values from backtesting, not guarantees.

    Attributes:
        min_sharpe: Minimum expected Sharpe ratio.
        max_drawdown_pct: Maximum expected drawdown percentage.
        min_win_rate_pct: Minimum expected win rate percentage.
    """

    min_sharpe: float = Field(
        default=0.0, description="Minimum expected Sharpe ratio"
    )
    max_drawdown_pct: float = Field(
        default=0.0, description="Maximum expected drawdown (%)"
    )
    min_win_rate_pct: float = Field(
        default=0.0, description="Minimum expected win rate (%)"
    )


class StrategyTemplate(BaseModel):
    """Strategy template definition loaded from YAML.

    Each template represents a pre-built trading strategy with
    configurable parameters. The template ID must match the
    ``Strategy.template_id`` field in the database model.

    Attributes:
        id: Unique template identifier.
        name: Human-readable template name.
        version: Semantic version string.
        type: Strategy classification type.
        description: Detailed template description.
        entry_logic: Description of entry signal logic.
        exit_logic: Description of exit signal logic.
        parameters: List of configurable parameter specifications.
        expected_performance: Guideline performance metrics.
        recommended_for: Regimes where this strategy performs well.
        not_recommended_for: Regimes where this strategy performs poorly.
        symbols: Recommended trading symbols.
        timeframes: Recommended timeframes.
    """

    id: str = Field(..., min_length=1, description="Unique template ID")
    name: str = Field(..., min_length=1, description="Template name")
    version: str = Field(
        default="1.0.0", description="Semantic version string"
    )
    type: str = Field(..., description="Strategy type classification")
    description: str = Field(
        default="", description="Detailed template description"
    )
    entry_logic: str = Field(
        default="", description="Entry signal logic description"
    )
    exit_logic: str = Field(
        default="", description="Exit signal logic description"
    )
    parameters: list[ParameterSpec] = Field(
        default_factory=list,
        description="Configurable parameter specifications",
    )
    expected_performance: ExpectedPerformance = Field(
        default_factory=ExpectedPerformance,
        description="Guideline performance metrics",
    )
    recommended_for: list[str] = Field(
        default_factory=list,
        description="Regimes where strategy performs well",
    )
    not_recommended_for: list[str] = Field(
        default_factory=list,
        description="Regimes where strategy performs poorly",
    )
    symbols: list[str] = Field(
        default_factory=list,
        description="Recommended trading symbols",
    )
    timeframes: list[str] = Field(
        default_factory=list,
        description="Recommended timeframes",
    )

    @field_validator("type")
    @classmethod
    def validate_strategy_type(cls, value: str) -> str:
        """Validate strategy type against known types.

        Args:
            value: Strategy type string.

        Returns:
            Validated strategy type.

        Raises:
            ValueError: If strategy type is not recognized.
        """
        valid_types = {
            "trend_following",
            "mean_reversion",
            "volatility_breakout",
            "trend_continuation",
            "trend_breakout",
            "intraday_pullback",
        }
        if value not in valid_types:
            raise ValueError(
                f"Invalid strategy type '{value}'. "
                f"Valid types: {sorted(valid_types)}"
            )
        return value

    def get_default_parameters(self) -> dict[str, int | float | bool | str]:
        """Get default parameter values as a dictionary.

        Returns:
            Dictionary mapping parameter names to their default values.
        """
        return {param.name: param.default for param in self.parameters}


class TemplateManager:
    """Manager for loading and validating strategy templates from YAML.

    Loads all ``*.yaml`` files from the templates directory and provides
    methods to retrieve templates by ID or type, validate user-provided
    parameters, and get default parameter sets.

    Attributes:
        templates_dir: Path to the directory containing template YAML files.
    """

    def __init__(
        self,
        templates_dir: Path | None = None,
    ) -> None:
        """Initialize the template manager.

        Args:
            templates_dir: Path to templates directory.
                Defaults to ``config/templates``.
        """
        self.templates_dir = templates_dir or Path("config/templates")
        self._templates: dict[str, StrategyTemplate] = {}
        self._loaded = False

    @property
    def templates(self) -> dict[str, StrategyTemplate]:
        """Get all loaded templates, loading on first access.

        Returns:
            Dictionary mapping template IDs to StrategyTemplate objects.
        """
        if not self._loaded:
            self._load_templates()
        return self._templates

    def _load_templates(self) -> None:
        """Load all templates from YAML files in the templates directory.

        Raises:
            FileNotFoundError: If the templates directory does not exist.
            ValueError: If a YAML file is malformed or invalid.
        """
        if not self.templates_dir.exists():
            raise FileNotFoundError(
                f"Templates directory not found: {self.templates_dir}"
            )

        for yaml_file in sorted(self.templates_dir.glob("*.yaml")):
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                continue

            template = StrategyTemplate(**data)
            self._templates[template.id] = template

        self._loaded = True

    def get_template(self, template_id: str) -> StrategyTemplate:
        """Get a template by its unique ID.

        Args:
            template_id: The template identifier string.

        Returns:
            The matching StrategyTemplate.

        Raises:
            ValueError: If the template ID is not found.
        """
        if template_id not in self.templates:
            available = ", ".join(sorted(self.templates.keys()))
            raise ValueError(
                f"Template '{template_id}' not found. "
                f"Available templates: {available}"
            )
        return self.templates[template_id]

    def get_templates_by_type(self, strategy_type: str) -> list[StrategyTemplate]:
        """Get all templates matching a strategy type.

        Args:
            strategy_type: Strategy type to filter by
                (e.g., 'trend_following').

        Returns:
            List of matching StrategyTemplate objects.
        """
        return [
            t for t in self.templates.values()
            if t.type == strategy_type
        ]

    def list_template_ids(self) -> list[str]:
        """List all available template IDs.

        Returns:
            Sorted list of template ID strings.
        """
        return sorted(self.templates.keys())

    def get_default_parameters(
        self, template_id: str
    ) -> dict[str, int | float | bool | str]:
        """Get default parameters for a template.

        Args:
            template_id: The template identifier string.

        Returns:
            Dictionary mapping parameter names to default values.

        Raises:
            ValueError: If the template ID is not found.
        """
        template = self.get_template(template_id)
        return template.get_default_parameters()

    def validate_parameters(
        self,
        template_id: str,
        params: dict[str, Any],  # HIGH-002: Any justified - values can be int/float/bool/str per template spec
    ) -> list[str]:
        """Validate parameters against a template specification.

        Checks that all required parameters are present, have correct
        types, and fall within allowed ranges.

        Args:
            template_id: The template identifier string.
            params: User-provided parameter dictionary. Values can be
                int, float, bool, or str depending on the parameter
                specification in the template.

        Returns:
            List of validation error messages (empty if valid).

        Raises:
            ValueError: If the template ID is not found.
        """
        template = self.get_template(template_id)
        errors: list[str] = []

        # MEDIUM-001: Handle edge case - template expects no parameters but params provided
        if not template.parameters and params:
            errors.append("Template expects no parameters but parameters were provided")
            return errors

        # Check for missing required parameters
        param_specs = {p.name: p for p in template.parameters}
        for name, spec in param_specs.items():
            if name not in params:
                errors.append(f"Missing required parameter: {name}")
                continue

            value = params[name]

            # Type validation
            if spec.type == "int":
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(
                        f"Parameter '{name}' must be int, got {type(value).__name__}"
                    )
                    continue
            elif spec.type == "float":
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(
                        f"Parameter '{name}' must be float, got {type(value).__name__}"
                    )
                    continue
            elif spec.type == "bool":
                if not isinstance(value, bool):
                    errors.append(
                        f"Parameter '{name}' must be bool, got {type(value).__name__}"
                    )
                    continue
            elif spec.type == "str":
                if not isinstance(value, str):
                    errors.append(
                        f"Parameter '{name}' must be str, got {type(value).__name__}"
                    )
                    continue
                # Check choices constraint
                if spec.choices and value not in spec.choices:
                    errors.append(
                        f"Parameter '{name}' must be one of {spec.choices}, "
                        f"got '{value}'"
                    )
                continue

            # Range validation for numeric types
            if spec.type in ("int", "float"):
                # HIGH-001 fix: Validate against NaN/Infinity before range checks
                # Violates DEC-2026-02-08-007 without this check
                import math

                if isinstance(value, float):
                    if math.isnan(value):
                        errors.append(f"Parameter '{name}' cannot be NaN")
                        continue  # Skip range validation
                    if math.isinf(value):
                        errors.append(f"Parameter '{name}' cannot be Infinity")
                        continue  # Skip range validation

                # Range validation
                if spec.min_value is not None and value < spec.min_value:
                    errors.append(
                        f"Parameter '{name}' must be >= {spec.min_value}, "
                        f"got {value}"
                    )
                if spec.max_value is not None and value > spec.max_value:
                    errors.append(
                        f"Parameter '{name}' must be <= {spec.max_value}, "
                        f"got {value}"
                    )

        # Check for unknown parameters
        for name in params:
            if name not in param_specs:
                errors.append(f"Unknown parameter: {name}")

        return errors
