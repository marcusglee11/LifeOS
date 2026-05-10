import json
from datetime import datetime

from runtime.orchestration.intent_fidelity import (
    build_source_manifest,
    hash_text,
    manifest_to_dict,
    validate_manifest_completeness,
)

SOURCE_TEXT = "Remove the legacy panel."


def _source(content: str = SOURCE_TEXT) -> dict:
    return {
        "source_id": "source-1",
        "source_type": "local_file",
        "uri": "runtime/tests/fixtures/intent_fidelity/v120_source.md",
        "retrieval_method": "local_file",
        "authority_tier": "current_ceo_instruction",
        "content": content,
    }


def _discovery() -> dict:
    return {
        "mode": "local_file",
        "commands_or_uris": ["runtime/tests/fixtures/intent_fidelity/v120_source.md"],
        "command_output_hashes_sha256": [hash_text(SOURCE_TEXT)],
        "completeness_claimed_by": "tool",
    }


def test_basic_manifest_creation_with_required_fields():
    manifest = build_source_manifest("W-1", "1.0.0", _discovery(), [_source()])
    payload = manifest_to_dict(manifest)
    assert payload["schema_version"] == "intent_source_manifest.v1"
    assert payload["work_item_id"] == "W-1"
    assert payload["sources"][0]["source_id"] == "source-1"
    assert payload["sources"][0]["extracted_intents"][0]["intent_class"] == "absence"


def test_missing_fail_closed_source_causes_validation_failure():
    manifest = build_source_manifest(
        "W-1",
        "1.0.0",
        _discovery(),
        [_source()],
        missing_sources=[
            {
                "expected_source": "CEO issue comment",
                "reason_missing": "not found",
                "disposition": "fail_closed",
            }
        ],
    )
    complete, issues = validate_manifest_completeness(manifest)
    assert not complete
    assert "CEO issue comment" in issues[0]


def test_missing_not_required_source_passes_validation():
    manifest = build_source_manifest(
        "W-1",
        "1.0.0",
        _discovery(),
        [_source()],
        missing_sources=[
            {
                "expected_source": "optional transcript",
                "reason_missing": "not applicable",
                "disposition": "not_required",
            }
        ],
    )
    assert validate_manifest_completeness(manifest) == (True, [])


def test_content_hash_is_populated_correctly():
    manifest = build_source_manifest("W-1", "1.0.0", _discovery(), [_source()])
    assert manifest.sources[0]["content_hash_sha256"] == hash_text(SOURCE_TEXT)


def test_timestamp_format():
    manifest = build_source_manifest("W-1", "1.0.0", _discovery(), [_source()])
    parsed = datetime.fromisoformat(manifest.created_at)
    assert parsed.tzinfo is not None


def test_serialization_round_trip():
    manifest = build_source_manifest("W-1", "1.0.0", _discovery(), [_source()])
    payload = manifest_to_dict(manifest)
    assert "_content" not in payload["sources"][0]
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload
