# REPORT — Doc Stewardship Status v1.0

**Date**: 2026-02-10
**Author**: Antigravity (doc steward)

---

## 1. Where Doc Stewardship Is Specified

| Document | Path | Scope |
|----------|------|-------|
| **GEMINI.md (Agent Constitution)** | `GEMINI.md` | Articles X–XIV: mission output, review packets, plan gates, doc steward protocol, zero-friction rule |
| **Document Steward Protocol v1.1** | `docs/02_protocols/Document_Steward_Protocol_v1.1.md` | INDEX.md updates, Strategic Corpus regeneration, stewardship triggers |
| **DOC_STEWARD Constitution v1.0** | `docs/01_governance/DOC_STEWARD_Constitution_v1.0.md` | Role definition, authority chain, allowed/forbidden actions |
| **Build Artifact Protocol v1.0** | `docs/02_protocols/Build_Artifact_Protocol_v1.0.md` | Artifact naming, versioning, path conventions |
| **Git Workflow Protocol v1.1** | `docs/02_protocols/Git_Workflow_Protocol_v1.1.md` | Branch naming, commit conventions, merge policy |

## 2. Where Doc Stewardship Is Enforced (Code vs Protocol)

| Mechanism | Path | Type | What It Enforces |
|-----------|------|------|------------------|
| **Pre-commit hook** | `.git/hooks/pre-commit` (source: `scripts/hooks/`) | **Code** | Blocks direct main commits; blocks untracked files (Art. XIX) |
| **claude_doc_stewardship_gate.py** | `scripts/claude_doc_stewardship_gate.py` | **Code** | Checks INDEX.md updated + Strategic Corpus regenerated when docs/ modified |
| **claude_review_packet_gate.py** | `scripts/claude_review_packet_gate.py` | **Code** | Validates Review Packet exists before session completion |
| **coo_land_policy.py** | `runtime/tools/coo_land_policy.py` | **Code** | Allowlist gate, EOL-only detection, **config-aware clean check** (new) |
| **coo_acceptance_policy.py** | `runtime/tools/coo_acceptance_policy.py` | **Code** | Clean-proof validation in acceptance notes (new) |
| **Review Packet Gate (Art. XII)** | `GEMINI.md` | **Protocol** | Review Packet required before notify_user |
| **Plan Artefact Gate (Art. XIII)** | `GEMINI.md` | **Protocol** | Plan required before substantive changes |
| **Stewardship Validation Rule (§6)** | `GEMINI.md` | **Protocol** | INDEX.md + Corpus must be updated when docs change |
| **Startup Protocol (Art. XVI §1)** | `GEMINI.md` | **Protocol** | Read LIFEOS_STATE.md at session start |
| **Admin Hygiene (Art. XVI §2)** | `GEMINI.md` | **Protocol** | Sort inbox, update state, check strays, archive packets |

## 3. Gap Analysis: Protocol-Only vs Code-Enforced

| Requirement | Protocol | Code | Gap |
|------------|----------|------|-----|
| Review Packet before closure | ✅ Art. XII | ✅ `claude_review_packet_gate.py` | **Partial** — gate script is Claude-specific; not portable to OpenClaw/Codex |
| Plan before implementation | ✅ Art. XIII | ❌ | **Protocol-only** — no automated enforcement |
| INDEX.md + Corpus update | ✅ Art. XIV | ✅ `claude_doc_stewardship_gate.py` | **Partial** — Claude-specific |
| Clean repo invariant | ✅ Art. X | ✅ `coo_land_policy.py clean-check` | **Closed** (this mission) |
| Acceptance clean proofs | ✅ Schema v1.0 | ✅ `coo_acceptance_policy.py` | **Closed** (this mission) |
| EOL config compliance | ✅ EOL_Policy_v1.0 | ✅ `coo_land_policy.py clean-check` | **Closed** (this mission) |
| Startup state read | ✅ Art. XVI | ❌ | **Protocol-only** |
| Admin hygiene | ✅ Art. XVI §2 | ❌ | **Protocol-only** |
| TODO Standard enforcement | ✅ TODO_Standard_v1.0 | ⚠️ `todo_inventory.py` (exists but not gated) | **Weak** |

## 4. What Must Be Codified Next (Cross-Agent Portability)

### Priority 1: Agent-Agnostic Gate Runner

The `claude_doc_stewardship_gate.py` and `claude_review_packet_gate.py` scripts are **Claude Code-specific** (invoked by Claude's hook system). They need to be refactored into agent-agnostic gates callable by any builder (OpenClaw, Codex, Claude Code):

1. **Rename/refactor** → `scripts/gates/doc_stewardship_gate.py` and `scripts/gates/review_packet_gate.py`
2. **Add `coo gate run-all`** CLI command that runs all gates in sequence
3. **Wire into `coo land`** as a pre-land check (alongside clean-check)

### Priority 2: Plan Gate Enforcement

Art. XIII (Plan Artefact Gate) is entirely protocol-only. Minimum codification:

1. Add `scripts/gates/plan_gate.py` — checks `artifacts/plans/` for a recent approved plan
2. Wire into `coo build` or equivalent as a pre-build check

### Priority 3: Startup Protocol Enforcement

Art. XVI §1 (read LIFEOS_STATE.md at session start) is protocol-only. Codify as:

1. `coo preflight` command that reads and validates LIFEOS_STATE.md
2. Exits non-zero if state contains BLOCKED items that affect the current workstream

---

## Summary

Doc stewardship is **well-specified** (5 documents, 13+ rules) but **unevenly enforced**:

- **3 code-enforced gates** (pre-commit hook, doc stewardship gate, review packet gate) — all Claude-specific
- **2 new code-enforced gates** (clean-check, acceptance validator) — agent-agnostic (this mission)
- **4+ rules are protocol-only** with no automated enforcement

The minimum next step for cross-agent portability is refactoring the Claude-specific gates into agent-agnostic `coo gate` commands.
