#!/usr/bin/env python3
"""
Claude Code Session Completion Orchestrator

Master gate runner that enforces all Claude Code session completion requirements:
1. Eligibility determination (Lightweight vs Standard mode)
2. Review Packet existence and validity
3. Doc stewardship when docs/ modified

Exit codes:
  0: All gates passed
  1: One or more gates failed
  2: Error condition
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any


def run_gate_script(script_name: str, args: list, repo_root: Path) -> Dict[str, Any]:
    """
    Run a gate script and parse JSON output.

    Returns:
      - exit_code: int
      - result: dict (parsed JSON output)
      - error: str (if any)
    """
    script_path = repo_root / "scripts" / script_name

    if not script_path.exists():
        return {
            'exit_code': 2,
            'result': {},
            'error': f"Gate script not found: {script_name}"
        }

    cmd = [sys.executable, str(script_path)] + args

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=120
        )

        # Try to parse JSON output
        try:
            if result.stdout.strip():
                parsed = json.loads(result.stdout)
            else:
                parsed = {}
        except json.JSONDecodeError:
            parsed = {'raw_output': result.stdout}

        return {
            'exit_code': result.returncode,
            'result': parsed,
            'error': result.stderr if result.stderr else None
        }

    except subprocess.TimeoutExpired:
        return {
            'exit_code': 2,
            'result': {},
            'error': f"Gate script timed out: {script_name}"
        }
    except Exception as e:
        return {
            'exit_code': 2,
            'result': {},
            'error': f"Error running gate script {script_name}: {str(e)}"
        }


def prompt_yes_no(message: str) -> bool:
    """Prompt user for yes/no input."""
    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def print_result(emoji: str, message: str):
    """Print a result message."""
    print(f"{emoji} {message}")


def main():
    """Main entry point."""
    # Determine repo root
    repo_root = Path.cwd()
    while repo_root != repo_root.parent:
        if (repo_root / ".git").exists():
            break
        repo_root = repo_root.parent
    else:
        print("❌ ERROR: Not in a git repository", file=sys.stderr)
        sys.exit(2)

    print_section("Claude Code Session Completion Gates")

    # Track overall status
    all_passed = True

    # ============================================================
    # Gate 1: Eligibility Check
    # ============================================================
    print_section("Gate 1: Eligibility Check")

    eligibility_result = run_gate_script("claude_session_checker.py", [], repo_root)

    if eligibility_result['exit_code'] == 2:
        print_result("❌", f"ERROR: {eligibility_result['error']}")
        sys.exit(2)

    eligible = eligibility_result['exit_code'] == 0
    mode = "Lightweight" if eligible else "Standard"

    print_result("ℹ️", f"Mode: {mode}")

    if not eligible:
        violations = eligibility_result['result'].get('violations', [])
        print("\nViolations:")
        for violation in violations:
            print(f"  • {violation}")

    stats = eligibility_result['result'].get('stats', {})
    file_count = stats.get('file_count', 0)
    print(f"\nStats:")
    print(f"  • Files modified: {file_count}")

    # ============================================================
    # Gate 2: Review Packet
    # ============================================================
    print_section("Gate 2: Review Packet")

    packet_args = ["--lightweight"] if eligible else []
    packet_result = run_gate_script("claude_review_packet_gate.py", packet_args, repo_root)

    if packet_result['exit_code'] == 2:
        print_result("❌", f"ERROR: {packet_result['error']}")
        sys.exit(2)

    if packet_result['exit_code'] == 0:
        packet_path = packet_result['result'].get('review_packet_path', 'unknown')
        print_result("✅", f"Review Packet found and valid: {packet_path}")
    else:
        all_passed = False
        print_result("❌", "Review Packet gate FAILED")
        errors = packet_result['result'].get('errors', [])
        for error in errors:
            print(f"  • {error}")

        # Provide guidance
        print("\n📋 Required action:")
        if eligible:
            print(f"  Create a Lightweight Review Packet using:")
            print(f"    Template: docs/02_protocols/templates/review_packet_lightweight.md")
        else:
            print(f"  Create a Standard Review Packet using:")
            print(f"    Template: docs/02_protocols/templates/review_packet_template.md")
        print(f"  Place in: artifacts/review_packets/Review_Packet_<Topic>_v1.0.md")

    # ============================================================
    # Gate 3: Doc Stewardship
    # ============================================================
    print_section("Gate 3: Doc Stewardship")

    doc_result = run_gate_script("claude_doc_stewardship_gate.py", [], repo_root)

    if doc_result['exit_code'] == 2:
        print_result("❌", f"ERROR: {doc_result['error']}")
        sys.exit(2)

    docs_modified = doc_result['result'].get('docs_modified', False)

    if not docs_modified:
        print_result("✅", "No docs/ modifications (N/A)")
    elif doc_result['exit_code'] == 0:
        print_result("✅", "Doc stewardship requirements met")
    else:
        all_passed = False
        print_result("❌", "Doc stewardship gate FAILED")
        errors = doc_result['result'].get('errors', [])
        for error in errors:
            print(f"  • {error}")

        # Offer auto-fix
        print("\n🔧 Auto-fix available")
        try:
            if prompt_yes_no("Apply auto-fix for doc stewardship?"):
                print("\nApplying auto-fix...")
                fix_result = run_gate_script("claude_doc_stewardship_gate.py", ["--auto-fix"], repo_root)

                if fix_result['exit_code'] == 0:
                    print_result("✅", "Doc stewardship auto-fix SUCCESSFUL")
                    files_modified = fix_result['result'].get('auto_fix_files', [])
                    print(f"\nFiles modified:")
                    for file in files_modified:
                        print(f"  • {file}")
                    all_passed = True  # Override failure since auto-fix succeeded
                else:
                    print_result("❌", "Auto-fix FAILED")
                    fix_errors = fix_result['result'].get('errors', [])
                    for error in fix_errors:
                        print(f"  • {error}")
            else:
                print("\n📋 Manual fix required:")
                print("  1. Update timestamp in docs/INDEX.md (Last Updated: YYYY-MM-DD)")
                print("  2. Regenerate Strategic Corpus:")
                print("     python docs/scripts/generate_strategic_context.py")
        except KeyboardInterrupt:
            print("\n\nUser cancelled auto-fix")
            all_passed = False

    # ============================================================
    # Summary
    # ============================================================
    print_section("Summary")

    if all_passed:
        print_result("✅", "All session completion gates PASSED")
        print(f"\n📦 Session Details:")
        print(f"  • Mode: {mode}")
        if packet_result['result'].get('review_packet_path'):
            print(f"  • Review Packet: {packet_result['result']['review_packet_path']}")
        print(f"  • Files modified: {file_count}")

        print("\n✨ Session ready for handoff")
        sys.exit(0)
    else:
        print_result("❌", "Session completion gates BLOCKED")
        print("\n⚠️  Please fix the issues above before completing your session")
        sys.exit(1)


if __name__ == "__main__":
    main()
