"""
Tests for backlog parser.

Per Mission Synthesis Engine MVP - P1.1
"""
import pytest
from pathlib import Path
from textwrap import dedent

from runtime.backlog.parser import (
    parse_backlog,
    get_task_by_id,
    sort_tasks_by_priority,
    BacklogParseError,
    TaskSpec,
)


@pytest.fixture
def valid_backlog_content():
    return dedent("""
        schema_version: "1.0"
        tasks:
          - id: "TASK-001"
            description: "First task"
            priority: P1
          - id: "TASK-002"
            description: "Second task"
            priority: P0
            constraints:
              - "Must be fast"
            context_hints:
              - "docs/README.md"
    """).strip()


@pytest.fixture
def valid_backlog_file(valid_backlog_content, tmp_path):
    p = tmp_path / "backlog.yaml"
    p.write_text(valid_backlog_content, encoding="utf-8")
    return p


class TestParseBacklog:
    """Tests for parse_backlog function."""
    
    def test_valid_backlog(self, valid_backlog_file):
        """Parse valid backlog returns TaskSpec list."""
        tasks = parse_backlog(valid_backlog_file)
        assert len(tasks) == 2
        assert tasks[0].id == "TASK-001"
        assert tasks[1].id == "TASK-002"
    
    def test_preserves_order(self, valid_backlog_file):
        """Tasks are returned in file order, not sorted."""
        tasks = parse_backlog(valid_backlog_file)
        # File order preserved (P1 before P0)
        assert tasks[0].priority == "P1"
        assert tasks[1].priority == "P0"
    
    def test_constraints_parsed(self, valid_backlog_file):
        """Constraints parsed as tuple."""
        tasks = parse_backlog(valid_backlog_file)
        assert tasks[1].constraints == ("Must be fast",)
    
    def test_context_hints_parsed(self, valid_backlog_file):
        """Context hints parsed as tuple."""
        tasks = parse_backlog(valid_backlog_file)
        assert tasks[1].context_hints == ("docs/README.md",)
    
    def test_default_status(self, valid_backlog_file):
        """Default status is TODO."""
        tasks = parse_backlog(valid_backlog_file)
        assert tasks[0].status == "TODO"
    
    def test_file_not_found(self, tmp_path):
        """Missing file raises BacklogParseError."""
        with pytest.raises(BacklogParseError, match="not found"):
            parse_backlog(tmp_path / "nonexistent.yaml")


class TestValidationFailures:
    """Tests for schema validation failures."""
    
    def test_missing_required_field_id(self, tmp_path):
        """Missing id raises BacklogParseError."""
        content = dedent("""
            schema_version: "1.0"
            tasks:
              - description: "Test"
                priority: P1
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(BacklogParseError, match="Missing required field 'id'"):
            parse_backlog(p)
    
    def test_missing_required_field_description(self, tmp_path):
        """Missing description raises BacklogParseError."""
        content = dedent("""
            schema_version: "1.0"
            tasks:
              - id: "X"
                priority: P1
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(BacklogParseError, match="Missing required field 'description'"):
            parse_backlog(p)
    
    def test_invalid_priority(self, tmp_path):
        """Invalid priority raises BacklogParseError."""
        content = dedent("""
            schema_version: "1.0"
            tasks:
              - id: "X"
                description: "Test"
                priority: URGENT
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(BacklogParseError, match="'priority' must be one of"):
            parse_backlog(p)
    
    def test_unknown_field_rejected(self, tmp_path):
        """Unknown field raises BacklogParseError (fail-closed)."""
        content = dedent("""
            schema_version: "1.0"
            tasks:
              - id: "X"
                description: "Test"
                priority: P1
                unknown_field: "bad"
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(BacklogParseError, match="Unknown fields"):
            parse_backlog(p)
    
    def test_invalid_id_format(self, tmp_path):
        """Invalid ID format raises BacklogParseError."""
        content = dedent("""
            schema_version: "1.0"
            tasks:
              - id: "bad id with spaces"
                description: "Test"
                priority: P1
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(BacklogParseError, match="must match pattern"):
            parse_backlog(p)
    
    def test_wrong_schema_version(self, tmp_path):
        """Wrong schema version raises BacklogParseError."""
        content = dedent("""
            schema_version: "2.0"
            tasks: []
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(BacklogParseError, match="Unsupported schema_version"):
            parse_backlog(p)
    
    def test_empty_description(self, tmp_path):
        """Empty description raises BacklogParseError."""
        content = dedent("""
            schema_version: "1.0"
            tasks:
              - id: "X"
                description: "   "
                priority: P1
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(BacklogParseError, match="must be non-empty"):
            parse_backlog(p)
    
    def test_invalid_status(self, tmp_path):
        """Invalid status raises BacklogParseError."""
        content = dedent("""
            schema_version: "1.0"
            tasks:
              - id: "X"
                description: "Test"
                priority: P1
                status: INVALID
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(BacklogParseError, match="'status' must be one of"):
            parse_backlog(p)
    
    def test_id_too_long(self, tmp_path):
        """ID exceeding max length raises BacklogParseError."""
        content = dedent(f"""
            schema_version: "1.0"
            tasks:
              - id: "{'x' * 100}"
                description: "Test"
                priority: P1
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(BacklogParseError, match="exceeds 64 chars"):
            parse_backlog(p)


class TestGetTaskById:
    """Tests for get_task_by_id function."""
    
    def test_found(self, valid_backlog_file):
        """Task found by ID."""
        tasks = parse_backlog(valid_backlog_file)
        task = get_task_by_id(tasks, "TASK-001")
        assert task is not None
        assert task.id == "TASK-001"
    
    def test_not_found(self, valid_backlog_file):
        """Missing task returns None."""
        tasks = parse_backlog(valid_backlog_file)
        task = get_task_by_id(tasks, "NONEXISTENT")
        assert task is None


class TestSortByPriority:
    """Tests for sort_tasks_by_priority function."""
    
    def test_sorts_by_priority_then_id(self, valid_backlog_file):
        """Tasks sorted by priority (P0 first) then ID."""
        tasks = parse_backlog(valid_backlog_file)
        sorted_tasks = sort_tasks_by_priority(tasks)
        # P0 comes before P1
        assert sorted_tasks[0].priority == "P0"
        assert sorted_tasks[1].priority == "P1"
    
    def test_stable_within_priority(self, tmp_path):
        """Tasks with same priority sorted by ID."""
        content = dedent("""
            schema_version: "1.0"
            tasks:
              - id: "Z-TASK"
                description: "Z task"
                priority: P1
              - id: "A-TASK"
                description: "A task"
                priority: P1
        """)
        p = tmp_path / "backlog.yaml"
        p.write_text(content)
        tasks = parse_backlog(p)
        sorted_tasks = sort_tasks_by_priority(tasks)
        assert sorted_tasks[0].id == "A-TASK"
        assert sorted_tasks[1].id == "Z-TASK"
