"""
Self-contained seat prompt payload builder for the council runner.

Assembles all context a seat needs to render a verdict without accessing
external files. This eliminates provider-side file reads and makes seat
prompts reproducible and archivable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import warnings
from typing import Any, Mapping

logger = logging.getLogger(__name__)

# Default token budget per seat payload (conservative; fits all supported providers)
DEFAULT_TOKEN_BUDGET = 8_000

# Rough chars-per-token estimate for truncation heuristics (conservative)
_CHARS_PER_TOKEN = 3


# ---------------------------------------------------------------------------
# Required top-level sections in every seat payload
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = (
    "review_objective",
    "decision_question",
    "sub_questions",
    "scope_statement",
    "ccp_excerpt",
    "output_schema",
)


def build_seat_payload(
    *,
    ccp: Mapping[str, Any],
    lens_name: str,
    lens_instructions: str = "",
    review_packet_excerpt: str = "",
    implementation_evidence: str = "",
    verification_summary: str = "",
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> dict[str, Any]:
    """
    Build a self-contained seat prompt payload.

    The payload shape is identical for every seat; lens-specific instructions
    are appended on top of the shared core.

    Args:
        ccp: Full CCP dict (Council Context Pack).
        lens_name: Name of the seat/lens receiving this payload.
        lens_instructions: Lens-specific review instructions to add on top.
        review_packet_excerpt: Compact excerpt from the review packet.
        implementation_evidence: Summary of relevant code/config evidence.
        verification_summary: Latest verification results (test output, etc.).
        token_budget: Maximum token budget for the full payload.

    Returns:
        Dict with required sections; truncation warnings logged and recorded.
    """
    header = ccp.get("header") or ccp
    sections = ccp.get("sections") or {}

    review_objective = str(
        sections.get("objective") or header.get("aur_id") or "Review requested."
    )
    decision_question = str(
        sections.get("decision_question") or "Does this change meet acceptance criteria?"
    )
    sub_questions_raw = sections.get("sub_questions") or []
    if isinstance(sub_questions_raw, list):
        sub_questions = [str(q) for q in sub_questions_raw]
    else:
        sub_questions = [str(sub_questions_raw)]

    scope_statement = str(
        sections.get("scope") or sections.get("constrained_scope") or "Scope: as defined in CCP."
    )
    constraints = sections.get("constraints") or []
    if isinstance(constraints, list):
        scope_statement += "\nConstraints:\n" + "\n".join(f"- {c}" for c in constraints)

    # Compact CCP excerpt: header fields only
    ccp_excerpt = _compact_ccp_excerpt(ccp)

    output_schema = _output_schema()

    payload: dict[str, Any] = {
        "lens_name": lens_name,
        "review_objective": review_objective,
        "decision_question": decision_question,
        "sub_questions": sub_questions,
        "scope_statement": scope_statement,
        "ccp_excerpt": ccp_excerpt,
        "review_packet_excerpt": review_packet_excerpt,
        "implementation_evidence": implementation_evidence,
        "verification_summary": verification_summary,
        "lens_instructions": lens_instructions,
        "output_schema": output_schema,
    }

    payload, truncated = _enforce_budget(payload, token_budget)
    if truncated:
        msg = (
            f"[{lens_name}] seat payload truncated fields to fit "
            f"{token_budget}-token budget: {truncated}"
        )
        logger.warning(msg)
        warnings.warn(msg, stacklevel=2)
        payload["_truncated_fields"] = truncated

    return payload


def hash_payload(payload: Mapping[str, Any]) -> str:
    """Return SHA-256 hex of the canonical JSON representation of a payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compact_ccp_excerpt(ccp: Mapping[str, Any]) -> dict[str, Any]:
    """Extract a compact, JSON-safe subset of the CCP for inline context."""
    header = dict(ccp.get("header") or ccp)
    # Omit large nested blobs; keep identifying metadata
    for key in ("model_plan_v1", "seat_overrides"):
        header.pop(key, None)

    sections = ccp.get("sections") or {}
    compact_sections: dict[str, Any] = {}
    for key in ("objective", "scope", "constraints", "artifacts"):
        value = sections.get(key)
        if value is not None:
            # Truncate long string values
            if isinstance(value, str) and len(value) > 800:
                compact_sections[key] = value[:800] + "…[truncated]"
            else:
                compact_sections[key] = value

    return {"header": header, "sections": compact_sections}


def _output_schema() -> dict[str, Any]:
    """Return the required output schema for normalized seat responses."""
    return {
        "required_fields": [
            "verdict",
            "findings",
            "risks",
            "fixes",
            "open_questions",
            "confidence",
            "assumptions",
            "complexity_budget",
        ],
        "verdict_values": ["Accept", "Revise", "Reject"],
        "confidence_values": ["low", "medium", "high"],
        "format": "YAML",
        "example": {
            "verdict": "Accept",
            "confidence": "high",
            "findings": ["Finding 1"],
            "risks": ["Risk 1"],
            "fixes": [],
            "open_questions": [],
            "assumptions": ["Assumption 1"],
            "complexity_budget": "low",
        },
    }


def _enforce_budget(
    payload: dict[str, Any],
    token_budget: int,
) -> tuple[dict[str, Any], list[str]]:
    """
    Truncate optional evidence fields to fit within the token budget.

    Required sections (REQUIRED_SECTIONS) are never truncated.
    Optional fields are trimmed in order of least importance.
    """
    char_budget = token_budget * _CHARS_PER_TOKEN
    truncated: list[str] = []

    # Fields that can be trimmed, in order of least importance
    trimmable = [
        "implementation_evidence",
        "verification_summary",
        "review_packet_excerpt",
        "lens_instructions",
    ]

    current_size = len(json.dumps(payload, default=str))
    if current_size <= char_budget:
        return payload, truncated

    for field in trimmable:
        if current_size <= char_budget:
            break
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            continue
        # Trim to half, then recalculate
        trimmed = value[: max(200, len(value) // 2)] + "…[truncated]"
        payload[field] = trimmed
        truncated.append(field)
        current_size = len(json.dumps(payload, default=str))

    return payload, truncated
