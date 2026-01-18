#!/usr/bin/env python3
"""
LIFEOS_TODO Inventory Scanner

Scans the codebase for LIFEOS_TODO tags and generates inventory reports.

Usage:
    python scripts/todo_inventory.py              # markdown output
    python scripts/todo_inventory.py --json       # JSON output
    python scripts/todo_inventory.py --priority P0  # filter by priority
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Tag patterns
TODO_PATTERN = re.compile(
    r'LIFEOS_TODO(!?)\[(P[012])\]\s*(?:\[area:\s*([^\]]+)\])?\s*(?:\[exit:\s*([^\]]+)\])?\s*(.+?)(?:\n|$)',
    re.MULTILINE
)

# Paths to include/exclude
INCLUDE_PATTERNS = [
    'runtime/**/*.py',
    'docs/**/*.md',
    'config/**/*.yaml',
    'config/**/*.yml',
    'scripts/**/*.py',
    '*.md',
    '*.py',
]

EXCLUDE_PATTERNS = [
    '.git/**',
    '__pycache__/**',
    '**/*.pyc',
    '.claude/skills/**',  # Third-party skills
    '.venv/**',
    'venv/**',
    'node_modules/**',
]


def should_include_file(file_path: Path, repo_root: Path) -> bool:
    """Check if file should be included in scan."""
    rel_path = file_path.relative_to(repo_root)

    # Check exclusions first
    for pattern in EXCLUDE_PATTERNS:
        if rel_path.match(pattern):
            return False

    # Check inclusions
    for pattern in INCLUDE_PATTERNS:
        if rel_path.match(pattern):
            return True

    return False


def scan_file(file_path: Path) -> List[Dict]:
    """Scan a single file for LIFEOS_TODO tags."""
    todos = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError):
        return todos  # Skip binary files or permission errors

    for match in TODO_PATTERN.finditer(content):
        fail_loud = match.group(1) == '!'
        priority = match.group(2)  # Already includes 'P' prefix
        area = match.group(3) or ''
        exit_cmd = match.group(4) or ''
        description = match.group(5).strip()

        # Calculate line number
        line_number = content[:match.start()].count('\n') + 1

        todos.append({
            'file': str(file_path),
            'line': line_number,
            'priority': priority,
            'is_fail_loud': fail_loud,
            'area': area.strip(),
            'exit': exit_cmd.strip(),
            'description': description,
        })

    return todos


def scan_repository(repo_root: Path) -> List[Dict]:
    """Scan entire repository for LIFEOS_TODO tags."""
    all_todos = []

    for file_path in repo_root.rglob('*'):
        if not file_path.is_file():
            continue

        if should_include_file(file_path, repo_root):
            todos = scan_file(file_path)
            all_todos.extend(todos)

    # Sort by priority (P0 first), then file, then line
    priority_order = {'P0': 0, 'P1': 1, 'P2': 2}
    all_todos.sort(key=lambda t: (
        priority_order.get(t['priority'], 99),
        t['file'],
        t['line']
    ))

    return all_todos


def output_json(todos: List[Dict]) -> None:
    """Output inventory as JSON."""
    print(json.dumps({'todos': todos}, indent=2, sort_keys=True))


def output_markdown(todos: List[Dict]) -> None:
    """Output inventory as Markdown."""
    if not todos:
        print("# LIFEOS_TODO Inventory\n")
        print("No TODOs found.")
        return

    print("# LIFEOS_TODO Inventory\n")

    # Group by priority
    by_priority = {'P0': [], 'P1': [], 'P2': []}
    for todo in todos:
        by_priority[todo['priority']].append(todo)

    for priority in ['P0', 'P1', 'P2']:
        items = by_priority[priority]
        if not items:
            continue

        print(f"## {priority} ({len(items)} item{'s' if len(items) != 1 else ''})\n")

        for todo in items:
            fail_loud_marker = '!' if todo['is_fail_loud'] else ''
            print(f"### `{todo['file']}:{todo['line']}`")
            print(f"**LIFEOS_TODO{fail_loud_marker}[{priority}]** {todo['description']}\n")

            if todo['area']:
                print(f"- **Area:** `{todo['area']}`")
            if todo['exit']:
                print(f"- **Exit:** `{todo['exit']}`")

            print()


def main():
    parser = argparse.ArgumentParser(
        description='Scan codebase for LIFEOS_TODO tags',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON instead of Markdown'
    )
    parser.add_argument(
        '--priority',
        choices=['P0', 'P1', 'P2'],
        help='Filter by priority level'
    )
    parser.add_argument(
        '--repo-root',
        type=Path,
        help='Repository root path (default: auto-detect from script location)'
    )

    args = parser.parse_args()

    # Determine repo root
    if args.repo_root:
        repo_root = args.repo_root.resolve()
    else:
        # Assume script is in scripts/ subdirectory
        repo_root = Path(__file__).parent.parent.resolve()

    if not repo_root.exists():
        print(f"Error: Repository root does not exist: {repo_root}", file=sys.stderr)
        return 1

    # Scan repository
    todos = scan_repository(repo_root)

    # Filter by priority if requested
    if args.priority:
        todos = [t for t in todos if t['priority'] == args.priority]

    # Output results
    if args.json:
        output_json(todos)
    else:
        output_markdown(todos)

    return 0


if __name__ == '__main__':
    sys.exit(main())
