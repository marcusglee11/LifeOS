# IMPL_PLAN: OpenCode Sandbox Activation

# Status: APPROVED

# Version: v1.0

# Authors: Antigravity

## 1. Context

LifeOS is transitioning to Phase 3. The "Builder" role requires an expanded sandbox environment to autonomously modify code, run tests, and manage git state. Currently, the OpenCode environment is restricted (Tier-2). We need to activate the Tier-3 capabilities (write access, test execution) under a controlled "sandbox" envelope.

## 2. Goals

- enable `OpenCode` agent to write to `runtime/` and `src/` directories (specifics TBD).
- enable `OpenCode` agent to invoke `pytest`.
- Maintain safety invariants (no network, no random, etc.).

## 3. Proposed Changes

| File | Operation | Description |
|------|-----------|-------------|
| `runtime/envelope/execution_envelope.py` | MODIFY | Update whitelist to allow write operations in sandbox mode. |
| `runtime/tests/test_sandbox_capabilities.py` | CREATE | New test suite to verify sandbox boundaries. |
| `config/agents.yaml` | MODIFY | Enable 'builder' role capabilities. |

## 4. Verification Plan

### 4.1 Automated Tests

- Run `pytest runtime/tests/test_sandbox_capabilities.py` to prove write access works and forbidden access fails.
- Run `scripts/verify_envelope.py` to ensure no regression in safety.

### 4.2 Manual Verification

- Execute a "Hello World" build mission using the new Builder role.

## 5. Risks

- **Risk**: Agent deletes critical files. **Mitigation**: Sandbox should have a "trash" recycle bin or git-only deletes.
- **Risk**: Infinite loops in build. **Mitigation**: Max step counters (already in place).

## 6. Rollback

- Revert `config/agents.yaml`.
- Revert `runtime/envelope/execution_envelope.py`.
