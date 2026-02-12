# Doc Freshness Gate Spec v1.0

**Status:** Active  
**Last Updated:** 2026-02-12

## Purpose

Reduce manual weekly audits by enforcing machine-checkable freshness and contradiction detection for state docs.

## Scope

- `docs/11_admin/LIFEOS_STATE.md`
- `docs/11_admin/BACKLOG.md`
- `docs/11_admin/AUTONOMY_STATUS.md`

## Generator

- Script: `scripts/generate_runtime_status.py`
- Output artifact: `artifacts/status/runtime_status.json`

## Checks

1. Freshness SLA: generated status must be no older than 24 hours.
2. Contradiction checks (v1):
   - OpenClaw installed runtime fact must not conflict with blocker claims in `LIFEOS_STATE.md`.
   - If OpenClaw is installed, backlog must not list install as open P0.
3. Gate mode:
   - Warning mode: active now.
   - Blocking mode: switch at end of Week 2 from plan activation (target date: 2026-02-26).

## CI Integration

1. Run generator in CI.
2. Compare generated facts against canonical docs.
3. Emit warnings now; fail pipeline once blocking mode is activated.

## Stewardship Rule

If any file in scope changes, doc steward mission must:

1. Re-run status generator.
2. Update `docs/INDEX.md` timestamp.
3. Regenerate `docs/LifeOS_Strategic_Corpus.md`.
4. Produce review packet with flattened Appendix A for changed files.
