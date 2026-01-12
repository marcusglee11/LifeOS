# Intent Routing Rule v1.1

**Status**: WIP (Non-Canonical)  
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0  
**Effective**: TBD (Provisional)

---

## 1. Supremacy Principle

The CEO is the sole originator of intent. All system authority is delegated, not inherent. Any delegation can be revoked. Ambiguity in intent interpretation resolves upward, ultimately to CEO.

---

## 2. Delegation Tiers

Authority flows downward through tiers. Each tier operates autonomously within its envelope and escalates when boundaries are reached.

| Tier | Role | Autonomous Authority |
|------|------|---------------------|
| T0 | CEO | Unlimited. Origin of all intent. |
| T1 | CSO | Interpret CEO intent. Resolve deadlocks by reframing. Escalate unresolvable ambiguity. |
| T2 | Councils / Reviewers | Gate decisions within defined scope. Flag disagreements. Cannot override each other. |
| T3 | Agents | Execute within envelope. No discretion on out-of-envelope actions. |
| T4 | Deterministic Rules | Automated execution. No discretion. Fail-closed on edge cases. |

**Downward delegation**: Higher tiers define envelopes for lower tiers.  
**Upward escalation**: Lower tiers escalate when envelope exceeded or ambiguity encountered.

---

## 3. Envelope Definitions

Envelopes define what a tier/agent can do without escalation. Envelopes are additive (whitelist), not subtractive.

### 3.1 Envelope Structure

Each envelope specifies:

| Element | Description |
|---------|-------------|
| **Scope** | What domain/actions are covered |
| **Boundaries** | Hard limits that trigger escalation |
| **Discretion** | Where judgment is permitted within scope |
| **Logging** | What must be recorded |

### 3.2 Current Envelopes (Early-Stage)

#### T4: Deterministic Rules
- **Scope**: Schema validation, format checks, link integrity, test execution
- **Boundaries**: Any ambiguous input → escalate to T3
- **Discretion**: None
- **Logging**: Pass/fail results

#### T3: Agents (Build, Stewardship)
- **Scope**: Execute specified tasks, maintain artifacts, run defined workflows
- **Boundaries**: No structural changes without review. No new commitments. No external communication.
- **Discretion**: Implementation details within spec. Ordering of subtasks.
- **Logging**: Actions taken, decisions made, escalations raised

#### T2: Councils / Reviewers
- **Scope**: Evaluate proposals against criteria. Approve/reject/request-revision.
- **Boundaries**: Cannot resolve own deadlocks. Cannot override CEO decisions. Cannot expand own scope.
- **Discretion**: Judgment on quality, risk, completeness within review criteria.
- **Logging**: Verdicts with reasoning, dissents recorded

#### T1: CSO
- **Scope**: Interpret CEO intent across system. Resolve T2 deadlocks. Represent CEO to system.
- **Boundaries**: Cannot contradict explicit CEO directive. Cannot make irreversible high-impact decisions. Cannot delegate T1 authority.
- **Discretion**: Reframe questions to enable progress. Narrow decision surface. Prioritize among competing valid options.
- **Logging**: Interpretations made, deadlocks resolved, escalations to CEO

---

## 4. Escalation Triggers

Escalation is mandatory when any trigger is met. Escalation target is the next tier up unless specified.

| Trigger | Description | Escalates To |
|---------|-------------|--------------|
| **Envelope breach** | Action would exceed tier's defined boundaries | Next tier |
| **Ambiguous intent** | Cannot determine what CEO would want | CSO (or CEO if CSO uncertain) |
| **Irreversibility** | Action is permanent or very costly to undo | CEO |
| **Precedent-setting** | First instance of a decision type | CSO minimum |
| **Deadlock** | Reviewers/councils cannot reach consensus | CSO |
| **Override request** | Lower tier believes higher tier decision is wrong | CEO |
| **Safety/integrity** | System integrity or safety concern | CEO direct |

---

## 5. CSO Authority

The CSO serves as gatekeeper to CEO attention - filtering routine from material, not just passing failures upward.

### 5.1 Escalation to CEO

CSO escalates to CEO when:

| Reason | Description |
|--------|-------------|
| **Authority exceeded** | Decision exceeds CSO's delegated envelope (see §5.4) |
| **Materiality** | Decision is significant enough that CEO should own it regardless of CSO capability |
| **Resolution failed** | Techniques in §5.2 exhausted without progress |
| **Uncertainty** | CSO uncertain whether CEO would want involvement |

### 5.2 Deadlock Resolution Techniques

When CSO handles (not escalates), the primary function is **not to decide**, but to enable decision. In order of preference:

1. **Reframe** - Reformulate the question to dissolve the disagreement
2. **Narrow** - Reduce the decision surface until consensus is reachable
3. **Sequence** - Convert blocking decision into staged/reversible steps
4. **Defer** - Identify what information would resolve it; pause until available
5. **Decide** - Only when above fail; log reasoning extensively

### 5.3 CSO Decision Constraints

When CSO decides (rather than escalates):

**Primary criterion**: Align with CEO intent. CSO acts as CEO's representative - the governing question is "what would the CEO decide here?"

**Supporting heuristics** (when intent is ambiguous):
- Choose the more reversible option
- Choose the option that preserves more future options
- Consider risk-adjusted cost-benefit
- If still unclear, choose option closer to status quo
- If still equal, escalate to CEO

### 5.4 CSO Envelope

CSO envelope boundaries (spend limits, commitment types, authority scope) are defined in **CSO Role Constitution v1.0**. This section is a stub pending that document's ratification.

---

## 6. Early-Stage Overrides

During system immaturity, tighter escalation applies. CEO releases these as confidence builds.

### 6.1 Current Overrides (Active)

| Override | Effect | Release Criteria |
|----------|--------|------------------|
| **Structural changes → CEO** | Any change to governance docs, protocols, tier definitions requires CEO approval | CEO discretion |
| **New agent activation → CEO** | Activating new autonomous capability requires CEO approval | CEO discretion |
| **External actions → CEO** | Any action visible outside system (commits, communications) requires CEO approval | CEO discretion |
| **CSO decisions → CEO review** | CSO logs all decisions; CEO reviews async | CEO satisfied with CSO calibration |

### 6.2 Maturity Indicators (Informational)

Suggested indicators that may inform CEO release decisions:
- Consistent track record (N decisions without override)
- Error rate below threshold
- Escalation quality (appropriate, not excessive)
- CSO interpretations align with CEO intent on review

CEO retains sole authority to release overrides regardless of indicators.

---

## 7. Routing Flow

```
Input received
    ↓
Can T4 (deterministic) handle? → Yes → Execute, log
    ↓ No
Can T3 (agent) handle within envelope? → Yes → Execute, log
    ↓ No
Does T2 (council) have jurisdiction? → Yes → Review, approve/reject/revise
    ↓ No or Deadlock
CSO: Reframe/narrow/sequence/defer/decide
    ↓ If unresolvable
CEO: Final decision
```

---

## 8. Logging Requirements

All tiers log to system record. Minimum fields:

| Field | Required |
|-------|----------|
| Timestamp | Yes |
| Tier | Yes |
| Action/Decision | Yes |
| Reasoning | T1-T3 |
| Escalation (if any) | Yes |
| Outcome | Yes |

Logs are immutable. CEO has full access. Lower tiers have read access to own logs.

---

## 9. Cross-Reference

- CSO Role Constitution v1.0 (WIP)
- Council Protocol v1.2
- Governance Protocol v1.0

---

**END OF RULE**
