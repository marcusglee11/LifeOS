"""
Tests for runtime/api/governance_api.py — Governance API facade

Test Coverage:
- GovernanceAPI initialization with/without lineage
- Hash algorithm retrieval
- Data hashing for various types
- Lineage entry retrieval
- Latest entry retrieval
- Chain integrity verification
"""

import pytest
from unittest.mock import Mock, MagicMock
from runtime.api.governance_api import GovernanceAPI
from runtime.amu0.lineage import LineageEntry


class TestGovernanceAPIInitialization:
    """Test suite for GovernanceAPI initialization."""

    def test_init_without_lineage(self):
        """GovernanceAPI can be initialized without lineage."""
        api = GovernanceAPI()
        assert api._lineage is None

    def test_init_with_lineage(self):
        """GovernanceAPI can be initialized with lineage."""
        mock_lineage = Mock()
        api = GovernanceAPI(lineage=mock_lineage)
        assert api._lineage is mock_lineage

    def test_init_with_none_lineage(self):
        """GovernanceAPI can be explicitly initialized with None lineage."""
        api = GovernanceAPI(lineage=None)
        assert api._lineage is None


class TestHashAlgorithm:
    """Test suite for hash algorithm retrieval."""

    def test_get_hash_algorithm(self):
        """get_hash_algorithm returns the council-approved algorithm."""
        api = GovernanceAPI()
        algorithm = api.get_hash_algorithm()
        assert isinstance(algorithm, str)
        assert algorithm  # Non-empty string

    def test_hash_algorithm_consistency(self):
        """Hash algorithm is consistent across instances."""
        api1 = GovernanceAPI()
        api2 = GovernanceAPI()
        assert api1.get_hash_algorithm() == api2.get_hash_algorithm()

    def test_hash_algorithm_with_lineage(self):
        """Hash algorithm is same regardless of lineage presence."""
        api_without = GovernanceAPI()
        api_with = GovernanceAPI(lineage=Mock())
        assert api_without.get_hash_algorithm() == api_with.get_hash_algorithm()


class TestDataHashing:
    """Test suite for data hashing."""

    def test_hash_simple_dict(self):
        """hash_data works with simple dictionary."""
        api = GovernanceAPI()
        data = {"key": "value"}
        hash_result = api.hash_data(data)
        assert isinstance(hash_result, str)
        assert len(hash_result) > 0

    def test_hash_deterministic(self):
        """hash_data produces deterministic results."""
        api = GovernanceAPI()
        data = {"key": "value", "number": 42}
        hash1 = api.hash_data(data)
        hash2 = api.hash_data(data)
        assert hash1 == hash2

    def test_hash_nested_dict(self):
        """hash_data works with nested dictionaries."""
        api = GovernanceAPI()
        data = {
            "outer": {
                "inner": {
                    "deep": "value"
                }
            }
        }
        hash_result = api.hash_data(data)
        assert isinstance(hash_result, str)
        assert len(hash_result) > 0

    def test_hash_list(self):
        """hash_data works with lists."""
        api = GovernanceAPI()
        data = [1, 2, 3, "four"]
        hash_result = api.hash_data(data)
        assert isinstance(hash_result, str)

    def test_hash_mixed_types(self):
        """hash_data works with mixed JSON-serializable types."""
        api = GovernanceAPI()
        data = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"}
        }
        hash_result = api.hash_data(data)
        assert isinstance(hash_result, str)

    def test_hash_different_data_different_hash(self):
        """Different data produces different hashes."""
        api = GovernanceAPI()
        hash1 = api.hash_data({"key": "value1"})
        hash2 = api.hash_data({"key": "value2"})
        assert hash1 != hash2

    def test_hash_empty_dict(self):
        """hash_data works with empty dictionary."""
        api = GovernanceAPI()
        hash_result = api.hash_data({})
        assert isinstance(hash_result, str)

    def test_hash_empty_list(self):
        """hash_data works with empty list."""
        api = GovernanceAPI()
        hash_result = api.hash_data([])
        assert isinstance(hash_result, str)


class TestLineageEntries:
    """Test suite for lineage entry retrieval."""

    def test_get_lineage_entries_without_lineage(self):
        """get_lineage_entries returns empty list when no lineage."""
        api = GovernanceAPI()
        entries = api.get_lineage_entries()
        assert entries == []

    def test_get_lineage_entries_with_empty_lineage(self):
        """get_lineage_entries returns empty list for lineage with no entries."""
        mock_lineage = Mock()
        mock_lineage.get_entries.return_value = []
        api = GovernanceAPI(lineage=mock_lineage)
        entries = api.get_lineage_entries()
        assert entries == []

    def test_get_lineage_entries_with_single_entry(self):
        """get_lineage_entries returns list with single entry."""
        mock_entry = Mock(spec=LineageEntry)
        mock_entry.to_dict.return_value = {"entry_id": "test1"}

        mock_lineage = Mock()
        mock_lineage.get_entries.return_value = [mock_entry]

        api = GovernanceAPI(lineage=mock_lineage)
        entries = api.get_lineage_entries()

        assert len(entries) == 1
        assert entries[0] == {"entry_id": "test1"}

    def test_get_lineage_entries_with_multiple_entries(self):
        """get_lineage_entries returns all entries."""
        mock_entries = [
            Mock(spec=LineageEntry),
            Mock(spec=LineageEntry),
            Mock(spec=LineageEntry)
        ]
        mock_entries[0].to_dict.return_value = {"entry_id": "test1"}
        mock_entries[1].to_dict.return_value = {"entry_id": "test2"}
        mock_entries[2].to_dict.return_value = {"entry_id": "test3"}

        mock_lineage = Mock()
        mock_lineage.get_entries.return_value = mock_entries

        api = GovernanceAPI(lineage=mock_lineage)
        entries = api.get_lineage_entries()

        assert len(entries) == 3
        assert entries[0]["entry_id"] == "test1"
        assert entries[1]["entry_id"] == "test2"
        assert entries[2]["entry_id"] == "test3"

    def test_get_lineage_entries_calls_get_entries(self):
        """get_lineage_entries calls lineage.get_entries()."""
        mock_lineage = Mock()
        mock_lineage.get_entries.return_value = []

        api = GovernanceAPI(lineage=mock_lineage)
        api.get_lineage_entries()

        mock_lineage.get_entries.assert_called_once()


class TestLatestEntry:
    """Test suite for latest entry retrieval."""

    def test_get_latest_entry_without_lineage(self):
        """get_latest_entry returns None when no lineage."""
        api = GovernanceAPI()
        entry = api.get_latest_entry()
        assert entry is None

    def test_get_latest_entry_with_empty_lineage(self):
        """get_latest_entry returns None for lineage with no entries."""
        mock_lineage = Mock()
        mock_lineage.get_last_entry.return_value = None

        api = GovernanceAPI(lineage=mock_lineage)
        entry = api.get_latest_entry()
        assert entry is None

    def test_get_latest_entry_with_entry(self):
        """get_latest_entry returns the most recent entry."""
        mock_entry = Mock(spec=LineageEntry)
        mock_entry.to_dict.return_value = {
            "entry_id": "latest",
            "timestamp": "2026-01-19T00:00:00Z"
        }

        mock_lineage = Mock()
        mock_lineage.get_last_entry.return_value = mock_entry

        api = GovernanceAPI(lineage=mock_lineage)
        entry = api.get_latest_entry()

        assert entry is not None
        assert entry["entry_id"] == "latest"

    def test_get_latest_entry_calls_get_last_entry(self):
        """get_latest_entry calls lineage.get_last_entry()."""
        mock_lineage = Mock()
        mock_lineage.get_last_entry.return_value = None

        api = GovernanceAPI(lineage=mock_lineage)
        api.get_latest_entry()

        mock_lineage.get_last_entry.assert_called_once()


class TestChainIntegrity:
    """Test suite for chain integrity verification."""

    def test_verify_chain_integrity_without_lineage(self):
        """verify_chain_integrity returns (True, []) when no lineage."""
        api = GovernanceAPI()
        is_valid, errors = api.verify_chain_integrity()
        assert is_valid is True
        assert errors == []

    def test_verify_chain_integrity_valid_chain(self):
        """verify_chain_integrity returns (True, []) for valid chain."""
        mock_lineage = Mock()
        mock_lineage.verify_chain.return_value = (True, [])

        api = GovernanceAPI(lineage=mock_lineage)
        is_valid, errors = api.verify_chain_integrity()

        assert is_valid is True
        assert errors == []

    def test_verify_chain_integrity_broken_chain(self):
        """verify_chain_integrity returns (False, errors) for broken chain."""
        mock_lineage = Mock()
        mock_lineage.verify_chain.return_value = (
            False,
            ["Entry test2: parent_hash mismatch"]
        )

        api = GovernanceAPI(lineage=mock_lineage)
        is_valid, errors = api.verify_chain_integrity()

        assert is_valid is False
        assert len(errors) == 1
        assert "parent_hash mismatch" in errors[0]

    def test_verify_chain_integrity_multiple_errors(self):
        """verify_chain_integrity returns all errors."""
        mock_lineage = Mock()
        mock_lineage.verify_chain.return_value = (
            False,
            [
                "Error 1: parent_hash mismatch",
                "Error 2: entry_hash invalid",
                "Error 3: broken link"
            ]
        )

        api = GovernanceAPI(lineage=mock_lineage)
        is_valid, errors = api.verify_chain_integrity()

        assert is_valid is False
        assert len(errors) == 3

    def test_verify_chain_integrity_calls_verify_chain(self):
        """verify_chain_integrity calls lineage.verify_chain()."""
        mock_lineage = Mock()
        mock_lineage.verify_chain.return_value = (True, [])

        api = GovernanceAPI(lineage=mock_lineage)
        api.verify_chain_integrity()

        mock_lineage.verify_chain.assert_called_once()


class TestIntegration:
    """Integration tests for GovernanceAPI."""

    def test_api_workflow_without_lineage(self):
        """Complete workflow without lineage."""
        api = GovernanceAPI()

        # Can get hash algorithm
        assert api.get_hash_algorithm()

        # Can hash data
        hash_result = api.hash_data({"test": "data"})
        assert hash_result

        # Lineage operations return safe defaults
        assert api.get_lineage_entries() == []
        assert api.get_latest_entry() is None
        is_valid, errors = api.verify_chain_integrity()
        assert is_valid is True
        assert errors == []

    def test_api_workflow_with_lineage(self):
        """Complete workflow with lineage."""
        # Setup mock lineage
        mock_entry = Mock(spec=LineageEntry)
        mock_entry.to_dict.return_value = {"entry_id": "test1"}

        mock_lineage = Mock()
        mock_lineage.get_entries.return_value = [mock_entry]
        mock_lineage.get_last_entry.return_value = mock_entry
        mock_lineage.verify_chain.return_value = (True, [])

        api = GovernanceAPI(lineage=mock_lineage)

        # All operations work
        assert api.get_hash_algorithm()
        assert api.hash_data({"test": "data"})
        assert len(api.get_lineage_entries()) == 1
        assert api.get_latest_entry()["entry_id"] == "test1"
        is_valid, errors = api.verify_chain_integrity()
        assert is_valid is True
