---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "DOC_DRAFT"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "0.1"
status: "DRAFT"

# Optional
chain_id: ""
mission_ref: ""
parent_artifact: ""
tags: []
---

# Documentation Draft: <Topic>

**Date:** YYYY-MM-DD
**Author:** Antigravity
**Version:** 0.1

---

## Target Document

**Path:** `<!-- docs/path/to/document.md -->`

**Current Status:** <!-- EXISTS / NEW -->

---

## Change Type

<!-- One of: ADDITIVE, MODIFYING, REPLACING -->

| Type | Description |
|------|-------------|
| **ADDITIVE** | Adding new content to existing document |
| **MODIFYING** | Changing existing content |
| **REPLACING** | Full replacement of document |

**This Draft:** <!-- ADDITIVE / MODIFYING / REPLACING -->

---

## Draft Content

<!-- The actual proposed content below -->

```markdown
<!-- Your documentation content here -->
```

---

## Dependencies

### Documents This Depends On

- `<!-- docs/path/to/dependency1.md -->`
- `<!-- docs/path/to/dependency2.md -->`

### Documents That Depend On This

- `<!-- docs/path/to/dependent1.md -->`

### Code References

- `<!-- runtime/path/to/module.py -->`

---

## Diff Preview

<!-- If MODIFYING, show what changes -->

```diff
-<!-- old content -->
+<!-- new content -->
```

---

*This documentation draft was created under LifeOS Build Artifact Protocol v1.0.*
