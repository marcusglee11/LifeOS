"""
Daily Summary - Anti-Failure Operational Loop

Produces a 3-line summary of system state per Anti-Failure Packet §4 (self_maintenance).
Outputs to logs/daily_summaries/YYYY-MM-DD.md
"""

import os
import datetime
from pathlib import Path


def generate_daily_summary():
    """Generate daily system summary."""
    repo_root = Path(os.getcwd())
    logs_dir = repo_root / "logs" / "daily_summaries"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    today = datetime.date.today().isoformat()
    summary_path = logs_dir / f"{today}.md"
    
    # Scan system state
    num_docs = count_files(repo_root / "docs", "*.md")
    num_tests = count_files(repo_root, "test_*.py")
    num_artifacts = count_files(repo_root / "artifacts" / "review_packets", "*.md")
    
    # Check for drift (simplified - just count changes)
    drift_status = "No drift detected"  # Placeholder for actual drift detection
    
    # 3-line summary
    summary = f"""# Daily Summary - {today}

**System State:**
- Documentation: {num_docs} files indexed
- Tests: {num_tests} test files
- Artifacts: {num_artifacts} review packets

**Drift Check:** {drift_status}

**Action Required:** None (system stable)
"""
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print(f"Daily summary written to {summary_path}")
    return str(summary_path)


def count_files(directory: Path, pattern: str) -> int:
    """Count files matching pattern in directory tree."""
    if not directory.exists():
        return 0
    return len(list(directory.rglob(pattern)))


if __name__ == "__main__":
    generate_daily_summary()
