# Document Steward Protocol v1.0

**Status**: Active  
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0  
**Effective**: 2026-01-01

---

## 1. Purpose

This protocol defines how canonical documents are created, updated, indexed, and synchronized across all LifeOS locations.

**Document Steward**: The agent (Antigravity or successor) — NOT the human CEO.

Per Constitution v2.0:
- **CEO performs**: Intent, approval, governance decisions only
- **Agent performs**: All file creation, indexing, git operations, syncing

The CEO must never manually shuffle documents, update indices, or run git commands. If the CEO is doing these things, it is a governance violation.

**Canonical Locations**:
1. **Local Repository**: `c:\Users\cabra\Projects\LifeOS\docs`
2. **GitHub**: https://github.com/marcusglee11/LifeOS/tree/main/docs
3. **Google Drive**: https://drive.google.com/drive/folders/1KHUBAOlH6UuJBzGGMevZ27qKO50ebrQ5

---

## 2. Sync Requirements

### 2.1 Source of Truth
The **local repository** is the primary source of truth. All changes originate here.

### 2.2 Sync Targets
Changes must be propagated to:
1. **GitHub** (primary backup, version control)
2. **Google Drive** (external access, offline backup)

### 2.3 Sync Frequency
| Event | GitHub Sync | Google Drive Sync |
|-------|:-----------:|:-----------------:|
| Document creation | Immediate | Same session |
| Document modification | Immediate | Same session |
| Document archival | Immediate | Same session |
| Index update | Immediate | Same session |

---

## 3. Steward Responsibilities

### 3.1 Document Creation
When creating a new document:
1. Create file in appropriate `docs/` subdirectory
2. Follow naming convention: `DocumentName_vX.Y.md`
3. Include metadata header (Status, Authority, Date)
4. Update `docs/INDEX.md` with new entry
5. Update `ARTEFACT_INDEX.json` if governance-related
6. Commit to git with descriptive message
7. Run corpus generator: `python docs/scripts/generate_corpus.py`
8. Push to GitHub
9. (Google Drive syncs automatically, including `LifeOS_Universal_Corpus.md`)

### 3.2 Document Modification
When modifying an existing document:
1. Edit the file
2. Update version if significant change
3. Update `docs/INDEX.md` if description changed
4. Commit to git with change description
5. Run corpus generator: `python docs/scripts/generate_corpus.py`
6. Push to GitHub
7. (Google Drive syncs automatically, including `LifeOS_Universal_Corpus.md`)

### 3.3 Document Archival
When archiving a superseded document:
1. Move to `docs/99_archive/` with appropriate subfolder
2. Remove from `docs/INDEX.md`
3. Remove from `ARTEFACT_INDEX.json` if applicable
4. Commit to git
5. Run corpus generator: `python docs/scripts/generate_corpus.py`
6. Push to GitHub
7. (Google Drive syncs automatically, including `LifeOS_Universal_Corpus.md`)

### 3.4 Index Maintenance
Indices that must be kept current:
- `docs/INDEX.md` — Master documentation index
- `docs/01_governance/ARTEFACT_INDEX.json` — Governance artefact registry
- `docs/LifeOS_Universal_Corpus.md` — Universal corpus for AI/NotebookLM
- Any subsystem-specific indexes

---

## 4. GitHub Sync Procedure

```bash
# Stage all changes
git add -A

# Commit with descriptive message
git commit -m "category: Brief description

- Detailed change 1
- Detailed change 2"

# Push to remote
git push origin <branch>

# If on feature branch, merge to main when approved
git checkout main
git merge <branch>
git push origin main
```

---

## 5. Google Drive Sync Procedure

### 5.1 Automated Sync (Active)

Google Drive for Desktop is configured to automatically sync the local repository to Google Drive.

**Configuration:**
- **Local folder**: `C:\Users\cabra\Projects\LifeOS\docs`
- **Drive folder**: [LifeOS/docs](https://drive.google.com/drive/folders/1KHUBAOlH6UuJBzGGMevZ27qKO50ebrQ5)
- **Sync mode**: Mirror (bidirectional)

**Behavior:**
- All local changes are automatically synced to Google Drive
- No manual upload required
- Sync occurs in background whenever files change

### 5.2 Steward Actions
The steward does NOT need to manually sync to Google Drive. The workflow is:
1. Edit files locally
2. Commit and push to GitHub
3. Google Drive syncs automatically

### 5.3 Verification
To verify sync is working:
- Check Google Drive for Desktop tray icon (green checkmark = synced)
- Spot-check recent file in Drive web interface

---

## 6. Verification Checklist

After any document operation, verify:

- [ ] File exists in correct local path
- [ ] `docs/INDEX.md` is current
- [ ] `ARTEFACT_INDEX.json` is current (if governance)
- [ ] Git commit created
- [ ] Corpus generated (`LifeOS_Universal_Corpus.md` updated)
- [ ] Pushed to GitHub
- [ ] Synced to Google Drive
- [ ] No broken links in related documents

---

## 7. Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Specification | `Name_Spec_vX.Y.md` | `COO_Runtime_Spec_v1.0.md` |
| Protocol | `Name_Protocol_vX.Y.md` | `Governance_Protocol_v1.0.md` |
| Packet | `Name_Packet_vX.Y.md` | `Implementation_Packet_v1.0.md` |
| Template | `Name_TEMPLATE_vX.Y.md` | `ALIGNMENT_REVIEW_TEMPLATE_v1.0.md` |
| Ruling | `Name_Ruling_vX.Y.md` | `Tier1_Hardening_Council_Ruling_v0.1.md` |
| Work Plan | `Name_Work_Plan_vX.Y.md` | `Tier1_Hardening_Work_Plan_v0.1.md` |

---

## 8. Directory Structure

```
docs/
├── 00_foundations/     ← Core principles, Constitution
├── 01_governance/      ← Governance protocols, contracts
├── 02_alignment/       ← (Empty after archive)
├── 03_runtime/         ← Runtime specs, roadmaps, work plans
├── 04_project_builder/ ← Builder specs
├── 05_agents/          ← Agent architecture
├── 06_user_surface/    ← User surface specs
├── 07_productisation/  ← Productisation briefs
├── 08_manuals/         ← Manuals
├── 09_prompts/         ← Prompt templates
├── 10_meta/            ← Meta docs, reviews, tasks
└── 99_archive/         ← Historical documents (immutable)
```

---

## 9. Anti-Failure Constraints

Per Constitution v2.0 and Anti-Failure Operational Packet:

- **Human performs**: Intent, approval, governance decisions only
- **System performs**: File creation, indexing, syncing, commit, push
- **Maximum human steps**: ≤ 2 (approve sync, confirm if needed)

If sync requires more than 2 human steps, the workflow must be automated.

---

**END OF PROTOCOL**
