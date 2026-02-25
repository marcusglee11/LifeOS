"""
Convergence detection for council lens outputs.

Compares parallel lens outputs for structural similarity. When lenses
strongly agree, the challenger review can be fast-pathed (skipped),
saving time and tokens.

Algorithm:
  - Extract text tokens from each lens output (claims, findings, verdicts)
  - Compute pairwise Jaccard similarity between lens token sets
  - Average pairwise similarity = convergence score
  - Score >= threshold (default 0.8) = convergent (fast-path eligible)

This module is advisory — the FSM decides whether to act on convergence.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Optional


# Default convergence threshold (80% agreement)
DEFAULT_THRESHOLD = 0.80


def _extract_tokens(output: Any) -> set[str]:
    """
    Extract normalized text tokens from a lens output dict.

    Recursively walks the dict, extracting string values and splitting
    into lowercase word tokens. Ignores keys starting with '_' (metadata).
    """
    tokens: set[str] = set()

    if isinstance(output, str):
        words = re.findall(r"[a-z0-9_]+", output.lower())
        tokens.update(words)
    elif isinstance(output, dict):
        for key, value in output.items():
            if isinstance(key, str) and key.startswith("_"):
                continue
            tokens.update(_extract_tokens(value))
    elif isinstance(output, (list, tuple)):
        for item in output:
            tokens.update(_extract_tokens(item))

    return tokens


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Compute Jaccard similarity between two token sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def compute_convergence(
    lens_results: Mapping[str, Any],
    threshold: float = DEFAULT_THRESHOLD,
) -> ConvergenceResult:
    """
    Compute convergence score across lens outputs.

    Args:
        lens_results: Dict mapping lens_name → output dict (from FSM).
        threshold: Similarity threshold for convergence (default 0.80).

    Returns:
        ConvergenceResult with score, convergent flag, and pairwise details.
    """
    # Filter out None/waived results
    active = {
        name: output
        for name, output in lens_results.items()
        if output is not None
    }

    if len(active) < 2:
        return ConvergenceResult(
            score=1.0,
            convergent=True,
            lens_count=len(active),
            pairwise={},
            threshold=threshold,
        )

    # Extract token sets per lens
    token_sets = {name: _extract_tokens(output) for name, output in active.items()}

    # Compute all pairwise similarities
    names = sorted(token_sets.keys())
    pairwise: dict[str, float] = {}
    total_sim = 0.0
    pair_count = 0

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            key = f"{names[i]}|{names[j]}"
            sim = _jaccard_similarity(token_sets[names[i]], token_sets[names[j]])
            pairwise[key] = round(sim, 4)
            total_sim += sim
            pair_count += 1

    avg_score = total_sim / pair_count if pair_count > 0 else 0.0

    return ConvergenceResult(
        score=round(avg_score, 4),
        convergent=avg_score >= threshold,
        lens_count=len(active),
        pairwise=pairwise,
        threshold=threshold,
    )


class ConvergenceResult:
    """Result of convergence analysis across lens outputs."""

    __slots__ = ("score", "convergent", "lens_count", "pairwise", "threshold")

    def __init__(
        self,
        score: float,
        convergent: bool,
        lens_count: int,
        pairwise: dict[str, float],
        threshold: float,
    ):
        self.score = score
        self.convergent = convergent
        self.lens_count = lens_count
        self.pairwise = pairwise
        self.threshold = threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "convergent": self.convergent,
            "lens_count": self.lens_count,
            "pairwise": self.pairwise,
            "threshold": self.threshold,
        }
