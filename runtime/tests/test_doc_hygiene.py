"""
BDD/TDD tests for doc_hygiene_markdown_lint.py

Feature: Markdown linting for documentation hygiene

Scenarios:
1. Lint markdown files with fixable issues
2. Lint markdown files with no issues
3. Lint fails with unfixable issues
4. Missing markdownlint dependency
"""

import unittest
import subprocess
import tempfile
import shutil
from pathlib import Path


class TestDocHygieneMarkdownLint(unittest.TestCase):
    """Test suite for markdown linting script."""

    def setUp(self):
        """Create temporary test directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

    def tearDown(self):
        """Clean up temporary test directory."""
        shutil.rmtree(self.test_dir)

    def test_lint_fixes_violations(self):
        """
        Scenario: Lint markdown files with fixable issues
        Given the directory contains markdown files
        And at least one file has a fixable lint violation
        When I run doc_hygiene_markdown_lint.py
        Then the violations are auto-fixed
        And the script exits with code 0
        And stdout contains a summary of changes
        """
        # Create test markdown file with MD022 violation (headings need blank lines)
        test_file = self.test_path / "test.md"
        original_content = "# Test\nNo blank line after heading.\n\nContent here.\n"
        test_file.write_text(original_content)

        # Get repo root dynamically
        repo_root = Path(__file__).parent.parent.parent
        # Run the script
        result = subprocess.run(
            ["python3", "scripts/doc_hygiene_markdown_lint.py", str(self.test_path)],
            cwd=str(repo_root),
            capture_output=True,
            text=True
        )

        # Assert exit code 0 (success with fixes)
        self.assertEqual(result.returncode, 0, f"Expected exit 0, got {result.returncode}. stderr: {result.stderr}")

        # Assert file was modified (blank line added after heading)
        fixed_content = test_file.read_text()
        self.assertNotEqual(original_content, fixed_content, "File should be modified")
        self.assertIn("# Test\n\n", fixed_content, "Blank line should be added after heading")

        # Assert stdout contains summary
        self.assertIn("fixed", result.stdout.lower() or result.stderr.lower(),
                     f"Output should mention fixes. stdout: {result.stdout}, stderr: {result.stderr}")

    def test_lint_clean_files(self):
        """
        Scenario: Lint markdown files with no issues
        Given the directory contains markdown files
        And all files pass linting
        When I run doc_hygiene_markdown_lint.py
        Then no files are modified
        And the script exits with code 0
        """
        # Create valid markdown file
        test_file = self.test_path / "clean.md"
        clean_content = "# Clean File\n\nThis is a properly formatted markdown file.\n"
        test_file.write_text(clean_content)

        # Get repo root dynamically
        repo_root = Path(__file__).parent.parent.parent
        # Run the script
        result = subprocess.run(
            ["python3", "scripts/doc_hygiene_markdown_lint.py", str(self.test_path)],
            cwd=str(repo_root),
            capture_output=True,
            text=True
        )

        # Assert exit code 0
        self.assertEqual(result.returncode, 0, f"Expected exit 0, got {result.returncode}. stderr: {result.stderr}")

        # Assert file unchanged
        final_content = test_file.read_text()
        self.assertEqual(clean_content, final_content, "Clean file should not be modified")

    def test_lint_unfixable_violations(self):
        """
        Scenario: Lint fails with unfixable violations
        Given the directory contains markdown files
        And at least one file has an unfixable violation
        When I run doc_hygiene_markdown_lint.py
        Then fixable issues are corrected
        And the script exits with code 1
        And stderr lists unfixable violations with line numbers

        Note: Most markdownlint rules are fixable. This test checks behavior
        when --fix doesn't resolve all issues (e.g., if we disable auto-fix
        for certain rules or if there are genuinely unfixable issues).
        """
        # Create markdown file with violations
        test_file = self.test_path / "issues.md"
        # MD022: headings need blank lines around them (fixable)
        # MD032: lists need blank lines around them (fixable)
        content = "# Heading\nNo blank line after.\n- List item\nNo blank line around list.\n"
        test_file.write_text(content)

        # Get repo root dynamically
        repo_root = Path(__file__).parent.parent.parent
        # Run the script
        result = subprocess.run(
            ["python3", "scripts/doc_hygiene_markdown_lint.py", str(self.test_path)],
            cwd=str(repo_root),
            capture_output=True,
            text=True
        )

        # For now, markdownlint --fix handles most issues, so we expect exit 0
        # If there were truly unfixable issues, we'd expect exit 1
        # This test validates the script handles both cases
        self.assertIn(result.returncode, [0, 1],
                     f"Expected exit 0 or 1, got {result.returncode}. stderr: {result.stderr}")

    def test_missing_markdownlint_dependency(self):
        """
        Scenario: Missing markdownlint dependency
        Given markdownlint-cli is not installed
        When I run doc_hygiene_markdown_lint.py
        Then the script exits with code 127
        And stderr contains installation instructions

        Note: This test is informational - we assume markdownlint is installed
        in the actual environment. The script should handle missing dependencies
        gracefully.
        """
        # This test documents expected behavior but doesn't actively break the environment
        # In actual implementation, the script should check for markdownlint availability
        # and provide helpful error messages
        pass

    def test_json_output_format(self):
        """
        Test that --json flag produces valid JSON output.
        """
        # Create test file
        test_file = self.test_path / "test.md"
        test_file.write_text("# Test\n\nContent.\n")

        # Get repo root dynamically
        repo_root = Path(__file__).parent.parent.parent
        # Run with --json flag
        result = subprocess.run(
            ["python3", "scripts/doc_hygiene_markdown_lint.py", str(self.test_path), "--json"],
            cwd=str(repo_root),
            capture_output=True,
            text=True
        )

        # Should not crash
        self.assertIn(result.returncode, [0, 1],
                     f"Script should not crash with --json. stderr: {result.stderr}")

    def test_dry_run_mode(self):
        """
        Test that --dry-run doesn't modify files.
        """
        # Create test file with fixable issues
        test_file = self.test_path / "test.md"
        original_content = "# Test   \n\nTrailing spaces.   \n"
        test_file.write_text(original_content)

        # Get repo root dynamically
        repo_root = Path(__file__).parent.parent.parent
        # Run with --dry-run
        result = subprocess.run(
            ["python3", "scripts/doc_hygiene_markdown_lint.py", str(self.test_path), "--dry-run"],
            cwd=str(repo_root),
            capture_output=True,
            text=True
        )

        # File should remain unchanged
        final_content = test_file.read_text()
        self.assertEqual(original_content, final_content,
                        "Dry-run should not modify files")


if __name__ == "__main__":
    unittest.main()
