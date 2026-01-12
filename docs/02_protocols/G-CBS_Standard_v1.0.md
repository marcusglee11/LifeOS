# Generic Closure Bundle Standard (G-CBS) v1.0

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Date** | 2026-01-06 |
| **Author** | Antigravity |
| **Status** | DRAFT |
| **Governance** | CT-2 Council Review Required for Activation |

---

## 1. Overview

The Generic Closure Bundle Standard (G-CBS) defines the schema, validation rules, and attestation model for closure bundles in LifeOS. Closure bundles provide auditable, deterministic evidence packages for step gates, council rulings, and other governance actions.

**Authority:** This protocol becomes binding when (1) approved via CT-2 council review and (2) listed in `docs/01_governance/ARTEFACT_INDEX.json`.

---

## 2. Detached Digest Mode

### 2.1 Purpose

Detached digest mode resolves circular dependencies when the validator transcript is embedded inside the bundle it validates.

### 2.2 Marker

**Manifest Field:** `zip_sha256`
**Detached Value:** `"DETACHED_SEE_SIBLING_FILE"`

When this marker is present, container integrity is attested by an external sidecar file.

### 2.3 Sidecar Specification

| Aspect | Requirement |
|--------|-------------|
| **Naming** | `<bundle_filename>.sha256` (e.g., `Bundle_v1.0.zip.sha256`) |
| **Content** | `<lowercase_hex_sha256>  <filename>` (two-space separator) |
| **Encoding** | UTF-8, LF line endings |
| **Location** | Same directory as bundle |

**Example:**
```
a1b2c3d4e5f6...  Bundle_v1.0.zip
```

### 2.4 Validator Requirements

| Condition | Behavior |
|-----------|----------|
| Sidecar missing | FAIL: `E_DIGEST_SIDECAR_MISSING` |
| Sidecar malformed | FAIL: `E_DIGEST_SIDECAR_MALFORMED` |
| Hash mismatch | FAIL: `E_DIGEST_MISMATCH` |
| Hash match | Print: `Sidecar digest verified: <sha256>` |

### 2.5 Backward Compatibility

If `zip_sha256` contains an actual hash (not the detached marker), the validator computes and compares directly (embedded mode). Embedded mode is DEPRECATED for new bundles.

---

## 3. Two-Part Attestation Model

### 3.1 Overview

G-CBS separates attestation into two distinct claims to eliminate circularity:

| Attestation | What is Validated | Evidence |
|-------------|-------------------|----------|
| **Payload Compliance** | Evidence files per manifest | Embedded transcript |
| **Container Integrity** | Shipped ZIP bytes | Detached sidecar |

### 3.2 Payload Compliance Attestation

**Domain:** All evidence files listed in `closure_manifest.json`
**Checks:**
- Schema validity
- Evidence SHA256 match
- Profile-specific rules
- Forbidden token scan

**Evidence Role:** `validator_payload_pass`

The embedded transcript MUST NOT claim to validate the final ZIP bytes (that's container integrity).

### 3.3 Container Integrity Attestation

**Domain:** Shipped ZIP file bytes
**Evidence:** Sidecar digest verification
**Validator Output:**
```
Detached digest mode: true
Sidecar digest path: <path>
Sidecar digest verified: <sha256>
```

---

## 4. Evidence Roles

### 4.1 Required Role

| Role | Description | Status |
|------|-------------|--------|
| `validator_payload_pass` | Payload compliance attestation | **REQUIRED** |

### 4.2 Legacy Role (Compatibility Window)

| Role | Description | Status |
|------|-------------|--------|
| `validator_final_shipped` | Legacy role | DEPRECATED |

**Compatibility Policy:**
- G-CBS v1.0: Accept both roles; emit warning for legacy
- G-CBS v1.1+: Reject `validator_final_shipped` with `E_ROLE_DEPRECATED`

### 4.3 Validator Behavior

```
IF neither role present:
  → E_REQUIRED_EVIDENCE_MISSING (exit 1)

IF validator_final_shipped AND gcbs_version < 1.1:
  → WARN: "Deprecated role, use validator_payload_pass"

IF validator_final_shipped AND gcbs_version >= 1.1:
  → E_ROLE_DEPRECATED (exit 1)

IF validator_payload_pass:
  → Accept (no warning)
```

---

## 5. Provenance Fields

### 5.1 Required Manifest Fields

| Field | Description |
|-------|-------------|
| `activated_protocols_ref` | Repo-relative path to `ARTEFACT_INDEX.json` |
| `activated_protocols_sha256` | SHA-256 of raw file bytes (uppercase hex) |
| `gcbs_standard_version` | Version of this standard (e.g., `"1.0"`) |

### 5.2 Optional Fields

| Field | Description |
|-------|-------------|
| `gcbs_standard_ref` | Path to this document |
| `validator_version` | Validator script version |

### 5.3 Validation

| Condition | Behavior |
|-----------|----------|
| `gcbs_standard_version` missing | FAIL: `E_GCBS_STANDARD_VERSION_MISSING` |
| `activated_protocols_sha256` mismatch | FAIL: `E_PROTOCOLS_PROVENANCE_MISMATCH` |

---

## 6. Validator Output Contract

### 6.1 Deterministic Stdout Lines

On detached digest mode success:
```
Detached digest mode: true
Sidecar digest path: <path>
Sidecar digest verified: <sha256>
```

On payload compliance success:
```
Payload compliance: PASS
Evidence roles verified: [validator_payload_pass]
```

### 6.2 Audit Report

| Mode | Bundle Hash Field |
|------|-------------------|
| Detached | `**Digest Strategy**: Detached (Sidecar Verified)` |
| Embedded (deprecated) | `**Bundle SHA256**: <hash>` |

---

## 7. Deterministic Error Codes

| Code | Condition | Message |
|------|-----------|---------|
| `E_DIGEST_SIDECAR_MISSING` | Sidecar file not found | `Sidecar not found: {path}` |
| `E_DIGEST_SIDECAR_MALFORMED` | Invalid sidecar format | `Malformed sidecar: {detail}` |
| `E_DIGEST_MISMATCH` | Expected vs actual mismatch | `Digest mismatch` |
| `E_REQUIRED_EVIDENCE_MISSING` | No valid payload role | `Missing evidence: {role}` |
| `E_ROLE_DEPRECATED` | Legacy role after cutoff | `Deprecated role: {role}` |
| `E_GCBS_STANDARD_VERSION_MISSING` | No gcbs_standard_version | `Missing: gcbs_standard_version` |
| `E_PROTOCOLS_PROVENANCE_MISMATCH` | Index hash mismatch | `Provenance mismatch: {detail}` |

---

## 8. Amendment

### 8.1 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-06 | Initial release |

### 8.2 Future Versions

- **v1.1:** Reject `validator_final_shipped` role (cutoff anchor)

---

*This protocol was created under LifeOS governance. Changes require Council review (CT-2).*
