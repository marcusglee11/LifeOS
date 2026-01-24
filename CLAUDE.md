# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Development Commands

### Running Tests

```bash
# Run all tests
pytest

# Run runtime tests (primary test suite)
pytest runtime/tests -q

# Run TDD compliance check (required before commit)
pytest tests_doc/test_tdd_compliance.py

# Run specific test suite
pytest runtime/tests/test_engine.py -v
python -m pytest -q runtime/tests/test_mission_registry

# Run with coverage
pytest --cov=runtime runtime/tests
```

**Test Configuration**: `pytest.ini`
- Main test directories: `runtime/tests`, `tests_doc`, `tests_recursive`
- 415+ tests in build handoff; all must pass
- No flaky tests allowed (immediate P0 bug)

### Installation & Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python docs/scripts/check_readiness.py
```

**Python Version**: 3.11+

### Doc Steward Operations

```bash
# Validate DAP compliance
python -m doc_steward.cli dap-validate .

# Check index integrity
python -m doc_steward.cli index-check docs docs/INDEX.md

# Validate cross-document links
python -m doc_steward.cli link-check docs

# Generate strategic corpus
python docs/scripts/generate_corpus.py
```

### Pre-Commit Checklist

```bash
# 1. Run tests
pytest runtime/tests -q

# 2. Check TDD compliance
pytest tests_doc/test_tdd_compliance.py

# 3. Validate documentation
python -m doc_steward.cli dap-validate .
python docs/scripts/check_readiness.py
```

### OpenCode CI Validation

```bash
# Run OpenCode CI validation (manual)
python scripts/opencode_ci_runner.py --model google/gemini-2.0-flash-001
```

### TODO Management

```bash
# View all TODOs
python scripts/todo_inventory.py

# View as JSON
python scripts/todo_inventory.py --json

# Filter by priority
python scripts/todo_inventory.py --priority P0
```

**Protocol**: `docs/02_protocols/TODO_Standard_v1.0.md`

**For Antigravity agents (stewards and builders):**
- Never use generic `TODO` - always use `LIFEOS_TODO[P0|P1|P2]` with area and exit command
- P0 incomplete code paths MUST raise `NotImplementedError` (fail-loud)
- Run `python scripts/todo_inventory.py` before committing to verify backlog state
- Remove TODOs only after exit command passes

## Development Workflow

### Superpowers Workflow

LifeOS adopts the **Superpowers** workflow discipline for structured development with strict TDD enforcement. This workflow is installed as a Claude Code skill at `.claude/skills/superpowers/`.

**Three-Phase Cycle**:

1. **Brainstorm** (`/superpowers:brainstorm` or use brainstorming skill)
   - Explore design space and identify alternatives
   - Ask clarifying questions about requirements
   - Understand existing patterns in codebase
   - Consider tradeoffs and edge cases
   - **When to use**: Before starting any non-trivial work

2. **Plan** (`/superpowers:write-plan` or use executing-plans skill)
   - Break work into small batches (2-5 min each)
   - Define clear success criteria for each batch
   - Identify test cases upfront
   - Specify verification commands
   - **When to use**: After brainstorming, before implementation

3. **Execute** (`/superpowers:execute-plan` or use test-driven-development skill)
   - Implement batch-by-batch with strict TDD
   - Write failing test first, then implementation
   - Run tests after each batch
   - Verify success criteria met
   - **When to use**: After planning, for actual code changes

**Key Principles**:
- **YAGNI** (You Aren't Gonna Need It): Don't add features not explicitly required
- **DRY** (Don't Repeat Yourself): Extract common patterns, but avoid premature abstraction
- **Strict TDD**: Test first, implementation second, refactor third
- **Small batches**: Keep changes focused and testable

**When scope grows**:
- STOP execution
- Document remaining work with clear boundaries
- Return to brainstorm or planning phase
- Break into smaller batches

**Available Superpowers Skills**:
- `brainstorming` - Explore design space
- `executing-plans` - Implement with TDD
- `test-driven-development` - Write tests first
- `systematic-debugging` - Debug methodically
- `dispatching-parallel-agents` - Coordinate multiple tasks
- `subagent-driven-development` - Delegate to specialized agents
- `requesting-code-review` - Prepare code for review
- `receiving-code-review` - Process review feedback
- `finishing-a-development-branch` - Complete and merge work
- `using-git-worktrees` - Manage parallel work

## High-Level Architecture

### Governance-First System

**LifeOS is fundamentally a governance system, not just a runtime system.** The Constitution and protocols override implementation details. Before modifying code, understand the governance layer.

**Authority Chain**:
```
LifeOS Constitution v2.0 (Supreme)
        │
        └── Governance Protocol v1.0
                │
                ├── COO Operating Contract v1.0
                ├── Document Steward Protocol v1.1
                ├── Deterministic Artefact Protocol v2.0
                └── Council Protocol v1.2
```

**Four Binding Constitutional Invariants**:
1. **CEO Supremacy** — Human CEO is sole source of strategic intent; no system override
2. **Audit Completeness** — All actions logged; no silent operations
3. **Reversibility** — All state versioned and restorable
4. **Amendment Discipline** — Constitutional changes logged with rationale

### Core Components

#### `runtime/` — COO Runtime
The Chief Operating Officer runtime implementing deterministic execution:
- `engine.py` — Finite state machine (FSM) orchestrating system lifecycle
- `mission/` — Tier-3 mission registry (definition-only, no execution logic)
- `reactive/` — Reactive Task Layer for task planning (definition-only)
- `orchestration/` — Tier-2 execution orchestration (mission dispatch, test harness)
- `governance/` — Protection layers, surface validators, override protocols
- `api/` — Public API surfaces (governance_api.py, runtime_api.py)
- `safety/` — Health checks, halt logic, failure playbooks

#### `project_builder/` — Multi-Agent Orchestration
- `agents/planner.py` — COO Agent for mission planning
- `orchestrator/` — FSM controller, mission management, budget enforcement
- `database/` — Mission timeline, snapshots, schema migrations
- `sandbox/` — Docker sandbox for secure agent execution
- `context/` — Context injection, tokenization, truncation

#### `recursive_kernel/` — Self-Improvement Loop
- `builder.py` — Builds tasks deterministically
- `planner.py` — Plans recursive improvement steps
- `runner.py` — Executes the recursive workflow
- `verifier.py` — Validates deterministic outputs

#### `doc_steward/` — Document Governance
- `cli.py` — Document steward CLI interface
- `dap_validator.py` — Validates DAP (Deterministic Artefact Protocol) compliance
- `index_checker.py` — Verifies document index integrity
- `link_checker.py` — Validates cross-document references

#### `docs/` — Authoritative Source of Truth
All governance, specifications, protocols, and architectural definitions. This directory is the supreme authority for system behavior.

### Tier Progression Model

LifeOS operates across multiple **Tiers** of automation capability:

- **Tier-1**: Basic orchestration (approved)
- **Tier-2**: Multi-mission concurrency with budgets (approved)
- **Tier-2.5**: Enhanced capacity (activated)
- **Tier-3**: Reactive tasks & mission synthesis (in development)

Each tier has specific activation conditions and Council approval requirements.

### Mission-Oriented Execution

- CEO provides high-level intent
- COO decomposes into missions
- Missions are definition-only at Tier-3, executed at Tier-2
- Each mission has budget, boundaries, approval gates
- All execution is deterministic and auditable

### Deterministic Design Principles

**All outputs must be reproducible**:
- Canonical JSON serialization (sorted keys, fixed separators)
- SHA256 hashes for all artifacts
- Identical inputs → identical outputs
- No randomness or timestamp-dependent behavior in core paths

## Governance & Protocol System

### Protected Paths

**The following paths are governance-protected and cannot be modified without Council approval**:

```json
{
  "protected_paths": [
    "docs/00_foundations",
    "docs/01_governance",
    "config/governance/protected_artefacts.json"
  ]
}
```

Enforcement: `runtime/governance/protection.py:GovernanceProtector`

**Violations raise `GovernanceProtectionError` and halt execution.**

### Council Protocol v1.2

**Council reviews are binding when invoked**. Key requirements:

- **Deterministic Seats**: Chair (mandatory), Co-Chair (M1/M2), Reviewer seats (Architect, Alignment, etc.)
- **Three Rigor Modes**: M0_FAST, M1_STANDARD, M2_FULL (selected deterministically)
- **Independence Rule**: M2_FULL with `safety_critical=true` MUST use independent AI models (different vendors)
- **Evidence-by-Reference**: Every material claim must cite the Artefact Under Review (AUR)
- **Contradiction Ledger**: Mandatory in M1/M2 to resolve seat conflicts
- **Closure Bundle**: "Done" or "Go" verdicts invalid without G-CBS compliant closure bundle

**Path**: `docs/02_protocols/Council_Protocol_v1.2.md`

### Document Steward Protocol v1.1

**Source of Truth**: Local repository (`docs/`)

**Required Operations**:
- File creation with naming convention `DocumentName_vX.Y.md`
- `INDEX.md` updates mandatory after any doc change
- Corpus regeneration via `python docs/scripts/generate_corpus.py`
- Stray file checks (prevent artifacts at root)

**Forbidden Actions**:
- Never leave files at `docs/` root (except INDEX.md and corpus)
- Governance files (`*Constitution*.md`, `*Protocol*.md`) are protected
- No modifications to `docs/00_foundations/` or `docs/01_governance/` without Council approval

**Path**: `docs/02_protocols/Document_Steward_Protocol_v1.1.md`

### Deterministic Artefact Protocol (DAP) v2.0

**Core Principles**: Determinism, Explicitness, Idempotence, Immutability, Auditability

**Key Rules**:
- Artefacts created only at StepGate Gate 3
- Archive files (`docs/99_archive/`) are immutable (cannot be rewritten)
- Naming pattern: `<BASE>_v<MAJOR>.<MINOR>[.<PATCH>].md`
- No placeholders or guessing filenames
- All artifacts must include complete content

**Path**: `docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md`

### Anti-Failure Operational Requirements

**Human Burden Minimization**:
- max_steps_per_workflow: 5
- max_human_actions_per_packet: 2
- Agents MUST execute all tasks that can reasonably be automated

**Failure Conditions** (must prevent):
- Human performing routine execution steps
- Manual indexing/renaming/structuring by human
- New architecture layers without friction evaluation
- Agents not enforcing invariants

**Path**: `docs/00_foundations/Anti_Failure_Operational_Packet_v0.1.md`

### OpenCode-First Stewardship

**All in-envelope documentation changes MUST go through OpenCode**:
- Must invoke CT-2 gate runner to validate changes
- Out-of-envelope changes (denylisted paths, non-.md, structural ops) → BLOCK with Governance Request
- Mixed changes (docs + code) → docs via OpenCode stewardship, code via standard gates

**Active Council Ruling**: `docs/01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md`

## Critical Navigation Points

### Starting Point for Any New Session

1. **Read**: `docs/INDEX.md` — Primary navigation for all documentation
2. **Read**: `docs/00_foundations/LifeOS_Constitution_v2.0.md` — Supreme authority
3. **Read**: `docs/11_admin/LIFEOS_STATE.md` — Current focus, WIP, blockers
4. **Check**: `docs/11_admin/BACKLOG.md` — Prioritized work items

### Key Documentation Files

| File | Purpose |
|------|---------|
| `docs/INDEX.md` | Primary navigation index (updated: 2026-01-07) |
| `docs/LifeOS_Strategic_Corpus.md` | Primary context for the LifeOS project |
| `docs/00_foundations/LifeOS_Constitution_v2.0.md` | Supreme governing document |
| `docs/02_protocols/Governance_Protocol_v1.0.md` | Envelopes, escalation rules |
| `docs/11_admin/LIFEOS_STATE.md` | Single source of truth for current state |
| `docs/11_admin/BACKLOG.md` | Actionable backlog (Now/Next/Later) |
| `docs/11_admin/DECISIONS.md` | Append-only decision log |

### Project Administration

**Thin Control Plane** located in `docs/11_admin/`:
- **LIFEOS_STATE.md** — Current focus, WIP, blockers, next actions
- **BACKLOG.md** — Target ≤40 items (Now/Next/Later)
- **DECISIONS.md** — Low-volume decision log
- **INBOX.md** — Raw capture scratchpad for triage

## Developer Constraints

### Test Coverage Requirements

- **100% coverage** for core track (deterministic envelope)
- **80%+ coverage** for support track
- All tests must pass with randomized order
- No `@pytest.mark.skip` without governance approval
- Flaky tests are immediate P0 bugs

### Determinism Requirements

**All artifacts must be deterministic**:
- Use canonical JSON everywhere (sorted keys, specific separators)
- Generate SHA256 hashes for all outputs
- No timestamp-dependent behavior in outputs
- Reproducible builds required

### Audit & Evidence Requirements

**All significant operations must be auditable**:
- SQLite message bus records all communication
- Timeline snapshots for state restoration
- Amendment log for constitutional changes
- Closure bundles for "Done"/"Go" verdicts

### Governance Escalation

**When to escalate to CEO**:
- Actions exceeding defined envelope
- Modifications to protected paths
- Constitutional changes
- Tier activation/deactivation
- Safety-critical decisions

### Code Modification Rules

**Before modifying any code**:
1. Verify it's not in a protected path
2. Check if Council approval required
3. Ensure changes don't violate constitutional invariants
4. Maintain deterministic behavior
5. Update tests and documentation

**If docs/ modified**: Update `docs/INDEX.md` timestamp and regenerate corpus

### WSL + Git Governance Rules

**These rules are non-negotiable for agent operations on WSL with Windows-mounted working copies.**

#### 2.1 Operating Rule (WSL + Windows-mount)

If the working copy remains on `/mnt/c/...`, enforce a single rule: **only one Git "reality" touches that working tree during agent runs** (avoid Windows Git/IDEs doing Git operations mid-run). This is the lowest-friction way to avoid lock/index/line-ending edge cases.

#### 2.2 Hard Evidence Gate (Non-negotiable for "DONE")

**Require every agent completion report to include verbatim**:

```bash
git rev-parse HEAD
git log -1 --oneline
git status --porcelain=v1  # MUST be empty
```

**No exceptions.** If absent, the work is BLOCKED, not "done."

#### 2.3 Hook Policy Compliance Rule

**No `--no-verify` without an emergency artefact entry.**

If `--no-verify` is used, the agent must:
1. Run the repo's emergency command: `python3 scripts/git_workflow.py --emergency direct-commit --reason "..."`
2. Commit the resulting artefact/log update
3. Surface it in the report

**Example**: See `artifacts/emergency_overrides.log` and commit `cefc673` for reference implementation.

#### 2.4 Line-Ending Prevention (Required Baseline Hygiene)

The `.gitattributes` LF enforcement is the **required permanent fix** for any cross-platform workflow:

```
# Enforce LF for git hooks to ensure WSL compatibility
scripts/hooks/* text eol=lf

# Enforce LF for shell scripts to ensure cross-platform compatibility
*.sh text eol=lf
```

Treat this as required baseline hygiene. If hooks or shell scripts break in WSL due to CRLF, this is a P0 bug.

## Repository Structure

```
lifeos/
├── docs/              # Authoritative governance & specifications (source of truth)
├── runtime/           # COO Runtime implementation
├── project_builder/   # Multi-agent orchestration
├── recursive_kernel/  # Self-improvement loop
├── doc_steward/       # Document governance
├── opencode_governance/ # OpenCode stewardship
├── config/            # Configuration files (invariants, backlog, governance)
├── artifacts/         # Agent-generated artifacts (plans, packets, evidence)
├── scripts/           # Utility scripts
├── tests/             # Project-level tests
└── logs/              # Runtime logs
```

## Key References

- **Constitution**: `docs/00_foundations/LifeOS_Constitution_v2.0.md`
- **Governance Protocol**: `docs/02_protocols/Governance_Protocol_v1.0.md`
- **Council Protocol**: `docs/02_protocols/Council_Protocol_v1.2.md`
- **Document Steward Protocol**: `docs/02_protocols/Document_Steward_Protocol_v1.1.md`
- **DAP**: `docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md`
- **Test Protocol**: `docs/02_protocols/Test_Protocol_v2.0.md`
- **Current State**: `docs/11_admin/LIFEOS_STATE.md`
- **Architecture**: `docs/00_foundations/Architecture_Skeleton_v1.0.md`
- **Tier Definitions**: `docs/00_foundations/Tier_Definition_Spec_v1.1.md`
