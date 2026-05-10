from pathlib import Path

import pytest

from runtime.orchestration.intent_fidelity import (
    build_source_manifest,
    check_fidelity,
    hash_text,
    load_lexicon,
)

FIXTURE_DIR = Path("runtime/tests/fixtures/intent_fidelity")
LEXICON_PATH = Path("runtime/data/intent_lexicon_v1.json")


def _read(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _manifest(source_text: str):
    return build_source_manifest(
        work_item_id="W-1",
        lexicon_version="1.0.0",
        source_discovery={
            "mode": "local_file",
            "commands_or_uris": ["source.md"],
            "command_output_hashes_sha256": [hash_text(source_text)],
            "completeness_claimed_by": "tool",
        },
        sources=[
            {
                "source_id": "source-1",
                "source_type": "local_file",
                "uri": "source.md",
                "retrieval_method": "local_file",
                "authority_tier": "current_ceo_instruction",
                "content": source_text,
            }
        ],
    )


def _report(source: str, brief: str):
    return check_fidelity(brief, "worker_prompt", _manifest(source), load_lexicon(LEXICON_PATH))


def test_v120_bad_brief_polish_framing_of_destructive_intent_fails():
    report = _report(_read("v120_source.md"), _read("v120_bad_brief.md"))
    assert report.decision == "fail_closed"
    assert report.checks["intent_inversion"].status == "fail"


def test_v120_good_brief_faithful_preservation_passes():
    report = _report(_read("v120_source.md"), _read("v120_good_brief.md"))
    assert report.decision == "pass"


def test_non_destructive_boundary_inversions_fail():
    report = _report(
        _read("non_destructive_source.md"),
        _read("non_destructive_bad_brief.md"),
    )
    assert report.decision == "fail_closed"
    assert report.checks["non_destructive_boundary"].status == "fail"


def test_ambiguous_broad_terms_warn_only_when_no_blocking_class_exists():
    report = _report(_read("non_destructive_source.md"), "Polish and clean up the copy.")
    assert report.decision == "warning_only"
    assert report.checks["hedge_or_softening"].status == "warn"


def test_unsupported_paraphrase_emits_requires_conductor_review():
    report = _report(_read("v120_source.md"), "Make the legacy panel less prominent.")
    assert report.decision == "requires_conductor_review"
    assert report.checks["verbatim_preservation"].status == "requires_conductor_review"


def test_not_yet_implemented_placeholder():
    pytest.skip("placeholder for semantic paraphrase model review outside v0.3 lexicon scope")
