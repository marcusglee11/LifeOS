---
packet_type: PLAN_ARTIFACT
version: 0.3
mission_name: Founder Intent Fidelity Gate
status: REVIEW_INTEGRATED_READY_FOR_IMPLEMENTATION_PLANNING
date: 2026-05-09
author: Hermes COO
review_state:
  openclaw: integrated
  aa: integrated
source_reviews:
  openclaw: artifacts/reviews/2026-05-09-founder-intent-fidelity-openclaw-redteam.md
  aa: artifacts/reviews/2026-05-09-founder-intent-fidelity-aa-redteam.md
supersedes:
  - artifacts/plans/2026-05-09-founder-feedback-fidelity-gate-spec-and-plan-v0.1.md
  - artifacts/plans/2026-05-09-founder-intent-fidelity-gate-spec-and-plan-v0.2.md
---

# Founder Intent Fidelity Gate — Spec and Implementation Plan v0.3

## 1. Raison d'être

LifeOS exists to convert Marcus's CEO intent into execution without making Marcus act as middleware. The Hermes production benchmark exposed a control-plane failure: explicit destructive feedback was softened into preservation-biased implementation. The output polished instead of removed.

The gate prevents a broader class of failures: active CEO intent being transformed before execution.

Examples:

- “remove/delete/start over” becomes “preserve/polish”;
- “do not implement yet” becomes “start work”;
- “ask me before changing channels” becomes “route automatically”;
- “keep private” becomes “post externally”;
- “minimum viable” becomes overbuilt;
- “no automation” becomes unattended automation.

## 2. Core thesis

Model swaps do not fix source-fidelity failures. LifeOS needs an auditable pre-handoff gate proving that the brief handed to a worker/EA/build loop preserves active CEO intent.

## 3. Authority clause

A fidelity pass is not implementation approval. It only certifies that the checked brief preserves active source intent. Dispatch, repo mutation, runtime mutation, external/public sends, credentials, destructive actions, and CEO-gated actions still require their normal gates.

Reviewer output is evidence only. OpenClaw, AA, and EAs do not create authority, override CEO intent, or verify their own work.

## 4. Conductor identity and separation

For this gate:

- **Brief author:** actor/session/tool that produced the brief under check.
- **Source collector:** actor/session/tool that collected source material.
- **Deterministic checker:** local code that emits `intent_fidelity_report.v1`.
- **Reviewer:** OpenClaw/AA/EA peer review; evidence only.
- **Conductor verifier:** the session responsible for final LifeOS truth claim.

Separation invariant:

- The same actor/session that authored the brief cannot be the sole conductor verification for high-risk triggered work.
- Marcus-solo fallback: Hermes may act as conductor only if verification is a separate turn/session from the brief-writing worker/EA, uses direct source readback, records source hashes, and explicitly states `brief_author_session != conductor_verification_session` or `human_verified: true`.
- Worker self-attestation cannot set `handoff_candidate: true`.

## 5. Scope and non-goals

### In scope for v0.3 implementation

- Inert/local source intent manifest.
- Versioned intent lexicon.
- Deterministic extraction against that lexicon.
- Brief-vs-source fidelity report.
- Conductor verification artifact with no implementation authority.
- Dry-run CLI.
- False-positive and false-negative fixtures.

### Out of scope / deferred

- Runtime handoff blocking.
- Production model-routing changes.
- Full compression quarantine implementation.
- External/public writes.
- Credentials or automation activation.
- Governance doc ratification.

Compression follow-on must consume the raw-source-hash interface defined here; it must not renegotiate source identity.

## 6. Precedence order

Highest first:

1. Current explicit CEO/founder instruction in the active work item or named feedback source.
2. Current issue/PR acceptance criteria and latest explicit owner/conductor comment.
3. Ratified architecture/governance documents.
4. Current implementation plan/build packet.
5. Older lessons, memory, style guides, prior preferences.
6. Model priors and generic “best practice”.

Lower-precedence material may add constraints only when it does not weaken, invert, omit, or reframe higher-precedence intent.

Stale-lesson enforcement is deferred unless a concrete lesson corpus path is supplied. v0.3 must not emit fake `stale_lessons_violating: []` as if lessons were checked.

## 7. Trigger policy

### Full gate required

Run the full gate when any condition is true:

- Current CEO/founder feedback is present and high-authority.
- Feedback contains destructive, absence, privacy, approval, channel, automation, pause, or reversibility constraints.
- A worker/EA/autonomous build loop will receive a summarised brief.
- A compression or summary layer sits between source and execution.
- The task follows prior bad output/correction.

### Warning-only terms

These are warning-only only when no blocking intent class appears in the same source set:

- simplify
- minimal
- not this
- whole surface

These become blocking softening/inversion terms when any absence/destructive source intent exists in the same source set:

- polish
- clean up
- rework
- iterate
- preserve
- retain
- maintain existing
- keep most
- leave structure

Index-case rule: if source says remove/delete/hide/start over, any brief framing the work as polish/cleanup/iteration is a blocking inversion unless it explicitly preserves the absence requirement.

### No gate required

Skip for routine low-risk edits with no high-authority feedback transformation, no worker handoff, no summary/compression layer, and deterministic local verification.

## 8. Intent classes v0.3

1. **Absence/destructive:** remove, delete, hide, strip, eliminate, no longer show, start from scratch.
2. **Pause/no-execution:** do not implement yet, wait, pause, hold, stop.
3. **Approval-before-action:** ask me first, before changing X, needs approval.
4. **Privacy/externality:** keep private, do not send, no public post, internal only.
5. **Reversibility:** reversible only, no destructive cleanup, no irreversible action.
6. **Automation boundary:** no automation, no unattended trigger, supervised only.
7. **Channel/source authority:** use GitHub only, use this doc, do not create another channel.
8. **Scope minimisation:** minimum viable, no overbuilding, only X.
9. **Softening/inversion:** polish, clean up, iterate, retain, preserve, maintain, keep most, leave structure, when conflicting with a blocking class.

## 9. Determinism and lexicon model

v0.3 is deterministic only within a closed, versioned lexicon.

Required data file:

- `runtime/data/intent_lexicon_v1.json`

It must define:

- intent class;
- phrase patterns;
- blocking vs warning default;
- inversion terms;
- negation/quote guards;
- examples;
- version.

Semantic paraphrase beyond the lexicon is out of scope for v0.3. If the checker detects low-confidence conflict or unsupported paraphrase, it must emit `requires_conductor_review`, not silently pass.

Determinism invariant: running the extractor twice on the same source bytes and same lexicon version must produce identical `IntentSpan`s.

## 10. Source discovery rules

### GitHub work

Canonical discovery command shape:

```bash
gh issue view <issue> --repo <owner/repo> --json number,title,body,comments,labels,state,url,updatedAt

gh pr view <pr> --repo <owner/repo> --json number,title,body,reviews,comments,files,headRefOid,baseRefName,url,updatedAt
```

If linked PRs/issues are discovered, their readback commands must also be recorded.

Manifest must record:

- exact command(s);
- command output sha256 hash;
- cutoff timestamp;
- actor/session;
- which source classes were excluded and why.

### Local/Obsidian/Drive work

Canonical discovery must record:

- exact path/URI;
- retrieval method;
- raw bytes/content hash;
- last-modified timestamp if available;
- source-of-source hash for transcripts or derived text.

Named high-authority source missing = fail closed unless Marcus/conductor explicitly marks it non-required.

Completeness invariant: triggered work must include at least one externally retrieved source (`retrieval_method != self`) unless the source is the current chat message from Marcus and that message hash is recorded.

## 11. Brief target invariant

The gate must name exactly what artifact is being checked.

Allowed `brief_type` values:

- `worker_prompt`
- `dispatch_packet`
- `build_packet`
- `implementation_plan`
- `pr_body`
- `issue_comment`
- `closure_packet`
- `other`

A pass for one brief does not transfer to another brief unless hashes match.

## 12. Required artifacts

### `intent_source_manifest.v1`

```yaml
schema_version: intent_source_manifest.v1
work_item_id: string
lexicon_version: string
created_at: iso8601
created_by: conductor|worker|ea|tool
source_discovery:
  mode: github|local_file|google_doc|obsidian|chat|mixed
  commands_or_uris: []
  command_output_hashes_sha256: []
  cutoff_timestamp: iso8601
  completeness_claimed_by: conductor|worker|ea|tool
sources:
  - source_id: string
    source_type: issue_body|issue_comment|pr_review|pr_comment|local_file|google_doc|obsidian_note|chat|plan|ratified_doc|transcript
    uri: string
    retrieved_at: iso8601
    retrieval_method: string
    content_hash_sha256: string
    source_of_source_hash_sha256: string|null
    authority_tier: current_ceo_instruction|acceptance_criteria|ratified_doc|plan|lesson|memory|other
    extracted_intents:
      - intent_class: absence|pause|approval_before_action|privacy|reversibility|automation_boundary|channel_authority|scope_minimisation|softening_inversion|other
        phrase: string
        line_or_offset: string
        surrounding_context: string
        blocking_strength: blocking|warning|requires_conductor_review
missing_sources:
  - expected_source: string
    reason_missing: string
    disposition: fail_closed|not_required
```

### `intent_fidelity_report.v1`

Deterministic/tool findings only.

```yaml
schema_version: intent_fidelity_report.v1
work_item_id: string
brief_type: worker_prompt|dispatch_packet|build_packet|implementation_plan|pr_body|issue_comment|closure_packet|other
brief_uri: string
brief_hash_sha256: string
source_manifest_uri: string
decision: pass|fail_closed|requires_ceo_clarification|requires_conductor_review|warning_only
checks:
  source_coverage:
    status: pass|fail
    missing_required_sources: []
  verbatim_preservation:
    status: pass|fail
    source_intents_total: integer
    source_intents_preserved_or_mapped: integer
    missing_intents: []
  intent_inversion:
    status: pass|fail
    inversions: []
  hedge_or_softening:
    status: pass|warn|fail
    findings: []
  contradiction_detection:
    status: pass|fail|requires_ceo_clarification
    contradictions: []
  false_positive_fixtures_passed: integer
  determinism_check:
    status: pass|fail
```

### `intent_review_report.v1`

Reviewer evidence only.

```yaml
schema_version: intent_review_report.v1
work_item_id: string
reviewer_surface: openclaw|aa|ea|other
reviewer_session: string
verdict: reject|amend|approve
findings:
  - severity: p0|p1|p2|note
    title: string
    recommendation: string
authority_note: reviewer_output_is_evidence_only
```

### `conductor_fidelity_verification.v1`

Only this artifact can mark the checked brief as a handoff candidate.

```yaml
schema_version: conductor_fidelity_verification.v1
work_item_id: string
brief_type: string
brief_hash_sha256: string
brief_author_session: string
conductor_verification_session: string
source_manifest_hash_sha256: string
fidelity_report_hash_sha256: string
conductor_independently_confirmed: true
fidelity_status: preserved_intent|not_preserved|needs_clarification|requires_review|warning_only
handoff_candidate: boolean
implementation_authority_granted: false
required_next_gate: none|dispatch_gate|ceo_clarification|ceo_approval|repo_gate|runtime_gate
forbidden_next_steps:
  - implementation_without_reload
  - additive_or_polish_framing_if_source_requires_absence
  - reviewer_output_as_authority
  - compression_as_canonical_memory
verified_by: conductor
verified_at: iso8601
```

## 13. Brief construction requirements

Triggered briefs must include:

```markdown
## Source Intent — Verbatim Requirements
- `<exact phrase>` — source: `<source_id>` — intent class: `<class>` — implementation meaning: `<plain-language requirement>`

## Absence / Boundary Requirements
- Requirement: `<what must be absent/forbidden/not done>`
- Verification: `<how absence or boundary will be checked>`

## Explicit Non-Softening Clause
- This brief does not convert removal/deletion/absence intent into polish, cleanup, iteration, preserve, retain, or additive-only work.

## Contradictions / Ambiguities
- `<none>` or exact contradiction requiring CEO clarification

## Handoff Boundary
- Fidelity pass does not grant implementation authority.
- Required next gate: `<dispatch/repo/CEO/runtime/etc>`
```

## 14. Gate algorithm

1. Discover active sources using canonical commands/URIs.
2. Hash raw command output/source bytes.
3. Load `intent_lexicon_v1.json`.
4. Extract intent spans.
5. Run determinism check: same bytes + lexicon => same spans.
6. Classify spans as blocking, warning, or requires conductor review.
7. Identify the exact `brief_type`, `brief_uri`, and brief hash.
8. Check verbatim preservation or explicit intent mapping.
9. Check inversion:
   - preserve/additive-only/polish/cleanup/iteration against absence/destructive intent;
   - implement/start against pause intent;
   - external/public against privacy intent;
   - autonomous/unattended against no-automation intent;
   - new channel/source against channel-authority intent.
10. Check negation, historical, hypothetical, and third-party quote guards to reduce false positives.
11. Emit deterministic report.
12. Conductor verifies source completeness and report decision independently from reviewer verdicts.
13. Only conductor verification may mark `handoff_candidate: true`.

## 15. Bypass policy

Bypass is not allowed for privacy/externality, destructive/irreversible, automation-boundary, or approval-before-action blocking classes without CEO approval.

Conductor-level bypass is limited to warning-only or known false-positive cases.

```yaml
schema_version: intent_fidelity_bypass.v1
work_item_id: string
requested_by: string
authorized_by: conductor|ceo
reason: string
sources_skipped: []
risk_accepted: string
scope: string
expires_at: iso8601 # must be <= 24h after created_at
single_use: true
not_authorized_for:
  - external_send
  - runtime_activation
  - credential_change
  - destructive_cleanup
```

Implementation must include a local bypass registry and expiry check before any bypass is honored.

## 16. Audit-only graduation criteria

Runtime blocking remains forbidden until an audit-only dogfood report shows:

- at least 20 real brief/source pairs reviewed;
- at least 3 destructive/absence cases;
- at least 3 non-destructive boundary cases;
- false-positive block rate ≤ 15%;
- false-negative rate 0 on seeded known-bad cases;
- at least one conductor-confirmed useful catch or a clear decision that the gate is too low-signal;
- no unbounded CEO-clarification spam pattern.

## 17. Implementation plan v0.3 — inert/local only

### Task 1: Fixture corpus

Create:

- `runtime/tests/fixtures/intent_fidelity/v120_source.md`
- `runtime/tests/fixtures/intent_fidelity/v120_bad_brief.md`
- `runtime/tests/fixtures/intent_fidelity/v120_good_brief.md`
- `runtime/tests/fixtures/intent_fidelity/non_destructive_source.md`
- `runtime/tests/fixtures/intent_fidelity/non_destructive_bad_brief.md`
- `runtime/tests/fixtures/intent_fidelity/false_positive_negation.md`
- `runtime/tests/fixtures/intent_fidelity/false_positive_historical.md`
- `runtime/tests/fixtures/intent_fidelity/false_positive_hypothetical.md`
- `runtime/tests/fixtures/intent_fidelity/false_positive_third_party_quote.md`

Verification: fixtures cover all intent classes and false-positive guards.

### Task 2: Versioned lexicon

Create:

- `runtime/data/intent_lexicon_v1.json`
- `runtime/tests/test_intent_lexicon.py`

Verification:

```bash
pytest runtime/tests/test_intent_lexicon.py -q
```

Must include polish/cleanup/rework as blocking inversion terms when absence/destructive intent exists.

### Task 3: JSON schemas

Create:

- `schemas/intent_source_manifest_v1.json`
- `schemas/intent_fidelity_report_v1.json`
- `schemas/intent_review_report_v1.json`
- `schemas/conductor_fidelity_verification_v1.json`
- `schemas/intent_fidelity_bypass_v1.json`

Test:

- `runtime/tests/test_intent_fidelity_schemas.py`

Verification:

```bash
pytest runtime/tests/test_intent_fidelity_schemas.py -q
```

### Task 4: Extractor

Create:

- `runtime/orchestration/intent_fidelity.py`
- `runtime/tests/test_intent_fidelity_extractor.py`

Core API:

```python
def extract_intents(text: str, source_id: str, lexicon: IntentLexicon) -> list[IntentSpan]:
    ...
```

Verification: boundary matching, case folding, deterministic rerun, false-positive guards.

### Task 5: Manifest builder

Modify/create:

- `runtime/orchestration/intent_fidelity.py`
- `runtime/tests/test_intent_source_manifest.py`

Verification: missing named high-authority source fails closed; present source includes raw hash, retrieval method, source-of-source hash when derived, extracted intents.

### Task 6: Fidelity checker

Modify/create:

- `runtime/orchestration/intent_fidelity.py`
- `runtime/tests/test_intent_fidelity_checker.py`

Verification:

- v120 bad brief fails because polish/additive/preserve framing softens destructive intent;
- v120 good brief passes;
- non-destructive boundary inversions fail;
- ambiguous broad terms warn only when no blocking class exists;
- unsupported paraphrase emits `requires_conductor_review`.

### Task 7: Conductor verification and bypass registry

Create:

- `runtime/receipts/intent_fidelity.py`
- `runtime/tests/test_intent_fidelity_verification.py`
- `runtime/tests/test_intent_fidelity_bypass.py`

Verification:

- `implementation_authority_granted` always false;
- `handoff_candidate` true only with separate conductor verification;
- bypass expires ≤24h and is single-use;
- bypass cannot cover CEO-only classes without CEO approval ref.

### Task 8: CLI dry-run

Add after codebase discovery:

```bash
python3 -m lifeos intent-fidelity check --source <source.md> --brief <brief.md> --brief-type worker_prompt --json
```

Verification:

- bad brief exits nonzero with JSON report;
- good brief exits zero;
- no repo/runtime mutation.

## 18. Deferred sibling work

1. Runtime handoff blocking after audit-only graduation.
2. Compression quarantine consuming `source_of_source_hash_sha256` and source manifest hashes.
3. Real-input model variance bench over LifeOS source/brief pairs.
4. Governance/doc promotion after implementation evidence.

## 19. Review integration summary

OpenClaw found v0.1 over-fitted and too broad. v0.2 broadened to intent fidelity, separated authority, added source discovery, warning-only mode, and deferred compression/routing.

AA found v0.2 still had P0s: polish warning-only reproduced v120, deterministic semantics were overstated, and conductor identity was undefined. v0.3 fixes those by promoting polish/cleanup/rework to blocking in destructive contexts, requiring a versioned lexicon with determinism tests, adding conductor/session separation, pinning discovery hashes, capping bypass, and adding audit-only graduation metrics.

## 20. COO recommendation

Implement only v0.3 inert/local tasks. Do not activate runtime blocking, compression quarantine, or model-routing changes until audit-only graduation criteria pass and a separate CEO/dispatch gate approves the next phase.
