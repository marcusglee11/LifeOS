# Build Handoff Protocol v1.1

**Version**: 1.1  
**Date**: 2026-01-06  
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

## 3. Context Retrieval Loop (Packet-Based)

The ad-hoc "Generate Context Pack" prompt is replaced by a canonical packet flow (P1.1).

**Trigger**: Agent (Architect/Builder) determines missing info.

**Flow**:
1. **Agent** emits `CONTEXT_REQUEST_PACKET`:
   - `requester_role`: ("Builder")
   - `topic`: ("Authentication")
   - `query`: ("Need auth schemas and user implementation")
2. **CEO** conveys packet to Builder/Architect (Mode 0) or routes automatically (Mode 2).
3. **Responder** (Builder/Architect) emits `CONTEXT_RESPONSE_PACKET`:
   - `request_packet_id`: (matches Request)
   - `repo_refs`: List of relevant file paths + summaries.
4. **Agent** ingestion:
   - "ACK loaded context <packet_id>."

**Constraint**: NO internal prompts. All context requests must be structural packets.


---

## 4. Packet Types (Canonical)

All packet schemas are defined authoritatively in [lifeos_packet_schemas_v1.1.yaml](lifeos_packet_schemas_v1.1.yaml).
This protocol utilizes:

### 4.1 CONTEXT_REQUEST_PACKET
- Used when an agent needs more information from the repository.
- Replaces ad-hoc "Generate Context" prompts.

### 4.2 CONTEXT_RESPONSE_PACKET
- Returns the requested context (files, summaries, or prior packets).
- Replaces ad-hoc context dumps.

### 4.3 HANDOFF_PACKET
- Used to transfer control and state between agents (e.g. Architect -> Builder).

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

- Defined by:
| Resource | Path |
|----------|------|
| **Canonical Schema** | `docs/02_protocols/lifeos_packet_schemas_v1.1.yaml` |
| Templates | `docs/02_protocols/lifeos_packet_templates_v1.yaml` |
- Default TTL: 72h.
- Stale: BLOCK by default.

---

## 10. Workstream Resolution

**Zero-Friction Rule**: CEO provides loose "human intent" strings. Agents MUST resolve these to strict internal IDs.

Resolution Logic (via `artifacts/workstreams.yaml` or repo scan):
1. Exact match on `human_name`
2. Fuzzy/Alias match
3. Create PROVISIONAL entry if ambiguous
4. BLOCK only if resolution is impossible without input.

**CEO MUST NEVER be asked for a `workstream_slug`.**

---

## 11. Artifact Bundling (Pickup Protocol)

At mission completion, Builder MUST:

1. **Bundle**: Create zip at `artifacts/bundles/<Mission>_<timestamp>.zip` containing:
   - All Review Packets for the mission
   - Council packets (if CT-triggered)
   - Readiness packets + evidence logs
   - Modified governance docs (for review)
   - **G-CBS Compliance**: Bundle MUST be built via `python scripts/closure/build_closure_bundle.py`.

2. **Manifest**: Create `artifacts/bundles/MANIFEST.md` listing bundle contents

3. **Copy to CEO Pickup (MANDATORY)**: You MUST copy the BUNDLE and the REVIEW PACKET to `artifacts/for_ceo/`.
   - The CEO should NOT have to hunt in `artifacts/bundles/` or `artifacts/review_packets/`.
   - The `artifacts/for_ceo/` directory is the **primary delivery interface**.
   - PathsToReview in notify_user (preview pane)
   - Raw copyable path in message text:
     ```
     📦 Path: <RepoRoot>\artifacts\bundles\<name>.zip
     ```

**Default**: No auto-open. No surprise windows.

**Optional**: Auto-open Explorer only when CEO explicitly requests or `--auto-open` flag is used.

CEO clears `artifacts/for_ceo/` after pickup. Agent MUST NOT delete from this folder.

---

## Changes in v1.1
- **Schema Unification**: Removed shadow schemas in Section 4; referenced `lifeos_packet_schemas_v1.1.yaml`.
- **Context Canonicalization**: Adopted `CONTEXT_REQUEST` / `CONTEXT_RESPONSE` packets.
- **Zero Friction**: Removed requirement for internal IDs in Section 10; strictly enforced agent-side resolution.

---

**END OF PROTOCOL**
