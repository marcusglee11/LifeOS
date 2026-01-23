import pytest
from runtime.invariants import check_invariant, InvariantViolation


class TestInvariantViolation:
    """Test suite for InvariantViolation exception class."""

    def test_instantiation_without_message(self):
        """InvariantViolation can be instantiated without a message."""
        exc = InvariantViolation()
        assert isinstance(exc, InvariantViolation)
        assert isinstance(exc, Exception)

    def test_instantiation_with_message(self):
        """InvariantViolation can be instantiated with a message."""
        message = "Test invariant violation"
        exc = InvariantViolation(message)
        assert str(exc) == message

    def test_exception_inheritance(self):
        """InvariantViolation inherits from Exception."""
        exc = InvariantViolation()
        assert isinstance(exc, Exception)
        assert issubclass(InvariantViolation, Exception)

    def test_raise_and_catch(self):
        """InvariantViolation can be raised and caught."""
        with pytest.raises(InvariantViolation):
            raise InvariantViolation("Test violation")

    def test_repr_representation(self):
        """InvariantViolation has correct repr."""
        message = "Invariant check failed"
        exc = InvariantViolation(message)
        repr_str = repr(exc)
        assert "InvariantViolation" in repr_str
        assert message in repr_str


class TestCheckInvariant:
    """Test suite for check_invariant() function."""

    def test_invariant_success(self):
        """check_invariant does not raise when condition is True."""
        check_invariant(True, "Should not fail")

    def test_invariant_failure(self):
        """check_invariant raises InvariantViolation when condition is False."""
        with pytest.raises(InvariantViolation) as exc:
            check_invariant(False, "This must fail")
        assert "This must fail" in str(exc.value)

    def test_message_formatting(self):
        """check_invariant formats message with 'Invariant violated:' prefix."""
        with pytest.raises(InvariantViolation) as exc:
            check_invariant(False, "custom message")
        assert str(exc.value) == "Invariant violated: custom message"

    def test_empty_message(self):
        """check_invariant handles empty message strings."""
        with pytest.raises(InvariantViolation) as exc:
            check_invariant(False, "")
        assert str(exc.value) == "Invariant violated: "

    def test_multiline_message(self):
        """check_invariant preserves multiline messages."""
        message = "Line 1\nLine 2\nLine 3"
        with pytest.raises(InvariantViolation) as exc:
            check_invariant(False, message)
        assert message in str(exc.value)

    def test_unicode_message(self):
        """check_invariant handles Unicode characters in messages."""
        message = "违反不变量 🚫"
        with pytest.raises(InvariantViolation) as exc:
            check_invariant(False, message)
        assert message in str(exc.value)

    def test_special_characters_message(self):
        """check_invariant handles special characters in messages."""
        message = "Test: {}, [], <>, &, @, #, $, %, ^, *, |, \\"
        with pytest.raises(InvariantViolation) as exc:
            check_invariant(False, message)
        assert message in str(exc.value)

    def test_truthy_non_bool_values(self):
        """check_invariant accepts truthy non-bool values."""
        # Should not raise
        check_invariant(1, "Non-zero integer")
        check_invariant("non-empty", "Non-empty string")
        check_invariant([1, 2, 3], "Non-empty list")
        check_invariant({"key": "value"}, "Non-empty dict")
        check_invariant((1,), "Non-empty tuple")

    def test_falsy_non_bool_values(self):
        """check_invariant raises for falsy non-bool values."""
        # All should raise
        with pytest.raises(InvariantViolation):
            check_invariant(0, "Zero")

        with pytest.raises(InvariantViolation):
            check_invariant("", "Empty string")

        with pytest.raises(InvariantViolation):
            check_invariant([], "Empty list")

        with pytest.raises(InvariantViolation):
            check_invariant({}, "Empty dict")

        with pytest.raises(InvariantViolation):
            check_invariant((), "Empty tuple")

        with pytest.raises(InvariantViolation):
            check_invariant(None, "None value")

    def test_traceback_preservation(self):
        """check_invariant preserves stack trace information."""
        def inner_function():
            check_invariant(False, "Inner violation")

        def outer_function():
            inner_function()

        with pytest.raises(InvariantViolation) as exc_info:
            outer_function()

        # Verify traceback contains our function calls
        tb_str = "".join(str(line) for line in exc_info.traceback)
        # The traceback should reference our test functions
        assert "outer_function" in tb_str or "inner_function" in tb_str

    def test_message_with_format_specifiers(self):
        """check_invariant handles messages with format specifiers."""
        message = "Value is %s, expected %d"
        with pytest.raises(InvariantViolation) as exc:
            check_invariant(False, message)
        # Message should be preserved as-is, not interpreted
        assert message in str(exc.value)
