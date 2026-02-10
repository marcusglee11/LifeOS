# Roadmap: Fully Autonomous Build Loops

**Version**: 1.0
**Date**: 2026-02-02
**Status**: PLANNING
**Owner**: Antigravity + Council

---

## Vision

Transform LifeOS from human-supervised build cycles to **fully autonomous operation** where human intervention is exception-based (escalations only).

The autonomous build loop will:
- Read tasks from `BACKLOG.md` automatically
- Design, build, review, and commit changes without human intervention
- Escalate ONLY on governance violations, policy conflicts, or budget exhaustion
- Self-monitor and self-correct within approved boundaries
- Maintain cryptographic audit trails for all decisions

---

## Current State

| Component | Status | Evidence |
|-----------|--------|----------|
| **Phase 3** | CLOSED | Council Ruling Phase3 Closure v1.0 (RATIFIED) |
| **Core Runtime Tests** | 1091 passing | `pytest runtime/tests -q` |
| **Trusted Builder Mode v1.1** | RATIFIED | Council Ruling 2026-01-26 |
| **Policy Engine** | Authoritative Gating | Closure Record v1.0 |
| **CSO Role Constitution** | FINALIZED | v1.0 (2026-01-23) |
| **Mission Types** | All implemented | Design, Build, Review, Steward, AutonomousBuildCycle |
| **Loop Infrastructure** | Operational | Ledger, Policy, Budgets, Taxonomy |
| **Envelope Enforcer** | Operational | Path containment, symlink rejection |

### Existing Infrastructure

**Loop Controller** (`runtime/orchestration/missions/autonomous_build_cycle.py`):
- Design -> Review -> Build -> Review -> Steward pipeline
- Ledger-based resumability
- Budget enforcement (tokens, diff lines, attempts)
- Terminal packet emission for CEO visibility

**Policy Engine** (`runtime/orchestration/loop/policy.py`, `configurable_policy.py`):
- Config-driven loop rules (`config/policy/loop_rules.yaml`)
- Failure classification and routing
- Deadlock/oscillation detection
- Plan bypass eligibility (Trusted Builder Mode)
- Waiver artifact support

**Governance** (`runtime/governance/envelope_enforcer.py`):
- Realpath containment
- Symlink rejection
- Allowlist/denylist pattern matching
- TOCTOU mitigation

**Escalation System** (`scripts/escalation_monitor.py`):
- Artifact-based escalation tracking
- TTL expiration handling
- Watch mode for continuous monitoring

---

## Target State

A fully autonomous system that:

1. **Reads** tasks from `BACKLOG.md` automatically
2. **Designs** solutions via agent prompts (designer.md)
3. **Builds** code changes within envelope constraints
4. **Reviews** changes via multi-reviewer architecture
5. **Commits** approved changes via StewardMission
6. **Escalates** ONLY on:
   - Governance violations (protected path access)
   - Policy conflicts (config mismatch mid-run)
   - Budget exhaustion (tokens, attempts, diff lines)
   - Waiver requirements (test flakes, timeouts)
7. **Self-monitors** via ledger integrity checks and bypass tracking
8. **Self-corrects** within approved boundaries (retry on review rejection)

---

## 5-Phase Roadmap (Corrected: 6 Phases with 4A0 as Critical Path)

### Phase 4A0: Loop Spine - A1 Chain Controller (P0) **CRITICAL PATH**

**Goal**: Build the canonical chain sequencer with checkpoint semantics.

**Why Phase 4A0 Exists**: **Verified reality correction** - the A1 loop controller is MISSING. The current `autonomous_build_cycle.py` is a mission implementation, not a resumable chain controller. Before CEO queue (4A) or backlog selection (4B) can be meaningful, we need a deterministic chain controller with:

- Checkpoint seam (pause/persist/resume contract)
- State machine with proper terminal packet emission
- Policy-validated resumption
- Fail-closed on dirty repo

#### Key Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| **A1 Controller Module** | `runtime/orchestration/loop/spine.py` | States: INIT, RUNNING, CHECKPOINT, RESUMED, TERMINAL |
| **Checkpoint Seam** | Pause contract with state persistence | Checkpoint file emitted, process exits clean (code 0) |
| **Resume Contract** | Policy-validated continuation | Validates policy hash before continuing |
| **Terminal Packet** | Outcome emission | PASS/BLOCKED with deterministic field ordering |
| **Artefact Contract** | Stable outputs | Ledger records, step summaries, terminal packet |

#### Success Criteria

- [ ] Single command runs one chain: `coo spine run --task "..."`
- [ ] Can pause at checkpoint: checkpoint file emitted, process exits clean
- [ ] Can resume deterministically: `coo spine resume --checkpoint CP_xxx`
- [ ] Emits stable artefacts: terminal packet, ledger records, step summaries
- [ ] Fail-closed on dirty repo: no execution, no artefacts
- [ ] All TDD scenarios pass

#### Orchestration Clarification

| Component | Role | File |
|-----------|------|------|
| **Loop Spine** | Canonical chain sequencer | `runtime/orchestration/loop/spine.py` |
| **Tier-2 Orchestrator** | Workflow executor | `runtime/orchestration/engine.py` |
| **Run Controller** | Lifecycle safety | `runtime/orchestration/run_controller.py` |

Loop Spine is the sequencer; Orchestrator is the executor; run_controller is safety. They are layered, not competing.

#### Dependencies

- None (builds on existing ledger infrastructure)

#### Estimated Effort

- Sprint 0-1 (1-2 weeks)

---

### Gating: Supervised Chain v0

**Phases 4A, 4B, 4C, 4D, and 4E are NOT to be started until "Supervised Chain v0" is achieved.**

Supervised Chain v0 milestone requires:
1. Phase 4A0 complete (Loop Spine operational)
2. Phase 4A complete (CEO Queue functional)
3. Phase 4B complete (Backlog-driven task selection)
4. E2E test: backlog task → design → build → checkpoint → CEO approve → steward → commit

Only after this milestone should further expansion (4C/4D) or enhancement (4E) phases be considered.

---

### Phase 4A: CEO Approval Queue (P0)

> **REQUIRES: Phase 4A0 (Loop Spine) checkpoint seam**
>
> Phase 4A implements the queue backend and resolution writer. The checkpoint seam itself is implemented in Phase 4A0.

**Goal**: Establish exception-based human-in-the-loop via persistent approval queue.

**Rationale**: The current system emits escalation artifacts but lacks a formal queue mechanism for CEO approval/rejection. Without this, the loop cannot pause, wait for human input, and resume.

#### Key Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| **Persistent Queue Backend** | SQLite or JSONL-based queue at `artifacts/ceo_queue/` | Queue survives process restart |
| **Queue Data Model** | Escalation packets with ID, timestamp, reason, context, TTL, status | Schema documented and validated |
| **CLI: `coo queue list`** | List pending escalations with status | Shows ID, reason, age, TTL |
| **CLI: `coo queue approve <id>`** | Approve escalation with optional comment | Updates status, logs decision |
| **CLI: `coo queue reject <id>`** | Reject escalation with mandatory reason | Updates status, terminates run |
| **Queue Polling** | Loop polls queue on ESCALATION_REQUESTED | Blocks until resolved or TTL expires |
| **Timeout Handling** | Stale escalations auto-reject after TTL | Default TTL: 24 hours |
| **Audit Trail** | All queue operations logged to ledger | CEO decisions cryptographically bound |

#### Implementation Notes

```
artifacts/
  ceo_queue/
    pending/
      ESC_20260202_abc123.json   # Pending escalation
    resolved/
      ESC_20260201_def456.json   # Approved/Rejected
    queue.db                      # Optional SQLite index
```

**Escalation Packet Schema**:
```yaml
id: ESC_20260202_abc123
created_at: "2026-02-02T10:30:00Z"
ttl_seconds: 86400
status: pending  # pending | approved | rejected | expired
reason: DIFF_BUDGET_EXCEEDED
requested_authority: CEO
context:
  run_id: "run_abc123"
  attempt_id: 3
  diff_lines: 412
  budget_max: 300
  affected_files:
    - runtime/api/governance_api.py
evidence_path: artifacts/rejected_diff_attempt_3.txt
resolution:
  resolved_at: null
  resolved_by: null
  decision: null
  comment: null
```

#### Success Criteria

- [ ] Loop can pause on ESCALATION_REQUESTED and emit queue packet
- [ ] `coo queue list` displays pending escalations
- [ ] `coo queue approve <id>` unblocks loop with WAIVER_APPLIED
- [ ] `coo queue reject <id>` terminates loop with BLOCKED
- [ ] Escalations expire after TTL with auto-reject
- [ ] All queue operations recorded in ledger with CEO identity

#### Dependencies

- None (builds on existing escalation infrastructure)

#### Estimated Effort

- Sprint 1-2 (2-3 weeks)

---

### Phase 4B: Backlog-Driven Autonomous Execution (P0)

**Goal**: Loop reads and processes `BACKLOG.md` without manual task input.

**Rationale**: Currently, `AutonomousBuildCycleMission` requires explicit `task_spec` input. For full autonomy, the loop must parse the backlog, select the next task, and execute it.

#### Key Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| **Backlog Parser** | Parse `BACKLOG.md` into structured task list | Extracts P0/P1/P2, DoD, Owner, Context |
| **Task Selection Heuristics** | Priority-based selection with dependency awareness | P0 before P1, unblocked before blocked |
| **Agent Role Prompts** | Standardized prompts for designer, reviewers | `docs/09_prompts/v1.0/roles/designer_v1.0.md` |
| **Task Completion Marking** | Toggle checkbox in BACKLOG.md after steward | `- [x]` on success, no change on failure |
| **Evidence Packet per Task** | Structured output linking task to commit | Task ID, commit hash, diff summary |
| **Multi-Task Orchestration** | Loop continues to next task after success | Configurable batch size (default: 1) |

#### Backlog Parser Specification

**Input Format** (existing BACKLOG.md structure):
```markdown
### P0 (Critical)

- [ ] **Task Title** -- DoD: Definition of Done -- Owner: owner -- Context: Additional context
- [x] **Completed Task** -- DoD: ... -- Owner: ... -- Context: ...

### P1 (High)

- [ ] **Another Task** -- DoD: ... -- Owner: ... -- Context: ...
```

**Parsed Structure**:
```python
@dataclass
class BacklogTask:
    id: str              # Generated hash
    title: str           # "Task Title"
    priority: str        # "P0", "P1", "P2"
    dod: str             # "Definition of Done"
    owner: str           # "antigravity"
    context: str         # "Additional context"
    completed: bool      # Checkbox state
    dependencies: List[str]  # Task IDs this depends on
    raw_line: str        # Original markdown line
    line_number: int     # For surgical editing
```

#### Agent Role Prompts

Create standardized role prompts:

| Role | File | Purpose |
|------|------|---------|
| **Designer** | `designer_v1.0.md` | Generate build packets from task specs |
| **Reviewer (Architect)** | `reviewer_architect_v1.0.md` | Structural coherence, invariants |
| **Reviewer (Security)** | `reviewer_security_v1.0.md` | Envelope compliance, protected paths |
| **Reviewer (L1 Unified)** | `reviewer_l1_unified_v1.0.md` | Technical correctness (exists) |

#### Task Selection Algorithm

```python
def select_next_task(tasks: List[BacklogTask]) -> Optional[BacklogTask]:
    """
    Select highest-priority unblocked uncompleted task.

    Priority order:
    1. P0 > P1 > P2
    2. Within priority: order in file (first wins)
    3. Skip completed tasks
    4. Skip tasks with unresolved dependencies
    """
    uncompleted = [t for t in tasks if not t.completed]
    unblocked = [t for t in uncompleted if all_deps_complete(t, tasks)]

    for priority in ["P0", "P1", "P2"]:
        candidates = [t for t in unblocked if t.priority == priority]
        if candidates:
            return candidates[0]  # First in file order

    return None  # No eligible tasks
```

#### Success Criteria

- [ ] Backlog parser correctly extracts all P0/P1/P2 tasks
- [ ] Loop selects P0 tasks before P1
- [ ] Loop marks task complete after successful steward
- [ ] Evidence packet generated with task-to-commit linkage
- [ ] Loop continues to next task without human intervention
- [ ] Dependency-blocked tasks are skipped until unblocked

#### Dependencies

- Phase 4A (CEO Queue) for escalation handling during autonomous run

#### Estimated Effort

- Sprint 2-3 (2-3 weeks)

---

### Phase 4C: OpenCode Envelope Expansion - Test Execution (P1)

**Goal**: Enable autonomous test execution (`pytest`) within the loop.

**Rationale**: Currently, the loop can build code but cannot verify it via tests. Test execution requires Council ruling for envelope expansion (Phase 3a per Trusted Builder v1.1).

#### Key Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| **Council Ruling: Phase 3a** | Authorize pytest tool within envelope | Ruling ID, scope, constraints documented |
| **Pytest Tool Policy Gate** | `tool_rules.yaml` entry for pytest | `decision: ALLOW` with path_scope |
| **Test Failure Classification** | Map pytest exit codes to FailureClass | Exit 0 = PASS, Exit 1 = TEST_FAILURE, etc. |
| **Retry Logic** | Inject failure context into next build attempt | Previous test output in feedback_context |
| **Test Scope Enforcement** | Limit tests to approved paths | Default: `runtime/tests/**` |
| **Failure Evidence Capture** | Capture pytest output on failure | Structured JSON with failed tests |
| **Flake Detection** | Identify intermittent failures for WAIVER | Same test passes then fails = FLAKE |

#### Council Ruling Requirements

**Phase 3a Envelope Expansion**:
```yaml
ruling_id: CR-Phase3a-Test-Envelope-v1.0
scope: pytest tool execution
constraints:
  - path_scope: runtime/tests/**
  - max_duration: 300s  # 5 minute timeout
  - no_side_effects: true  # Cannot modify files
  - output_capture: required
authorities:
  - CEO approval for scope expansion
  - CSO review for security implications
```

#### Tool Policy Configuration

Addition to `config/policy/tool_rules.yaml`:
```yaml
- rule_id: tool.pytest.run
  decision: ALLOW
  priority: 100
  match:
    tool: pytest
    action: run
  constraints:
    path_scope: runtime/tests/**
    max_duration_seconds: 300
    capture_output: true
```

#### Failure Classification Mapping

| Exit Code | FailureClass | Action |
|-----------|--------------|--------|
| 0 | (success) | PASS |
| 1 | TEST_FAILURE | RETRY (up to limit) |
| 2 | SYNTAX_ERROR | TERMINATE (fail-closed) |
| 3 | VALIDATION_ERROR | TERMINATE |
| 4 | TIMEOUT | ESCALATE |
| 5 | UNKNOWN | TERMINATE |

#### Success Criteria

- [ ] Council ruling Phase 3a RATIFIED
- [ ] Loop can execute `pytest runtime/tests -q` autonomously
- [ ] Test failures trigger retry with failure context
- [ ] Test scope limited to `runtime/tests/**` (cannot run arbitrary tests)
- [ ] Test timeout enforced (300s default)
- [ ] Flaky tests detected and routed to WAIVER flow

#### Dependencies

- Council ruling for Phase 3a envelope expansion
- Phase 4A (CEO Queue) for timeout/flake escalations

#### Estimated Effort

- Sprint 3-4 (2-3 weeks, plus Council review cycle)

---

### Phase 4D: Full Code Autonomy (P1)

**Goal**: Enable autonomous code creation and modification within governance bounds.

**Rationale**: Currently, the loop operates in a constrained envelope. Full autonomy requires Council rulings for Phase 3b (code paths) and Phase 3c (config paths).

#### Key Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| **Council Ruling: Phase 3b** | Authorize code creation in `coo/`, `runtime/`, `tests/` | Ruling ID, protected path exclusions |
| **Council Ruling: Phase 3c** | Authorize config modification in `config/` | Ruling ID, governance exclusions |
| **Code Generation Policy Gate** | Enforce envelope on file writes | EnvelopeEnforcer integration |
| **Diff Budget Enforcement** | Hard limit on lines changed per attempt | Default: 300 lines (existing) |
| **Self-Mod Protection** | Prevent modification of governance paths | Hardcoded + registry-backed |
| **New File Validation** | Ensure new files follow naming conventions | Pattern matching on path |
| **Atomic Commit Guarantee** | All-or-nothing commit on success | Rollback on any failure |

#### Council Ruling Requirements

**Phase 3b: Code Path Envelope**:
```yaml
ruling_id: CR-Phase3b-Code-Envelope-v1.0
scope: file creation/modification
allowed_paths:
  - coo/**
  - runtime/**
  - tests/**
  - scripts/**
denied_paths:
  - runtime/governance/**
  - runtime/orchestration/loop/ledger.py  # Critical infrastructure
  - docs/00_foundations/**
  - docs/01_governance/**
constraints:
  - diff_budget: 300 lines
  - no_binary_files: true
  - no_symlinks: true
```

**Phase 3c: Config Path Envelope**:
```yaml
ruling_id: CR-Phase3c-Config-Envelope-v1.0
scope: configuration modification
allowed_paths:
  - config/opencode/**
  - config/templates/**
denied_paths:
  - config/governance/**
  - config/policy/**  # Policy is governance-controlled
constraints:
  - schema_validation: required
  - backup_before_modify: true
```

#### Protected Path Registry (Hardcoded)

From `runtime/orchestration/loop/configurable_policy.py`:
```python
GOVERNANCE_CONTROLLED_PATHS = [
    "docs/00_foundations/",
    "docs/01_governance/",
    "runtime/governance/",
    "GEMINI.md",
]

GOVERNANCE_PATTERNS = [
    "*Constitution*.md",
    "*Protocol*.md",
]
```

**Extension for Phase 4D**:
```python
SELF_MOD_PROTECTED_PATHS = [
    "runtime/orchestration/loop/ledger.py",
    "runtime/orchestration/loop/policy.py",
    "runtime/orchestration/loop/configurable_policy.py",
    "runtime/governance/envelope_enforcer.py",
    "config/governance/",
    "config/policy/",
]
```

#### Success Criteria

- [ ] Council rulings Phase 3b and 3c RATIFIED
- [ ] Loop can create new files in `runtime/`, `tests/`
- [ ] Loop can modify existing code within diff budget
- [ ] Protected paths (governance, self-mod) remain untouchable
- [ ] EnvelopeEnforcer blocks all violations (fail-closed)
- [ ] Atomic commit: partial failures roll back completely

#### Dependencies

- Council rulings for Phase 3b and 3c
- Phase 4A (CEO Queue) for governance violation escalations
- Phase 4C (Test Execution) for verifying code changes

#### Estimated Effort

- Sprint 4-6 (4-6 weeks, including Council review cycles)

---

### Phase 4E: Self-Improvement Loop (P2)

**Goal**: Enable the loop to improve itself within governance bounds, with CEO approval for all self-modifications.

**Rationale**: True autonomy includes the ability to optimize and improve the autonomous system itself. This requires the highest level of governance oversight.

#### Key Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| **Ledger Hash Chain** | Cryptographic linking of all records | SHA256 chain, tamper-evident |
| **Monitoring Dashboard** | Real-time visibility into loop health | Bypass utilization, escalation rate |
| **Semantic Guardrails** | Detect "meaningful" vs trivial changes | Heuristics beyond protected paths |
| **Performance Baseline** | Track metrics over time | Commit rate, test pass rate, token usage |
| **Improvement Proposals** | Structured format for self-improvement | CEO review required |
| **Recursive Improvement** | Loop can propose changes to itself | Always requires CEO approval |

#### Ledger Hash Chain Specification

**Current Ledger** (`runtime/orchestration/loop/ledger.py`):
- Append-only JSONL
- Sequence enforcement
- Integrity checks

**Enhancement for Hash Chain**:
```python
@dataclass
class AttemptRecord:
    # ... existing fields ...

    # New: Cryptographic linking
    prev_record_hash: Optional[str]  # SHA256 of previous record
    record_hash: str                  # SHA256 of this record (excluding this field)

    def compute_hash(self) -> str:
        """Compute deterministic hash of record."""
        data = asdict(self)
        del data["record_hash"]  # Exclude self-reference
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
```

**Integrity Verification**:
```python
def verify_chain_integrity(ledger: AttemptLedger) -> bool:
    """Verify cryptographic chain integrity."""
    prev_hash = None
    for record in ledger.history:
        # Verify this record links to previous
        if record.prev_record_hash != prev_hash:
            return False
        # Verify this record's hash is correct
        if record.compute_hash() != record.record_hash:
            return False
        prev_hash = record.record_hash
    return True
```

#### Monitoring Dashboard Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| **Bypass Utilization** | % of attempts using Plan Bypass | > 50% |
| **Escalation Rate** | Escalations / Total Attempts | > 10% |
| **Commit Success Rate** | Successful Commits / Total Attempts | < 90% |
| **Mean Time to Commit** | Avg time from task selection to commit | > 2 hours |
| **Token Efficiency** | Tokens per successful commit | > 50,000 |
| **Deadlock Rate** | Deadlock terminations / Total runs | > 5% |

#### Semantic Guardrails

Beyond protected path checks, detect:

1. **Behavioral Changes**: Modifications that alter control flow significantly
2. **Policy Weakening**: Changes that reduce validation strictness
3. **Envelope Expansion**: Changes that expand allowed paths
4. **Budget Relaxation**: Changes that increase limits

**Detection Heuristics**:
```python
def is_semantically_significant(diff: Dict) -> bool:
    """Detect changes that require extra scrutiny."""
    patterns = [
        r"envelope|protected|allowed|denied",  # Envelope changes
        r"budget|limit|max_",                   # Budget changes
        r"escalate|terminate|block",           # Control flow
        r"policy|ruling|governance",           # Governance
    ]
    for pattern in patterns:
        if re.search(pattern, diff["content"], re.IGNORECASE):
            return True
    return False
```

#### Improvement Proposal Format

```yaml
proposal_id: IMP_20260301_abc123
created_at: "2026-03-01T10:00:00Z"
proposer: autonomous_loop
type: self_improvement
category: performance  # performance | reliability | observability
target_files:
  - runtime/orchestration/loop/policy.py
description: |
  Optimize deadlock detection by caching diff hashes.
  Expected improvement: 15% reduction in policy evaluation time.
evidence:
  current_metric: 120ms avg
  projected_metric: 102ms avg
  test_results: artifacts/improvement_tests/IMP_abc123.json
risk_assessment:
  severity: LOW
  governance_impact: NONE
  self_mod_paths: []
requires_approval: CEO
```

#### Success Criteria

- [ ] Ledger hash chain implemented and verified
- [ ] Monitoring dashboard operational with alerting
- [ ] Semantic guardrails detect all governance-related changes
- [ ] Performance baselines established and tracked
- [ ] Improvement proposals generate correctly formatted requests
- [ ] All self-improvement requires CEO approval (never bypassed)

#### Dependencies

- Phase 4A-4D complete (full autonomous capability)
- CSO Role Constitution W1 waiver management
- Council approval for self-improvement framework

#### Estimated Effort

- Sprint 6+ (ongoing, never complete)

---

## Risk Mitigation

| Risk | Severity | Mitigation | Owner |
|------|----------|------------|-------|
| **Runaway Execution** | HIGH | Kill switch (`STOP_AUTONOMY` file), token budgets, attempt limits | CEO |
| **Governance Violation** | CRITICAL | Fail-closed envelope enforcement, protected path hardcoding | CSO |
| **State Corruption** | HIGH | Ledger integrity checks, checkpoint recovery, hash chain | Runtime |
| **Infinite Loops** | MEDIUM | Oscillation detection, no-progress detection, attempt budgets | Policy |
| **Self-Modification Attacks** | CRITICAL | Hardcoded protected paths, Council key for overrides | Council |
| **Budget Exhaustion** | MEDIUM | Token accounting (fail-closed), diff budgets, escalation on overage | Budget |
| **Stale Escalations** | LOW | TTL expiration, auto-reject after timeout | Queue |
| **Test Flakiness** | MEDIUM | Flake detection, WAIVER flow, retry limits | Policy |

### Kill Switch Implementation

**Location**: `runtime/orchestration/run_controller.py`

**Mechanism**:
```python
STOP_AUTONOMY_FILE = Path("STOP_AUTONOMY")

def check_kill_switch() -> bool:
    """Check if kill switch is engaged. Called before every operation."""
    if STOP_AUTONOMY_FILE.exists():
        raise AutonomyHalted("Kill switch engaged: STOP_AUTONOMY file present")
    return False
```

**CEO Action**:
```bash
# Engage kill switch
touch STOP_AUTONOMY

# Disengage kill switch
rm STOP_AUTONOMY
```

---

## Timeline (Relative)

| Phase | Sprints | Duration | Blocking Dependencies |
|-------|---------|----------|----------------------|
| **4A: CEO Queue** | 1-2 | 2-3 weeks | None |
| **4B: Backlog Integration** | 2-3 | 2-3 weeks | 4A complete |
| **4C: Test Execution** | 3-4 | 2-3 weeks | Council ruling Phase 3a |
| **4D: Code Autonomy** | 4-6 | 4-6 weeks | Council rulings Phase 3b, 3c |
| **4E: Self-Improvement** | 6+ | Ongoing | 4A-4D complete |

**Critical Path**: Council rulings for envelope expansion (4C, 4D) are the primary schedule risk.

---

## Dependencies Matrix

| Phase | Depends On | Blocks |
|-------|------------|--------|
| 4A | (none) | 4B, 4C, 4D |
| 4B | 4A | 4E |
| 4C | 4A, Council Ruling 3a | 4D, 4E |
| 4D | 4A, 4C, Council Rulings 3b/3c | 4E |
| 4E | 4A, 4B, 4C, 4D | (none) |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Mean Time to Commit** | < 30 minutes (autonomous) | Timestamp: task selection to commit |
| **Escalation Rate** | < 10% of tasks | Escalations / Total tasks attempted |
| **Commit Success Rate** | > 90% | Successful commits / Total attempts |
| **Governance Violations** | ZERO | Violations blocked by envelope enforcer |
| **Self-Modification Outside Bounds** | ZERO | Audit of changed files vs allowed paths |
| **Human Intervention Rate** | < 5% (exception only) | Manual interventions / Total tasks |
| **Test Pass Rate** | > 95% | Tests passing after autonomous changes |
| **Budget Overruns** | ZERO | Token/diff budgets never exceeded |

---

## Governance Requirements

### Council Rulings Required

| Ruling | Phase | Purpose |
|--------|-------|---------|
| **Phase 3a: Test Envelope** | 4C | Authorize pytest execution |
| **Phase 3b: Code Envelope** | 4D | Authorize code creation/modification |
| **Phase 3c: Config Envelope** | 4D | Authorize config modification |
| **Self-Improvement Framework** | 4E | Authorize recursive improvement |

### CEO Authorities

- Approve/reject escalations via queue
- Engage/disengage kill switch
- Approve self-improvement proposals
- Waiver issuance for retry limit exceptions

### CSO Responsibilities

- Review envelope expansion rulings
- Audit protected path registry
- Monitor bypass utilization
- Security review of self-improvement proposals

---

## Appendix A: Existing Infrastructure Reference

### Core Files

| File | Purpose |
|------|---------|
| `runtime/orchestration/missions/autonomous_build_cycle.py` | Loop controller |
| `runtime/orchestration/loop/policy.py` | Policy adapter |
| `runtime/orchestration/loop/configurable_policy.py` | Config-driven policy |
| `runtime/orchestration/loop/ledger.py` | Attempt ledger |
| `runtime/orchestration/loop/taxonomy.py` | FailureClass, TerminalOutcome enums |
| `runtime/orchestration/loop/budgets.py` | Budget controller |
| `runtime/governance/envelope_enforcer.py` | Path containment |
| `scripts/escalation_monitor.py` | Escalation visibility |
| `config/policy/loop_rules.yaml` | Loop policy rules |
| `config/policy/tool_rules.yaml` | Tool policy rules |

### Existing Prompts

| File | Purpose |
|------|---------|
| `docs/09_prompts/v1.0/roles/chair_prompt_v1.0.md` | Council chair |
| `docs/09_prompts/v1.0/roles/cochair_prompt_v1.0.md` | Council co-chair |
| `docs/09_prompts/v1.0/roles/reviewer_architect_alignment_v1.0.md` | Architecture review |
| `docs/09_prompts/v1.0/roles/reviewer_l1_unified_v1.0.md` | Technical review |

---

## Appendix B: Deferred Items from Trusted Builder v1.1

Per Council Ruling Trusted Builder Mode v1.1 (2026-01-26), the following P1 items were deferred to Phase 4:

1. **Ledger Hash Chain** - Addressed in Phase 4E
2. **Bypass Monitoring** - Addressed in Phase 4E
3. **Semantic Guardrails** - Addressed in Phase 4E

These items are now formally incorporated into the Phase 4E deliverables.

---

## Appendix C: Backlog Integration (P1 Items)

Current P1 items from `docs/11_admin/BACKLOG.md` that align with this roadmap:

- [ ] **Ledger Hash Chain (Trusted Builder P1)** - Phase 4E
- [ ] **Bypass Monitoring (Trusted Builder P1)** - Phase 4E
- [ ] **Semantic Guardrails (Trusted Builder P1)** - Phase 4E

---

**END OF ROADMAP**

---

*Document generated: 2026-02-02*
*Next review: After Phase 4A completion*
