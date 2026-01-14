# ARTEFACT_INDEX Schema v1.0

<!-- LIFEOS_TODO[P1][area: docs/01_governance/ARTEFACT_INDEX_SCHEMA.md][exit: status change to ACTIVE + DAP validate] Finalize ARTEFACT_INDEX_SCHEMA v1.0: Remove WIP/Provisional markers -->

**Status**: WIP (Non-Canonical)
**Authority**: LifeOS Constitution v2.0 → Document Steward Protocol v1.1
**Effective**: 2026-01-07 (Provisional)

---

## 1. Purpose

Defines the structure and validation rules for `ARTEFACT_INDEX.json`, the canonical source of truth for LifeOS binding artefacts.

---

## 2. Schema Structure (YAML Representation)

```yaml
meta:
  version: "string (SemVer)"
  updated: "string (ISO 8601)"
  description: "string"
  sha256_policy: "string"
  counting_rule: "string"
  binding_classes:
    FOUNDATIONAL: "string"
    GOVERNANCE: "string"
    PROTOCOL: "string"
    RUNTIME: "string"
artefacts:
  _comment_<class>: "string (Visual separator)"
  <doc_key>: "string (Repo-relative path)"
```

---

## 3. Validation Rules

1. **Path Resolvability**: All paths in `artefacts` MUST resolve to valid files on disk.
2. **Unique Keys**: No duplicate keys allowed in `artefacts`.
3. **Unique Paths**: No duplicate paths allowed in `artefacts`.
4. **Binding Class Alignment**: Artefacts should be grouped by their binding class comments.
5. **Version Increments**: Any modification to the indexing structure or counting rules MUST increment the `meta.version`.

---

## 4. Stewardship

The Document Steward is responsible for maintaining the index and ensuring parity with the filesystem. Automated validators MUST verify this schema before any commit involving governance docs.

---

**END OF SCHEMA**
