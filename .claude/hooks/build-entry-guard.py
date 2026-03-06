#!/usr/bin/env python3
"""PreToolUse hook: warn when writing qualifying files outside managed build context.
Phase 1: warn only (exit 0 always). Phase 2 will promote to hard block.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

QUALIFYING_PREFIXES = (
    "runtime/", "scripts/", "config/", "schemas/", "tests/", ".github/workflows/",
)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir and file_path.startswith(project_dir):
        file_path = file_path[len(project_dir):].lstrip("/")

    if not any(file_path.startswith(p) for p in QUALIFYING_PREFIXES):
        sys.exit(0)

    try:
        repo_root = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not repo_root:
            sys.exit(0)
        gate_script = str(Path(repo_root) / "scripts" / "workflow" / "build_entry_gate.py")
        if not Path(gate_script).exists():
            sys.exit(0)

        result = subprocess.run(
            ["python3", gate_script],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if result.returncode == 1:
            msg = (result.stdout.strip() or result.stderr.strip() or "Build entry gate check failed.")
            warning = {
                "decision": "allow",
                "systemMessage": (
                    f"⚠️  BUILD ENTRY WARNING: Writing to qualifying path '{file_path}' "
                    f"outside managed build context.\n{msg}\n"
                    "Use: python3 scripts/workflow/start_build.py <topic>"
                ),
            }
            print(json.dumps(warning))
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
