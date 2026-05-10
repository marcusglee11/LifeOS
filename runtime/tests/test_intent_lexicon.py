import json
from pathlib import Path

LEXICON_PATH = Path("runtime/data/intent_lexicon_v1.json")
REQUIRED_CLASSES = {
    "absence",
    "pause",
    "approval_before_action",
    "privacy",
    "reversibility",
    "automation_boundary",
    "channel_authority",
    "scope_minimisation",
    "softening_inversion",
}
REQUIRED_FIELDS = {
    "class",
    "phrases",
    "default_blocking",
    "inversion_terms",
    "negation_guards",
}
VALID_BLOCKING = {"blocking", "warning", "requires_conductor_review"}


def _load() -> dict:
    return json.loads(LEXICON_PATH.read_text(encoding="utf-8"))


def test_intent_lexicon_exists_and_is_valid_json():
    assert LEXICON_PATH.exists()
    data = _load()
    assert data["schema_version"] == "intent_lexicon_v1"
    assert data["version"] == "1.0.0"


def test_all_required_intent_classes_present():
    classes = {item["class"] for item in _load()["intent_classes"]}
    assert REQUIRED_CLASSES <= classes


def test_each_class_has_required_fields():
    for item in _load()["intent_classes"]:
        assert REQUIRED_FIELDS <= set(item)
        assert isinstance(item["phrases"], list)
        assert isinstance(item["inversion_terms"], list)
        assert isinstance(item["negation_guards"], list)


def test_default_blocking_values_are_valid():
    for item in _load()["intent_classes"]:
        assert item["default_blocking"] in VALID_BLOCKING


def test_deterministic_load_twice_is_identical():
    assert _load() == _load()
