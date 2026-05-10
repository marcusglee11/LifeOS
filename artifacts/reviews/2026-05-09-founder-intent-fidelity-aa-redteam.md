# AA Red-Team Review — Founder Intent Fidelity Gate v0.2

Review target: `/home/cabra/LifeOS/artifacts/plans/2026-05-09-founder-intent-fidelity-gate-spec-and-plan-v0.2.md`
Reviewer: Claude Code as AA reviewer, read-only
Session: `779ea88a-c3a4-4018-b1d7-828dcea62f06`
Model: `opus`
Date: 2026-05-09
Verdict: `amend` — architecture sound, P0 issues remain
Cost observed: `$0.43519825`

## P0 findings

1. **“Polish” warning-only reproduces v120.** If destructive/absence feedback is present, polish/clean-up/rework language must be treated as blocking softening/inversion, not warning-only.
2. **Deterministic extractor claim is overstated.** Inversion checks require semantic equivalence or a closed/tested lexicon. Paraphrases like “retain the structure” can bypass phrase tables.
3. **Conductor identity is undefined in Marcus-solo loop.** Worker/self-attestation can collapse into conductor verification unless actor/session separation is specified.

## P1 findings

- Source discovery remains free-form; canonical commands and output hashes are needed.
- Stale-lesson precedence has no defined lesson corpus/producer.
- Brief artifact type is undefined.
- Bypass expiry is schema-only and unenforced.
- No audit-only dogfood graduation criteria.

## Required amendments accepted into v0.3

- Promote polish/clean-up/rework to blocking when co-occurring with absence/destructive intent.
- Add closed versioned lexicon and state semantic paraphrase limits explicitly.
- Add conductor identity/session separation rule.
- Add canonical discovery commands and output byte hashes.
- Define lesson corpus or remove stale lesson checker from v0.3 core.
- Add exact `brief_type` and `brief_uri` requirements.
- Cap bypass duration and require registry/sweep.
- Add false-positive fixtures for negation, historical, hypothetical, third-party quote.
- Add dogfood graduation metrics before runtime blocking.
- Pull forward raw-source-hash interface for future compression quarantine.
