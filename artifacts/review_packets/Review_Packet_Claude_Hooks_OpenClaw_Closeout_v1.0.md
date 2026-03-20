# Scope Envelope
- Mission: close out Claude governance hooks + OpenClaw model-provider wiring merge.
- In scope: post-merge evidence capture for `.claude/settings.json`, `.claude/hooks/protected-path-guard.js`, `.claude/hooks/session-context-inject.py`.
- Out of scope: provider feature development, runtime behavior changes, governance-doc edits.

# Summary
- Verified merge to `main` already completed as squash commit `68bfe304a25fb3602f46edb8dfb813a5fd2ed51f`.
- Confirmed merged file set contains the three intended Claude hook/config files.
- Produced this closure-grade review packet with deterministic evidence and flattened code appendix.

# Issue Catalogue
- IC-001 (Resolved): build closure was previously blocked by dirty working tree; merged state is now clean on `main`.
- IC-002 (Resolved): governance path-guard and session context injection hooks are present in merged commit.
- IC-003 (Resolved): closeout evidence packet was missing and is now provided.

# Acceptance Criteria
| ID | Criterion | Status | Evidence Pointer | SHA-256 |
|---|---|---|---|---|
| AC-001 | Branch changes are merged to `main` via squash merge. | PASS | N/A(validated via local git log on 2026-02-16) | N/A(commit evidence in git object store) |
| AC-002 | `.claude/settings.json` contains merged hook configuration. | PASS | .claude/settings.json | 0f94a52867d07b604a2f921d7b153554a9faf04ceaf793efaf21b225e1ac78b8 |
| AC-003 | `.claude/hooks/protected-path-guard.js` is present with governance path enforcement logic. | PASS | .claude/hooks/protected-path-guard.js | c3d949b1d40f62d76f1f3278fc8e608b5f69a96daeb626a9c84a53b1733f1d8d |
| AC-004 | `.claude/hooks/session-context-inject.py` is present with session context injection logic. | PASS | .claude/hooks/session-context-inject.py | 7c3ef6d68cd686623d46f0ff2217eaec2438f439898ee5d6dacb05f49c687f50 |
| AC-005 | Closure review packet exists in canonical review packet location. | PASS | artifacts/review_packets/Review_Packet_Claude_Hooks_OpenClaw_Closeout_v1.0.md | N/A(self-describing artifact) |

# Closure Evidence Checklist
| Item | Requirement | Verification |
|---|---|---|
| Provenance | Source branch and merge commit are identified. | Verified: branch `build/claude-hooks-governance-context` merged as `68bfe304a25fb3602f46edb8dfb813a5fd2ed51f`. |
| Artifacts | All in-scope merged files are captured with hashes. | Verified: AC-002/AC-003/AC-004 include paths and SHA-256 values. |
| Repro | Evidence can be re-derived with deterministic local commands. | Verified: `git show --name-only 68bfe30` and `sha256sum` on listed files reproduce this packet data. |
| Governance | No protected governance/foundation docs were edited in this mission. | Verified: in-scope files are under `.claude/` and `artifacts/review_packets/` only. |
| Outcome | Build closeout evidence packet is complete and reviewable. | Verified: packet created and queued for validator gates. |

# Non-Goals
- No changes to `docs/00_foundations/` or `docs/01_governance/`.
- No re-execution of full closure merge flow (already completed in merge commit `68bfe30`).
- No model/provider endpoint edits in this closeout packet mission.

# Appendix
## Appendix A: Flattened Code

### File: `.claude/settings.json`
```json
{
  "permissions": {
    "allow": [
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git push:*)",
      "Bash(git stash:*)",
      "Bash(git checkout:*)",
      "Bash(git restore:*)",
      "Bash(git reset:*)",
      "Bash(git clone:*)",
      "Bash(git remote set-url:*)",
      "Bash(zip:*)",
      "Bash(sync)",
      "Bash(tee:*)",
      "Bash(python -m scripts.*:*)",
      "Bash(scripts/workflow/*:*)",
      "WebFetch(domain:docs.claude.com)",
      "WebFetch(domain:code.claude.com)",
      "WebFetch(domain:www.anthropic.com)",
      "WebFetch(domain:claudefa.st)"
    ],
    "deny": [
      "Bash(git push --force:*)",
      "Bash(git push -f:*)",
      "Bash(rm -rf:*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/close-build-gate.sh",
            "timeout": 300,
            "statusMessage": "Running close-build enforcement gates..."
          }
        ]
      },
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "node \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protected-path-guard.js",
            "timeout": 5000,
            "statusMessage": "Checking governance protection..."
          }
        ]
      },
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "node \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protected-path-guard.js",
            "timeout": 5000,
            "statusMessage": "Checking governance protection..."
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/session-context-inject.py",
            "timeout": 10000,
            "statusMessage": "Loading project context..."
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/repo-cleanliness-check.sh",
            "timeout": 10,
            "statusMessage": "Checking repo cleanliness..."
          }
        ]
      }
    ]
  }
}
```

### File: `.claude/hooks/protected-path-guard.js`
```javascript
#!/usr/bin/env node
/**
 * PreToolUse hook: block Write/Edit to governance-protected paths.
 * Reads config/governance/protected_artefacts.json at runtime.
 * Fail-open on any error (missing file, parse failure, etc.).
 */
"use strict";

const fs = require("fs");
const path = require("path");

const PROJECT_DIR = process.env.CLAUDE_PROJECT_DIR || process.cwd();

function main() {
  let input;
  try {
    input = JSON.parse(require("fs").readFileSync("/dev/stdin", "utf8"));
  } catch {
    process.exit(0); // fail-open: can't parse stdin
  }

  const filePath = (input.tool_input && input.tool_input.file_path) || "";
  if (!filePath) {
    process.exit(0); // no file_path means nothing to guard
  }

  // Normalize: resolve absolute, then make relative to project dir
  const absTarget = path.resolve(PROJECT_DIR, filePath);
  const relativePath = path.relative(PROJECT_DIR, absTarget).replace(/\\/g, "/");

  // Load protected paths
  let config;
  try {
    const raw = fs.readFileSync(
      path.join(PROJECT_DIR, "config", "governance", "protected_artefacts.json"),
      "utf8"
    );
    config = JSON.parse(raw);
  } catch {
    process.exit(0); // fail-open: config missing or unparseable
  }

  const protectedPaths = config.protected_paths || [];
  const lockedBy = config.locked_by || "governance policy";

  for (const pp of protectedPaths) {
    const normalized = pp.replace(/\\/g, "/");
    if (
      relativePath === normalized ||                          // exact match
      relativePath.startsWith(normalized + "/")               // directory child (boundary-safe)
    ) {
      process.stderr.write(
        `BLOCKED: "${relativePath}" is governance-protected.\n` +
        `Protected by: ${lockedBy}\n` +
        `To modify, you need explicit Council approval. Ask the user first.\n`
      );
      process.exit(2);
    }
  }

  process.exit(0); // not protected, allow
}

main();
```

### File: `.claude/hooks/session-context-inject.py`
```python
#!/usr/bin/env python3
"""SessionStart hook: inject project state context into Claude Code session.

Gathers git branch, status summary, and key fields from LIFEOS_STATE.md.
Outputs {"additionalContext": "..."} JSON to stdout.
Always exits 0 (never blocks session start).
"""

import json
import os
import re
import subprocess
import sys


PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
STATE_FILE = os.path.join(PROJECT_DIR, "docs", "11_admin", "LIFEOS_STATE.md")
MAX_CONTEXT_CHARS = 600


def run_git(args: list[str], timeout: int = 3) -> str:
    """Run a git command, return stdout or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", PROJECT_DIR] + args,
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def git_context() -> str:
    """Return compact git branch + status summary."""
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    status_raw = run_git(["status", "--porcelain"])

    if not status_raw:
        status = "clean"
    else:
        lines = status_raw.splitlines()
        status = f"{len(lines)} changed file(s)"

    return f"Branch: {branch} | Status: {status}"


def state_context() -> str:
    """Extract key fields from LIFEOS_STATE.md."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return ""

    fields = []
    for pattern in [
        r"\*\*Current Focus:\*\*\s*(.+)",
        r"\*\*Active WIP:\*\*\s*(.+)",
    ]:
        m = re.search(pattern, content)
        if m:
            fields.append(m.group(1).strip())

    # Extract the "Next immediate" one-liner
    next_match = re.search(r"\*\*Next immediate:\*\*\s*(.+)", content)

    if next_match:
        fields.append("Next: " + next_match.group(1).strip())

    return " | ".join(fields)


def main() -> int:
    parts = []

    git = git_context()
    if git:
        parts.append(git)

    state = state_context()
    if state:
        parts.append(state)

    if not parts:
        # Nothing to inject
        print(json.dumps({"additionalContext": ""}))
        return 0

    context = " || ".join(parts)

    # Cap to avoid token waste
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[: MAX_CONTEXT_CHARS - 3] + "..."

    output = {"additionalContext": context}
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
