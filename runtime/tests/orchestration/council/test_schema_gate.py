from __future__ import annotations

from runtime.orchestration.council.policy import load_council_policy
from runtime.orchestration.council.schema_gate import validate_seat_output


def _valid_output() -> dict:
    return {
        "verdict": "Accept",
        "key_findings": ["- Deterministic behavior preserved"],
        "risks": ["- No major risk identified"],
        "fixes": ["- Add one integration test"],
        "confidence": "high",
        "assumptions": ["environment has git"],
        "operator_view": "Safe and simple.",
        "complexity_budget": {
            "net_human_steps": 1,
            "new_surfaces_introduced": 0,
            "surfaces_removed": 0,
            "mechanized": "yes",
            "trade_statement": "n/a",
        },
    }


def test_schema_gate_accepts_valid_output_and_labels_assumptions():
    policy = load_council_policy()
    result = validate_seat_output(_valid_output(), policy)
    assert result.valid is True
    assert result.rejected is False
    assert result.normalized_output is not None
    assert result.normalized_output["key_findings"][0].endswith("[ASSUMPTION]")
    assert any("ASSUMPTION" in warning for warning in result.warnings)


def test_schema_gate_rejects_missing_section():
    policy = load_council_policy()
    payload = _valid_output()
    payload.pop("operator_view")
    result = validate_seat_output(payload, policy)
    assert result.valid is False
    assert result.rejected is True
    assert "Missing required section: operator_view" in result.errors


def test_schema_gate_rejects_invalid_verdict():
    policy = load_council_policy()
    payload = _valid_output()
    payload["verdict"] = "PASS"
    result = validate_seat_output(payload, policy)
    assert result.valid is False
    assert result.rejected is True
    assert any("Invalid verdict" in msg for msg in result.errors)


def test_schema_gate_normalizes_legacy_go_with_fixes_to_revise():
    policy = load_council_policy()
    payload = _valid_output()
    payload["verdict"] = "Go with Fixes"
    result = validate_seat_output(payload, policy)
    assert result.valid is True
    assert result.normalized_output is not None
    assert result.normalized_output["verdict"] == "Revise"
    assert any("Normalized legacy verdict alias" in msg for msg in result.warnings)


def test_schema_gate_flags_complexity_budget_without_trade_statement():
    policy = load_council_policy()
    payload = _valid_output()
    payload["complexity_budget"]["mechanized"] = "no"
    payload["complexity_budget"]["trade_statement"] = "none"
    result = validate_seat_output(payload, policy)
    assert result.valid is True
    assert any("complexity_budget has net-positive" in msg for msg in result.warnings)


def test_schema_gate_parses_yaml_string_input():
    import yaml

    policy = load_council_policy()
    payload = _valid_output()
    yaml_string = yaml.dump(payload)
    result = validate_seat_output(yaml_string, policy)
    assert result.valid is True
    assert result.rejected is False
    assert result.normalized_output is not None
    assert result.normalized_output["verdict"] == "Accept"


def test_schema_gate_rejects_empty_string():
    policy = load_council_policy()
    result = validate_seat_output("", policy)
    assert result.valid is False
    assert result.rejected is True
    assert any("empty" in msg.lower() for msg in result.errors)


def test_schema_gate_adds_assumption_to_dict_items():
    policy = load_council_policy()
    payload = _valid_output()
    payload["key_findings"] = [
        {"claim": "No regressions found", "priority": "P1"},
    ]
    result = validate_seat_output(payload, policy)
    assert result.valid is True
    finding = result.normalized_output["key_findings"][0]
    assert isinstance(finding, dict)
    assert finding["assumption"] is True
    assert any("assumption=true" in msg for msg in result.warnings)


def test_schema_gate_warns_p0_without_blocker_category():
    policy = load_council_policy()
    payload = _valid_output()
    payload["key_findings"] = [
        {"claim": "Style issue", "priority": "P0", "category": "style"},
    ]
    result = validate_seat_output(payload, policy)
    assert result.valid is True
    assert any("P0 without recognized blocker category" in msg for msg in result.warnings)
