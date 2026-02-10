
import json
import hashlib
import sys
import os
import subprocess
import time
import shutil
import platform
import re
import tomllib
from pathlib import Path

def compute_file_sha256(filepath):
    """Compute SHA256 of a file from disk (P0.5)."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()

def find_repo_root(start_path):
    """Walk up from start_path to find pyproject.toml (P0.7)."""
    path = list(Path(start_path).resolve().parents)
    path.insert(0, Path(start_path).resolve())
    for p in path:
        if (p / "pyproject.toml").exists():
            return p
    return None

class SearchEngine:
    """
    Scans the repository for proofs to satisfy E2E requirements (P0.2).
    Ordering: Lexicographic by path. First match wins.
    """
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.proofs = {
            "entrypoint": None,
            "wrapper_contract": {"authority": None, "required_fields": []},
            "exit_conventions": None,
            "volatile_set": {"source": None, "fields": []},
            "python_m_blessing": None,
            "negative_invocation": {"source": None, "params": None, "expected_exit_code": None}
        }
        self.search_log = []

    def scan(self):
        """Perform deterministic scan of docs, artifacts, runtime, scripts, README*, pyproject.toml."""
        targets = ["docs", "artifacts", "runtime", "scripts"]
        
        # Files in root: README*, pyproject.toml
        root_files = sorted(list(self.repo_root.glob("README*")))
        if (self.repo_root / "pyproject.toml").exists():
            root_files.append(self.repo_root / "pyproject.toml")
        
        all_paths = []
        for target in targets:
            dir_path = self.repo_root / target
            if dir_path.exists():
                for ext in ["**/*.md", "**/*.py", "**/*.toml", "**/*.yaml", "**/*.json"]:
                    all_paths.extend(list(dir_path.glob(ext)))
        
        all_paths.extend(root_files)
        # Unique and sorted
        all_paths = sorted(list(set([p.relative_to(self.repo_root) for p in all_paths if "__pycache__" not in str(p)])))

        self.search_log.append(f"Scanning {len(all_paths)} files in deterministic order [done]")

        for rel_path in all_paths:
            abs_path = self.repo_root / rel_path
            content = ""
            try:
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except (IOError, OSError):
                continue

            # Debug for wrapper contract
            if "test_cli_mission.py" in str(rel_path):
                 print(f"DEBUG: Scanning {rel_path} for wrapper contract...")
                 # print(f"DEBUG Snippet: {content[:200]}...")

            # 1. Entrypoint
            if rel_path.name == "pyproject.toml":
                if 'lifeos = "runtime.cli:main"' in content or "lifeos = 'runtime.cli:main'" in content:
                    self._add_proof("entrypoint", rel_path)

            # 2. Wrapper Contract (Minimal Extraction)
            if rel_path.name == "test_cli_mission.py": # Prefer test authority
                # Heuristic: Assert 'final_state' in data
                # Capture asserted fields. Minimal: ['final_state', 'mission_result', 'success', 'id']
                # Proof strength: We only accept if we see explicit assertions.
                fields = []
                # Allow assert 'final_state' in data OR assert data['final_state']
                if re.search(r"assert\s+.*['\"]final_state['\"]", content):
                    fields.append("final_state")
                
                # Check for success assertion (nested or direct)
                if re.search(r"['\"]success['\"].*is\s+(True|False)", content) or \
                   re.search(r"['\"]success['\"].*==\s*(True|False)", content):
                    fields.append("success")
                    fields.append("mission_result")
                
                if re.search(r"['\"]id['\"].*==", content):
                    fields.append("id")
                
                if fields:
                    # Deterministic Authority Tie-Breaker: First valid test wrapper proof wins.
                    # Since we scan sorted, first match is deterministic.
                    if not self.proofs["wrapper_contract"]["authority"]:
                        self.proofs["wrapper_contract"] = {
                            "authority": str(rel_path),
                            "required_fields": sorted(list(set(fields)))
                        }
                        self.search_log.append(f"FOUND PROOF [wrapper_contract]: {rel_path} with fields {fields}")
                
                print(f"DEBUG: {rel_path} fields found: {fields}")

            # 3. Exit Conventions
            # Loose heuristic removed. Only strict if extracted.
            # But P0.6 says: "ensure exit proof is meaningful or removed".
            # We will rely on P0.3 negative extraction to prove exit code 1.
            # For general conventions, we won't gate unless we find a strict statement.
            # Skipping explicit "exit_conventions" proof object unless a strict doc is found.
            pass

            # 4. Volatile Set (Strict Parsing)
            # Look for VOLATILE_FIELDS = {...} or similar
            if rel_path.name == "test_cli_mission.py" or "docs" in str(rel_path):
                 # Pattern: VOLATILE_FIELDS = { "path.to.field", ... } or [ ...
                 match = re.search(r"VOLATILE_FIELDS\s*=\s*([\{\[].*?[\}\]])", content, re.DOTALL)
                 if match:
                     try:
                         # Safe eval? Or json load?
                         # Let's try to parse as JSON if possible, or simple python literal
                         # It's regex extracted, might be multiline.
                         raw = match.group(1)
                         # Simple cleaning for python literal set/list
                         # This is "machine parseable" within python context
                         # Dangerous to eval? We are in a closed repo.
                         # Better: heuristic parse strings
                         volatiles = re.findall(r"['\"]([^'\"]+)['\"]", raw)
                         if volatiles:
                             if not self.proofs["volatile_set"]["source"]:
                                 self.proofs["volatile_set"] = {
                                     "source": str(rel_path),
                                     "fields": sorted(volatiles)
                                 }
                                 self.search_log.append(f"FOUND PROOF [volatile_set]: {rel_path} with {len(volatiles)} fields")
                     except (SyntaxError, ValueError, TypeError) as e:
                         self.search_log.append(f"WARN: Found VOLATILE_FIELDS in {rel_path} but failed to parse: {e}")

            # 5. Python-M Blessing
            if "python -m runtime.cli" in content and ("canonical" in content.lower() or "equivalent" in content.lower()):
                self._add_proof("python_m_blessing", rel_path)
            
            # 6. Negative Invocation (Conflict-Safe Extraction)
            if rel_path.name == "test_cli_mission.py":
                # Pattern: Look for params={...} and assert ret == 1
                # Simplified strategy: Extract test functions that use {invalid_json} or known failure patterns
                # match: def test_...(self...): ... params = "..." ... assert ret == 1
                
                # We'll split simply by def test_
                tests = content.split("def test_")
                for t in tests[1:]:
                    lines = t.splitlines()
                    # Check if it has assert ret == 1
                    if any("assert ret == 1" in l for l in lines) and \
                       any("cmd_mission_run" in l for l in lines):
                       
                       # Extract params
                       params = None
                       for l in lines:
                           if "params =" in l and "class Args" in t: # crude check if it's inside the Args class
                               # Try to extract value
                               v = l.split("params =", 1)[1].strip()
                               if v.startswith("'") or v.startswith('"'):
                                   params = v.strip("'\"")
                       
                       if params:
                           test_name = "test_" + lines[0].split("(")[0]
                           if not self.proofs["negative_invocation"]["source"]:
                               self.proofs["negative_invocation"] = {
                                   "source": str(rel_path) + "::" + test_name,
                                   "params": params,
                                   "expected_exit_code": 1
                               }
                               self.search_log.append(f"FOUND PROOF [negative_invocation]: {test_name} with params={params}")

    def _add_proof(self, key, path):
        if self.proofs[key] is None:
            self.proofs[key] = str(path)
            self.search_log.append(f"FOUND PROOF [{key}]: {path}")

    def get_structured_log(self):
        log_lines = ["# SEARCH LOG\n", "## Selected Proofs\n"]
        for k, v in self.proofs.items():
            val_str = "MISSING"
            if v:
                if isinstance(v, dict):
                    if v.get("source") or v.get("authority"):
                         val_str = v.get("source") or v.get("authority")
                    elif v.get("params"): # negative 
                         val_str = f"{v.get('source')} (Expect: {v.get('expected_exit_code')})"
                    else:
                         val_str = str(v)
                else:
                    val_str = str(v)
            log_lines.append(f"- {k}: {val_str}")
        log_lines.append("\n## Scan Activity\n")
        log_lines.extend(self.search_log)
        return "\n".join(log_lines)

def normalize_json_for_determinism(data, volatile_paths=None):
    """
    Normalize JSON for strict determinism check (P0.5).
    Removes ONLY specific volatile leaf paths.
    """
    if not volatile_paths:
        return data # No proven volatiles => skip filtering

    def _clean(obj, path="root"):
        if path in volatile_paths:
            return "<VOLATILE>"
        
        if isinstance(obj, dict):
            return {k: _clean(v, f"{path}.{k}") for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [_clean(v, f"{path}[{i}]") for i, v in enumerate(obj)]
        else:
            return obj

    return _clean(data)

def run_test_case(case_id, cmd, out_dir, repo_root, expect_exit_code=0, required_wrapper_fields=None, proof_source=None):
    """
    Run a test case with fail-closed evidence capture (P0.4).
    P0.1: Force cwd=repo_root.
    P0.9: Record proof_source in meta.
    """
    start_time = time.monotonic()
    
    stdout_path = out_dir / f"{case_id}.stdout.txt"
    stderr_path = out_dir / f"{case_id}.stderr.txt"
    exitcode_path = out_dir / f"{case_id}.exitcode.txt"
    meta_path = out_dir / f"{case_id}.meta.json"

    result = {
        "name": case_id,
        "status": "PASS",
        "expected": {"exit_code": expect_exit_code},
        "observed": {"exit_code": None, "wrapper_success": None},
        "json_parse": {"ok": False, "error": None},
        "wrapper_validation": {"ok": False, "errors": []},
        "reason": None
    }

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(repo_root), # P0.1
            env=os.environ.copy()
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)
        
        # Write bytes (P0.4)
        with open(stdout_path, 'wb') as f: f.write(proc.stdout)
        with open(stderr_path, 'wb') as f: f.write(proc.stderr)
        with open(exitcode_path, 'w', encoding='utf-8') as f: f.write(str(proc.returncode))
        
        result["observed"]["exit_code"] = proc.returncode
        
        # Meta
        meta = {
            "argv": cmd,
            "duration_ms": duration_ms,
            "repo_root": str(repo_root) # P0.1
        }
        if proof_source:
             meta["proof_source"] = proof_source # P0.9

        with open(meta_path, 'w', encoding='utf-8') as f: json.dump(meta, f, indent=2)

        # 1. Exit Code Check
        if proc.returncode != expect_exit_code:
            result["status"] = "FAIL"
            result["reason"] = f"Exit code mismatch: expected {expect_exit_code}, got {proc.returncode}"

        # 2. JSON Parse (if --json)
        json_data = None
        if "--json" in cmd:
            try:
                json_data = json.loads(proc.stdout.decode('utf-8', errors='replace'))
                result["json_parse"]["ok"] = True
                
                # 3. Wrapper Validation (P0.5 Proven Authority)
                errors = []
                if required_wrapper_fields:
                    for field in required_wrapper_fields:
                        # Simple flat check for now, can be sophisticated if needed
                        # Our proof extractor handles flat 'final_state' etc.
                        # For leaf fields like mission_result.success, we need logic
                        if field == "final_state":
                            if "final_state" not in json_data: errors.append("Missing final_state")
                        elif field == "mission_result":
                            if "final_state" not in json_data or "mission_result" not in json_data["final_state"]:
                                errors.append("Missing final_state.mission_result")
                        elif field == "success":
                            if "final_state" not in json_data or "mission_result" not in json_data["final_state"] or "success" not in json_data["final_state"]["mission_result"]:
                                errors.append("Missing success field")
                        elif field == "id":
                            if "id" not in json_data: errors.append("Missing id")
                        # Add more if proven
                
                # Check wrapper success if meaningful (implied by typical usage)
                wrapper_success = json_data.get("final_state", {}).get("mission_result", {}).get("success")
                result["observed"]["wrapper_success"] = wrapper_success

                if errors:
                    result["wrapper_validation"]["ok"] = False
                    result["wrapper_validation"]["errors"] = errors
                    result["status"] = "FAIL"
                    result["reason"] = f"Wrapper contract violation: {', '.join(errors)}"
                else:
                    result["wrapper_validation"]["ok"] = True

            except json.JSONDecodeError as e:
                result["json_parse"]["error"] = str(e)
                # If we expected a failure (exit code != 0), non-JSON output might be acceptable
                # (e.g. strict argparse errors, invalid JSON params preventing JSON emitter)
                if expect_exit_code == 0:
                     result["status"] = "FAIL"
                     result["reason"] = "JSON parse failed"
                     
                     # P0.8: Coherent Wrapper Validation Errors
                     result["wrapper_validation"]["ok"] = False
                     result["wrapper_validation"]["errors"] = ["JSON parse failed; wrapper validation not evaluated"]
                else:
                     # For negative tests, if JSON parsing fails, we assume it's a text-based error
                     # and rely solely on exit code matching (already checked above).
                     result["json_parse"]["ok"] = False
                     # P0.8: wrapper validation is n/a or false?
                     # If we expected failure and got non-JSON text, wrapper validation is effectively N/A or passed (as in "no wrapper to validate")
                     # But consistency says: if parse ok=False, validation ok should probably be False/None with reason?
                     # Since E2E-3 checks 'observed.wrapper_success' separately, we leave this consistent.
                     result["wrapper_validation"]["ok"] = False
                     result["wrapper_validation"]["errors"] = ["JSON parse failed (expected failure); wrapper validation not evaluated"]

        return result, json_data

    except FileNotFoundError as e:
        # P0.2 / P0.4: Dependencies missing = BLOCKED
        with open(meta_path, 'w', encoding='utf-8') as f: 
            json.dump({"error": str(e), "cmd": cmd}, f)
        
        result["status"] = "BLOCKED"
        result["reason"] = f"Command not found: {e}"
        return result, None

    except Exception as e:
        result["status"] = "BLOCKED"
        result["reason"] = f"Unexpected harness error: {e}"
        return result, None

def write_blocked(out_root, run_id, reason, search_log_path=None):
    """Write BLOCKED.md and exit."""
    path = out_root / run_id / "BLOCKED.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# BLOCKED\n\nReason: {reason}\n")
        if search_log_path:
            f.write(f"Search Log: {search_log_path}\n")
    print(f"Harness BLOCKED: {reason}", file=sys.stderr)
    sys.exit(1)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="E2E Mission CLI Harness (Audit-Grade)")
    parser.add_argument("--out-dir", required=False, help="Override output directory")
    args = parser.parse_args()

    repo_root = find_repo_root(__file__)
    if not repo_root:
        # Fallback out dir if we can't find repo root
        out_root = Path(os.getcwd()) / "artifacts" / "evidence" / "mission_cli_e2e"
        write_blocked(out_root, "unknown_run_id", "Could not locate repo root (pyproject.toml not found)")
    
    if args.out_dir:
        out_root = Path(args.out_dir)
    else:
        out_root = repo_root / "artifacts/evidence/mission_cli_e2e"

    # --- P0.2: Search & Proof ---
    engine = SearchEngine(repo_root)
    engine.scan()
    
    # Fail-closed checking
    if not engine.proofs["entrypoint"]:
        write_blocked(out_root, "unknown", "Cannot prove entrypoint definition", engine.get_structured_log())
    
    # Wrapper Authority Check (P0.5)
    wrapper_proof = engine.proofs["wrapper_contract"]
    if not wrapper_proof["authority"]:
        write_blocked(out_root, "unknown", "Cannot prove JSON wrapper contract from authoritative source", engine.get_structured_log())
    
    # --- P0.3: Entrypoint Fallback ---
    # ... existing logic ok, proving blessing checked via engine ...

    if shutil.which("lifeos"):
        entrypoint_cmd = ["lifeos"]
        entrypoint_mode = "lifeos"
    else:
        if engine.proofs["python_m_blessing"]:
            entrypoint_cmd = [sys.executable, "-m", "runtime.cli"]
            entrypoint_mode = "python-m"
        else:
            write_blocked(out_root, "unknown", "lifeos missing in path and no python-m blessing found", engine.get_structured_log())

    # --- P0.7: Derived Canonical Command ---
    CANONICAL_CLI_ARGV = entrypoint_cmd + ["mission", "run", "build_with_validation", "--params", '{"mode":"smoke"}', "--json"]
    
    # P0.1: Run ID from stable argv
    run_id = hashlib.sha256("\n".join(CANONICAL_CLI_ARGV).encode('utf-8')).hexdigest()[:16]
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    search_log_path = run_dir / "search_log.txt"
    with open(search_log_path, 'w', encoding='utf-8') as f:
        f.write(engine.get_structured_log())

    summary = {
        "schema_version": "e2e_mission_cli_summary_v1",
        "run_id": run_id,
        "canonical_cli_argv": CANONICAL_CLI_ARGV,
        "selected_entrypoint_mode": entrypoint_mode,
        "cwd": str(repo_root),
        "cases": [],
        "overall_outcome": "PASS"
    }

    # --- E2E-1: Smoke ---
    # P0.11: Pre-run cleanup for deterministic evidence collision
    # The build_with_validation mission computes a deterministic run_token from
    # baseline_commit + params. Without a baseline_commit and with fixed params,
    # the token is always the same, causing collision errors on repeat runs.
    # Clean up any existing evidence directories before running.
    mission_evidence_root = repo_root / "artifacts" / "evidence" / "mission_runs" / "build_with_validation"
    if mission_evidence_root.exists():
        for child in mission_evidence_root.iterdir():
            if child.is_dir():
                try:
                    shutil.rmtree(child)
                except Exception as e:
                    # Non-fatal: log but continue
                    print(f"WARN: Failed to clean {child}: {e}", file=sys.stderr)

    res1, json1 = run_test_case(
        "E2E-1", 
        CANONICAL_CLI_ARGV, 
        run_dir, 
        repo_root, 
        expect_exit_code=0, 
        required_wrapper_fields=wrapper_proof["required_fields"]
    )
    summary["cases"].append(res1)
    
    if res1["status"] != "PASS":
        summary["overall_outcome"] = res1["status"]

    # --- E2E-2: Determinism (P0.4 Prove-or-Skip) ---
    volatile_proof = engine.proofs["volatile_set"]
    if summary["overall_outcome"] == "PASS":
        if volatile_proof["source"] and volatile_proof["fields"]:
            # Volatiles Proven!
            res2, json2 = run_test_case(
                "E2E-2", 
                CANONICAL_CLI_ARGV, 
                run_dir, 
                repo_root,
                expect_exit_code=0,
                required_wrapper_fields=wrapper_proof["required_fields"]
            )
            
            if res2["status"] == "PASS" and json1 and json2:
                # Use proven fields
                proven_volatiles = set(volatile_proof["fields"])
                norm1 = normalize_json_for_determinism(json1, proven_volatiles)
                norm2 = normalize_json_for_determinism(json2, proven_volatiles)
                s1 = json.dumps(norm1, sort_keys=True)
                s2 = json.dumps(norm2, sort_keys=True)
                
                if s1 != s2:
                    res2["status"] = "FAIL"
                    res2["reason"] = f"Strict determinism breach. Diff saved to {run_id}.diff.json"
                    summary["overall_outcome"] = "FAIL"
                    # Save diff (P0.7)
                    with open(run_dir / f"{run_id}.diff.json", 'w') as f:
                        json.dump({"run1": json1, "run2": json2}, f)
            summary["cases"].append(res2)
        else:
            summary["cases"].append({ "name": "E2E-2", "status": "SKIPPED", "reason": "No proven volatile field set extractable from repo" })
    else:
        summary["cases"].append({"name": "E2E-2", "status": "SKIPPED", "reason": "E2E-1 Failed"})

    # --- E2E-3: Negative (P0.3 Prove-or-Skip) ---
    neg_proof = engine.proofs["negative_invocation"]
    if neg_proof["source"] and neg_proof["params"]:
        # Proven Negative case!
        # Construct cmd with extracted params
        # Note: We must be careful about quoting. Extracted param string might be '"{...}"'
        # Can we rely on simply reusing entrypoint_cmd + ...?
        # Yes, standard mission structure.
        
        # params is raw string from code, e.g. "{invalid_json}" or '{"unknown":"bad"}'
        # If extracted with quotes, strip them?
        # In scan logic we stripped outer quotes.
        
        params_arg = neg_proof["params"]
        expect_code = neg_proof.get("expected_exit_code", 1)
        
        case3_cmd = entrypoint_cmd + ["mission", "run", "build_with_validation", "--params", params_arg, "--json"]
        res3, _ = run_test_case(
            "E2E-3", 
            case3_cmd, 
            run_dir, 
            repo_root,
            expect_exit_code=expect_code,
            required_wrapper_fields=wrapper_proof["required_fields"],
            proof_source=neg_proof["source"] # P0.9
        )
        
        if res3["status"] == "PASS":
            # Only check wrapper success if we successfully parsed JSON
            if res3["json_parse"]["ok"] and res3["observed"]["wrapper_success"] is not False:
                 res3["status"] = "FAIL"
                 res3["reason"] = "Expected wrapper success=False on negative case"
                 summary["overall_outcome"] = "FAIL"
        else:
            summary["overall_outcome"] = "FAIL"
            
        summary["cases"].append(res3)
    else:
         summary["cases"].append({ "name": "E2E-3", "status": "SKIPPED", "reason": "No concrete failing invocation proven/extracted from repo" })

    # --- Evidence Metadata ---
    evidence_files = []
    summary_path = run_dir / "summary.json"
    
    # Write summary first
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    for case in summary["cases"]:
        cid = case["name"]
        for ext in ["exitcode.txt", "meta.json", "stdout.txt", "stderr.txt"]:
             p = run_dir / f"{cid}.{ext}"
             if p.exists():
                 evidence_files.append({
                     "path": p.name,
                     "bytes": p.stat().st_size,
                     "sha256": compute_file_sha256(p)
                 })
    
    # P0.10: Explicitly include search_log.txt and other root artifacts
    for fname in ["search_log.txt", f"{run_id}.diff.json"]:
         p = run_dir / fname
         if p.exists():
             evidence_files.append({
                 "path": p.name,
                 "bytes": p.stat().st_size,
                 "sha256": compute_file_sha256(p)
             })
    
    # Update summary with complete evidence
    # Sort for stability
    evidence_files.sort(key=lambda x: x["path"])
    summary["evidence_files"] = evidence_files
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    # Pointer
    latest_path = out_root / "latest.json"
    latest = {
        "run_id": run_id,
        "relative_path": f"{run_id}/summary.json",
        "sha256":compute_file_sha256(summary_path)
    }
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(latest, f, indent=2)
    
    print(json.dumps(summary, indent=2))
    
    if summary["overall_outcome"] != "PASS":
        sys.exit(1)

if __name__ == "__main__":
    main()
