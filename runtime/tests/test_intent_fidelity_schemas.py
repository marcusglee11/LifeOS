import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMAS = [
    Path("schemas/intent_source_manifest_v1.json"),
    Path("schemas/intent_fidelity_report_v1.json"),
    Path("schemas/intent_review_report_v1.json"),
    Path("schemas/conductor_fidelity_verification_v1.json"),
    Path("schemas/intent_fidelity_bypass_v1.json"),
]
SHA = "a" * 64
ISO = "2026-05-10T00:00:00+00:00"


def _load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _valid_examples() -> dict[str, dict]:
    return {
        "intent_source_manifest_v1": {
            "schema_version": "intent_source_manifest.v1",
            "work_item_id": "W-1",
            "lexicon_version": "1.0.0",
            "created_at": ISO,
            "created_by": "tool",
            "source_discovery": {
                "mode": "local_file",
                "commands_or_uris": ["fixtures/source.md"],
                "command_output_hashes_sha256": [SHA],
                "cutoff_timestamp": ISO,
                "completeness_claimed_by": "tool",
            },
            "sources": [
                {
                    "source_id": "source-1",
                    "source_type": "local_file",
                    "uri": "fixtures/source.md",
                    "retrieved_at": ISO,
                    "retrieval_method": "local_file",
                    "content_hash_sha256": SHA,
                    "source_of_source_hash_sha256": None,
                    "authority_tier": "current_ceo_instruction",
                    "extracted_intents": [
                        {
                            "intent_class": "absence",
                            "phrase": "remove",
                            "source_id": "source-1",
                            "line_or_offset": "line 1",
                            "surrounding_context": "remove this",
                            "blocking_strength": "blocking",
                            "guard_triggered": None,
                        }
                    ],
                }
            ],
            "missing_sources": [],
        },
        "intent_fidelity_report_v1": {
            "schema_version": "intent_fidelity_report.v1",
            "work_item_id": "W-1",
            "brief_type": "worker_prompt",
            "brief_uri": "brief.md",
            "brief_hash_sha256": SHA,
            "source_manifest_uri": "manifest.json",
            "decision": "pass",
            "checks": {
                "source_coverage": {"status": "pass", "details": []},
                "determinism_check": {"status": "pass", "details": []},
            },
            "false_positive_fixtures_passed": 4,
        },
        "intent_review_report_v1": {
            "schema_version": "intent_review_report.v1",
            "work_item_id": "W-1",
            "reviewer_surface": "openclaw",
            "reviewer_session": "review-1",
            "verdict": "approve",
            "findings": [
                {
                    "severity": "note",
                    "title": "Evidence only",
                    "recommendation": "No authority granted.",
                }
            ],
            "authority_note": "reviewer_output_is_evidence_only",
        },
        "conductor_fidelity_verification_v1": {
            "schema_version": "conductor_fidelity_verification.v1",
            "work_item_id": "W-1",
            "brief_type": "worker_prompt",
            "brief_hash_sha256": SHA,
            "brief_author_session": "brief-1",
            "conductor_verification_session": "conductor-1",
            "source_manifest_hash_sha256": SHA,
            "fidelity_report_hash_sha256": SHA,
            "conductor_independently_confirmed": True,
            "fidelity_status": "preserved_intent",
            "handoff_candidate": True,
            "implementation_authority_granted": False,
            "required_next_gate": "dispatch_gate",
            "forbidden_next_steps": [
                "implementation_without_reload",
                "additive_or_polish_framing_if_source_requires_absence",
                "reviewer_output_as_authority",
                "compression_as_canonical_memory",
            ],
            "verified_by": "conductor",
            "verified_at": ISO,
        },
        "intent_fidelity_bypass_v1": {
            "schema_version": "intent_fidelity_bypass.v1",
            "work_item_id": "W-1",
            "requested_by": "tool",
            "authorized_by": "conductor",
            "reason": "known false positive",
            "sources_skipped": [],
            "risk_accepted": "warning-only audit risk",
            "scope": "warning-only fixture",
            "expires_at": ISO,
            "single_use": True,
            "not_authorized_for": [
                "external_send",
                "runtime_activation",
                "credential_change",
                "destructive_cleanup",
            ],
        },
    }


@pytest.mark.parametrize("schema_path", SCHEMAS)
def test_schema_file_exists_and_is_valid_json_schema(schema_path):
    assert schema_path.exists()
    Draft202012Validator.check_schema(_load_schema(schema_path))


@pytest.mark.parametrize("schema_path", SCHEMAS)
def test_schema_version_metadata_matches_filename(schema_path):
    schema = _load_schema(schema_path)
    assert schema["schema_version"] == schema_path.stem


@pytest.mark.parametrize("schema_path", SCHEMAS)
def test_valid_example_data_passes_validation(schema_path):
    schema = _load_schema(schema_path)
    Draft202012Validator(schema).validate(_valid_examples()[schema_path.stem])


@pytest.mark.parametrize("schema_path", SCHEMAS)
def test_invalid_malformed_data_fails_validation(schema_path):
    schema = _load_schema(schema_path)
    example = dict(_valid_examples()[schema_path.stem])
    example.pop("schema_version")
    errors = list(Draft202012Validator(schema).iter_errors(example))
    assert errors
