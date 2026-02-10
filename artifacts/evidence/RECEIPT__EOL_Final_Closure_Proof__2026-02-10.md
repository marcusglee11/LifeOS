# RECEIPT: EOL Final Closure Proof — 2026-02-10

**Purpose**: Verbatim proof of EOL clean invariant at FINAL HEAD for closure.

---

## 1. Final HEAD Attribution

```
HEAD: 73010db3c3c75c82e0bf70058e3710446c09701a
Branch: build/eol-clean-invariant
```

## 2. Config Provenance

### 2.1 Effective core.autocrlf

```
$ git config --show-origin --get core.autocrlf
file:.git/config        false
```

### 2.2 System core.autocrlf

```
$ git config --show-origin --system --get core.autocrlf
file:C:/Program Files/Git/etc/gitconfig true
```

**Observation**: System sets `true` (standard Git for Windows), which causes the checkout oscillation.
Local `.git/config` correctly overrides to `false` at the repo level.

---

## 3. .gitattributes verification

```
$ git check-attr -a -- runtime/tools/coo_land_policy.py
runtime/tools/coo_land_policy.py: text: set
runtime/tools/coo_land_policy.py: eol: lf

$ git check-attr -a -- docs/02_protocols/EOL_Policy_v1.0.md
docs/02_protocols/EOL_Policy_v1.0.md: text: set
docs/02_protocols/EOL_Policy_v1.0.md: eol: lf

$ git check-attr -a -- spikes/claude-code-mcp-test/node_modules/.bin/claude-code-mcp.cmd
spikes/claude-code-mcp-test/node_modules/.bin/claude-code-mcp.cmd: text: set
spikes/claude-code-mcp-test/node_modules/.bin/claude-code-mcp.cmd: eol: crlf
```

**Observation**: LF policy applied to code/docs; CRLF safety exception applied to `.cmd` files.

---

## 4. Status & Checkout/Restore Proof

### 4.1 Working Tree Status

```
$ git status --porcelain=v1
(empty)
```

### 4.2 Checkout --

```
$ git checkout -- .
$ git status --porcelain=v1
(empty)
```

### 4.3 Restore

```
$ git restore .
$ git status --porcelain=v1
(empty)
```

**Observation**: Working tree remains clean after explicit checkout/restore, proving LF normalization is stable.

---

## 5. Clean-check JSON Receipt

```json
{
  "repo": "C:\\Users\\cabra\\Projects\\LifeOS",
  "head_sha": "73010db3c3c75c82e0bf70058e3710446c09701a",
  "git_status_porcelain": "(empty)",
  "core_autocrlf_show_origin": "file:.git/config\tfalse",
  "result_clean": true,
  "result_reason": "CLEAN",
  "result_file_count": 0,
  "result_detail": "working tree clean; core.autocrlf=false (compliant)"
}
```

*Generated at: artifacts/evidence/FINAL_CLEAN_CHECK_RECEIPT.json*
