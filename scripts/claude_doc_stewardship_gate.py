#!/usr/bin/env python3
"""
Claude Code Doc Stewardship Gate

Enforces INDEX.md update and Strategic Corpus regeneration when docs/ modified.

Exit codes:
  0: Doc stewardship gate passed (or N/A)
  1: Doc stewardship gate failed
  2: Error condition
"""

import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def run_git_command(cmd: List[str], repo_root: Path) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{e.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Git command timed out: {' '.join(cmd)}")


def get_docs_modified_files(repo_root: Path) -> List[str]:
    """Get list of modified files in docs/ directory."""
    # Get all modified files
    try:
        output = run_git_command(["git", "diff", "--name-only", "HEAD"], repo_root)
        all_files = [f for f in output.split('\n') if f.strip()]

        # Also check git status for new files
        status_output = run_git_command(["git", "status", "--porcelain"], repo_root)
        for line in status_output.split('\n'):
            if line.strip():
                # Parse git status format: "XY filename"
                parts = line.strip().split(maxsplit=1)
                if len(parts) >= 2:
                    filename = parts[1]
                    # Handle renames (e.g., "R  old -> new")
                    if '->' in filename:
                        filename = filename.split('->')[-1].strip()
                    if filename not in all_files:
                        all_files.append(filename)

    except RuntimeError as e:
        # If git commands fail, return empty list
        return []

    # Filter for docs/ directory
    docs_files = [f for f in all_files if f.startswith('docs/')]
    return docs_files


def check_index_updated(repo_root: Path, docs_files: List[str]) -> Dict[str, Any]:
    """
    Check if docs/INDEX.md has been updated.

    Returns:
      - updated: bool
      - current_timestamp: str (if found)
      - error: str (if any)
    """
    index_path = repo_root / "docs" / "INDEX.md"

    if not index_path.exists():
        return {
            'updated': False,
            'current_timestamp': None,
            'error': 'docs/INDEX.md not found'
        }

    # Check if INDEX.md itself is in modified files
    if 'docs/INDEX.md' in docs_files:
        # Parse timestamp from INDEX.md
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for "Last Updated: YYYY-MM-DD" pattern
            match = re.search(r'Last Updated:\s*(\d{4}-\d{2}-\d{2})', content)
            if match:
                timestamp_str = match.group(1)
                # Check if timestamp is today
                today = datetime.now().strftime('%Y-%m-%d')

                return {
                    'updated': timestamp_str == today,
                    'current_timestamp': timestamp_str,
                    'error': None if timestamp_str == today else f'Timestamp is {timestamp_str}, expected {today}'
                }
            else:
                return {
                    'updated': False,
                    'current_timestamp': None,
                    'error': 'No "Last Updated: YYYY-MM-DD" timestamp found in INDEX.md'
                }

        except Exception as e:
            return {
                'updated': False,
                'current_timestamp': None,
                'error': f'Error reading INDEX.md: {str(e)}'
            }
    else:
        return {
            'updated': False,
            'current_timestamp': None,
            'error': 'docs/INDEX.md not in modified files'
        }


def check_strategic_corpus_updated(repo_root: Path, docs_files: List[str]) -> bool:
    """Check if Strategic Corpus appears in modified files."""
    return 'docs/LifeOS_Strategic_Corpus.md' in docs_files


def auto_fix_doc_stewardship(repo_root: Path) -> Dict[str, Any]:
    """
    Auto-fix doc stewardship violations.

    Returns:
      - success: bool
      - files_modified: list of files modified
      - errors: list of errors
    """
    files_modified = []
    errors = []

    # 1. Update INDEX.md timestamp
    index_path = repo_root / "docs" / "INDEX.md"
    today = datetime.now().strftime('%Y-%m-%d')

    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find and replace timestamp
        new_content = re.sub(
            r'(Last Updated:\s*)\d{4}-\d{2}-\d{2}',
            f'\\1{today}',
            content
        )

        if new_content != content:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            files_modified.append('docs/INDEX.md')
        else:
            # Try to add timestamp if not found
            if 'Last Updated:' not in content:
                errors.append('Could not find "Last Updated:" pattern in INDEX.md')

    except Exception as e:
        errors.append(f'Error updating INDEX.md: {str(e)}')

    # 2. Regenerate Strategic Corpus
    corpus_script = repo_root / "docs" / "scripts" / "generate_strategic_context.py"

    if not corpus_script.exists():
        errors.append(f'Strategic Corpus generator not found: {corpus_script}')
    else:
        try:
            result = subprocess.run(
                [sys.executable, str(corpus_script)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                files_modified.append('docs/LifeOS_Strategic_Corpus.md')
            else:
                errors.append(f'Strategic Corpus regeneration failed: {result.stderr}')

        except subprocess.TimeoutExpired:
            errors.append('Strategic Corpus regeneration timed out')
        except Exception as e:
            errors.append(f'Error regenerating Strategic Corpus: {str(e)}')

    return {
        'success': len(errors) == 0,
        'files_modified': files_modified,
        'errors': errors
    }


def enforce_doc_stewardship(repo_root: Path) -> Dict[str, Any]:
    """
    Enforce doc stewardship requirements.

    Returns:
      - passed: bool
      - docs_modified: bool
      - errors: list of error messages
    """
    # Check if any docs/ files were modified
    docs_files = get_docs_modified_files(repo_root)

    if not docs_files:
        # No docs modified, gate passes trivially
        return {
            'passed': True,
            'docs_modified': False,
            'errors': []
        }

    # Docs were modified, check stewardship requirements
    errors = []

    # 1. Check INDEX.md updated
    index_check = check_index_updated(repo_root, docs_files)
    if not index_check['updated']:
        error_msg = index_check['error'] or 'INDEX.md not updated'
        errors.append(f"INDEX.md stewardship required: {error_msg}")

    # 2. Check Strategic Corpus updated
    if not check_strategic_corpus_updated(repo_root, docs_files):
        errors.append("Strategic Corpus not regenerated (docs/LifeOS_Strategic_Corpus.md not in modified files)")

    return {
        'passed': len(errors) == 0,
        'docs_modified': True,
        'docs_files': docs_files,
        'errors': errors
    }


def main():
    """Main entry point."""
    # Parse arguments
    auto_fix = "--auto-fix" in sys.argv

    # Determine repo root
    repo_root = Path.cwd()
    while repo_root != repo_root.parent:
        if (repo_root / ".git").exists():
            break
        repo_root = repo_root.parent
    else:
        print(json.dumps({
            'passed': False,
            'docs_modified': False,
            'errors': ['Not in a git repository']
        }), file=sys.stderr)
        sys.exit(2)

    # Enforce gate
    result = enforce_doc_stewardship(repo_root)

    # Auto-fix if requested and gate failed
    if auto_fix and not result['passed']:
        fix_result = auto_fix_doc_stewardship(repo_root)
        result['auto_fix_attempted'] = True
        result['auto_fix_success'] = fix_result['success']
        result['auto_fix_files'] = fix_result['files_modified']

        if fix_result['success']:
            # Re-check after fix
            result = enforce_doc_stewardship(repo_root)
            result['auto_fix_applied'] = True
        else:
            result['errors'].extend(fix_result['errors'])

    # Output JSON
    print(json.dumps(result, indent=2))

    # Exit code
    if result['passed']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
