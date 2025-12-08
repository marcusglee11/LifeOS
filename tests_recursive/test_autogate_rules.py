from recursive_kernel.autogate import AutoGate, GateDecision

def test_autogate_low_risk():
    config = {
        "max_diff_lines_auto_merge": 10,
        "risk_rules": {
            "low_risk_paths": ["docs/"]
        }
    }
    gate = AutoGate(config)
    decision = gate.evaluate(["docs/foo.md"], 5)
    assert decision == GateDecision.AUTO_MERGE

def test_autogate_high_risk_path():
    config = {
        "max_diff_lines_auto_merge": 10,
        "risk_rules": {
            "low_risk_paths": ["docs/"]
        }
    }
    gate = AutoGate(config)
    decision = gate.evaluate(["src/foo.py"], 5)
    assert decision == GateDecision.HUMAN_REVIEW

def test_autogate_diff_limit():
    config = {
        "max_diff_lines_auto_merge": 10,
        "risk_rules": {
            "low_risk_paths": ["docs/"]
        }
    }
    gate = AutoGate(config)
    decision = gate.evaluate(["docs/foo.md"], 15)
    assert decision == GateDecision.HUMAN_REVIEW
