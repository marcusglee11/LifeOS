---
paths: ["**"]
---
# Git Hygiene

- Before finishing, run `git status` -- the repo must be clean.
- Never leave untracked files. Stage, gitignore, or remove them.
- Always work on a feature branch (build/, fix/, hotfix/, spike/), never directly on main.
- After committing, verify with `git status --porcelain=v1` that the tree is clean.
