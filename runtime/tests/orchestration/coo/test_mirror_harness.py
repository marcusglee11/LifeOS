"""Fixture-first mirror harness tests for COO propose/direct flows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import yaml

from runtime.orchestration.coo.claim_verifier import collect_evidence, verify_claims
from runtime.orchestration.coo.commands import (
    _parse_escalation_packet,
    _parse_ntp,
    cmd_coo_direct,
    cmd_coo_propose,
)
from runtime.orchestration.coo.mirror import build_evaluation_row, diff_evidence
from runtime.orchestration.coo.parser import (
    _extract_yaml_payload_with_stage,
    parse_proposal_response,
)
from runtime.tests.orchestration.coo.test_commands import _write_backlog, _write_delegation

REPO_ROOT = Path(__file__).resolve().parents[4]
PARITY_PACK = REPO_ROOT / "artifacts" / "coo" / "step6_parity_pack"


def _load_json(name: str) -> dict:
    text = (PARITY_PACK / name).read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    payload, _ = decoder.raw_decode(text)
    return payload


def _load_text(name: str) -> str:
    return (PARITY_PACK / name).read_text(encoding="utf-8")


def test_mirror_propose_parity_row_no_side_effects(tmp_path: Path, capsys) -> None:
    propose_context = _load_json("propose_context.json")
    expected_yaml = _load_text("propose_expected.yaml")

    _write_backlog(tmp_path, propose_context["actionable_tasks"])
    delegation_path = tmp_path / "config" / "governance" / "delegation_envelope.yaml"
    delegation_path.parent.mkdir(parents=True, exist_ok=True)
    delegation_path.write_text(
        yaml.safe_dump(propose_context["delegation_envelope"], sort_keys=False),
        encoding="utf-8",
    )

    before = collect_evidence(tmp_path)
    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning", return_value=expected_yaml
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
            tmp_path,
        )
    assert rc == 0
    after = collect_evidence(tmp_path)

    _, stage = _extract_yaml_payload_with_stage(expected_yaml)
    parsed_expected = parse_proposal_response(expected_yaml)
    parsed_actual = parse_proposal_response(capsys.readouterr().out)
    assert [proposal.task_id for proposal in parsed_actual] == [
        proposal.task_id for proposal in parsed_expected
    ]

    diff = diff_evidence(before, after)
    violations = verify_claims(expected_yaml, before, repo_root=tmp_path)
    row = build_evaluation_row(
        scenario_id="fixture_propose_parity",
        mode="propose",
        source_kind="fixture",
        input_ref=str(PARITY_PACK / "propose_context.json"),
        expected_packet_family="task_proposal",
        actual_packet_family="task_proposal",
        parse_status="pass",
        parse_recovery_stage=stage,
        claim_verifier_status="pass" if not violations else "fail",
        diff=diff,
        invocation_receipt_ref=None,
        token_usage=None,
        notes="parity_pack_replay",
    )

    assert row["side_effect_class"] == "none"
    assert row["inside_outside_consistent"] is True
    assert row["new_escalation_ids"] == []
    assert row["new_order_ids"] == []


def test_mirror_ntp_parity_row_no_side_effects(tmp_path: Path, capsys) -> None:
    ntp_context = _load_json("ntp_context.json")
    expected_yaml = _load_text("ntp_expected.yaml")

    _write_backlog(tmp_path, ntp_context["actionable_tasks"])
    delegation_path = tmp_path / "config" / "governance" / "delegation_envelope.yaml"
    delegation_path.parent.mkdir(parents=True, exist_ok=True)
    delegation_path.write_text(
        yaml.safe_dump(ntp_context["delegation_envelope"], sort_keys=False),
        encoding="utf-8",
    )

    before = collect_evidence(tmp_path)
    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning", return_value=expected_yaml
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
            tmp_path,
        )
    assert rc == 0
    after = collect_evidence(tmp_path)

    _, stage = _extract_yaml_payload_with_stage(expected_yaml)
    parsed_actual = _parse_ntp(capsys.readouterr().out)
    assert parsed_actual["schema_version"] == "nothing_to_propose.v1"

    diff = diff_evidence(before, after)
    violations = verify_claims(expected_yaml, before, repo_root=tmp_path)
    row = build_evaluation_row(
        scenario_id="fixture_ntp_parity",
        mode="propose",
        source_kind="fixture",
        input_ref=str(PARITY_PACK / "ntp_context.json"),
        expected_packet_family="nothing_to_propose",
        actual_packet_family="nothing_to_propose",
        parse_status="pass",
        parse_recovery_stage=stage,
        claim_verifier_status="pass" if not violations else "fail",
        diff=diff,
        invocation_receipt_ref=None,
        token_usage=None,
        notes="parity_pack_replay",
    )

    assert row["side_effect_class"] == "none"
    assert row["inside_outside_consistent"] is True


def test_mirror_direct_escalation_parity_queues_side_effect(tmp_path: Path, capsys) -> None:
    escalation_context = _load_json("escalation_context.json")
    expected_yaml = _load_text("escalation_expected.yaml")

    _write_backlog(tmp_path, [])
    _write_delegation(tmp_path)

    before = collect_evidence(tmp_path)
    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning", return_value=expected_yaml
    ):
        rc = cmd_coo_direct(argparse.Namespace(intent=escalation_context["intent"]), tmp_path)
    assert rc == 0
    after = collect_evidence(tmp_path)

    _, stage = _extract_yaml_payload_with_stage(expected_yaml)
    packet = _parse_escalation_packet(expected_yaml)
    out = capsys.readouterr().out
    assert "queued:" in out

    diff = diff_evidence(before, after)
    violations = verify_claims(expected_yaml, before, repo_root=tmp_path)
    row = build_evaluation_row(
        scenario_id="fixture_direct_escalation_parity",
        mode="direct",
        source_kind="fixture",
        input_ref=str(PARITY_PACK / "escalation_context.json"),
        expected_packet_family="escalation_packet",
        actual_packet_family="escalation_packet",
        parse_status="pass",
        parse_recovery_stage=stage,
        claim_verifier_status="pass" if not violations else "fail",
        diff=diff,
        invocation_receipt_ref=None,
        token_usage=None,
        notes=packet["type"],
    )

    assert row["side_effect_class"] == "queued_escalation"
    assert row["inside_outside_consistent"] is True
    assert len(row["new_escalation_ids"]) == 1
