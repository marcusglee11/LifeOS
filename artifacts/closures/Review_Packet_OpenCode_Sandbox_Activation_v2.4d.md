# Delivery Context: OpenCode Sandbox Activation v2.4d

**Date**: 2026-01-13
**Strategy**: Option A (Self-Contained Delivery Wrapper)

## 1. Overview

This package (`Bundle_OpenCode_Sandbox_Activation_v2.4d_delivery.zip`) acts as a secure shipping container. It delivers the **Canonical Closure Bundle** together with its **Detached Digest Sidecar** to ensure the sidecar travels reliably with the artifact.

## 2. Inventory

- `payload/Bundle_OpenCode_Sandbox_Activation_v2.4.zip`
  - **Canonical Record**: This is the immutable closure bundle. Verified by the sidecar.
- `payload/Bundle_OpenCode_Sandbox_Activation_v2.4.zip.sha256`
  - **Detached Digest**: The verification truth. Contains the SHA-256 of the bundle zip.
- `payload/VERIFY.txt`
  - **Instructions**: Commands to cryptographically verify the bundle using the sidecar.

## 3. Verification Integrity

To verify the integrity of the shipped code:

1. Extract this wrapper zip.
2. Verify the inner bundle matches the sidecar (see `VERIFY.txt`).
3. Check the internal `audit_report.md` (inside the inner bundle) for the passing audit status.

## 4. Updates in v2.4

- **Sidecar**: Fully compliant `HASH  FILENAME` format.
- **Evidence**: Full-fidelity capture (no truncation) and strict validation.
