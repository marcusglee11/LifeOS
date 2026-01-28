---
description: Standard Operating Procedure for Closing a Mission
---

# Mission Closure Workflow

This workflow enforces the strict protocol for closing a mission in LifeOS. It is designed to prevent state drift by ensuring the system-of-record (`LIFEOS_STATE.md`) is always updated *before* the agent considers the task done.

## 1. Finalize Deliverables

- [ ] Ensure all code changes are committed.
- [ ] Ensure `Review_Packet` is created/updated (vX.X).
- [ ] Ensure `Closure_Record` is created (if applicable).
- [ ] Verify all SHA256 hashes are full-length (no truncation).

## 2. Verify Artifacts

- [ ] Run `scripts/closure/validate_closure_bundle.py` (if applicable).
- [ ] Confirm all artifacts are in the correct `artifacts/` subdirectories.

## 3. Update System-of-Record (CRITICAL)

- [ ] Open `docs/11_admin/LIFEOS_STATE.md`.
- [ ] **Move** the current "IMMEDIATE NEXT STEP" item to the "RECENT ACHIEVEMENTS" section.
  - [ ] Mark it as **[CLOSED]**.
  - [ ] Add the date and a 1-line outcome summary.
  - [ ] Link the canonical closure artifact (`CLOSURE_...`) or primary evidence.
- [ ] **Select** the next item from the "ROADMAP" or "BACKLOG".
- [ ] **Promote** it to the "IMMEDIATE NEXT STEP" section.
  - [ ] Set "Objective", "Status" (to IN_PROGRESS/PLANNING), and "Owner".
  - [ ] Write a clear "Context" and "Instructions" prompt for the next agent.
  - [ ] List "Required Artifacts" (Policy, Design, etc.) needed for that task.
- [ ] **Verify** the Roadmap and Backlog are still accurate.
- [ ] **STOP**: Do not proceed until this file is saved. Enforce that the "Prompt" is ready for the next session.

## 4. Notify User

- [ ] Send final `notify_user` message summarizing the closure and referencing the updated state file.
