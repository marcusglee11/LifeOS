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
