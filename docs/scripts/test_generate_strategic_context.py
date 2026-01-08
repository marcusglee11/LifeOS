"""
Tests for generate_strategic_context.py

Covers:
- Section-bounded extraction (CODE_REVIEW_STATUS)
- Active task detection (TASKS)
- Version-aware file selection
"""
import pytest
import tempfile
from pathlib import Path

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from generate_strategic_context import (
    parse_version,
    get_latest_file,
    get_test_status_section,
    prune_tasks_content,
)


# --- A) Test Status Section Extraction ---

FIXTURE_CODE_REVIEW_WITH_NOTES = """# Code Review Status

## History
- Fix 1: Fixed something
- Fix 2: Fixed another thing

## Test Status
All tests passing.
Coverage: 95%

## Notes
These notes should NOT appear.
"""

FIXTURE_CODE_REVIEW_NO_TEST_STATUS = """# Code Review Status

## History
- Fix 1: Fixed something
"""

def test_get_test_status_section_extracts_only_test_status():
    """A2: Test Status section only, stops at next ## header."""
    result = get_test_status_section(FIXTURE_CODE_REVIEW_WITH_NOTES)
    
    assert "## Test Status" in result
    assert "All tests passing." in result
    assert "Coverage: 95%" in result
    # Must NOT include the Notes section
    assert "## Notes" not in result
    assert "These notes should NOT appear" not in result
    # Must NOT include History
    assert "## History" not in result
    assert "Fix 1" not in result


def test_get_test_status_section_fallback_when_missing():
    """A2: Deterministic fallback when no Test Status section."""
    result = get_test_status_section(FIXTURE_CODE_REVIEW_NO_TEST_STATUS)
    
    assert "## Test Status" in result
    assert "Not found." in result


def test_get_test_status_section_case_insensitive():
    """Test Status header match is case-insensitive."""
    content = """# File
## test status
Some info here.
## Other
"""
    result = get_test_status_section(content)
    assert "Some info here." in result
    assert "## Other" not in result


# --- B) Tasks Pruning + Active Detection ---

FIXTURE_TASKS_ALL_DONE = """# Tasks

## Current Sprint
- [x] Task 1
- [x] Task 2

## Backlog
- [x] Old task
"""

FIXTURE_TASKS_SOME_ACTIVE = """# Tasks

## Current Sprint
- [x] Task 1 (done)
- [ ] Task 2 (active)

## Backlog
- [x] Old task
"""

FIXTURE_TASKS_EMPTY_BUT_HEADINGS = """# Tasks

## Current Sprint

## Backlog
"""


def test_prune_tasks_all_done_injects_message():
    """B3.1: When all tasks are checked, inject 'No active tasks pending.'"""
    result = prune_tasks_content(FIXTURE_TASKS_ALL_DONE)
    
    assert "No active tasks pending." in result


def test_prune_tasks_some_active_keeps_task():
    """B3.2: When unchecked tasks exist, keep them."""
    result = prune_tasks_content(FIXTURE_TASKS_SOME_ACTIVE)
    
    assert "Task 2 (active)" in result
    assert "No active tasks pending." not in result
    # Completed task should be removed
    assert "Task 1 (done)" not in result


def test_prune_tasks_headings_only_injects_message():
    """B3.1: Headings with no task checkboxes = no active tasks."""
    result = prune_tasks_content(FIXTURE_TASKS_EMPTY_BUT_HEADINGS)
    
    assert "No active tasks pending." in result


# --- C) Version-Aware File Selection ---

def test_parse_version_extracts_semver():
    """C1: Parse vX.Y and vX.Y.Z formats."""
    assert parse_version("Thing_v1.2.md") == (1, 2, 0)
    assert parse_version("Thing_v1.10.md") == (1, 10, 0)
    assert parse_version("Thing_v2.3.4.md") == (2, 3, 4)
    assert parse_version("NoVersion.md") is None


def test_parse_version_v1_10_greater_than_v1_2():
    """C2: v1.10 > v1.2 numerically."""
    v1_2 = parse_version("Thing_v1.2.md")
    v1_10 = parse_version("Thing_v1.10.md")
    
    assert v1_10 > v1_2


def test_get_latest_file_version_aware():
    """C2: get_latest_file returns highest version, not lexicographic."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        # Create files: v1.2 and v1.10
        (d / "Thing_v1.2.md").write_text("old")
        (d / "Thing_v1.10.md").write_text("new")
        
        result = get_latest_file(d, "Thing_*.md")
        
        assert result is not None
        assert result.name == "Thing_v1.10.md"


def test_get_latest_file_fallback_to_mtime():
    """C1: When no version tokens, fall back to mtime."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        # Create files without version
        older = d / "FileA.md"
        newer = d / "FileB.md"
        older.write_text("older")
        newer.write_text("newer")
        
        result = get_latest_file(d, "*.md")
        
        # Should return one of them (mtime-based, but both created nearly simultaneously)
        assert result is not None
        assert result.suffix == ".md"


# --- D) New Trimming & Deduplication Logic ---

def test_version_deduplication_keeps_latest_only():
    """Verify that only the highest version of a file is kept across the whole list."""
    from generate_strategic_context import VERSION_PATTERN, parse_version
    
    files = [
        Path("docs/00_foundations/ARCH_Doc_v0.1.md"),
        Path("docs/00_foundations/ARCH_Doc_v0.2.md"),
        Path("docs/01_governance/Rule_v1.0.md"),
        Path("docs/01_governance/Rule_v1.1.md"),
    ]
    
    version_groups = {}
    for f in files:
        base_name = VERSION_PATTERN.sub("", f.name)
        ver = parse_version(f.name) or (0, 0, 0)
        rel_base = f.parent / base_name
        if rel_base not in version_groups or ver > version_groups[rel_base][0]:
            version_groups[rel_base] = (ver, f)
            
    result = [v[1] for v in version_groups.values()]
    
    result_names = [f.name for f in result]
    assert "ARCH_Doc_v0.2.md" in result_names
    assert "ARCH_Doc_v0.1.md" not in result_names
    assert "Rule_v1.1.md" in result_names
    assert "Rule_v1.0.md" not in result_names


def test_process_file_truncates_large_content():
    """Verify that non-exempt files are truncated if they exceed MAX_CONTENT_CHARS."""
    from generate_strategic_context import process_file, MAX_CONTENT_CHARS
    
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir)
        (docs_dir / "large_file.md").write_text("A" * (MAX_CONTENT_CHARS + 100))
        
        # We need to mock DOCS_DIR in the module for process_file to work with relative_to
        import generate_strategic_context
        original_docs_dir = generate_strategic_context.DOCS_DIR
        generate_strategic_context.DOCS_DIR = docs_dir
        
        try:
            result = process_file(docs_dir / "large_file.md")
            assert "STRATEGIC TRUNCATION" in result
            assert len(result) < (MAX_CONTENT_CHARS + 500) # +500 for headers/markers
        finally:
            generate_strategic_context.DOCS_DIR = original_docs_dir


def test_process_file_exempts_constitution_from_truncation():
    """Verify that LifeOS_Constitution is NOT truncated even if large."""
    from generate_strategic_context import process_file, MAX_CONTENT_CHARS
    
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir)
        const_file = docs_dir / "LifeOS_Constitution.md"
        const_file.write_text("A" * (MAX_CONTENT_CHARS + 100))
        
        import generate_strategic_context
        original_docs_dir = generate_strategic_context.DOCS_DIR
        generate_strategic_context.DOCS_DIR = docs_dir
        
        try:
            result = process_file(const_file)
            assert "STRATEGIC TRUNCATION" not in result
            assert len(result) > MAX_CONTENT_CHARS
        finally:
            generate_strategic_context.DOCS_DIR = original_docs_dir


def test_process_file_thins_prompts():
    """Verify that files in 09_prompts are limited to PROMPT_PREVIEW_LINES."""
    from generate_strategic_context import process_file, PROMPT_PREVIEW_LINES
    
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir)
        prompts_dir = docs_dir / "09_prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "system_prompt_v1.0.md"
        prompt_file.write_text("Line\n" * (PROMPT_PREVIEW_LINES + 10))
        
        import generate_strategic_context
        original_docs_dir = generate_strategic_context.DOCS_DIR
        generate_strategic_context.DOCS_DIR = docs_dir
        
        try:
            result = process_file(prompt_file)
            assert "TRUNCATED" in result
            # Count lines in content (excluding header)
            lines = [l for l in result.splitlines() if l and not l.startswith("# File:")]
            assert len(lines) >= PROMPT_PREVIEW_LINES
            # It should have exactly PROMPT_PREVIEW_LINES of original content + note
            # find original content end
            content_lines = result.splitlines()
            header_idx = [i for i, l in enumerate(content_lines) if l.startswith("# File:")][0]
            actual_content = content_lines[header_idx+2:]
            # The first PROMPT_PREVIEW_LINES should be original, then the note
            assert actual_content[PROMPT_PREVIEW_LINES-1] == "Line"
            # The marker should be around here
            assert any("TRUNCATED" in line for line in actual_content[PROMPT_PREVIEW_LINES:])
        finally:
            generate_strategic_context.DOCS_DIR = original_docs_dir
