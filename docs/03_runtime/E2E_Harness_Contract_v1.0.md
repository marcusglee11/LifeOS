# E2E Harness Contract v1.0 — Resolved Conventions

This document defines the binding conventions for the Tier-3 Mission CLI End-to-End (E2E) Sanity Harness.

Broadly aligned with the **fail-closed** and **prove-or-skip** posture.

## 1. Entrypoint Selection

- The harness **MUST** verify the selected entrypoint mode (e.g., `lifeos` vs `python -m`).
- `lifeos` script usage is the preferred canonical mode.
- `python -m runtime.cli` fallback is allowed **ONLY if blessed** by an explicit repo artefact (e.g., specific wording in `pyproject.toml` or `docs/`).
- If no blessing is found and `lifeos` is unavailable in the environment, the harness must **BLOCK**.

## 2. Test Execution Posture (Prove-or-Skip)

### 2.1 Smoke Case (E2E-1)

- Always run against `build_with_validation --params '{"mode":"smoke"}'`.
- Must match expected exit code 0 and valid JSON wrapper.

### 2.2 Determinism (E2E-2)

- Enforced **ONLY if** a determinism guarantee and a machine-parseable volatile leaf-field set are extractable from the repo.
- If unproven: **SKIP** with reason.
- Prevents hardcoded volatile lists and CI flakes.

### 2.3 Negative Case (E2E-3)

- Run **ONLY if** a concrete failing invocation and its expected exit code are explicitly extractable from repo test artifacts.
- If unproven: **SKIP** with reason.
- Ensures negative tests are grounded in proven failure modes.

## 3. Audit Controls

- **Repo-Root Anchoring**: All harness subprocesses must force `cwd=repo_root`.
- **Evidence Lifecycle**: Evidence is collected in `<out_root>/mission_cli_e2e/<run_id>/`.
- **Integrity**: `summary.json` must be disk-anchored via SHA256 hashes of all evidence files (including itself and `search_log.txt`).
- **Coherence**: No `ok=false` wrapper validation results without explicit, readable error markers.

---
**Standard**: G-CBS v1.1
**Governance**: Tier-3 dogfooding loop.
