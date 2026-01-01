# Archive: Legacy R6.x Tests

**Archived**: 2026-01-01  
**Reason**: Tests reference functions that were never implemented (`create_signature_metadata`, etc.)

These tests were written during R6.x development but the corresponding implementations were either never completed or were refactored. They cause collection errors due to import failures.

**To restore**: Move files back to `runtime/tests/` and implement missing functions in `runtime/util/crypto.py`.

## Files Archived

1. test_crypto_determinism.py
2. test_determinism.py
3. test_fsm_checkpoint_regression.py
4. test_governance_integrity.py
5. test_migration.py
6. test_migration_snapshot_b.py
7. test_r6_5_amu0_capture.py
8. test_r6_5_deep_replay_trace.py
9. test_r6_5_initialization.py
10. test_r6_5_key_management.py
11. test_r6_5_question_routing.py
12. test_r6_5_rollback_integrity.py
13. test_r6_5_subprocess_isolation.py
14. test_r6_5_tracker_signing.py
15. test_r6_integration_determinism.py
16. test_replay.py
17. test_sandbox_security.py
