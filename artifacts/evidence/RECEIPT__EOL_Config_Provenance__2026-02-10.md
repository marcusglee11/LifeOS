# RECEIPT: EOL Config Provenance — 2026-02-10

**Purpose**: Capture pre-existing and post-fix state of EOL/CRLF configuration.

---

## Section 1: Config Provenance (post-fix state)

All commands run from BUILD_REPO root (`C:\Users\cabra\Projects\LifeOS`).

### 1.1 core.autocrlf effective value

```
$ git config --show-origin --get core.autocrlf
file:.git/config        false
```

### 1.2 core.eol effective value

```
$ git config --show-origin --get core.eol
(exit 1 — key not set at any level)
```

### 1.3 Layered autocrlf provenance

```
$ git config --show-origin --system --get core.autocrlf
file:C:/Program Files/Git/etc/gitconfig true

$ git config --show-origin --global --get core.autocrlf
(exit 1 — not set at global level)

$ git config --show-origin --local --get core.autocrlf
file:.git/config        false
```

**Analysis**: System-level config sets `core.autocrlf=true` (Windows Git installer default).
Repo-local override sets `false`, which is the fix applied in commit `e11eae0`.
Local override takes precedence → effective value is `false` ✅

### 1.4 HEAD SHA

```
$ git rev-parse HEAD
c1dc3db5daaf43f672faa6275455c791a0b82059
```

### 1.5 Working tree status

```
$ git status --porcelain=v1
(empty — 0 modified files)
```

---

## Section 2: .gitattributes Application Proof

### 2.1 .py file

```
$ git check-attr -a -- runtime/tools/coo_land_policy.py
runtime/tools/coo_land_policy.py: text: set
runtime/tools/coo_land_policy.py: eol: lf
```

### 2.2 .md file

```
$ git check-attr -a -- docs/02_protocols/EOL_Policy_v1.0.md
docs/02_protocols/EOL_Policy_v1.0.md: text: set
docs/02_protocols/EOL_Policy_v1.0.md: eol: lf
```

### 2.3 .sh file

```
$ git check-attr -a -- runtime/tools/coo_worktree.sh
runtime/tools/coo_worktree.sh: text: set
runtime/tools/coo_worktree.sh: eol: lf
```

### 2.4 .cmd file (CRLF exception)

```
$ git check-attr -a -- spikes/claude-code-mcp-test/node_modules/.bin/claude-code-mcp.cmd
spikes/claude-code-mcp-test/node_modules/.bin/claude-code-mcp.cmd: text: set
spikes/claude-code-mcp-test/node_modules/.bin/claude-code-mcp.cmd: eol: crlf
```

---

## Section 3: CRLF-Required File Safety Check

### 3.1 *.bat files (tracked)

```
$ git ls-files '*.bat'
(empty — zero .bat files tracked)
```

### 3.2 *.cmd files (tracked)

```
$ git ls-files '*.cmd'
spikes/claude-code-mcp-test/node_modules/.bin/claude-code-mcp.cmd
spikes/claude-code-mcp-test/node_modules/.bin/node-which.cmd
```

**Action**: Added `.gitattributes` exception: `*.cmd text eol=crlf`
Verified post-fix: `.cmd` files now get `eol: crlf` attribute (see 2.4 above).

---

## Section 4: Renormalization Proofs

### 4.1 Semantic-diff zero proof (from commit `e11eae0`)

```
$ git diff --cached --ignore-space-at-eol --ignore-cr-at-eol --stat
(empty — zero semantic diff)
```

### 4.2 Renormalization file count

```
$ git diff --name-only e11eae0^..e11eae0 | wc -l
289
```

Note: This is the canonical count. Earlier estimate of "270" was from an imprecise
`git status --porcelain=v1 | wc -l` before renormalization, which counted both
staged and unstaged entries. Renormalization confirmed exactly 289 files.

### 4.3 Checkout-doesn't-re-dirty proof

```
$ git status --porcelain=v1
(empty)

$ git checkout -- .
$ git status --porcelain=v1
(empty)

$ git restore .
$ git status --porcelain=v1
(empty)
```

All three passes: clean before, clean after `checkout --`, clean after `restore`.

---

## Section 5: Gate Integration Proof

### 5.1 clean-check CLI receipt

```
$ python -m runtime.tools.coo_land_policy clean-check --repo . --receipt /tmp/test.json
CLEAN: working tree clean; core.autocrlf=false (compliant)
```

Receipt JSON includes: repo path, HEAD SHA, git status verbatim, core.autocrlf --show-origin.

### 5.2 coo land preflight integration

File: `runtime/tools/coo_worktree.sh`, lines 1083-1098  
Location: After existing `git status` preflight check, before source ref resolution.  
Gate: `coo_land_policy.py clean-check --repo "$BUILD_REPO" --receipt "$evid_dir/clean_check_preflight.json"`  
Failure: Emits `REPORT_BLOCKED__coo_land__CLEAN_CHECK_FAILED.md` and exits 41.

### 5.3 coo land postflight integration

File: `runtime/tools/coo_worktree.sh`, lines 1466-1469  
Location: After post-merge dirty check, before land receipt emission.  
Gate: `coo_land_policy.py clean-check --repo "$BUILD_REPO" --receipt "$evid_dir/clean_check_postflight.json"`
