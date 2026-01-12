#!/usr/bin/env python3
"""
Tests for OpenCode Gate Policy (CT-2 Phase 2 v1.3)
===================================================

Bypass-resistance and functional tests for the doc-steward gate policy.
"""

import pytest
import os
import sys

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.opencode_gate_policy import (
    normalize_path,
    check_path_security,
    check_symlink,
    check_symlink_git_index,
    check_symlink_filesystem,
    matches_denylist,
    matches_allowlist,
    check_extension_under_docs,
    check_review_packets_addonly,
    parse_git_status_z,
    detect_blocked_ops,
    execute_diff_and_parse,
    get_diff_command,
    compute_hash,
    truncate_log,
    ReasonCode,
    DENYLIST_ROOTS,
    ALLOWLIST_ROOTS,
    WRITABLE_INDEX_FILES,
    LOG_MAX_LINES,
    LOG_MAX_BYTES,
)


class TestNormalizePath:
    """P1.2 — normalize_path() tests."""
    
    def test_backslash_conversion(self):
        assert normalize_path("docs\\INDEX.md") == "docs/index.md"
    
    def test_strip_leading_dot_slash(self):
        assert normalize_path("./docs/test.md") == "docs/test.md"
    
    def test_collapse_repeated_slashes(self):
        assert normalize_path("docs//sub//file.md") == "docs/sub/file.md"
    
    def test_lowercase(self):
        assert normalize_path("DOCS/00_Foundations/x.md") == "docs/00_foundations/x.md"
    
    def test_gemini_case(self):
        assert normalize_path("Gemini.MD") == "gemini.md"
    
    def test_mixed_normalization(self):
        assert normalize_path(".\\DOCS\\\\Test.MD") == "docs/test.md"


class TestPathSecurity:
    """P1.1 — Path traversal/absolute defense tests."""
    
    def test_traversal_blocked(self):
        safe, reason = check_path_security("docs/../etc/passwd", "/repo")
        assert not safe
        assert reason == ReasonCode.PATH_TRAVERSAL_BLOCKED
    
    def test_absolute_unix_blocked(self):
        safe, reason = check_path_security("/etc/passwd", "/repo")
        assert not safe
        assert reason == ReasonCode.PATH_ABSOLUTE_BLOCKED
    
    def test_absolute_windows_blocked(self):
        safe, reason = check_path_security("C:\\Windows\\System32", "/repo")
        assert not safe
        assert reason == ReasonCode.PATH_ABSOLUTE_BLOCKED
    
    def test_normal_path_allowed(self):
        safe, reason = check_path_security("docs/test.md", "/repo")
        assert safe
        assert reason is None


class TestDenylistMatching:
    """P0.2 — Denylist-first evaluation tests."""
    
    def test_denylist_root_config(self):
        matched, reason = matches_denylist("config/test.yaml")
        assert matched
        assert reason == ReasonCode.DENYLIST_ROOT_BLOCKED
    
    def test_denylist_root_foundations(self):
        matched, reason = matches_denylist("docs/00_foundations/constitution.md")
        assert matched
        assert reason == ReasonCode.DENYLIST_ROOT_BLOCKED
    
    def test_denylist_root_governance(self):
        matched, reason = matches_denylist("docs/01_governance/index.md")
        assert matched
        assert reason == ReasonCode.DENYLIST_ROOT_BLOCKED
    
    def test_denylist_exact_gemini(self):
        matched, reason = matches_denylist("gemini.md")
        assert matched
        assert reason == ReasonCode.DENYLIST_FILE_BLOCKED
    
    def test_denylist_extension_py(self):
        matched, reason = matches_denylist("docs/script.py")
        assert matched
        assert reason == ReasonCode.DENYLIST_EXT_BLOCKED
    
    def test_allowed_path_not_denied(self):
        matched, reason = matches_denylist("docs/test.md")
        assert not matched
        assert reason is None
    
    def test_case_bypass_gemini(self):
        """Bypass attempt: different case for GEMINI.md."""
        matched, reason = matches_denylist("Gemini.MD")
        assert matched
        assert reason == ReasonCode.DENYLIST_FILE_BLOCKED
    
    def test_case_bypass_foundations(self):
        """Bypass attempt: different case for foundations."""
        matched, reason = matches_denylist("DOCS/00_Foundations/x.md")
        assert matched
        assert reason == ReasonCode.DENYLIST_ROOT_BLOCKED


class TestExtensionRestriction:
    """Extension restriction under docs/."""
    
    def test_md_allowed(self):
        ok, reason = check_extension_under_docs("docs/test.md")
        assert ok
        assert reason is None
    
    def test_json_blocked(self):
        ok, reason = check_extension_under_docs("docs/data.json")
        assert not ok
        assert reason == ReasonCode.NON_MD_EXTENSION_BLOCKED
    
    def test_txt_blocked(self):
        ok, reason = check_extension_under_docs("docs/notes.txt")
        assert not ok
        assert reason == ReasonCode.NON_MD_EXTENSION_BLOCKED
    
    def test_double_extension_blocked(self):
        """Bypass attempt: double extension."""
        ok, reason = check_extension_under_docs("docs/file.md.py")
        assert not ok
        assert reason == ReasonCode.NON_MD_EXTENSION_BLOCKED


class TestReviewPacketsAddOnly:
    """P1.1 — Review packets add-only tests."""
    
    def test_add_md_allowed(self):
        ok, reason = check_review_packets_addonly("artifacts/review_packets/Review_Packet_Test_v1.0.md", "A")
        assert ok
        assert reason is None
    
    def test_modify_blocked(self):
        ok, reason = check_review_packets_addonly("artifacts/review_packets/Review_Packet_Test_v1.0.md", "M")
        assert not ok
        assert reason == ReasonCode.REVIEW_PACKET_NOT_ADD_ONLY
    
    def test_delete_blocked(self):
        ok, reason = check_review_packets_addonly("artifacts/review_packets/Review_Packet_Test_v1.0.md", "D")
        assert not ok
        assert reason == ReasonCode.REVIEW_PACKET_NOT_ADD_ONLY
    
    def test_non_md_blocked(self):
        ok, reason = check_review_packets_addonly("artifacts/review_packets/data.json", "A")
        assert not ok
        assert reason == ReasonCode.NON_MD_IN_REVIEW_PACKETS


class TestGitStatusParsing:
    """P0.3 — Rename/copy parsing tests."""
    
    def test_parse_add(self):
        output = "A\tdocs/new.md\0"
        parsed = parse_git_status_z(output)
        assert len(parsed) == 1
        assert parsed[0] == ("A", "docs/new.md")
    
    def test_parse_modify(self):
        output = "M\tdocs/existing.md\0"
        parsed = parse_git_status_z(output)
        assert len(parsed) == 1
        assert parsed[0] == ("M", "docs/existing.md")
    
    def test_parse_delete(self):
        output = "D\tdocs/deleted.md\0"
        parsed = parse_git_status_z(output)
        assert len(parsed) == 1
        assert parsed[0] == ("D", "docs/deleted.md")
    
    def test_parse_rename(self):
        """R100 with tab-separated status and old path, NUL, new path."""
        output = "R100\told.md\0new.md\0"
        parsed = parse_git_status_z(output)
        assert len(parsed) == 1
        assert parsed[0][0] == "R"
        assert "old" in parsed[0][1] or "old" in str(parsed[0])
    
    def test_parse_empty(self):
        parsed = parse_git_status_z("")
        assert parsed == []


class TestBlockedOpsDetection:
    """P0.3 — Blocked operation detection tests."""
    
    def test_delete_blocked(self):
        parsed = [("D", "docs/deleted.md")]
        blocked = detect_blocked_ops(parsed)
        assert len(blocked) == 1
        assert blocked[0][1] == "delete"
        assert blocked[0][2] == ReasonCode.PH2_DELETE_BLOCKED
    
    def test_rename_blocked(self):
        parsed = [("R", "old.md", "new.md")]
        blocked = detect_blocked_ops(parsed)
        assert len(blocked) == 1
        assert blocked[0][1] == "rename"
        assert blocked[0][2] == ReasonCode.PH2_RENAME_BLOCKED
        assert "old.md->new.md" in blocked[0][0]
    
    def test_copy_blocked(self):
        parsed = [("C", "src.md", "dst.md")]
        blocked = detect_blocked_ops(parsed)
        assert len(blocked) == 1
        assert blocked[0][1] == "copy"
        assert blocked[0][2] == ReasonCode.PH2_COPY_BLOCKED
    
    def test_add_modify_not_blocked(self):
        parsed = [("A", "new.md"), ("M", "existing.md")]
        blocked = detect_blocked_ops(parsed)
        assert blocked == []


class TestIndexDiscovery:
    """P0.1 — Index discovery scope tests."""
    
    def test_governance_index_excluded(self):
        """docs/01_governance/ is in denylist, so its index should be excluded."""
        assert "docs/01_governance/index.md" not in WRITABLE_INDEX_FILES
    
    def test_docs_root_index_included(self):
        """docs/index.md should be in writable list."""
        assert "docs/index.md" in WRITABLE_INDEX_FILES
    
    def test_review_packets_not_in_index(self):
        """Review packets should not affect index enumeration."""
        for path in WRITABLE_INDEX_FILES:
            assert not path.startswith("artifacts/")


class TestHashing:
    """Evidence contract — hashing tests."""
    
    def test_hash_format(self):
        result = compute_hash("test content")
        assert "algorithm" in result
        assert result["algorithm"] == "sha256"
        assert "hex" in result
        assert len(result["hex"]) == 64


class TestTruncation:
    """Evidence contract — truncation tests."""
    
    def test_no_truncation_small(self):
        content = "small content"
        result, truncated = truncate_log(content)
        assert not truncated
        assert result == content
    
    def test_truncation_footer_format(self):
        # Create content exceeding limits
        large_content = "\n".join(["line"] * (LOG_MAX_LINES + 100))
        result, truncated = truncate_log(large_content)
        assert truncated
        assert "[TRUNCATED]" in result
        assert f"cap_lines={LOG_MAX_LINES}" in result
        assert f"cap_bytes={LOG_MAX_BYTES}" in result
        assert "observed_lines=" in result
        assert "observed_bytes=" in result
        # STRICT: No ellipses in footer
        assert "..." not in result
        assert result.endswith("observed_bytes=" + str(len(large_content.encode('utf-8'))))


class TestRunnerLogHygiene:
    """P0.3 — Verify runner logs do not contain ellipses."""
    
    def test_runner_source_no_ellipses_in_logs(self):
        """Scan opencode_ci_runner.py to ensure no log() calls contain partial ellipses."""
        import scripts.opencode_ci_runner as runner_module
        import inspect
        
        # Static scan of the source file
        source = inspect.getsource(runner_module)
        
        # Find all log("...") calls
        import re
        # Look for log("text...") or log('text...')
        # Note: We want to catch the literal sequence "..." inside quotes passed to log()
        
        # Simple check: does the file contain '..."' inside a log call?
        # This is hard to regex perfectly, but we can search for the specific lines we removed.
        
        forbidden = [
            'Executing mission...',
            'Validating post-execution diff against envelope...',
            'Simulating server response...',
            'Starting ephemeral OpenCode server on port {port}...',
            'key[:8]...'
        ]
        
        for phrase in forbidden:
            assert phrase not in source, f"Found forbidden ellipsis phrase: {phrase}"
        
        # General regex check for log() calls with trailing ellipses
        # Matches: log("text...", ...) or log(f"text...", ...) or log(f'text...', ...)
        ellipsis_log_pattern = re.compile(r'log\s*\(\s*f?["\'].*\.\.\.["\']')
        matches = ellipsis_log_pattern.findall(source)
        
        # We allow "..." in comments or docstrings, but pattern above targets log() calls
        assert not matches, f"Found log() calls with trailing ellipses: {matches}"


class TestSymlinkDefense:
    """P0 — Symlink defense tests."""
    
    def test_symlink_reason_code_exists(self):
        """Verify SYMLINK_BLOCKED reason code exists."""
        assert hasattr(ReasonCode, 'SYMLINK_BLOCKED')
        assert ReasonCode.SYMLINK_BLOCKED == "SYMLINK_BLOCKED"
    
    def test_symlink_filesystem_regular_file(self, tmp_path):
        """Regular file should not be detected as symlink."""
        regular_file = tmp_path / "test.md"
        regular_file.write_text("content")
        is_sym, reason = check_symlink_filesystem("test.md", str(tmp_path))
        assert not is_sym
        assert reason is None
    
    def test_symlink_filesystem_detects_symlink(self, tmp_path):
        """Symlink should be detected by filesystem check."""
        target_file = tmp_path / "target.md"
        target_file.write_text("target")
        symlink = tmp_path / "link.md"
        try:
            symlink.symlink_to(target_file)
            is_sym, reason = check_symlink_filesystem("link.md", str(tmp_path))
            assert is_sym
            assert reason == ReasonCode.SYMLINK_BLOCKED
        except OSError:
            pytest.skip("Symlink creation not supported on this system")
    
    def test_symlink_in_parent_path(self, tmp_path):
        """Symlink in parent path component should be detected."""
        target_dir = tmp_path / "real_docs"
        target_dir.mkdir()
        docs_link = tmp_path / "docs"
        try:
            docs_link.symlink_to(target_dir)
            is_sym, reason = check_symlink_filesystem("docs/test.md", str(tmp_path))
            assert is_sym
            assert reason == ReasonCode.SYMLINK_BLOCKED
        except OSError:
            pytest.skip("Symlink creation not supported on this system")


class TestGoldenFixturesRenameCopy:
    """P0 — Rename/copy parsing with exact wire formats (golden fixtures)."""
    
    def test_golden_rename_r100(self):
        """Golden fixture: R100\\told_path\\0new_path\\0 → BLOCK rename."""
        # Wire format: R100<TAB>old_path<NUL>new_path<NUL>
        output = "R100\told_path.md\0new_path.md\0"
        parsed = parse_git_status_z(output)
        assert len(parsed) == 1
        assert parsed[0][0] == "R"
        # Check blocked ops detection
        blocked = detect_blocked_ops(parsed)
        assert len(blocked) == 1
        assert blocked[0][1] == "rename"
        assert blocked[0][2] == ReasonCode.PH2_RENAME_BLOCKED
        # Evidence includes both paths
        assert "old_path.md" in blocked[0][0]
        assert "new_path.md" in blocked[0][0]
    
    def test_golden_copy_c100(self):
        """Golden fixture: C100\\told_path\\0new_path\\0 → BLOCK copy."""
        output = "C100\tsrc.md\0dst.md\0"
        parsed = parse_git_status_z(output)
        assert len(parsed) == 1
        assert parsed[0][0] == "C"
        blocked = detect_blocked_ops(parsed)
        assert len(blocked) == 1
        assert blocked[0][1] == "copy"
        assert blocked[0][2] == ReasonCode.PH2_COPY_BLOCKED
        assert "src.md" in blocked[0][0]
        assert "dst.md" in blocked[0][0]
    
    def test_golden_mixed_operations(self):
        """Golden fixture: mixed A/M/R/D operations."""
        output = "A\tnew.md\0M\tmodified.md\0R100\told.md\0renamed.md\0D\tdeleted.md\0"
        parsed = parse_git_status_z(output)
        # Should have 4 entries
        assert len(parsed) >= 3  # At minimum A, M, R
        blocked = detect_blocked_ops(parsed)
        # At least rename and delete should be blocked
        assert any(b[1] == "rename" for b in blocked)
        assert any(b[1] == "delete" for b in blocked)


class TestBoundarySafeMatching:
    """P1 — Boundary-safe root matching tests."""
    
    def test_docsx_does_not_match_docs(self):
        """docsx/ must NOT match docs/ allowlist."""
        # Path "docsx/..." should not be allowed
        assert not matches_allowlist("docsx/test.md")
    
    def test_docs_matches_docs(self):
        """docs/ SHOULD match docs/ allowlist."""
        assert matches_allowlist("docs/test.md")
    
    def test_docs_with_trailing_slashes(self):
        """docs/// should normalize and match."""
        from scripts.opencode_gate_policy import normalize_path
        norm = normalize_path("docs///test.md")
        assert norm == "docs/test.md"
    
    def test_artifacts_review_packets_prefix(self):
        """artifacts_review_packets/ must NOT match artifacts/review_packets/."""
        assert not matches_allowlist("artifacts_review_packets/test.md")
    
    def test_config_denylist_prefix(self):
        """configs/ does NOT match config/ denylist."""
        matched, reason = matches_denylist("configs/test.yaml")
        # 'configs/' starts with 'config' but not 'config/'
        # This should NOT match denylist because it's a different path
        # Strict assertion: must NOT match
        assert matched is False, f"configs/ should NOT match config/ denylist, got reason={reason}"


class TestCIDiffFailClosed:
    """P0 — CI diff acquisition terminal fail-closed tests."""
    
    def test_diff_exec_failed_reason_code_exists(self):
        """Verify DIFF_EXEC_FAILED reason code exists."""
        assert hasattr(ReasonCode, 'DIFF_EXEC_FAILED')
        assert ReasonCode.DIFF_EXEC_FAILED == "DIFF_EXEC_FAILED"
    
    def test_refs_unavailable_reason_code_exists(self):
        """Verify REFS_UNAVAILABLE reason code exists."""
        assert hasattr(ReasonCode, 'REFS_UNAVAILABLE')
    
    def test_merge_base_failed_reason_code_exists(self):
        """Verify MERGE_BASE_FAILED reason code exists."""
        assert hasattr(ReasonCode, 'MERGE_BASE_FAILED')


class TestCIDiffFailClosedMocked:
    """P0.2 — Mock-based behavioral tests for CI diff fail-closed."""
    
    def test_refs_unavailable_when_github_base_ref_missing(self, monkeypatch):
        """Missing GITHUB_BASE_REF in CI => REFS_UNAVAILABLE."""
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_SHA", "abc123")
        monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
        
        cmd, mode = get_diff_command()
        
        assert cmd is None, "Command must be None when refs unavailable"
        assert mode == ReasonCode.REFS_UNAVAILABLE, f"Expected REFS_UNAVAILABLE, got {mode}"
    
    def test_refs_unavailable_when_github_sha_missing(self, monkeypatch):
        """Missing GITHUB_SHA in CI => REFS_UNAVAILABLE."""
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_BASE_REF", "main")
        monkeypatch.delenv("GITHUB_SHA", raising=False)
        
        cmd, mode = get_diff_command()
        
        assert cmd is None, "Command must be None when refs unavailable"
        assert mode == ReasonCode.REFS_UNAVAILABLE, f"Expected REFS_UNAVAILABLE, got {mode}"
    
    def test_merge_base_failed_on_subprocess_error(self, monkeypatch, tmp_path):
        """Subprocess merge-base failure => terminal BLOCK with MERGE_BASE_FAILED."""
        from unittest.mock import patch, MagicMock
        
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_BASE_REF", "main")
        monkeypatch.setenv("GITHUB_SHA", "abc123")
        
        # Mock subprocess.run to simulate merge-base failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "fatal: not a valid object name"
        
        with patch('scripts.opencode_gate_policy.subprocess.run', return_value=mock_result) as mock_run:
            parsed, mode, error = execute_diff_and_parse(str(tmp_path))
            
            assert parsed is None, "Parsed must be None on merge-base failure"
            assert error == ReasonCode.MERGE_BASE_FAILED or error == ReasonCode.DIFF_EXEC_FAILED, \
                f"Expected MERGE_BASE_FAILED or DIFF_EXEC_FAILED, got {error}"
    
    def test_diff_exec_failed_on_exception(self, monkeypatch, tmp_path):
        """Exception during diff execution => terminal BLOCK with DIFF_EXEC_FAILED."""
        from unittest.mock import patch
        
        # Use LOCAL mode to avoid merge-base call in get_diff_command()
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("CI_MERGE_REQUEST_TARGET_BRANCH_SHA", raising=False)
        
        with patch('scripts.opencode_gate_policy.subprocess.run', side_effect=Exception("Subprocess crashed")):
            parsed, mode, error = execute_diff_and_parse(str(tmp_path))
            
            assert parsed is None, "Parsed must be None on exception"
            assert mode == "LOCAL", f"Expected LOCAL mode, got {mode}"
            assert error == ReasonCode.DIFF_EXEC_FAILED, f"Expected DIFF_EXEC_FAILED, got {error}"
    
    def test_successful_diff_returns_parsed_list(self, monkeypatch, tmp_path):
        """Successful diff execution returns parsed list with no error."""
        from unittest.mock import patch, MagicMock
        
        # Use local mode (no CI env vars)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("CI", raising=False)
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M\tdocs/test.md\0"
        
        with patch('scripts.opencode_gate_policy.subprocess.run', return_value=mock_result):
            parsed, mode, error = execute_diff_and_parse(str(tmp_path))
            
            assert error is None, f"Expected no error, got {error}"
            assert parsed is not None, "Parsed should not be None on success"
            assert mode == "LOCAL", f"Expected LOCAL mode, got {mode}"


class TestSymlinkGitIndexMocked:
    """P0.3 — Mock-based tests for git-index symlink detection (deterministic)."""
    
    def test_git_index_symlink_mode_120000_detected(self, tmp_path):
        """Git index mode 120000 => SYMLINK_BLOCKED."""
        from unittest.mock import patch, MagicMock
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "120000 abc123def456 0\tdocs/link.md"
        
        with patch('scripts.opencode_gate_policy.subprocess.run', return_value=mock_result):
            is_sym, reason = check_symlink_git_index("docs/link.md", str(tmp_path))
            
            assert is_sym is True, "Mode 120000 must be detected as symlink"
            assert reason == ReasonCode.SYMLINK_BLOCKED, f"Expected SYMLINK_BLOCKED, got {reason}"
    
    def test_git_index_regular_file_mode_100644_not_flagged(self, tmp_path):
        """Git index mode 100644 (regular file) => NOT a symlink."""
        from unittest.mock import patch, MagicMock
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "100644 abc123def456 0\tdocs/file.md"
        
        with patch('scripts.opencode_gate_policy.subprocess.run', return_value=mock_result):
            is_sym, reason = check_symlink_git_index("docs/file.md", str(tmp_path))
            
            assert is_sym is False, "Mode 100644 must NOT be flagged as symlink"
            assert reason is None, f"Expected no reason, got {reason}"
    
    def test_git_index_executable_mode_100755_not_flagged(self, tmp_path):
        """Git index mode 100755 (executable) => NOT a symlink."""
        from unittest.mock import patch, MagicMock
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "100755 abc123def456 0\tscripts/run.sh"
        
        with patch('scripts.opencode_gate_policy.subprocess.run', return_value=mock_result):
            is_sym, reason = check_symlink_git_index("scripts/run.sh", str(tmp_path))
            
            assert is_sym is False, "Mode 100755 must NOT be flagged as symlink"
            assert reason is None
    
    def test_git_index_empty_response_not_flagged(self, tmp_path):
        """Empty git ls-files response => NOT a symlink (untracked file)."""
        from unittest.mock import patch, MagicMock
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        
        with patch('scripts.opencode_gate_policy.subprocess.run', return_value=mock_result):
            is_sym, reason = check_symlink_git_index("docs/new.md", str(tmp_path))
            
            assert is_sym is False, "Empty response must NOT be flagged"
            assert reason is None
    
    def test_git_index_exception_blocks_fail_closed(self, tmp_path):
        """Exception during git ls-files => BLOCK with SYMLINK_CHECK_FAILED (fail-closed)."""
        from unittest.mock import patch
        
        with patch('scripts.opencode_gate_policy.subprocess.run', side_effect=Exception("Git not available")):
            is_sym, reason = check_symlink_git_index("docs/file.md", str(tmp_path))
            
            # Phase 2: fail-closed - if we can't verify, we BLOCK
            assert is_sym is True, "Exception must trigger BLOCK (fail-closed)"
            assert reason == ReasonCode.SYMLINK_CHECK_FAILED
    
    def test_git_index_nonzero_return_blocks_fail_closed(self, tmp_path):
        """Nonzero return code from git ls-files => BLOCK with SYMLINK_CHECK_FAILED."""
        from unittest.mock import patch, MagicMock
        
        mock_result = MagicMock()
        mock_result.returncode = 128  # Git error
        mock_result.stdout = ""
        
        with patch('scripts.opencode_gate_policy.subprocess.run', return_value=mock_result):
            is_sym, reason = check_symlink_git_index("docs/file.md", str(tmp_path))
            
            assert is_sym is True, "Nonzero return code must trigger BLOCK"
            assert reason == ReasonCode.SYMLINK_CHECK_FAILED



class TestBoundaryMatchingStrict:
    """P1.1 — Strict boundary-safe matching assertions (replaces weak tests)."""
    
    def test_docsx_strictly_not_allowed(self):
        """docsx/ must STRICTLY NOT match docs/ allowlist."""
        result = matches_allowlist("docsx/test.md")
        assert result is False, "STRICT: docsx/ must return False, not truthy-falsy"
    
    def test_artifacts_review_packets_underscore_strictly_blocked(self):
        """artifacts_review_packets/ STRICTLY not allowed."""
        result = matches_allowlist("artifacts_review_packets/test.md")
        assert result is False, "STRICT: artifacts_review_packets/ must return False"
    
    def test_docs_strictly_allowed(self):
        """docs/ STRICTLY allowed."""
        result = matches_allowlist("docs/test.md")
        assert result is True, "STRICT: docs/test.md must return True"
    
    def test_artifacts_review_packets_strictly_allowed(self):
        """artifacts/review_packets/ STRICTLY allowed."""
        result = matches_allowlist("artifacts/review_packets/Review_Packet_Test_v1.0.md")
        assert result is True, "STRICT: artifacts/review_packets/ must return True"
    
    def test_root_file_strictly_blocked(self):
        """Root-level files STRICTLY blocked."""
        result = matches_allowlist("README.md")
        assert result is False, "STRICT: root-level files must return False"


class TestRunnerEnvelopeEnforcement:
    """P0.3 — Runner-level tests proving no envelope bypass."""
    
    @pytest.fixture
    def validate_entry(self):
        """Import validate_diff_entry from runner."""
        from scripts.opencode_ci_runner import validate_diff_entry
        return validate_diff_entry
    
    def test_denylisted_path_blocked(self, validate_entry):
        """Denylisted path change => BLOCK with DENYLIST_ROOT_BLOCKED."""
        allowed, reason = validate_entry("M", "docs/00_foundations/test.md")
        assert allowed is False, "Denylisted path must be blocked"
        assert reason == ReasonCode.DENYLIST_ROOT_BLOCKED
    
    def test_denylisted_governance_blocked(self, validate_entry):
        """Governance path change => BLOCK."""
        allowed, reason = validate_entry("A", "docs/01_governance/new.md")
        assert allowed is False, "Governance path must be blocked"
        assert reason == ReasonCode.DENYLIST_ROOT_BLOCKED
    
    def test_denylisted_scripts_blocked(self, validate_entry):
        """Scripts path change => BLOCK."""
        allowed, reason = validate_entry("M", "scripts/test.py")
        assert allowed is False, "Scripts path must be blocked"
        # Could be DENYLIST_ROOT_BLOCKED or DENYLIST_EXT_BLOCKED
        assert reason in [ReasonCode.DENYLIST_ROOT_BLOCKED, ReasonCode.DENYLIST_EXT_BLOCKED]
    
    def test_outside_allowlist_blocked(self, validate_entry):
        """Out-of-allowlist path => BLOCK with OUTSIDE_ALLOWLIST_BLOCKED."""
        allowed, reason = validate_entry("M", "src/main.py")
        assert allowed is False, "Out-of-allowlist path must be blocked"
        # Could be DENYLIST_EXT_BLOCKED first or OUTSIDE
        assert reason in [ReasonCode.OUTSIDE_ALLOWLIST_BLOCKED, ReasonCode.DENYLIST_EXT_BLOCKED]
    
    def test_non_md_under_docs_blocked(self, validate_entry):
        """Non-.md under docs/ => BLOCK with NON_MD_EXTENSION_BLOCKED."""
        allowed, reason = validate_entry("A", "docs/test.txt")
        assert allowed is False, "Non-.md under docs must be blocked"
        assert reason == ReasonCode.NON_MD_EXTENSION_BLOCKED
    
    def test_yaml_under_docs_blocked(self, validate_entry):
        """YAML under docs/ => BLOCK."""
        allowed, reason = validate_entry("M", "docs/config.yaml")
        assert allowed is False, "YAML under docs must be blocked"
        assert reason == ReasonCode.NON_MD_EXTENSION_BLOCKED
    
    def test_review_packets_modify_blocked(self, validate_entry):
        """Review packets modify => BLOCK with REVIEW_PACKET_NOT_ADD_ONLY."""
        allowed, reason = validate_entry("M", "artifacts/review_packets/Review_Packet_Test_v1.0.md")
        assert allowed is False, "Review packets modify must be blocked"
        assert reason == ReasonCode.REVIEW_PACKET_NOT_ADD_ONLY
    
    def test_review_packets_delete_blocked(self, validate_entry):
        """Review packets delete => BLOCK with PH2_DELETE_BLOCKED."""
        allowed, reason = validate_entry("D", "artifacts/review_packets/old.md")
        assert allowed is False, "Review packets delete must be blocked"
        assert reason == ReasonCode.PH2_DELETE_BLOCKED
    
    def test_review_packets_rename_blocked(self, validate_entry):
        """Review packets rename => BLOCK with PH2_RENAME_BLOCKED."""
        allowed, reason = validate_entry("R100", "artifacts/review_packets/renamed.md")
        assert allowed is False, "Review packets rename must be blocked"
        assert reason == ReasonCode.PH2_RENAME_BLOCKED
    
    def test_review_packets_add_non_md_blocked(self, validate_entry):
        """Review packets add non-.md => BLOCK with NON_MD_IN_REVIEW_PACKETS."""
        allowed, reason = validate_entry("A", "artifacts/review_packets/data.json")
        assert allowed is False, "Review packets add non-.md must be blocked"
        assert reason == ReasonCode.NON_MD_IN_REVIEW_PACKETS
    
    def test_review_packets_add_md_allowed(self, validate_entry):
        """Review packets add .md => ALLOWED."""
        allowed, reason = validate_entry("A", "artifacts/review_packets/Review_Packet_New_v1.0.md")
        assert allowed is True, "Review packets add .md must be allowed"
        assert reason is None
    
    def test_docs_add_md_allowed(self, validate_entry):
        """docs/ add .md => ALLOWED."""
        allowed, reason = validate_entry("A", "docs/new_doc.md")
        assert allowed is True, "docs add .md must be allowed"
        assert reason is None
    
    def test_docs_modify_md_allowed(self, validate_entry):
        """docs/ modify .md => ALLOWED."""
        allowed, reason = validate_entry("M", "docs/existing.md")
        assert allowed is True, "docs modify .md must be allowed"
        assert reason is None
    
    def test_any_delete_blocked(self, validate_entry):
        """Any delete operation => BLOCK."""
        allowed, reason = validate_entry("D", "docs/test.md")
        assert allowed is False, "Delete must always be blocked"
        assert reason == ReasonCode.PH2_DELETE_BLOCKED
    
    def test_any_copy_blocked(self, validate_entry):
        """Any copy operation => BLOCK."""
        allowed, reason = validate_entry("C100", "docs/copy.md")
        assert allowed is False, "Copy must always be blocked"
        assert reason == ReasonCode.PH2_COPY_BLOCKED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


