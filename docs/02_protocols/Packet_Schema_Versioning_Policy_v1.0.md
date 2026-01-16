# Packet Schema Versioning Policy v1.0

**Status**: Active  
**Authority**: [Governance Protocol v1.0](../01_governance/Governance_Protocol_v1.0.md)  
**Date**: 2026-01-06

---

## 1. Purpose
Defines the semantic versioning and amendment rules for `lifeos_packet_schemas`.

## 2. Versioning Scheme (SemVer)
Format: `MAJOR.MINOR.PATCH`

### MAJOR (Breaking)
Increment when:
- Removing a field that was previously required.
- Renaming a field.
- Removing an enum value.
- Removing a packet type.
- Changing validation logic to be strictly more restrictive (e.g. decreasing max payload).

**Migration**: Requires a migration map and potentially a validator update to flag deprecated usage.

### MINOR (Additive)
Increment when:
- Adding a new optional field.
- Adding a new enum value.
- Adding a new packet type.
- Relaxing validation logic.

**Compatibility**: Backward compatible. Old validators may warn on "unknown field" (if strict) or ignore it.

### PATCH (Fixes)
Increment when:
- Updating descriptions/comments.
- Fixing typos.
- Adding non-normative examples.

**Compatibility**: Fully compatible.

## 3. Amendment Process

1. **Proposal**: Submit a `COUNCIL_REVIEW_PACKET` (Governance) with the proposed schema change.
2. **Review**: Council evaluates impact on existing agents/tooling.
3. **Approval**: `COUNCIL_APPROVAL_PACKET` authorizes the merge.
4. **Merge**:
   - Update `lifeos_packet_schemas_vX.Y.yaml`.
   - Update `Packet_Schema_Versioning_Policy` (if policy itself changes).
   - Bump version number in the schema file header.

## 4. Deprecation Policy
- Deprecated fields/types must be marked with `# DEPRECATED: <Reason>`.
- Must remain valid for at least one MAJOR cycle unless critical security flaw exists.

---
**END OF POLICY**
