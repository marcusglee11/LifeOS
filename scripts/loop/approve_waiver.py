#!/usr/bin/env python3
"""
Waiver Approval CLI (Phase B.3.2)

CEO-facing tool for approving or rejecting loop waiver requests.
Implements stable debt pointer protocol (no line numbers).
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, UTC, timedelta
from pathlib import Path


# Debt scoring table (Phase B.3.4)
DEBT_SCORES = {
    "test_failure": 30,          # Low impact - tests can be fixed later
    "review_rejection": 40,      # Medium - design iteration debt
    "timeout": 50,               # Medium - performance optimization needed
    "dependency_error": 60,      # Medium-high - dependency management issue
    "environment_error": 50,     # Medium - tooling/env configuration
    "unknown": 50,               # Default - unknown failures
}

# Repayment window (days)
DEFAULT_REPAYMENT_DAYS = 14


def compute_waiver_request_hash(waiver_request_path: Path) -> str:
    """Compute SHA256 hash of waiver request file for tamper detection."""
    with open(waiver_request_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def get_debt_score(failure_class: str) -> int:
    """Get debt score for failure class."""
    return DEBT_SCORES.get(failure_class.lower(), 50)


def register_debt(backlog_path: Path, debt_id: str, failure_class: str, run_id: str) -> bool:
    """
    Register debt in BACKLOG.md with stable debt ID (no line numbers).

    Returns:
        True if debt registered successfully, False otherwise
    """
    score = get_debt_score(failure_class)
    due_date = (datetime.now(UTC) + timedelta(days=DEFAULT_REPAYMENT_DAYS)).strftime("%Y-%m-%d")

    debt_entry = f"- [ ] [{debt_id}] [Score: {score}] [DUE: {due_date}] Loop waiver: {failure_class} (Run: {run_id})\n"

    # Append to BACKLOG.md
    try:
        # Ensure backlog exists
        if not backlog_path.exists():
            print(f"Warning: BACKLOG.md not found at {backlog_path}. Creating new file.")
            backlog_path.parent.mkdir(parents=True, exist_ok=True)
            with open(backlog_path, 'w', encoding='utf-8') as f:
                f.write("# BACKLOG\n\n## Technical Debt\n\n")

        # Append debt entry
        with open(backlog_path, 'a', encoding='utf-8') as f:
            f.write(debt_entry)

        print(f"✓ Debt registered: {debt_id} (Score: {score}, DUE: {due_date})")
        return True

    except Exception as e:
        print(f"✗ Failed to register debt: {e}", file=sys.stderr)
        return False


def approve_waiver(run_id: str, rationale: str, repo_root: Path):
    """
    Approve waiver request.

    Steps:
    1. Load waiver request
    2. Calculate debt score
    3. Register debt in BACKLOG.md with stable debt ID
    4. Create waiver decision file
    """
    waiver_request_path = repo_root / "artifacts/loop_state" / f"WAIVER_REQUEST_{run_id}.md"

    if not waiver_request_path.exists():
        print(f"✗ Waiver request not found: {waiver_request_path}", file=sys.stderr)
        sys.exit(1)

    # Compute hash for tamper detection
    waiver_hash = compute_waiver_request_hash(waiver_request_path)

    # Parse waiver request to extract failure class
    # Simple parsing: look for "**Failure Class**: <class>"
    failure_class = "unknown"
    with open(waiver_request_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("**Failure Class**:"):
                failure_class = line.split(":", 1)[1].strip()
                break

    # Stable debt ID (no line numbers!)
    debt_id = f"DEBT-{run_id}"

    # Register debt
    backlog_path = repo_root / "docs/11_admin/BACKLOG.md"
    debt_registered = register_debt(backlog_path, debt_id, failure_class, run_id)

    # Create waiver decision file
    decision = {
        "run_id": run_id,
        "waiver_request_hash": waiver_hash,
        "decision": "APPROVE",
        "decision_timestamp": datetime.now(UTC).isoformat() + "Z",
        "decision_authority": "CEO",
        "rationale": rationale,
        "debt_registered": debt_registered,
        "debt_id": debt_id,  # Stable pointer (not line number!)
        "debt_score": get_debt_score(failure_class),
        "debt_repayment_due": (datetime.now(UTC) + timedelta(days=DEFAULT_REPAYMENT_DAYS)).strftime("%Y-%m-%d")
    }

    decision_path = repo_root / "artifacts/loop_state" / f"WAIVER_DECISION_{run_id}.json"
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    with open(decision_path, 'w', encoding='utf-8') as f:
        json.dump(decision, f, indent=2)

    print(f"✓ Waiver APPROVED for run: {run_id}")
    print(f"  Decision file: {decision_path}")
    print(f"  Debt ID: {debt_id}")
    print(f"  Resume loop to continue with waived state.")


def reject_waiver(run_id: str, rationale: str, repo_root: Path):
    """
    Reject waiver request.

    Steps:
    1. Load waiver request
    2. Create waiver decision file (no debt registration)
    """
    waiver_request_path = repo_root / "artifacts/loop_state" / f"WAIVER_REQUEST_{run_id}.md"

    if not waiver_request_path.exists():
        print(f"✗ Waiver request not found: {waiver_request_path}", file=sys.stderr)
        sys.exit(1)

    # Compute hash for tamper detection
    waiver_hash = compute_waiver_request_hash(waiver_request_path)

    # Create waiver decision file
    decision = {
        "run_id": run_id,
        "waiver_request_hash": waiver_hash,
        "decision": "REJECT",
        "decision_timestamp": datetime.now(UTC).isoformat() + "Z",
        "decision_authority": "CEO",
        "rationale": rationale,
        "debt_registered": False,
        "debt_id": None
    }

    decision_path = repo_root / "artifacts/loop_state" / f"WAIVER_DECISION_{run_id}.json"
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    with open(decision_path, 'w', encoding='utf-8') as f:
        json.dump(decision, f, indent=2)

    print(f"✓ Waiver REJECTED for run: {run_id}")
    print(f"  Decision file: {decision_path}")
    print(f"  Loop will terminate with BLOCKED status.")


def main():
    parser = argparse.ArgumentParser(
        description="Approve or reject loop waiver requests (Phase B.3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Approve waiver (registers debt)
  python scripts/loop/approve_waiver.py --run-id acc_run_12345 --decision APPROVE

  # Reject waiver with rationale
  python scripts/loop/approve_waiver.py --run-id acc_run_12345 --decision REJECT --rationale "Requires manual fix"

  # Approve with custom rationale
  python scripts/loop/approve_waiver.py --run-id acc_run_12345 --decision APPROVE --rationale "Non-critical test failures, defer to next sprint"
        """
    )

    parser.add_argument(
        "--run-id",
        required=True,
        help="Run ID of the waiver request (from WAIVER_REQUEST_<run_id>.md)"
    )

    parser.add_argument(
        "--decision",
        required=True,
        choices=["APPROVE", "REJECT"],
        help="Approval decision (APPROVE or REJECT)"
    )

    parser.add_argument(
        "--rationale",
        default="",
        help="Optional rationale for decision"
    )

    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory (default: current directory)"
    )

    args = parser.parse_args()

    # Validate repo root
    if not args.repo_root.exists():
        print(f"✗ Repository root not found: {args.repo_root}", file=sys.stderr)
        sys.exit(1)

    # Execute decision
    if args.decision == "APPROVE":
        approve_waiver(args.run_id, args.rationale, args.repo_root)
    else:
        reject_waiver(args.run_id, args.rationale, args.repo_root)


if __name__ == "__main__":
    main()
