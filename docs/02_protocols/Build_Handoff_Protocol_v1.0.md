# Build Handoff Protocol v1.0

**Version**: 1.0  
**Date**: 2026-01-04  
**Status**: Active  
**Authority**: [LifeOS Constitution v2.0](../00_foundations/LifeOS_Constitution_v2.0.md)

---

## 1. Purpose

Defines the messaging architecture for agent-to-agent handoffs in LifeOS build cycles. Enables:
- Human-mediated handoffs (Mode 0/1)
- Future automated handoffs (Mode 2)

---

## 2. CEO Contract

### CEO Does
- Start chat thread, attach `LIFEOS_STATE.md`
- Speak normally (no IDs/slugs/paths)
- Paste dispatch block to Builder
- Read Review Packet

### CEO Never Does
- Supply internal IDs, slugs, paths, templates
- Fetch repo files for ChatGPT

---

## 3. Context Retrieval Loop

```
1. CEO attaches LIFEOS_STATE.md, asks normally
2. IF more context needed:
   → ChatGPT outputs: "Generate Context Pack for <role> regarding <component>"
3. CEO pastes to Builder
4. Builder returns Context Pack
5. CEO attaches pack to ChatGPT
6. ChatGPT proceeds
```

---

## 4. Packet Schemas

### 4.1 ARCHITECT_CONTEXT_PACKET
- `component_human_name`, `workstream_slug` (internal)
- `goal_summary` (≤5 lines), `constraints` (≤12), `success_criteria` (≤10)
- `state_ref`, `recent_work_refs` (≤5), `required_templates_refs` (≤5)
- `context_ttl_hours`: 72h default

### 4.2 BUILDER_CONTEXT_PACKET
- `state_ref`, `architect_context_ref`, `readiness_ref`, `last_review_packet_ref`
- `constraints_summary` (≤10), `success_criteria` (≤5)

### 4.3 COUNCIL_REVIEW_PACKET
- `artefact_under_review_ref`, `trigger_reasons`
- `required_decision_questions` (≤5)

---

## 5. Council Triggers

| ID | Trigger |
|----|---------|
| CT-1 | New/changed external interface |
| CT-2 | Touches protected paths |
| CT-3 | New CI script or gating change |
| CT-4 | Deviation from spec |
| CT-5 | Agent recommends (requires CT-1..CT-4 linkage) |

---

## 6. Preflight Priority

1. `docs/scripts/check_readiness.py` (if exists)
2. Fallback: `pytest runtime/tests -q`
3. Check LIFEOS_STATE Blockers
4. Check `artifacts/packets/blocked/`

---

## 7. Evidence Requirements

| Mode | Requirement |
|------|-------------|
| Mode 0 | Log path in `logs/preflight/` |
| Mode 1 | Hash attestation in READINESS packet |

---

## 8. Internal Lineage

- Never surfaced to CEO
- Mode 0: Builder generates for new workstream
- Mode 1+: Inherited from context packet

---

## 9. TTL and Staleness

- Default: 72 hours
- Council extension: until outcome (max +72h)
- Stale: BLOCK by default

---

## 10. Workstream Resolution

Via `artifacts/workstreams.yaml`:
1. Exact match on `component_human_name`
2. Alias match
3. Slugify + add as PROVISIONAL
4. BLOCK only on true ambiguity

---

## 11. Artifact Bundling (Pickup Protocol)

At mission completion, Builder MUST:

1. **Bundle**: Create zip at `artifacts/bundles/<Mission>_<timestamp>.zip` containing:
   - All Review Packets for the mission
   - Council packets (if CT-triggered)
   - Readiness packets + evidence logs
   - Modified governance docs (for review)

2. **Manifest**: Create `artifacts/bundles/MANIFEST.md` listing bundle contents

3. **Copy to CEO Pickup**: Copy deliverables to `artifacts/for_ceo/` for easy access

4. **Delivery**: Provide CEO:
   - PathsToReview in notify_user (preview pane)
   - Raw copyable path in message text:
     ```
     📦 Path: <RepoRoot>\artifacts\bundles\<name>.zip
     ```

**Default**: No auto-open. No surprise windows.

**Optional**: Auto-open Explorer only when CEO explicitly requests or `--auto-open` flag is used.

CEO clears `artifacts/for_ceo/` after pickup. Agent MUST NOT delete from this folder.

---

**END OF PROTOCOL**
