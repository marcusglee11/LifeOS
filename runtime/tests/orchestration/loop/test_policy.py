import pytest
from runtime.orchestration.loop.policy import LoopPolicy
from runtime.orchestration.loop.ledger import AttemptLedger, AttemptRecord
from runtime.orchestration.loop.taxonomy import FailureClass, LoopAction, TerminalReason

@pytest.fixture
def mock_ledger(tmp_path):
    return AttemptLedger(tmp_path / "mock.jsonl")

def make_record(id, diff_hash, failure_class=None, success=False):
    return AttemptRecord(
        attempt_id=id,
        timestamp="t",
        run_id="r",
        policy_hash="p",
        input_hash="i",
        actions_taken=[],
        diff_hash=diff_hash,
        changed_files=[],
        evidence_hashes={},
        success=success,
        failure_class=failure_class,
        terminal_reason=None,
        next_action="retry",
        rationale=""
    )

def test_policy_pass(mock_ledger):
    policy = LoopPolicy()
    mock_ledger.history = [make_record(1, "h1", success=True)]
    
    action, reason = policy.decide_next_action(mock_ledger)
    assert action == LoopAction.TERMINATE.value
    assert reason == TerminalReason.PASS.value

def test_policy_deadlock(mock_ledger):
    policy = LoopPolicy()
    # Attempt 1 and 2 have same diff_hash
    mock_ledger.history = [
        make_record(1, "h1", FailureClass.TEST_FAILURE.value),
        make_record(2, "h1", FailureClass.TEST_FAILURE.value)
    ]
    
    action, reason = policy.decide_next_action(mock_ledger)
    assert action == LoopAction.TERMINATE.value
    assert reason == TerminalReason.NO_PROGRESS.value

def test_policy_oscillation(mock_ledger):
    policy = LoopPolicy()
    # A -> B -> A
    mock_ledger.history = [
        make_record(1, "hA", FailureClass.TEST_FAILURE.value),
        make_record(2, "hB", FailureClass.TEST_FAILURE.value),
        make_record(3, "hA", FailureClass.TEST_FAILURE.value) 
    ]
    
    action, reason = policy.decide_next_action(mock_ledger)
    assert action == LoopAction.TERMINATE.value
    assert reason == TerminalReason.OSCILLATION_DETECTED.value

def test_policy_retry_rules(mock_ledger):
    policy = LoopPolicy()
    
    # TEST_FAILURE -> RETRY
    mock_ledger.history = [make_record(1, "h1", FailureClass.TEST_FAILURE.value)]
    action, reason = policy.decide_next_action(mock_ledger)
    assert action == LoopAction.RETRY.value
    assert "Test failure" in reason

    # SYNTAX_ERROR -> TERMINATE
    mock_ledger.history = [make_record(1, "h1", FailureClass.SYNTAX_ERROR.value)]
    action, reason = policy.decide_next_action(mock_ledger)
    assert action == LoopAction.TERMINATE.value
    assert "Syntax error" in reason

    # TIMEOUT -> RETRY ONCE
    mock_ledger.history = [make_record(1, "h1", FailureClass.TIMEOUT.value)]
    action, reason = policy.decide_next_action(mock_ledger)
    assert action == LoopAction.RETRY.value
    
    # TIMEOUT TWICE -> TERMINATE
    mock_ledger.history = [
        make_record(1, "h1", FailureClass.TIMEOUT.value),
        make_record(2, "h2", FailureClass.TIMEOUT.value)
    ]
    action, reason = policy.decide_next_action(mock_ledger)
    assert action == LoopAction.TERMINATE.value
    assert "limit exceeded" in reason
