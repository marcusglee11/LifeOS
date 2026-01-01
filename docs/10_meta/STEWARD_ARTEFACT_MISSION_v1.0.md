# STEWARD_ARTEFACT_MISSION_v1.0

## Description
Persist a canonical LifeOS artefact into the repo, update registry/index, commit, and sync to the brain mirror for ChatGPT.

## Inputs
- `key` (string): Registry key (e.g., "programme_charter")
- `title` (string): Human-readable filename base (e.g., "PROGRAMME_CHARTER_v1.0")
- `type` (enum string): "governance" | "runtime" | "template" | "council" | "alignment" | "other"
- `track` (enum string): "core" | "fuel" | "plumbing"
- `relative_repo_path` (string): Path under docs (e.g., "00_foundations/PROGRAMME_CHARTER_v1.0.md")
- `version` (string): Version string (e.g., "1.0")
- `content` (string): Full markdown content of the doc
- `status` (string, optional): Default "active"

## Environment
- `LIFEOS_REPO_ROOT`: Root of the LifeOS git repository.
- `LIFEOS_BRAIN_MIRROR_ROOT`: Root of the Google Drive mirror.

## Steps

### 1. Resolve Paths
- Compute `repo_root`, `brain_root`, `docs_root`.
- `registry_path` = `docs/00_foundations/CANONICAL_REGISTRY.yaml`
- `index_path` = `docs/INDEX.md` (or current index)

### 2. Write Artefact
- Write `content` to `docs/<relative_repo_path>`.
- Ensure parent directories exist.

### 3. Update Index
- Read `index_path`.
- Insert entry into "## Canonical Artefacts" (or appropriate section manifest).
- Format: `- [{title}]({relative_repo_path}) — {type}/{track} v{version}`

### 4. Upsert Registry
- Read `registry_path`.
- Update/Create `artefacts.<key>`:
    - `title`: input.title
    - `type`: input.type
    - `track`: input.track
    - `version`: input.version
    - `status`: input.status
    - `repo_path`: input.relative_repo_path
    - `drive_path`: input.relative_repo_path
    - `updated_at`: current_timestamp

### 5. Git Commit & Push
- `git add docs`
- `git commit -m "chore: steward {key} v{version}"`
- `git push`

### 6. Sync to Brain
- Run `python docs/scripts/sync_to_brain.py`

### 7. Summary
- Emit summary confirming stewardship and sync.
