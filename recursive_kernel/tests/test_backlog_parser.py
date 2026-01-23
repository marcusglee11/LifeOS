# -*- coding: utf-8 -*-
"""
Tests for recursive_kernel/backlog_parser.py
"""
import pytest
from pathlib import Path
from recursive_kernel.backlog_parser import (
    parse_backlog,
    select_eligible_item,
    mark_item_done,
    BacklogItem,
    BacklogParseError,
    ItemStatus,
    Priority,
    _compute_item_key,
)


def write_backlog(path: Path, content: str) -> None:
    """Write content to path with explicit UTF-8 encoding."""
    path.write_bytes(content.encode('utf-8'))


class TestBacklogParser:
    """Tests for parse_backlog function."""
    
    def test_parses_valid_p0_item(self, tmp_path: Path):
        """Parser extracts P0 item with all required fields."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """# BACKLOG

### P0 (Critical)

- [ ] **Fix Critical Bug** -- DoD: Bug fixed and tested -- Owner: antigravity -- Context: High priority
""")
        
        items = parse_backlog(backlog)
        
        assert len(items) == 1
        item = items[0]
        assert item.priority == Priority.P0
        assert item.title == "Fix Critical Bug"
        assert item.dod == "Bug fixed and tested"
        assert item.owner == "antigravity"
        assert item.status == ItemStatus.TODO
        assert item.context == "High priority"
    
    def test_parses_why_now_as_dod(self, tmp_path: Path):
        """Parser accepts 'Why Now:' in place of 'DoD:'."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P1 (High)

- [ ] **New Feature** -- Why Now: Immediate focus -- Owner: dev
""")
        
        items = parse_backlog(backlog)
        
        assert len(items) == 1
        assert items[0].dod == "Immediate focus"
    
    def test_ignores_headers_and_blank_lines(self, tmp_path: Path):
        """Parser skips non-item lines without error."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """# BACKLOG

**Last Updated:** 2026-01-20

## Now

### P0 (Critical)

Some random text

- [ ] **Task** -- DoD: Done -- Owner: dev

## Done
""")
        
        items = parse_backlog(backlog)
        assert len(items) == 1
    
    def test_done_item_status(self, tmp_path: Path):
        """Parser correctly identifies [x] as DONE."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P0 (Critical)

- [x] **Completed Task** -- DoD: Done -- Owner: dev
""")
        
        items = parse_backlog(backlog)
        assert len(items) == 1
        assert items[0].status == ItemStatus.DONE
    
    def test_inprogress_status(self, tmp_path: Path):
        """Parser correctly identifies [/] as INPROGRESS."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P1 (High)

- [/] **WIP Task** -- DoD: In progress -- Owner: dev
""")
        
        items = parse_backlog(backlog)
        assert len(items) == 1
        assert items[0].status == ItemStatus.INPROGRESS
    
    def test_fails_closed_on_missing_required_fields(self, tmp_path: Path):
        """Parser raises error for dispatchable items missing DoD."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P0 (Critical)

- [ ] **No DoD Task** -- Owner: dev
""")
        
        with pytest.raises(BacklogParseError) as exc_info:
            parse_backlog(backlog)
        
        assert "DoD" in str(exc_info.value)
    
    def test_fails_closed_on_missing_owner(self, tmp_path: Path):
        """Parser raises error for dispatchable items missing Owner."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P0 (Critical)

- [ ] **No Owner Task** -- DoD: Something
""")
        
        with pytest.raises(BacklogParseError) as exc_info:
            parse_backlog(backlog)
        
        assert "Owner" in str(exc_info.value)
    
    def test_item_without_priority_section_gets_p3(self, tmp_path: Path):
        """Items without priority section header default to P3 and don't require complete fields."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """# BACKLOG

- [ ] **No Priority Section** -- DoD: Done -- Owner: dev
""")
        
        # Should parse successfully with P3 priority
        items = parse_backlog(backlog)
        assert len(items) == 1
        assert items[0].priority == Priority.P3
    
    def test_stable_item_key_generation(self, tmp_path: Path):
        """Same line content produces same item_key."""
        line1 = "- [ ] **Task** -- DoD: Done -- Owner: dev"
        line2 = "- [ ] **Task** -- DoD: Done -- Owner: dev"
        
        key1, full1 = _compute_item_key(line1)
        key2, full2 = _compute_item_key(line2)
        
        assert key1 == key2
        assert full1 == full2
    
    def test_different_content_different_key(self, tmp_path: Path):
        """Different line content produces different item_key."""
        key1, _ = _compute_item_key("- [ ] **Task A** -- DoD: Done -- Owner: dev")
        key2, _ = _compute_item_key("- [ ] **Task B** -- DoD: Done -- Owner: dev")
        
        assert key1 != key2
    
    def test_file_not_found_raises(self, tmp_path: Path):
        """Parser raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_backlog(tmp_path / "nonexistent.md")


class TestSelectEligibleItem:
    """Tests for select_eligible_item function."""
    
    def test_selects_first_p0_over_p1(self, tmp_path: Path):
        """Selection prefers P0 items over P1."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P1 (High)

- [ ] **P1 Task** -- DoD: Done -- Owner: dev

### P0 (Critical)

- [ ] **P0 Task** -- DoD: Done -- Owner: dev
""")
        
        items = parse_backlog(backlog)
        selected = select_eligible_item(items)
        
        assert selected is not None
        assert selected.priority == Priority.P0
        assert selected.title == "P0 Task"
    
    def test_selects_file_order_within_priority(self, tmp_path: Path):
        """Selection preserves file order within same priority."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P0 (Critical)

- [ ] **First P0** -- DoD: Done -- Owner: dev
- [ ] **Second P0** -- DoD: Done -- Owner: dev
""")
        
        items = parse_backlog(backlog)
        selected = select_eligible_item(items)
        
        assert selected.title == "First P0"
    
    def test_skips_done_items(self, tmp_path: Path):
        """Selection ignores completed items."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P0 (Critical)

- [x] **Done Task** -- DoD: Done -- Owner: dev
- [ ] **Todo Task** -- DoD: Done -- Owner: dev
""")
        
        items = parse_backlog(backlog)
        selected = select_eligible_item(items)
        
        assert selected.title == "Todo Task"
    
    def test_returns_none_when_no_eligible(self, tmp_path: Path):
        """Selection returns None when no eligible items exist."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P2 (Normal)

- [ ] **P2 Task** -- DoD: Done -- Owner: dev
""")
        
        items = parse_backlog(backlog)
        selected = select_eligible_item(items)
        
        assert selected is None


class TestMarkItemDone:
    """Tests for mark_item_done function."""
    
    def test_marks_item_done_atomically(self, tmp_path: Path):
        """mark_item_done changes [ ] to [x]."""
        backlog = tmp_path / "BACKLOG.md"
        original_content = """### P0 (Critical)

- [ ] **Task** -- DoD: Done -- Owner: dev
"""
        write_backlog(backlog, original_content)
        
        items = parse_backlog(backlog)
        mark_item_done(backlog, items[0])
        
        new_content = backlog.read_text(encoding='utf-8')
        assert "[x] **Task**" in new_content
        assert "[ ] **Task**" not in new_content
    
    def test_preserves_other_lines(self, tmp_path: Path):
        """mark_item_done preserves unrelated content."""
        backlog = tmp_path / "BACKLOG.md"
        original_content = """# BACKLOG

### P0 (Critical)

- [ ] **Task** -- DoD: Done -- Owner: dev

## Other section
"""
        write_backlog(backlog, original_content)
        
        items = parse_backlog(backlog)
        mark_item_done(backlog, items[0])
        
        new_content = backlog.read_text(encoding='utf-8')
        assert "# BACKLOG" in new_content
        assert "## Other section" in new_content
    
    def test_fails_on_file_changed(self, tmp_path: Path):
        """mark_item_done raises error if file changed unexpectedly."""
        backlog = tmp_path / "BACKLOG.md"
        write_backlog(backlog, """### P0 (Critical)

- [ ] **Task** -- DoD: Done -- Owner: dev
""")
        
        items = parse_backlog(backlog)
        
        # Modify file after parsing
        write_backlog(backlog, """### P0 (Critical)

- [ ] **Modified Task** -- DoD: Done -- Owner: dev
""")
        
        with pytest.raises(BacklogParseError) as exc_info:
            mark_item_done(backlog, items[0])
        
        assert "changed unexpectedly" in str(exc_info.value)
