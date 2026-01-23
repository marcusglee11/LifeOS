"""
Tests for runtime/errors.py — Runtime exception taxonomy

Test Coverage:
- AntiFailureViolation exception class
- EnvelopeViolation exception class
- Exception instantiation, messages, and inheritance
"""

import pytest
from runtime.errors import AntiFailureViolation, EnvelopeViolation


class TestAntiFailureViolation:
    """Test suite for AntiFailureViolation exception class."""

    def test_instantiation_without_message(self):
        """AntiFailureViolation can be instantiated without a message."""
        exc = AntiFailureViolation()
        assert isinstance(exc, AntiFailureViolation)
        assert isinstance(exc, Exception)

    def test_instantiation_with_message(self):
        """AntiFailureViolation can be instantiated with a message."""
        message = "Step count limit exceeded"
        exc = AntiFailureViolation(message)
        assert str(exc) == message

    def test_exception_inheritance(self):
        """AntiFailureViolation inherits from Exception."""
        exc = AntiFailureViolation()
        assert isinstance(exc, Exception)
        assert issubclass(AntiFailureViolation, Exception)

    def test_raise_and_catch(self):
        """AntiFailureViolation can be raised and caught."""
        with pytest.raises(AntiFailureViolation):
            raise AntiFailureViolation("Test violation")

    def test_raise_and_catch_with_message(self):
        """AntiFailureViolation preserves message when raised."""
        message = "Mission boundary validation failed"
        with pytest.raises(AntiFailureViolation) as exc_info:
            raise AntiFailureViolation(message)
        assert str(exc_info.value) == message

    def test_repr_representation(self):
        """AntiFailureViolation has correct repr."""
        message = "Input validation failure"
        exc = AntiFailureViolation(message)
        repr_str = repr(exc)
        assert "AntiFailureViolation" in repr_str
        assert message in repr_str

    def test_subclassing(self):
        """AntiFailureViolation can be subclassed."""
        class CustomAntiFailureViolation(AntiFailureViolation):
            pass

        exc = CustomAntiFailureViolation("Custom violation")
        assert isinstance(exc, AntiFailureViolation)
        assert isinstance(exc, CustomAntiFailureViolation)

    def test_empty_string_message(self):
        """AntiFailureViolation handles empty string messages."""
        exc = AntiFailureViolation("")
        assert str(exc) == ""

    def test_multiline_message(self):
        """AntiFailureViolation preserves multiline messages."""
        message = "Line 1\nLine 2\nLine 3"
        exc = AntiFailureViolation(message)
        assert str(exc) == message

    def test_unicode_message(self):
        """AntiFailureViolation handles Unicode characters."""
        message = "Violation: 违反规则 🚫"
        exc = AntiFailureViolation(message)
        assert str(exc) == message


class TestEnvelopeViolation:
    """Test suite for EnvelopeViolation exception class."""

    def test_instantiation_without_message(self):
        """EnvelopeViolation can be instantiated without a message."""
        exc = EnvelopeViolation()
        assert isinstance(exc, EnvelopeViolation)
        assert isinstance(exc, Exception)

    def test_instantiation_with_message(self):
        """EnvelopeViolation can be instantiated with a message."""
        message = "Disallowed step kind detected"
        exc = EnvelopeViolation(message)
        assert str(exc) == message

    def test_exception_inheritance(self):
        """EnvelopeViolation inherits from Exception."""
        exc = EnvelopeViolation()
        assert isinstance(exc, Exception)
        assert issubclass(EnvelopeViolation, Exception)

    def test_raise_and_catch(self):
        """EnvelopeViolation can be raised and caught."""
        with pytest.raises(EnvelopeViolation):
            raise EnvelopeViolation("Test violation")

    def test_raise_and_catch_with_message(self):
        """EnvelopeViolation preserves message when raised."""
        message = "Forbidden I/O operation attempted"
        with pytest.raises(EnvelopeViolation) as exc_info:
            raise EnvelopeViolation(message)
        assert str(exc_info.value) == message

    def test_repr_representation(self):
        """EnvelopeViolation has correct repr."""
        message = "Governance constraint violation"
        exc = EnvelopeViolation(message)
        repr_str = repr(exc)
        assert "EnvelopeViolation" in repr_str
        assert message in repr_str

    def test_subclassing(self):
        """EnvelopeViolation can be subclassed."""
        class CustomEnvelopeViolation(EnvelopeViolation):
            pass

        exc = CustomEnvelopeViolation("Custom violation")
        assert isinstance(exc, EnvelopeViolation)
        assert isinstance(exc, CustomEnvelopeViolation)

    def test_empty_string_message(self):
        """EnvelopeViolation handles empty string messages."""
        exc = EnvelopeViolation("")
        assert str(exc) == ""

    def test_multiline_message(self):
        """EnvelopeViolation preserves multiline messages."""
        message = "Violation 1\nViolation 2\nViolation 3"
        exc = EnvelopeViolation(message)
        assert str(exc) == message

    def test_unicode_message(self):
        """EnvelopeViolation handles Unicode characters."""
        message = "Envelope violation: 包络违规 ⚠️"
        exc = EnvelopeViolation(message)
        assert str(exc) == message


class TestExceptionDistinction:
    """Test that the two exception types are distinct."""

    def test_different_exception_types(self):
        """AntiFailureViolation and EnvelopeViolation are distinct types."""
        anti_failure = AntiFailureViolation("Test")
        envelope = EnvelopeViolation("Test")

        assert type(anti_failure) != type(envelope)
        assert not isinstance(anti_failure, EnvelopeViolation)
        assert not isinstance(envelope, AntiFailureViolation)

    def test_catch_specific_exception(self):
        """Can catch each exception type specifically."""
        # Catch AntiFailureViolation specifically
        with pytest.raises(AntiFailureViolation):
            raise AntiFailureViolation("Test")

        # Catch EnvelopeViolation specifically
        with pytest.raises(EnvelopeViolation):
            raise EnvelopeViolation("Test")

    def test_both_catchable_as_exception(self):
        """Both exception types are catchable as generic Exception."""
        try:
            raise AntiFailureViolation("Test")
        except Exception:
            pass

        try:
            raise EnvelopeViolation("Test")
        except Exception:
            pass
