---
paths: ["**"]
---
# Git Hygiene

- Before finishing, run `git status` -- the repo must be clean.
- Never leave untracked files. Stage, gitignore, or remove them.
- Always work on a feature branch (build/, fix/, hotfix/, spike/), never directly on main.
- After committing, verify with `git status --porcelain=v1` that the tree is clean.

## Article XIX Hook

A pre-commit hook enforces that no untracked files exist before any commit. This creates a chicken-and-egg situation when Codex WIP is in-flight: the hygiene commit that *resolves* untracked files is itself blocked by those files.

**Exception — use `--no-verify` only when ALL of these are true:**
1. The commit being made IS the resolution (e.g., committing `jarda/` to a spike branch, or adding a `.gitignore` entry).
2. The remaining untracked file(s) belong to a concurrent agent's active WIP (check `stat` timestamps — recent = active).
3. You cannot resolve the blocker by staging that file (wrong semantic context).

**Required:** document the exception in the commit message body with `--no-verify: Article XIX chicken-and-egg exemption. <reason>.`
