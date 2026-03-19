# COO Promotion Council Provider Handoff

Date: 2026-03-19
Repo: `/mnt/c/Users/cabra/Projects/LifeOS`
Branch: `main`

## Mission

Run the **Council V2 review for the COO unsandboxed production L3 promotion** and get it unstuck at the live-provider stage.

This is not generic provider debugging. The provider validation is only in service of the actual governance step:

- validate available council members
- run the promotion Council review
- if Council returns `Accept`, continue toward manual approval and the remaining promotion gates

## Promotion Context

The underlying promotion work was already merged to `main`.

Relevant merged state:

- promotion infrastructure for COO unsandboxed prod L3 is on `main`
- Council V2 promotion workflow was also merged to `main`
- build branch was already closed and merged earlier

The promotion-specific Council workflow lives at:

- [run_council_review_coo_unsandboxed_promotion.py](/mnt/c/users/cabra/projects/lifeos/scripts/workflow/run_council_review_coo_unsandboxed_promotion.py)
- [coo_unsandboxed_prod_l3.ccp.yaml](/mnt/c/users/cabra/projects/lifeos/artifacts/council_reviews/coo_unsandboxed_prod_l3.ccp.yaml)

Earlier implementation/testing handoff:

- [2026-03-19-council-v2-coo-unsandboxed-promotion-l3-handoff.md](/mnt/c/users/cabra/projects/lifeos/artifacts/handoffs/2026-03-19-council-v2-coo-unsandboxed-promotion-l3-handoff.md)

Earlier promotion handoff:

- [2026-03-18-coo-unsandboxed-promotion-l3-handoff.md](/mnt/c/users/cabra/projects/lifeos/artifacts/handoffs/2026-03-18-coo-unsandboxed-promotion-l3-handoff.md)

## Current Blocker

The blocker is the **live Council run**, not the promotion code.

The Council workflow logic was already narrowed earlier:

- there had been a runner bug around `council_provider_overrides`
- that issue was narrowed/fixed locally during the previous pass
- the remaining blocker moved to provider availability/auth/runtime health

So the current task for Claude Code is:

1. validate which council providers are actually healthy in Claude Code’s runtime
2. choose a live provider mix that works
3. run the COO promotion Council review for real

## What Was Verified In This Session

### Codex

Confirmed usable:

```bash
codex login status
```

reported logged in.

This is the only provider positively confirmed healthy from this session.

### Gemini

Gemini has local OAuth material:

- `~/.gemini/oauth_creds.json`
- `~/.gemini/google_accounts.json`

Observed active account:

- `garfieldlee11@gmail.com`

But runtime probes timed out:

```bash
timeout 15 gemini -m gemini-2.5-flash -p 'reply with exactly OK'
```

Interpretation:

- Gemini is not missing auth
- Gemini is not yet proven runtime-healthy
- Claude Code should validate Gemini directly before relying on it as a council member

### Claude Code

I could not verify `claude_code` live from this Codex-driven WSL session.

What was proven:

- browser auth flow works
- WSL localhost callback flow works
- returned `code` and `state` matched
- callback endpoint accepted the authorization code and returned the normal success redirect

But the CLI always failed after callback acceptance with:

```text
Login failed: Request failed with status code 400
```

Important interpretation:

- this does **not** prove Claude Code itself cannot use `claude_code`
- it proves only that I could not establish `claude_code` auth from this Codex-driven session
- Claude Code should validate `claude_code` from inside Claude Code’s own runtime before removing it from council routing

## What Claude Code Should Do

Claude Code should treat provider validation as part of the live COO promotion Council mission.

Recommended sequence:

1. validate `claude_code` directly in Claude Code’s own runtime
2. validate `gemini` with a real short probe
3. keep `codex` as the already-confirmed fallback/member
4. choose a provider mix that actually works live
5. run the promotion Council review

## The Actual Goal

The actual goal is:

- execute the promotion Council for COO unsandboxed prod L3
- not just benchmark providers in isolation

So after provider validation, Claude Code should immediately use the healthy providers to run:

- `scripts/workflow/run_council_review_coo_unsandboxed_promotion.py`

If the promotion review succeeds with `Accept`, the next downstream flow remains:

1. manual approval
2. ruling stewardship into `docs/01_governance/`
3. `gate3_prepare.py`
4. remaining promotion gates

## Suggested Provider Framing For Claude Code

Do not assume my failed `claude auth login` attempt is final authority on `claude_code`.

Instead:

- validate `claude_code` directly
- validate whether `gemini` can serve as a council member
- use `codex` as the known-good baseline

Practical target:

- best case: `claude_code` + `codex` + `gemini`
- acceptable fallback: `claude_code` + `codex`
- last-resort fallback: mostly `codex`, if governance standards still permit the run

## Relevant Files

- [config/models.yaml](/mnt/c/users/cabra/projects/lifeos/config/models.yaml)
- [run_council_review_coo_unsandboxed_promotion.py](/mnt/c/users/cabra/projects/lifeos/scripts/workflow/run_council_review_coo_unsandboxed_promotion.py)
- [multi_provider.py](/mnt/c/users/cabra/projects/lifeos/runtime/orchestration/council/multi_provider.py)
- [test_council_promotion_mock.py](/mnt/c/users/cabra/projects/lifeos/runtime/tests/orchestration/council/test_council_promotion_mock.py)
- [coo_unsandboxed_prod_l3.ccp.yaml](/mnt/c/users/cabra/projects/lifeos/artifacts/council_reviews/coo_unsandboxed_prod_l3.ccp.yaml)

## Repo State

No code changes were landed during this auth-debugging pass.

This handoff is operational and mission-oriented:

- original purpose: COO unsandboxed promotion Council review
- immediate task: Claude Code validates providers in its own runtime and then uses that validation to run the Council

