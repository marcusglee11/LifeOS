"""
v2.2.1 schema gate validator tests: validate_lens_output, validate_synthesis_output,
validate_challenger_output. 12 tests.
"""
from __future__ import annotations

import pytest

from runtime.orchestration.council.schema_gate import (
    validate_lens_output,
    validate_synthesis_output,
    validate_challenger_output,
)
from runtime.orchestration.council.policy import load_council_policy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_policy():
    return load_council_policy()


def make_valid_lens_review(lens_name="Risk"):
    return {
        "run_type": "review",
        "lens_name": lens_name,
        "operator_view": ["point 1", "point 2"],
        "confidence": "high",
        "notes": "No issues found.",
        "claims": [{"claim_id": "c1", "statement": "Safe", "evidence_refs": ["REF:1"]}],
        "verdict_recommendation": "Accept",
    }


def make_valid_synthesis_t1():
    return {
        "run_type": "review",
        "tier": "T1",
        "verdict": "Accept",
        "fix_plan": [],
        "complexity_budget": {"net_human_steps": 0},
        "operator_view": ["point 1", "point 2"],
        "coverage_degraded": False,
        "waived_lenses": [],
        "evidence_summary": {"ref_count": 3, "assumption_count": 0},
    }


def make_valid_challenger_t1():
    return {
        "weakest_claim": "Claim X may be unproven",
        "stress_test": "What if Y fails?",
        "material_issue": False,
        "issue_class": "other",
        "severity": "p2",
        "required_action": "rework_synthesis",
        "notes": "Minor concern only.",
    }


# ---------------------------------------------------------------------------
# Lens output: review
# ---------------------------------------------------------------------------


def test_lens_output_review_valid():
    policy = make_policy()
    result = validate_lens_output(make_valid_lens_review(), policy, "review", "T1")
    assert result.valid


def test_lens_output_review_missing_claims():
    policy = make_policy()
    raw = make_valid_lens_review()
    del raw["claims"]
    result = validate_lens_output(raw, policy, "review", "T1")
    assert not result.valid
    assert any("claims" in e for e in result.errors)


def test_lens_output_review_claim_without_id():
    policy = make_policy()
    raw = make_valid_lens_review()
    raw["claims"] = [{"statement": "No ID here", "evidence_refs": ["REF:1"]}]
    result = validate_lens_output(raw, policy, "review", "T1")
    assert not result.valid
    assert any("claim_id" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Lens output: advisory
# ---------------------------------------------------------------------------


def test_lens_output_advisory_valid():
    policy = make_policy()
    raw = {
        "run_type": "advisory",
        "lens_name": "Risk",
        "operator_view": ["point 1", "point 2"],
        "confidence": "medium",
        "notes": "Some thoughts.",
        "claims": [],
        "recommendations": [
            {"action": "monitor", "rationale": "r", "expected_impact": "low", "confidence": "medium"}
        ],
        "evidence_status": "speculative",
    }
    result = validate_lens_output(raw, policy, "advisory", "T1")
    assert result.valid


def test_lens_output_advisory_missing_evidence_status():
    policy = make_policy()
    raw = {
        "run_type": "advisory",
        "lens_name": "Risk",
        "operator_view": ["point 1", "point 2"],
        "confidence": "medium",
        "notes": "Some thoughts.",
        "claims": [],
        "recommendations": [{"action": "monitor"}],
        # evidence_status intentionally missing
    }
    result = validate_lens_output(raw, policy, "advisory", "T1")
    assert not result.valid
    assert any("evidence_status" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Synthesis output
# ---------------------------------------------------------------------------


def test_synthesis_review_valid():
    policy = make_policy()
    result = validate_synthesis_output(make_valid_synthesis_t1(), policy, "T1", "review")
    assert result.valid


def test_synthesis_t2_requires_ledger():
    policy = make_policy()
    raw = make_valid_synthesis_t1()
    raw["tier"] = "T2"
    # No contradiction_ledger key
    result = validate_synthesis_output(raw, policy, "T2", "review")
    assert not result.valid
    assert any("ledger" in e.lower() or "contradiction" in e.lower() for e in result.errors)


def test_synthesis_t1_no_ledger_ok():
    policy = make_policy()
    result = validate_synthesis_output(make_valid_synthesis_t1(), policy, "T1", "review")
    assert result.valid


# ---------------------------------------------------------------------------
# Challenger output
# ---------------------------------------------------------------------------


def test_challenger_output_valid():
    policy = make_policy()
    result = validate_challenger_output(make_valid_challenger_t1(), policy, "T1")
    assert result.valid


def test_challenger_t3_requires_ledger_check():
    policy = make_policy()
    raw = make_valid_challenger_t1()
    # Missing ledger_completeness_ok + missing_disagreements for T3
    result = validate_challenger_output(raw, policy, "T3")
    assert not result.valid
    assert any("ledger_completeness_ok" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Contradiction ledger entries
# ---------------------------------------------------------------------------


def test_contradiction_ledger_valid_entry():
    policy = make_policy()
    raw = make_valid_synthesis_t1()
    raw["tier"] = "T2"
    raw["contradiction_ledger"] = [{
        "topic": "scope",
        "positions": {"Risk": "c1", "Governance": "c2"},
        "resolution": {"decision": "accept", "rationale": "both valid"},
        "status": "resolved",
    }]
    result = validate_synthesis_output(raw, policy, "T2", "review")
    assert result.valid


def test_contradiction_ledger_missing_positions():
    policy = make_policy()
    raw = make_valid_synthesis_t1()
    raw["tier"] = "T2"
    raw["contradiction_ledger"] = [{"topic": "scope"}]  # positions missing
    result = validate_synthesis_output(raw, policy, "T2", "review")
    assert not result.valid
    assert any("positions" in e for e in result.errors)
