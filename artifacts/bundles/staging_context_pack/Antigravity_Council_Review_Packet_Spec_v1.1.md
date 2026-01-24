# Antigravity Council Review Packet Spec v1.1

**Status**: Canonical Packaging Spec  
**Authority**: [lifeos_packet_schemas_CURRENT.yaml](../02_protocols/lifeos_packet_schemas_CURRENT.yaml)  
**Date**: 2026-01-06

---

## 1. Requirement
All Council Review Packets MUST be generated as Markdown files with a **strict YAML Frontmatter** block.

- The YAML Frontmatter is the **authoritative payload**.
- The Markdown body is **non-authoritative narrative**.

## 2. Format
File: `council_review/COO_Runtime_Phase<X>_Build_<ID>_ReviewPacket_v1.1.md`

```markdown
---
packet_id: "<UUID>"
packet_type: "COUNCIL_REVIEW_PACKET"
schema_version: "1.1"
created_at: "2026-01-06T12:00:00Z"
source_agent: "Antigravity"
target_agent: "Council"
chain_id: "<UUID>"
nonce: "<UUID>"
ttl_hours: 72
priority: "P2_NORMAL"
review_type: "CODE"
subject_ref: "Release Candidate 1"
subject_summary: "Phase 3 implementation of Core Runtime."
objective: "Approve for Tier 2 Entry."
context_refs:
  - "docs/specs/COO_Runtime_Spec_v1.0.md"
urgency_rationale: "Unblocks Tier 2 work."
---

# Narrative Walkthrough (Non-Authoritative)
[... Human readable content ...]
```

## 3. Validation
The validator will:
1. Extract the YAML frontmatter.
2. Validate it against the `COUNCIL_REVIEW_PACKET` schema in `lifeos_packet_schemas_CURRENT.yaml`.
3. Ignore the body content for schema validation purposes (though body integrity may be checked via hashing).

## 4. Lineage
This packet ID MUST be referenced by any subsequent `COUNCIL_APPROVAL_PACKET`.
