---
description: Complete stewardship after marking a mission/workstream as DONE or APPROVED
---

# Stewardship Close Workflow

Use this workflow after any mission is marked DONE, APPROVED, or CLOSED.

## Pre-Requisites
- Mission has been marked complete with evidence
- Approval record or Review Packet has been created

## Checklist

### 1. Update LIFEOS_STATE.md
// turbo
```bash
# View current state
cat docs/11_admin/LIFEOS_STATE.md
```

Edit `docs/11_admin/LIFEOS_STATE.md`:
- [ ] Mark relevant WIP slot as "None" or update to next item
- [ ] Update "Current Focus" if focus has shifted
- [ ] Add **[DONE]** tag to the mission in "Next Actions" with evidence ref
- [ ] Update "Thread Kickoff Block" if needed

### 2. Update Programme Roadmap (if Tier-relevant)
If the completed mission is a Tier milestone:
- [ ] Add milestone line under the relevant Tier section in `docs/03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md`
- Format: `**Milestone Completed (YYYY-MM-DD):** <Description>. Evidence: <path>.`

### 3. Update INDEX.md Timestamp
// turbo
```bash
python docs/scripts/generate_strategic_context.py
```

### 4. Regenerate Strategic Corpus
// turbo
```bash
python docs/scripts/generate_strategic_context.py
```

### 5. Archive Superseded Artifacts (if applicable)
- [ ] Move old bundle versions to `artifacts/99_archive/`
- [ ] Move superseded review packets to `artifacts/99_archive/review_packets/`

## Verification
After completing the checklist, confirm:
- [ ] `LIFEOS_STATE.md` reflects current state (no stale WIP)
- [ ] Roadmap has milestone if applicable
- [ ] INDEX.md timestamp is current (within last 10 minutes)

## When to Use
Invoke with: `/stewardship-close`
