# Validation Implementation Notes (v1.1)

## 1. Canonical Packet Hashing (Lineage Verification)

To verify `COUNCIL_APPROVAL_PACKET` -> `COUNCIL_REVIEW_PACKET` lineage:

1.  **Extract Packet Data**:
    *   Parse YAML or Markdown Frontmatter into a Python Dictionary.
2.  **Canonicalize**:
    *   Re-serialize the dictionary to a JSON-compatible YAML string.
    *   **Rules**:
        *   `sort_keys=True` (Deterministic field ordering)
        *   `allow_unicode=True` (UTF-8 preservation)
        *   `width=Infinity` (No wrapping/newlines for structure)
3.  **Hash**:
    *   Apply `SHA-256` to the UTF-8 encoded bytes of the canonical string.
4.  **Verify**:
    *   The `subject_hash` in the Approval packet MUST match this calculated hash.

## 2. Validation Logic
*   **Schema-Driven**: The validator loads rules (limits, taxonomy, payload requirements, signature policy) from `docs/02_protocols/lifeos_packet_schemas_v1.1.yaml` at runtime.
*   **Fail-Closed**: Any unknown field, schema violation, or security check failure exits with a non-zero code.
*   **Bundle Validation**: Iterates all files, validates each individually, checks for nonce collisions (Replay), and verifies hash linkage.

## 3. Schema-Driven Enforcement Details
The following parameters are derived from the canonical schema YAML (no hardcoding in validator):

| Parameter | Schema Key Path |
|-----------|-----------------|
| Max Payload Size | `limits.max_payload_size_kb` |
| Max Clock Skew | `limits.max_clock_skew_seconds` |
| Required Envelope Fields | `envelope.required` |
| Optional Envelope Fields | `envelope.optional` |
| Core Packet Types | `taxonomy.core_packet_types` |
| Deprecated Packet Types | `taxonomy.deprecated_packet_types` |
| Payload Allow/Required | `payloads.<packet_type>.allow`, `.required` |
| Signature Policy (Non-Draft) | `signature_policy.require_for_non_draft` |
| Signature Policy (Types) | `signature_policy.require_for_packet_types` |

**Flat Frontmatter Model**:
- `ALLOWED_KEYS(ptype)` = `envelope.required` + `envelope.optional` + `payloads.<ptype>.allow`
- `REQUIRED_KEYS(ptype)` = `envelope.required` + `payloads.<ptype>.required`
- Any key not in `ALLOWED_KEYS` → `EXIT_SCHEMA_VIOLATION`
- Any key missing from `REQUIRED_KEYS` → `EXIT_SCHEMA_VIOLATION`
