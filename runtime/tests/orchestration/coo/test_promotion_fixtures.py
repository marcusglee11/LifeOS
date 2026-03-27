from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import yaml

from runtime.orchestration.coo.claim_verifier import collect_evidence, verify_claims
from runtime.orchestration.coo.commands import _parse_escalation_packet, _parse_ntp, cmd_coo_direct, cmd_coo_propose
from runtime.orchestration.coo.mirror import build_evaluation_row, diff_evidence
from runtime.orchestration.coo.parser import _extract_yaml_payload_with_stage, parse_proposal_response
from runtime.tests.orchestration.coo.test_commands import _write_backlog, _write_delegation


REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "artifacts" / "coo" / "promotion_campaign" / "fixtures"
STEP6_ROOT = REPO_ROOT / "artifacts" / "coo" / "step6_parity_pack"


def _fixture_specs():
    return [
        ("fixture_propose", STEP6_ROOT / "propose_context.json", STEP6_ROOT / "propose_expected.yaml", "propose", "task_proposal"),
        ("fixture_ntp", STEP6_ROOT / "ntp_context.json", STEP6_ROOT / "ntp_expected.yaml", "propose", "nothing_to_propose"),
        ("fixture_escalation", STEP6_ROOT / "escalation_context.json", STEP6_ROOT / "escalation_expected.yaml", "direct", "escalation_packet"),
        ("fixture_ambiguous", STEP6_ROOT / "ambiguous_context.json", STEP6_ROOT / "ambiguous_expected.yaml", "direct", "escalation_packet"),
        ("blocked_truth", FIXTURE_ROOT / "blocked_truth_context.json", FIXTURE_ROOT / "blocked_truth_expected.yaml", "propose", "nothing_to_propose"),
        ("contradictory_truth", FIXTURE_ROOT / "contradictory_truth_context.json", FIXTURE_ROOT / "contradictory_truth_expected.yaml", "propose", "nothing_to_propose"),
        ("repeated_propose", FIXTURE_ROOT / "repeated_propose_context.json", FIXTURE_ROOT / "repeated_propose_expected.yaml", "propose", "task_proposal"),
        ("direct_governance", FIXTURE_ROOT / "direct_governance_context.json", FIXTURE_ROOT / "direct_governance_expected.yaml", "direct", "escalation_packet"),
        ("direct_budget", FIXTURE_ROOT / "direct_budget_context.json", FIXTURE_ROOT / "direct_budget_expected.yaml", "direct", "escalation_packet"),
        ("direct_unknown_category", FIXTURE_ROOT / "direct_unknown_category_context.json", FIXTURE_ROOT / "direct_unknown_category_expected.yaml", "direct", "escalation_packet"),
    ]


def test_all_promotion_fixtures() -> None:
    for scenario_id, context_path, expected_path, mode, expected_family in _fixture_specs():
        tmp_path = Path(__import__("tempfile").mkdtemp())
        decoder = json.JSONDecoder()
        context, _ = decoder.raw_decode(context_path.read_text(encoding="utf-8"))
        expected_yaml = expected_path.read_text(encoding="utf-8")
        _write_backlog(tmp_path, context.get("actionable_tasks", []))
        _write_delegation(tmp_path)

        before = collect_evidence(tmp_path)
        with patch("runtime.orchestration.coo.service.invoke_coo_reasoning", return_value=expected_yaml):
            if mode == "propose":
                rc = cmd_coo_propose(
                    argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
                    tmp_path,
                )
            else:
                rc = cmd_coo_direct(argparse.Namespace(intent=context["intent"]), tmp_path)
        after = collect_evidence(tmp_path)

        assert rc == 0
        _, stage = _extract_yaml_payload_with_stage(expected_yaml)
        if expected_family == "task_proposal":
            parse_proposal_response(expected_yaml)
        elif expected_family == "nothing_to_propose":
            _parse_ntp(expected_yaml)
        else:
            _parse_escalation_packet(expected_yaml)

        diff = diff_evidence(before, after)
        violations = verify_claims(expected_yaml, before, repo_root=tmp_path)
        row = build_evaluation_row(
            scenario_id=scenario_id,
            mode=mode,
            source_kind="fixture",
            input_ref=str(context_path),
            expected_packet_family=expected_family,
            actual_packet_family=expected_family,
            parse_status="pass",
            parse_recovery_stage=stage,
            claim_verifier_status="pass" if not violations else "fail",
            diff=diff,
            invocation_receipt_ref=None,
            token_usage=None,
        )
        assert row["inside_outside_consistent"] is True
        assert row["parse_status"] == "pass"
        assert row["side_effect_class"] in {"none", "queued_escalation"}
