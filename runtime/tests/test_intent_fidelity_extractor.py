from dataclasses import asdict
from pathlib import Path

from runtime.orchestration.intent_fidelity import (
    determinism_check,
    extract_intents,
    load_lexicon,
)

FIXTURE_DIR = Path("runtime/tests/fixtures/intent_fidelity")
LEXICON_PATH = Path("runtime/data/intent_lexicon_v1.json")


def _lexicon():
    return load_lexicon(LEXICON_PATH)


def _fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_extract_intents_finds_absence_phrases():
    spans = extract_intents(_fixture("v120_source.md"), "v120", _lexicon())
    assert any(span.intent_class == "absence" and span.phrase == "remove" for span in spans)
    assert any(span.intent_class == "absence" and span.phrase == "delete" for span in spans)
    assert any(span.blocking_strength == "blocking" for span in spans)


def test_negation_guard_prevents_false_positive():
    spans = extract_intents(_fixture("false_positive_negation.md"), "negation", _lexicon())
    assert not [span for span in spans if span.intent_class == "absence"]


def test_historical_guard_prevents_false_positive():
    spans = extract_intents(_fixture("false_positive_historical.md"), "historical", _lexicon())
    assert not [span for span in spans if span.intent_class == "absence"]


def test_hypothetical_guard_prevents_false_positive():
    spans = extract_intents(_fixture("false_positive_hypothetical.md"), "hypothetical", _lexicon())
    assert not [span for span in spans if span.intent_class == "absence"]


def test_third_party_quote_guard_prevents_false_positive():
    spans = extract_intents(_fixture("false_positive_third_party_quote.md"), "quote", _lexicon())
    assert not [span for span in spans if span.intent_class == "absence"]


def test_softening_inversion_warning_alone_becomes_blocking_with_absence():
    lexicon = _lexicon()
    warning_only = extract_intents("Polish and clean up the report.", "brief", lexicon)
    assert {span.blocking_strength for span in warning_only} == {"warning"}

    with_absence = extract_intents(
        "Remove the panel, then polish any remaining copy.",
        "source",
        lexicon,
    )
    softening = [span for span in with_absence if span.intent_class == "softening_inversion"]
    assert softening
    assert {span.blocking_strength for span in softening} == {"blocking"}


def test_deterministic_rerun_produces_identical_results():
    text = _fixture("v120_source.md")
    lexicon = _lexicon()
    first = [asdict(span) for span in extract_intents(text, "v120", lexicon)]
    second = [asdict(span) for span in extract_intents(text, "v120", lexicon)]
    assert first == second
    assert determinism_check(text, lexicon)


def test_case_folding_works():
    spans = extract_intents("REMOVE the old banner and DELETE the card.", "case", _lexicon())
    assert [span.phrase for span in spans] == ["remove", "delete"]


def test_empty_text_produces_empty_results():
    assert extract_intents("", "empty", _lexicon()) == []


def test_multi_line_text_reports_line_offsets():
    spans = extract_intents("Keep this.\nRemove that panel.", "multi", _lexicon())
    assert len(spans) == 1
    assert spans[0].line_or_offset.startswith("line 2")
