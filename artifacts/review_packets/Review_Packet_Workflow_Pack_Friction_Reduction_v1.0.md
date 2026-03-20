# Review Packet: Workflow Pack Friction Reduction v1.0

## Scope
Implemented low-friction workflow pack additions:
- new `review-fix` and `handoff-pack` commands/skills
- compact context contract utilities (`.context/active_work.yaml`)
- targeted test routing utility (`scripts/workflow/test_router.sh` + python backend)
- strict report section ordering in review/handoff command surfaces

## Branch
- `build/master-plan-v1-1-canonicalization`

## Commit
- `cd0fdba` workflow: add review-fix/handoff-pack skills and compact workflow utilities

## Verification
- `pytest -q runtime/tests/test_workflow_pack.py` -> PASS (4 passed)
- `python3 scripts/workflow/test_router.py runtime/orchestration/openclaw_bridge.py runtime/agents/api.py` -> PASS
- `scripts/workflow/test_router.sh runtime/tools/workflow_pack.py` -> PASS
- `python3 scripts/workflow/active_work.py --repo-root . refresh --focus "review-fix" --test "pytest -q runtime/tests/test_workflow_pack.py"` -> PASS

## Appendix A: Flattened Code (Full)

### FILE: `.claude/skills/lifeos-workflow/.claude-plugin/plugin.json`

```json
{
  "name": "lifeos-workflow",
  "description": "LifeOS-specific workflow skills for multi-agent development, build reviews, and inter-agent handoffs",
  "version": "1.2.0",
  "author": "LifeOS Team",
  "keywords": ["git", "merge", "workflow", "concurrent", "sprints", "review", "review-fix", "handoff", "handoff-pack", "multi-agent"]
}

```

### FILE: `.claude/skills/lifeos-workflow/README.md`

```markdown
# LifeOS Workflow Skills

Claude Code skills specific to LifeOS concurrent development workflows.

## Skills

### merge-concurrent-sprints

**Purpose:** Safely merge multiple divergent feature branches developed in parallel.

**When to use:**
- 5+ unmerged feature branches
- Branches >1 week old with divergent histories
- Multiple stashes accumulating (3+)
- Unclear which branch contains canonical work
- Team asking "which branch should I base on?"

**What it provides:**
- Pre-merge inventory workflow (branch audit script)
- Decision flowchart for selecting merge strategy
- Three merge strategies: Sequential, Integration Branch, Cherry-Pick
- Execution checklists (before/during/after)
- Post-merge cleanup procedures
- Prevention guidance for future work

**Key files:**
- `skills/merge-concurrent-sprints/SKILL.md` - Main workflow guide
- `skills/merge-concurrent-sprints/branch-audit.sh` - Branch inventory script

### review-build

**Purpose:** Tiered review + fix flow for incoming builds.

### handoff

**Purpose:** Structured outbound/inbound handoff between agents.

### review-fix

**Purpose:** Diff-first review remediation (read reviewer commit diff first, then fix/report).

### handoff-pack

**Purpose:** Compact deterministic handoff packs (`to_codex` / `from_codex`) with fixed section order.

## Commands

- `/review-build`
- `/handoff`
- `/review-fix`
- `/handoff-pack`

## Workflow Utilities

- `scripts/workflow/test_router.sh` - Map changed files to targeted test commands.
- `scripts/workflow/active_work.py` - Maintain compact context artifact at `.context/active_work.yaml` (ignored by git).

## Installation

This plugin is auto-loaded when working in the LifeOS repository since it's located in `.claude/skills/`.

To verify the skill is loaded:
```bash
/skills list
```

You should see `merge-concurrent-sprints` in the output.

## Usage

The skill auto-activates based on context when you ask questions like:
- "I have 5 feature branches that need merging, help me figure out how to merge them safely"
- "How do I merge multiple concurrent development branches?"
- "I have lots of stashes and divergent branches, what should I do?"

You can also manually invoke it:
```bash
/merge-concurrent-sprints
```

Or reference it directly in your request:
> "Use the merge-concurrent-sprints skill to help me merge phase-5 branches"

## Testing

The skill was designed based on the Phase 4 concurrent merge scenario where:
- 27 commits on `pr/canon-spine-autonomy-baseline`
- 50 commits on `phase/4a-clean`
- 12 commits on `build/repo-cleanup-p0`
- 6 stashes with unclear content
- Multiple other divergent branches

The skill would have guided to using an **integration branch strategy** for that scenario, with comprehensive testing at each step.

## Version History

- **v1.0.0** (2026-02-03): Initial release
  - Pre-merge inventory workflow
  - Three merge strategies (Sequential, Integration, Cherry-Pick)
  - Branch audit script with LifeOS-specific checks
  - Execution checklists and cleanup procedures
  - Prevention guidance

## Future Enhancements

**v1.1 candidates:**
- Interactive branch audit script (prompts for decisions)
- Integration branch template generator
- Automated conflict resolution strategies
- ACTIVE_BRANCHES.md template and management commands

**v1.2 candidates:**
- CI/CD integration (pre-merge checks)
- Branch lifecycle automation (auto-archive after merge)

```

### FILE: `.claude/skills/lifeos-workflow/commands/review-build.md`

```markdown
---
description: Review a build from another agent using the tiered review-fix-report protocol. Fixes obvious issues in-place, proposes options for judgment calls, escalates architectural concerns.
---

Invoke the lifeos-workflow:review-build skill and follow it exactly as presented to you.

The user may provide a branch name, commit range, build summary, or PR number. If none is provided, ask for the branch or commits to review.

Output must end in compact sections in this order:
1. Branch
2. Commits
3. Test Results
4. What Was Done
5. What Remains

```

### FILE: `.claude/skills/lifeos-workflow/commands/handoff.md`

```markdown
---
description: Generate a structured handoff summary for another agent, or process an inbound handoff. Use when finishing a sprint, review, or build cycle that another agent will continue.
---

Invoke the lifeos-workflow:handoff skill and follow it exactly as presented to you.

If the user says "handoff" without direction, assume outbound (you are handing off your completed work). If the user provides another agent's output, process it as inbound.

Output must use compact sections in this order:
1. Branch
2. Commits
3. Test Results
4. What Was Done
5. What Remains

```

### FILE: `.claude/skills/lifeos-workflow/commands/review-fix.md`

```markdown
---
description: Run diff-first review-fix workflow. Reads reviewer commit diff first, applies obvious/patterned fixes, and emits compact report sections.
---

Invoke the lifeos-workflow:review-fix skill and follow it exactly as presented.

If the user does not provide a reviewer commit, ask for either:
- reviewer commit SHA, or
- commit range (`<base>..<head>`), or
- branch to review against `main`.


```

### FILE: `.claude/skills/lifeos-workflow/commands/handoff-pack.md`

```markdown
---
description: Produce compact, deterministic inter-agent handoff packs (to_codex or from_codex) using branch/commit/test facts and active context artifact.
---

Invoke the lifeos-workflow:handoff-pack skill and follow it exactly as presented.

Default mode:
- outbound handoff if the user says "handoff pack" with no input blob.
- inbound processing if user pastes another agent handoff block.


```

### FILE: `.claude/skills/lifeos-workflow/skills/review-build/SKILL.md`

```markdown
---
name: review-build
description: Use when asked to review a build, branch, or set of commits from another agent (Codex, Claude Code, or any builder). Applies the tiered review-fix-report protocol from CLAUDE.md to minimize round-trips and token waste.
---

# Review Build

Review a build from another agent using the tiered review-fix-report protocol. Fix obvious issues in-place rather than just reporting them.

## Inputs

The user will provide one or more of:
- A branch name (e.g., `build/master-plan-v1-1-canonicalization`)
- A commit range (e.g., `e7d7ab8..d848d1f`)
- A build summary (pasted from the building agent)
- A PR number

If only a branch name is given, diff against the branch's merge-base with `main`.

## Step 1: Understand the Scope

```bash
# Get the commit range
git log --oneline <base>..<head>

# Get the full diff
git diff <base>..<head> --stat
```

Read the changed files. Understand what was built, not just what changed.

## Step 2: Run Pre-Existing Baseline

```bash
# Check if failures exist BEFORE this build
git stash && git checkout <base-commit> --quiet
pytest runtime/tests -q 2>&1 | tail -5
git checkout <branch> --quiet && git stash pop 2>/dev/null
```

This establishes which test failures are pre-existing vs introduced.

## Step 3: Review Each Change

For each file changed, assess:

1. **Correctness** - Does the code do what it claims?
2. **Completeness** - Are there missing cases, uncovered paths?
3. **Consistency** - Does it follow existing codebase patterns?
4. **Safety** - Error handling, validation, security concerns?
5. **Tests** - Are new behaviors tested? Are edge cases covered?

## Step 4: Classify Findings by Tier

| Tier | Criteria | Action |
|------|----------|--------|
| **Critical** | Broken logic, security holes, dead code, contract violations | Fix immediately |
| **Moderate** | Missing error handling, coverage gaps, pattern inconsistencies | Fix if straightforward, otherwise propose |
| **Low** | Style, naming, documentation, minor improvements | Report only |

### Decision Rules

**Fix it yourself if ALL of these are true:**
- The fix follows an existing pattern in the codebase
- The fix is under ~20 lines of code
- The fix doesn't change any public API or contract
- You can write a test for it (or the fix IS a test)

**Propose options if ANY of these are true:**
- Multiple valid approaches exist
- The fix changes a public interface or data contract
- The fix touches protected paths (`docs/00_foundations/`, `docs/01_governance/`)
- The fix requires a design decision the builder should make

**Escalate if:**
- The issue requires architectural changes across multiple modules
- The issue affects governance or constitution
- You're unsure whether the fix is correct

## Step 5: Fix and Verify

For each fix applied:
1. Make the change
2. Run targeted tests for the affected module
3. Run `pytest runtime/tests -q` to check for regressions
4. Commit with a clear message: `Fix review findings: <summary>`

## Step 6: Report

Structure your report as:

```
Branch: <branch-name>
Commits: <start-sha>..<end-sha>
Test Results:
- Targeted: <result>
- Full/expanded: <result>
What Was Done:
- <concise bullet list>
What Remains:
- <open items or "None">
```

If needed, include a short `Verdict` line above this block, but keep the five
core sections in this exact order for inter-agent consistency.

## Quick Reference

```bash
# Typical review flow
git log --oneline main..<branch>
git diff main..<branch> --stat
git diff main..<branch> -- <file>       # Deep-read specific files
pytest runtime/tests -q                  # Verify current state
# Fix issues, commit, re-run tests
pytest runtime/tests -q && git status    # Final verification
```

```

### FILE: `.claude/skills/lifeos-workflow/skills/handoff/SKILL.md`

```markdown
---
name: handoff
description: Use when finishing work that another agent will continue, or when receiving work from another agent. Structures inter-agent communication to minimize copy-paste and token waste. Use at the end of a sprint, review, or build cycle.
---

# Agent Handoff

Structure handoffs between agents (Codex, Claude Code, Antigravity) so the receiving agent gets maximum context with minimum tokens.

## Outbound Handoff (You finished work, another agent continues)

### Step 1: Verify Clean State

```bash
pytest runtime/tests -q
git status --porcelain=v1
```

If tests fail or working tree is dirty, fix before handing off.

### Step 2: Generate Handoff Summary

Produce a structured handoff block the user can paste to the next agent:

```
Branch: <branch-name>
Commits: <first-sha>..<last-sha>
Test Results:
- <targeted result>
- <expanded/full result>
What Was Done:
- <1-line summary per commit or logical unit>
What Remains:
- <specific next steps, if any>
- <open questions or decisions needed>
Key Files (optional):
- <file>: <what changed and why>
Gotchas (optional):
- <anything non-obvious: test fixtures, env vars, patterns to follow>
```

The first five sections are mandatory and must stay in this exact order:
1. Branch
2. Commits
3. Test Results
4. What Was Done
5. What Remains

### Rules for Handoff Summaries

- **Reference commits, not code** — the next agent can read the diffs
- **Be specific about what remains** — "finish the feature" is useless; "add token extraction to steward phase matching the pattern at line 412" is useful
- **Flag decisions made** — if you chose approach A over B, say why, so the next agent doesn't re-litigate
- **Flag pre-existing issues** — if you noticed broken tests or tech debt outside your scope, mention it so the next agent doesn't waste time investigating

## Inbound Handoff (You're picking up another agent's work)

### Step 1: Read the Handoff

Parse the structured block for: branch, commits, what was done, what remains.

### Step 2: Orient

```bash
git checkout <branch>
git log --oneline -10
git diff main..<branch> --stat
pytest runtime/tests -q
```

### Step 3: Verify Claims

- Do the commits match the summary?
- Do tests actually pass as claimed?
- Are the "key files" actually the ones that changed?

If claims don't match reality, note discrepancies and proceed with what's actually there.

### Step 4: Continue Work

Pick up from "What remains" in the handoff. Follow existing patterns in the code that was just written.

## Handoff to Codex (Specific)

Codex works from a task prompt, not a conversation. Structure the handoff as a self-contained task:

```
Task: <what to do>
Branch: <branch-name>
Context: <1-2 sentences of why this matters>

Scope:
- <specific file or module to modify>
- <specific file or module to modify>

Acceptance criteria:
- <testable condition>
- <testable condition>

Patterns to follow:
- See <file:line> for the existing pattern
- Match <specific convention> used in <sibling module>

Do NOT:
- <specific anti-pattern to avoid>
- Modify files outside scope
```

## Handoff from Codex (Specific)

Codex returns a build summary. To process it:

1. Read the summary for branch, commits, test results
2. Checkout the branch and verify
3. If the user says "review this build" — invoke the `review-build` skill

## Compact Context Update

After completing or ingesting a handoff, refresh compact context:

```bash
python3 scripts/workflow/active_work.py refresh
python3 scripts/workflow/active_work.py show
```

## Anti-Patterns

- **Wall of prose** — handoffs should be structured, not narrative
- **Copy-pasting full diffs** — reference commits instead
- **Vague next steps** — "finish up" means nothing; be specific
- **Missing branch/commit info** — the receiving agent needs coordinates, not just descriptions
- **Re-explaining the codebase** — the receiving agent has CLAUDE.md and can explore

```

### FILE: `.claude/skills/lifeos-workflow/skills/review-fix/SKILL.md`

```markdown
---
name: review-fix
description: Use when review findings are provided and you must fix obvious/patterned issues quickly with minimal tokens. Reads reviewer commit diff first, then applies the tiered review-fix-report protocol.
---

# Review Fix (Diff-First)

This skill enforces low-friction review handling:
- read reviewer commit diff first (shared truth),
- fix obvious/patterned issues in-place,
- keep judgment/architectural items explicit,
- emit compact deterministic report.

## Inputs

At least one of:
- reviewer commit SHA,
- commit range (`<base>..<head>`),
- branch to review.

## Step 1: Read Shared Truth First

```bash
git show --stat --name-only <reviewer-commit>
git show <reviewer-commit>
```

If a range is provided:

```bash
git log --oneline <base>..<head>
git diff <base>..<head> --stat
```

Do not rely on pasted prose if commit diff exists.

## Step 2: Run Targeted Tests via Router

```bash
scripts/workflow/test_router.sh <changed-file>...
```

Run returned commands first, then run broader suite only if needed.

## Step 3: Fix by Tier

- **Obvious/Patterned:** fix and commit directly.
- **Judgment:** present 2-3 options with recommendation.
- **Architectural:** escalate, do not silently decide.

## Step 4: Update Active Context Artifact

```bash
python3 scripts/workflow/active_work.py refresh \
  --focus "<task-id-or-scope>" \
  --test "<targeted-test-command>"
```

This keeps sessions small and handoffs deterministic.

## Step 5: Report Format (strict)

Always use these headings and order:

1. `Branch`
2. `Commits`
3. `Test Results`
4. `What Was Done`
5. `What Remains`

If no remaining items exist, write `What Remains: None`.


```

### FILE: `.claude/skills/lifeos-workflow/skills/handoff-pack/SKILL.md`

```markdown
---
name: handoff-pack
description: Use when handing work to another agent or processing an inbound handoff. Produces compact, deterministic pack sections and updates active context.
---

# Handoff Pack

Generate minimal-token handoffs with deterministic structure.

## Modes

- `to_codex`: outbound task handoff to Codex.
- `from_codex`: ingest Codex build summary and continue.

Default:
- If user supplied a pasted summary, use `from_codex`.
- Otherwise use `to_codex`.

## Step 1: Collect Facts

```bash
git rev-parse --abbrev-ref HEAD
git log --oneline -n 10
git status --short
```

Use targeted test routing:

```bash
scripts/workflow/test_router.sh
```

## Step 2: Refresh Active Context

```bash
python3 scripts/workflow/active_work.py refresh
python3 scripts/workflow/active_work.py show
```

## Step 3: Emit Strict Pack

Use exact section order:

1. `Branch`
2. `Commits`
3. `Test Results`
4. `What Was Done`
5. `What Remains`

Optional section (only when needed):
- `Key Files`
- `Gotchas`

## `to_codex` extras

Add:
- `Task`
- `Scope`
- `Acceptance Criteria`
- `Patterns To Follow`
- `Do NOT`

## `from_codex` extras

Add:
- `Claims Verified`
- `Deltas from Claims`


```

### FILE: `runtime/tools/workflow_pack.py`

```python
"""Workflow pack helpers for low-friction multi-agent handoffs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable, Sequence


ACTIVE_WORK_RELATIVE_PATH = Path(".context/active_work.yaml")


def _unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def build_active_work_payload(
    *,
    branch: str,
    latest_commits: Sequence[str],
    focus: Sequence[str],
    tests_targeted: Sequence[str],
    findings_open: Sequence[dict[str, str]],
) -> dict:
    """Build normalized active-work payload."""
    normalized_findings = []
    for finding in findings_open:
        finding_id = str(finding.get("id", "")).strip()
        severity = str(finding.get("severity", "")).strip().lower()
        status = str(finding.get("status", "")).strip().lower()
        if not finding_id or not severity or not status:
            continue
        normalized_findings.append(
            {"id": finding_id, "severity": severity, "status": status}
        )

    return {
        "version": "1.0",
        "branch": branch.strip() or "unknown",
        "latest_commits": _unique_ordered(latest_commits),
        "focus": _unique_ordered(focus),
        "tests_targeted": _unique_ordered(tests_targeted),
        "findings_open": normalized_findings,
    }


def write_active_work(repo_root: Path, payload: dict) -> Path:
    """Write .context/active_work.yaml deterministically."""
    output_path = Path(repo_root) / ACTIVE_WORK_RELATIVE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def read_active_work(repo_root: Path) -> dict:
    """Read .context/active_work.yaml, returning a normalized fallback when absent."""
    input_path = Path(repo_root) / ACTIVE_WORK_RELATIVE_PATH
    if not input_path.exists():
        return build_active_work_payload(
            branch="unknown",
            latest_commits=[],
            focus=[],
            tests_targeted=[],
            findings_open=[],
        )
    try:
        loaded = json.loads(input_path.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    return build_active_work_payload(
        branch=str(loaded.get("branch", "unknown")),
        latest_commits=loaded.get("latest_commits") or [],
        focus=loaded.get("focus") or [],
        tests_targeted=loaded.get("tests_targeted") or [],
        findings_open=loaded.get("findings_open") or [],
    )


def _matches(file_path: str, prefixes: Sequence[str]) -> bool:
    return any(file_path == prefix or file_path.startswith(prefix) for prefix in prefixes)


def route_targeted_tests(changed_files: Sequence[str]) -> list[str]:
    """Map changed files to targeted test commands."""
    files = _unique_ordered(changed_files)

    routed: list[str] = []

    def add(command: str) -> None:
        if command not in routed:
            routed.append(command)

    for file_path in files:
        if _matches(
            file_path,
            (
                "runtime/orchestration/openclaw_bridge.py",
                "runtime/tests/orchestration/test_openclaw_bridge.py",
            ),
        ):
            add("pytest -q runtime/tests/orchestration/test_openclaw_bridge.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/orchestration/missions/autonomous_build_cycle.py",
                "runtime/tests/orchestration/missions/test_autonomous_loop.py",
            ),
        ):
            add("pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/agents/api.py",
                "runtime/agents/opencode_client.py",
                "runtime/tests/test_agent_api_usage_plumbing.py",
                "tests/test_agent_api.py",
            ),
        ):
            add(
                "pytest -q runtime/tests/test_agent_api_usage_plumbing.py tests/test_agent_api.py"
            )
            continue

        if _matches(
            file_path,
            (
                "runtime/tools/workflow_pack.py",
                "runtime/tests/test_workflow_pack.py",
                "scripts/workflow/",
            ),
        ):
            add("pytest -q runtime/tests/test_workflow_pack.py")
            continue

    if not routed:
        routed.append("pytest -q runtime/tests")
    return routed


def discover_changed_files(repo_root: Path) -> list[str]:
    """Discover changed files with staged-first precedence."""
    repo = Path(repo_root)
    probes = [
        ["git", "-C", str(repo), "diff", "--name-only", "--cached"],
        ["git", "-C", str(repo), "diff", "--name-only"],
        ["git", "-C", str(repo), "diff", "--name-only", "HEAD~1..HEAD"],
    ]
    for cmd in probes:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            continue
        files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if files:
            return _unique_ordered(files)
    return []

```

### FILE: `runtime/tests/test_workflow_pack.py`

```python
from __future__ import annotations

from pathlib import Path

from runtime.tools.workflow_pack import (
    build_active_work_payload,
    read_active_work,
    route_targeted_tests,
    write_active_work,
)


def test_active_work_roundtrip(tmp_path: Path) -> None:
    payload = build_active_work_payload(
        branch="feature/workflow-pack",
        latest_commits=["abc123 add router", "def456 add skills"],
        focus=["W4-T01", "W5-T04"],
        tests_targeted=["pytest -q runtime/tests/test_workflow_pack.py"],
        findings_open=[{"id": "M1", "severity": "moderate", "status": "open"}],
    )

    output = write_active_work(tmp_path, payload)
    assert output == tmp_path / ".context" / "active_work.yaml"

    loaded = read_active_work(tmp_path)
    assert loaded["version"] == "1.0"
    assert loaded["branch"] == "feature/workflow-pack"
    assert loaded["focus"] == ["W4-T01", "W5-T04"]
    assert loaded["findings_open"] == [{"id": "M1", "severity": "moderate", "status": "open"}]


def test_route_targeted_tests_routes_known_files() -> None:
    changed = [
        "runtime/orchestration/openclaw_bridge.py",
        "runtime/orchestration/missions/autonomous_build_cycle.py",
    ]
    commands = route_targeted_tests(changed)
    assert commands == [
        "pytest -q runtime/tests/orchestration/test_openclaw_bridge.py",
        "pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py",
    ]


def test_route_targeted_tests_deduplicates() -> None:
    changed = [
        "runtime/agents/api.py",
        "tests/test_agent_api.py",
        "runtime/agents/opencode_client.py",
    ]
    commands = route_targeted_tests(changed)
    assert commands == [
        "pytest -q runtime/tests/test_agent_api_usage_plumbing.py tests/test_agent_api.py",
    ]


def test_route_targeted_tests_fallback() -> None:
    commands = route_targeted_tests(["docs/11_admin/BACKLOG.md"])
    assert commands == ["pytest -q runtime/tests"]


```

### FILE: `scripts/workflow/active_work.py`

```python
#!/usr/bin/env python3
"""Manage .context/active_work.yaml compact context artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.workflow_pack import (
    build_active_work_payload,
    read_active_work,
    write_active_work,
)


def _git_stdout(repo_root: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _parse_finding(raw: str) -> dict[str, str]:
    parts = [part.strip() for part in raw.split(":", 2)]
    if len(parts) != 3 or any(not part for part in parts):
        raise argparse.ArgumentTypeError(
            "finding must be formatted as id:severity:status"
        )
    return {"id": parts[0], "severity": parts[1], "status": parts[2]}


def cmd_refresh(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    branch = _git_stdout(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    commit_lines = _git_stdout(
        repo_root,
        ["log", "--oneline", f"-n{args.commit_limit}"],
    ).splitlines()

    payload = build_active_work_payload(
        branch=branch,
        latest_commits=commit_lines,
        focus=args.focus or [],
        tests_targeted=args.test or [],
        findings_open=args.finding or [],
    )
    output_path = write_active_work(repo_root, payload)
    print(output_path)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    payload = read_active_work(repo_root)
    print(json.dumps(payload, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_refresh = sub.add_parser("refresh", help="Refresh active context from git + flags.")
    p_refresh.add_argument("--commit-limit", type=int, default=5)
    p_refresh.add_argument("--focus", action="append", default=[])
    p_refresh.add_argument("--test", action="append", default=[])
    p_refresh.add_argument("--finding", action="append", type=_parse_finding, default=[])
    p_refresh.set_defaults(func=cmd_refresh)

    p_show = sub.add_parser("show", help="Print active_work.yaml normalized content.")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

```

### FILE: `scripts/workflow/test_router.py`

```python
#!/usr/bin/env python3
"""Route changed files to targeted pytest commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.workflow_pack import discover_changed_files, route_targeted_tests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Changed file paths. If omitted, auto-discover from git diff.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    files = args.files if args.files else discover_changed_files(repo_root)
    commands = route_targeted_tests(files)
    for command in commands:
        print(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

### FILE: `scripts/workflow/test_router.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
python3 "$REPO_ROOT/scripts/workflow/test_router.py" --repo-root "$REPO_ROOT" "$@"


```
