# G-CBS Audit Report: PASS
**Date**: 1980-01-01T00:00:00
**Bundle**: Bundle_Fix_Harden_E2E_Harness_Patch_v1.2.zip
**Digest Strategy**: Detached (Sidecar Verified)

## Checks Performed
- ZIP path canonicalization (no backslashes, no .., no absolute)
- Required root files (closure_manifest.json, closure_addendum.md)
- Manifest schema validation (G-CBS-1.0)
- Addendum elision check (no elision tokens allowed)
- Addendum row count vs manifest evidence count
- Addendum table parsing (role, path, sha256)
- Portability check (.md files: no file:///, no C:\\Users\\)
- Evidence file integrity (SHA256 verification)
- Transcript completeness (Exit Code presence)
- Protocols provenance hash

## Provenance Evidence
| Component | Reference | Expected SHA256 | Actual SHA256 | Status |
|-----------|-----------|-----------------|---------------|--------|
| protocols | docs/01_governance/ARTEFACT_INDEX.json | `74BBF6A08C5D37968F77E48C28AB5F19E960140A368A3ABB6F4826B806D316BE` | `74BBF6A08C5D37968F77E48C28AB5F19E960140A368A3ABB6F4826B806D316BE` | PASS |

## Validation Findings
No issues found. Bundle is COMPLIANT.
