"""Strategy similarity detection to prevent near-duplicate strategies.

Compares a new strategy configuration against existing strategies using
weighted similarity scoring across four dimensions:

- Template ID match (40%): Same template = high overlap.
- Parameter similarity (30%): Normalized distance between parameter sets.
- Symbol overlap (20%): Jaccard similarity of symbol lists.
- Entry logic (10%): Text similarity of template entry logic.

A score >= 70% triggers a warning (not blocking).

Decision: DEC-2026-02-08-006 - Type hints 100% coverage
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Similarity weights (must sum to 1.0)
WEIGHT_TEMPLATE = 0.40
WEIGHT_PARAMS = 0.30
WEIGHT_SYMBOLS = 0.20
WEIGHT_ENTRY_LOGIC = 0.10

# Threshold above which a warning is issued
SIMILARITY_THRESHOLD = 0.70


@dataclass(frozen=True)
class SimilarityResult:
    """Result of comparing two strategies for similarity.

    Attributes:
        strategy_id: ID of the existing strategy being compared.
        strategy_name: Name of the existing strategy.
        overall_score: Weighted similarity score (0.0 to 1.0).
        template_score: Template ID match score (0 or 1).
        params_score: Parameter similarity score (0.0 to 1.0).
        symbols_score: Symbol overlap score (0.0 to 1.0).
        entry_logic_score: Entry logic similarity score (0.0 to 1.0).
        is_similar: Whether score exceeds the similarity threshold.
    """

    strategy_id: str
    strategy_name: str
    overall_score: float
    template_score: float
    params_score: float
    symbols_score: float
    entry_logic_score: float
    is_similar: bool


def _compute_template_score(
    new_template_id: str,
    existing_template_id: str,
) -> float:
    """Score template ID match (binary: 0 or 1).

    Args:
        new_template_id: Template ID of the new strategy.
        existing_template_id: Template ID of the existing strategy.

    Returns:
        1.0 if templates match, 0.0 otherwise.
    """
    return 1.0 if new_template_id == existing_template_id else 0.0


def _compute_params_score(
    new_params: dict[str, Any],
    existing_params: dict[str, Any],
) -> float:
    """Score parameter similarity using normalized distance.

    For numeric parameters, similarity = 1 - |new - existing| / max(|new|, |existing|, 1).
    For non-numeric parameters, similarity = 1 if equal, 0 otherwise.
    Final score is the average across all parameters.

    Args:
        new_params: Parameters of the new strategy.
        existing_params: Parameters of the existing strategy.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    if not new_params and not existing_params:
        return 1.0
    if not new_params or not existing_params:
        return 0.0

    all_keys = set(new_params.keys()) | set(existing_params.keys())
    if not all_keys:
        return 1.0

    total = 0.0
    for key in all_keys:
        if key not in new_params or key not in existing_params:
            total += 0.0
            continue

        new_val = new_params[key]
        old_val = existing_params[key]

        if isinstance(new_val, (int, float)) and isinstance(old_val, (int, float)):
            denominator = max(abs(new_val), abs(old_val), 1.0)
            total += 1.0 - abs(new_val - old_val) / denominator
        else:
            total += 1.0 if new_val == old_val else 0.0

    return total / len(all_keys)


def _compute_symbols_score(
    new_symbols: list[str],
    existing_symbols: list[str],
) -> float:
    """Score symbol overlap using Jaccard similarity.

    Jaccard = |intersection| / |union|.

    Args:
        new_symbols: Symbols of the new strategy.
        existing_symbols: Symbols of the existing strategy.

    Returns:
        Jaccard similarity score between 0.0 and 1.0.
    """
    new_set = set(new_symbols)
    old_set = set(existing_symbols)

    if not new_set and not old_set:
        return 1.0
    if not new_set or not old_set:
        return 0.0

    intersection = new_set & old_set
    union = new_set | old_set
    return len(intersection) / len(union)


def _compute_entry_logic_score(
    new_entry_logic: str,
    existing_entry_logic: str,
) -> float:
    """Score entry logic similarity using word overlap.

    Uses token-level Jaccard similarity (case-insensitive).

    Args:
        new_entry_logic: Entry logic text of the new strategy template.
        existing_entry_logic: Entry logic text of the existing strategy template.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    if not new_entry_logic and not existing_entry_logic:
        return 1.0
    if not new_entry_logic or not existing_entry_logic:
        return 0.0

    new_tokens = set(new_entry_logic.lower().split())
    old_tokens = set(existing_entry_logic.lower().split())

    if not new_tokens or not old_tokens:
        return 0.0

    intersection = new_tokens & old_tokens
    union = new_tokens | old_tokens
    return len(intersection) / len(union)


@dataclass
class StrategyCandidate:
    """Lightweight representation of a strategy for similarity comparison.

    Attributes:
        template_id: Strategy template identifier.
        parameters: Strategy parameter dictionary.
        symbols: List of trading symbols.
        entry_logic: Entry logic description from the template.
    """

    template_id: str
    parameters: dict[str, Any]
    symbols: list[str]
    entry_logic: str = ""


@dataclass
class ExistingStrategy:
    """Lightweight representation of an existing strategy for comparison.

    Attributes:
        strategy_id: Database strategy ID.
        strategy_name: Strategy display name.
        template_id: Template identifier.
        parameters: Strategy parameters.
        symbols: Trading symbols.
        entry_logic: Entry logic description.
    """

    strategy_id: str
    strategy_name: str
    template_id: str
    parameters: dict[str, Any]
    symbols: list[str]
    entry_logic: str = ""


def check_similarity(
    candidate: StrategyCandidate,
    existing: list[ExistingStrategy],
) -> list[SimilarityResult]:
    """Check a new strategy candidate against existing strategies.

    Returns similarity results for ALL existing strategies, sorted by
    overall score descending. Results with ``is_similar=True`` indicate
    strategies that exceed the similarity threshold and should trigger
    a warning to the operator.

    Args:
        candidate: The new strategy being evaluated.
        existing: List of existing strategies to compare against.

    Returns:
        List of SimilarityResult, sorted by overall_score descending.
    """
    results: list[SimilarityResult] = []

    for ex in existing:
        template_score = _compute_template_score(
            candidate.template_id, ex.template_id
        )
        params_score = _compute_params_score(
            candidate.parameters, ex.parameters
        )
        symbols_score = _compute_symbols_score(
            candidate.symbols, ex.symbols
        )
        entry_logic_score = _compute_entry_logic_score(
            candidate.entry_logic, ex.entry_logic
        )

        overall = (
            WEIGHT_TEMPLATE * template_score
            + WEIGHT_PARAMS * params_score
            + WEIGHT_SYMBOLS * symbols_score
            + WEIGHT_ENTRY_LOGIC * entry_logic_score
        )

        is_similar = overall >= SIMILARITY_THRESHOLD

        result = SimilarityResult(
            strategy_id=ex.strategy_id,
            strategy_name=ex.strategy_name,
            overall_score=round(overall, 4),
            template_score=template_score,
            params_score=round(params_score, 4),
            symbols_score=round(symbols_score, 4),
            entry_logic_score=round(entry_logic_score, 4),
            is_similar=is_similar,
        )
        results.append(result)

        if is_similar:
            logger.warning(
                "similar_strategy_detected",
                candidate_template=candidate.template_id,
                existing_strategy_id=ex.strategy_id,
                existing_strategy_name=ex.strategy_name,
                overall_score=result.overall_score,
                threshold=SIMILARITY_THRESHOLD,
            )

    # Sort by overall score descending
    results.sort(key=lambda r: r.overall_score, reverse=True)
    return results
