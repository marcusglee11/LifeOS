# Context Pack: Architecture Lens (Codex)
# Reviewer: Codex | Seat: Architecture | Date: 2026-03-05

You are reviewing a plan for bootstrapping the LifeOS COO agent. Your role is the Architecture lens — evaluate structural coherence, component boundaries, and integration with existing infrastructure.

## Context
LifeOS is a multi-agent orchestrator with a working build loop (spine), dispatch engine, council review system, and evidence infrastructure. The plan proposes standing up an OpenClaw COO agent as project manager.

## Your Checklist
- [ ] Components/roles are enumerated and responsibilities are non-overlapping
- [ ] Interfaces/contracts are explicit and versionable
- [ ] Data/control flow is clear (who calls whom, when, with what inputs/outputs)
- [ ] State management is explicit; no hidden global state
- [ ] Failure modes and recovery paths exist
- [ ] The plan reuses existing infrastructure rather than rebuilding
- [ ] The simplest viable design is chosen

## Red Flags to Call Out
- Components not grounded in existing codebase
- Interfaces that duplicate what already exists
- Missing dependency between steps
- Tight coupling across domains
- Over-engineering (building what isn't needed yet)

## Key Questions
1. Does the structured backlog schema duplicate or conflict with the existing nightly_queue.yaml or recursive_kernel/backlog_parser.py?
2. Is the 5-level autonomy model enforceable through the proposed config, or is it advisory?
3. Are the COO CLI commands (propose/approve/status/report/direct) correctly integrated with the existing dispatch/spine/queue CLI surface?
4. Does the campaign tracker add necessary value or is it premature?
5. Is the trust growth model mechanically enforceable or does it depend on human discipline?

## Output Format
Produce a structured YAML review packet with the following fields:
```yaml
verdict_recommendation: APPROVE | APPROVE_WITH_CONDITIONS | REJECT
summary: "<1-2 sentence summary>"
claims:
  - id: A1
    category: architecture | interface | data_flow | failure_mode | over_engineering
    severity: blocker | major | minor | observation
    description: "<what is the issue>"
    evidence: "<specific reference to plan text or codebase>"
    recommendation: "<what to do>"
complexity_budget:
  new_files_count: <number>
  new_files_justified: true | false
  rationale: "<why>"
conditions:
  - "<condition if APPROVE_WITH_CONDITIONS>"
```

---

## Plan Document

(Full plan at: artifacts/plans/2026-03-05-coo-bootstrap-plan.md)

### Summary of Key Design Decisions

**COO Role:** OpenClaw instance acting as project manager. File-based communication only. No mid-execution agent communication.

**New Components Proposed:**
- `runtime/orchestration/coo/backlog.py` — TaskEntry dataclass + YAML load/save
- `runtime/orchestration/coo/context.py` — context builders (propose/status/report)
- `runtime/orchestration/coo/parser.py` — response parser + TaskProposal dataclass
- `runtime/orchestration/coo/templates.py` — ExecutionOrder template instantiation
- `runtime/orchestration/coo/commands.py` — CLI command handlers
- `config/governance/delegation_envelope.yaml` — autonomy level config
- `config/tasks/backlog.yaml` — structured backlog (YAML)
- `config/tasks/order_templates/*.yaml` — build/content/hygiene templates
- `config/agent_roles/coo.md` — COO system prompt

**Reused Infrastructure:**
- DispatchEngine (Phase 1, 56 tests) — COO writes to `artifacts/dispatch/inbox/`
- ExecutionOrder schema v1 — COO generates matching orders
- SupervisorPort / CuratorPort — file-based protocols COO implements
- CEOQueue (SQLite) — COO writes escalations
- CLI surface (`runtime/cli.py`) — extended with `coo` subparser
- CLIDispatch (`runtime/agents/cli_dispatch.py`) — COO invoked via this

**Data Flow:**
1. CEO directive → COO session
2. COO reads backlog.yaml + agent_perf log + campaign state
3. COO proposes → `lifeos coo propose` → ranked YAML proposals
4. CEO approves → `lifeos coo approve T-001`
5. COO generates ExecutionOrder → places in `artifacts/dispatch/inbox/`
6. DispatchEngine picks up → LoopSpine executes → terminal packet written
7. COO post-execution hook reads terminal packet → updates backlog.yaml

---

## Existing Infrastructure References

### runtime/orchestration/dispatch/order.py (ExecutionOrder schema)
```python
ORDER_SCHEMA_VERSION = "execution_order.v1"

@dataclass
class StepSpec:
    name: str
    role: str
    provider: str = "auto"
    mode: str = "blocking"
    lens_providers: Dict[str, str] = field(default_factory=dict)

@dataclass
class ConstraintsSpec:
    governance_policy: Optional[str] = None
    worktree: bool = False
    max_duration_seconds: int = 3600
    scope_paths: List[str] = field(default_factory=list)

@dataclass
class ExecutionOrder:
    schema_version: str  # must be "execution_order.v1"
    order_id: str        # regex: [a-zA-Z0-9_\-]{1,128}
    task_ref: str
    created_at: str
    steps: List[StepSpec]
    constraints: ConstraintsSpec
    shadow: ShadowSpec
    supervision: SupervisionSpec
```

### runtime/orchestration/dispatch/ports.py (COO file-based protocols)
```python
class SupervisorPort(Protocol):
    """COO implements via files in artifacts/supervision/"""
    def on_cycle_complete(self, terminal_packet: Path) -> Path: ...
    def on_batch_complete(self, batch_id: str, terminal_packets: List[Path]) -> Path: ...
    def check_promotion_criteria(self, batch_id: str) -> Optional[Dict]: ...

class CuratorPort(Protocol):
    """Task selection interface — COO Agent later"""
    def select_tasks(self, backlog: Path, batch_size: int) -> List[Dict]: ...
    def validate_selection(self, tasks: List[Dict]) -> Dict: ...
```

### runtime/orchestration/dispatch/engine.py (DispatchEngine)
```
Phase 1: Single-flight execution layer.
Inbox: artifacts/dispatch/inbox/
Active: artifacts/dispatch/active/
Completed: artifacts/dispatch/completed/
Delegates step execution to LoopSpine.
Enforces non-bypassable gates + canonical manifest.
```

### runtime/orchestration/ceo_queue.py (CEOQueue)
```python
class EscalationType(str, Enum):
    GOVERNANCE_SURFACE_TOUCH = "governance_surface_touch"
    BUDGET_ESCALATION = "budget_escalation"
    PROTECTED_PATH_MODIFICATION = "protected_path_modification"
    AMBIGUOUS_TASK = "ambiguous_task"
    POLICY_VIOLATION = "policy_violation"

class CEOQueue:
    """SQLite-backed escalation queue"""
    def enqueue(self, entry: EscalationEntry) -> str: ...
    def pending(self) -> List[EscalationEntry]: ...
    def resolve(self, id: str, status: EscalationStatus, note: str) -> None: ...
```

### runtime/agents/cli_dispatch.py (CLIDispatch)
```python
class CLIProvider(enum.Enum):
    CODEX = "codex"
    GEMINI = "gemini"
    CLAUDE_CODE = "claude_code"

# Spawns CLI agents as subprocesses with full tool use + file access
```

### config/models.yaml (Provider routing)
```yaml
council:
  topology: HYBRID
  provider_overrides:
    Architecture: claude_code
    Risk: gemini
    Governance: codex

cli_providers:
  codex:
    binary: "codex"
    sandbox: false  # --full-auto for unattended
  gemini:
    binary: "gemini"
    sandbox: true
```

### COO Operating Contract v1.0 (ratified governance)
```
Phase 0 — Bootstrapping: COO requires confirmation before initiating new workstreams
Phase 1 — Guided Autonomy: COO may propose and initiate unless altering identity/strategy
Phase 2 — Operational Autonomy: COO runs independently, only escalates defined categories

Escalation Rules (mandatory escalation when):
- Identity/Values changes
- Strategy decisions or direction shifts
- Irreversible or high-risk actions
- Ambiguity in intent
- Resource allocation above threshold
```
