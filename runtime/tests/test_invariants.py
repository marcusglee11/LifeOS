import pytest
from runtime.invariants import check_invariant, InvariantViolation

def test_invariant_success():
    check_invariant(True, "Should not fail")

def test_invariant_failure():
    with pytest.raises(InvariantViolation) as exc:
        check_invariant(False, "This must fail")
    assert "This must fail" in str(exc.value)
