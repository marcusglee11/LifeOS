# LifeOS — Runtime Complexity Constraints v0.1

**Status**: Active
**Parent**: Anti-Failure Operational Packet v0.1
**Purpose**: Prevent "Complexity Drift" where the system becomes too heavy to maintain.

## 1. Thresholds

The Runtime (and Builder agents) must respect these limits. Exceeding them requires a **Refactor** or **Governance Override**.

### 1.1 Workflow Limits
- **Max Steps per Workflow**: 5 atomic steps.
    - *Reason*: If a workflow is longer, it's brittle. Break it into sub-workflows.
- **Max Human Actions**: 2 per workflow (Initiate + Approve).
    - *Reason*: More interaction points = higher friction and failure rate.

### 1.2 Project Limits
- **Max Active Lateral Projects**: 3.
    - *Reason*: Context switching cost destroys productivity.
- **Max Recursive Depth**: 2 layers (Agent implies Agent).
    - *Reason*: Debugging infinite recursion is impossible for a human.

### 1.3 Time Limits
- **Max Daily Maintenance**: < 10 mins (Human time).
    - *Reason*: If "keeping the lights on" takes >10 mins, the system is a burden.

## 2. Friction-Based Veto
Any new feature that adds a manual step for the human:
- **Default Judgment**: VETO.
- **Exceptions**: Must be proven to be temporary (scaffolding) or high-value governance.

## 3. The "Simplify" Trigger
If any threshold is breached:
1. The Runtime flags the breach.
2. The Agent proposes a **Simplification Plan** (not just "doing the work").
3. New work halts until complexity is reduced.

