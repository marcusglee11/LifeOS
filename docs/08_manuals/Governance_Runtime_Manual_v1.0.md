# Governance + Runtime Manual v1.0

## 1. Overview

This manual defines how the user interacts with AI assistants (ChatGPT, Gemini, etc.) as part of the LifeOS / COO-Agent ecosystem, using:

- Discussion Mode
- StepGate Protocol
- Deterministic Artefact Protocol
- Council Roles and Reviewers
- Prompt Library v1.0

The goals are:
- Low human friction
- Deterministic behaviour
- Clear governance and escalation
- Safe, auditable workflows

---

## 2. Modes

### 2.1 Discussion Mode

Use for:
- Exploration, framing, and conceptual reasoning.
- Comparing options or designs.
- Clarifying requirements.

Key rules:
- Assistant keeps scope tight.
- Assistant asks before generating long outputs or many branches.
- Assistant clarifies intent (depth vs breadth vs single path).
- When you start giving actionable instructions, the assistant proposes switching to StepGate.

### 2.2 StepGate Mode

Use for:
- Multi-step builds (specs, code, prompts, systems).
- Work with operational or safety risk.
- Artefact creation and integration.

Key rules:
- Assistant asks clarifying questions once upfront.
- Assistant shows a short workflow scaffold.
- Each step is small and self-contained.
- Assistant waits for **"go"** before advancing.

---

## 3. Deterministic Artefact Protocol

When generating files, folders, or archives:

1. Assistant outputs all file contents in a single consolidated text block.
2. You review and confirm (or request edits).
3. Only after confirmation does the assistant create files or ZIPs via tools, using exactly those contents.
4. No placeholders; no implicit changes after confirmation.

This ensures repeatability and prevents “flaky” artefacts.

---

## 4. Council Roles (v1.0)

### 4.1 Chair
- Frames missions.
- Builds review/build packets.
- Routes work to roles.
- Aggregates results and actions.

### 4.2 Co-Chair
- Validates packets for clarity, scope, and governance.
- Spots risks and drift.
- Produces role-specific prompt blocks.

### 4.3 L1 Unified Reviewer
- Provides a single, integrated review across architecture, technical feasibility, risk, and alignment.
- Returns a verdict, issues, risks, required changes, and questions.

### 4.4 Architect + Alignment Reviewer
- Focuses on invariants, lifecycle, boundaries, and alignment with user intent.
- Identifies contradictions, missing contracts, and governance drift.

---

## 5. Prompt Library v1.0

Location:

```text
governance-hub/prompts/v1.0/
```

Structure:

- `protocols/` — StepGate, Discussion, capability envelopes.
- `roles/` — Chair, Co-Chair, L1, Architect+Alignment.
- `system/` — universal envelope, modes overview.
- `initialisers/` — master initialiser for models.

Usage patterns:
- For ChatGPT: inject the master initialiser + ChatGPT capability envelope.
- For Gemini: inject the master initialiser + Gemini capability envelope.
- For council work: Chair and Co-Chair use their prompts to create and validate packets, then L1 and Architect+Alignment reviewers operate on those packets.

---

## 6. Versioning

This is **v1.0** of the governance + runtime manual and prompt library.

When changes are needed:
- Create a new folder `v1.1/` under `prompts/`.
- Copy and modify files rather than editing in place.
- Update this manual (or create `governance_runtime_manual_v1.1.md`) with a short changelog.

This preserves determinism and makes it possible to reproduce prior decisions and workflows.
