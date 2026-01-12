import sys
from pathlib import Path

def main():
    repo_root = Path.cwd()
    artifacts_dir = repo_root / "artifacts"
    
    # Report Path
    report_path = artifacts_dir / "evidence/Evidence_Audit_Gate_Report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Files to audit
    files_to_check = [
        artifacts_dir / "Evidence_Commands_And_Outputs.md",
        artifacts_dir / "review_packets/Review_Packet_OpenCode_Phase1_v1.0.md",
        Path(r"C:\Users\cabra\.gemini\antigravity\brain\c9967bad-7ca5-4451-b5fc-8f521b90e1e7\Packet_Fix_Summary.md"),
        report_path # Self-scan
    ]
    
    report_lines = []
    failed = False
    
    report_lines.append("# Evidence Audit Gate Report")
    report_lines.append(f"Run ID: v1.9_FINAL_AUDIT")
    report_lines.append(f"Date: {sys.argv[1] if len(sys.argv) > 1 else 'Unknown'}")
    report_lines.append("")
    
    # Check 1: Ellipsis Token Scan (Zero Tolerance for literal three dots)
    # Reference as "."*3 to avoid self-flagging in the script source
    elision_token = "." * 3
    
    report_lines.append(f"## 1. Ellipsis Token Scan (Target: '\"+\".\"*3+\"')") # Safe description
    report_lines.append("Scanned Files:")
    for f in files_to_check:
        report_lines.append(f"- {f.name}")
        
    report_lines.append("")
    
    # We construct the report content in memory FIRST to allow self-scanning simulation
    # But checking the report file itself requires it to be written?
    # We will check the OTHER files first.
    
    audit_results = []
    
    for f in files_to_check:
        if f == report_path:
            continue # We scan the generated content later
            
        if not f.exists():
            audit_results.append(f"FAIL: File not found: {f.name}")
            failed = True
            continue
            
        content = f.read_text(encoding="utf-8")
        
        # Check for literal token
        if elision_token in content:
            lines = content.splitlines()
            found_hits = []
            for i, line in enumerate(lines):
                if elision_token in line:
                    clean_line = line.strip()
                    # Safe context representation to avoid polluting the report
                    safe_context = clean_line[:80].replace(elision_token, "[ELLIPSIS]")
                    if len(clean_line) > 80:
                        safe_context += "(truncated)"
                    found_hits.append(f"Line {i+1}: {safe_context}")

            if found_hits:
                audit_results.append(f"FAIL: {f.name} contains forbidden token.")
                for hit in found_hits:
                    audit_results.append(f"  - {hit}")
                failed = True
            else:
                 # Should not happen if 'in content' was true but not loops?
                 pass
        else:
            audit_results.append(f"PASS: {f.name} clean.")

    # Check 2: Output Completeness
    report_lines.append("## 2. Output Completeness Scan")
    evidence_doc = artifacts_dir / "Evidence_Commands_And_Outputs.md"
    completeness_results = []
    
    if evidence_doc.exists():
        content = evidence_doc.read_text(encoding="utf-8")
        has_100 = "100" in content
        has_l0 = "Line 0: Evidence capture test." in content
        has_l99 = "Line 99: Evidence capture test." in content
        
        if has_100 and has_l0 and has_l99:
            completeness_results.append(f"PASS: {evidence_doc.name} contains required output signatures.")
        else:
            completeness_results.append(f"FAIL: {evidence_doc.name} missing required outputs.")
            completeness_results.append(f"  - Has '100': {has_100}")
            completeness_results.append(f"  - Has Line 0: {has_l0}")
            completeness_results.append(f"  - Has Line 99: {has_l99}")
            failed = True
    else:
        completeness_results.append(f"FAIL: {evidence_doc.name} missing.")
        failed = True

    # Assemble Check 1 Results
    report_lines.extend(audit_results)
    report_lines.append("")
    report_lines.extend(completeness_results)
    
    # Finalize Content
    report_content = "\n".join(report_lines)
    
    # Self-Scan the generated content
    if elision_token in report_content:
        # This is a critical failure of the auditor itself
        report_content += "\n\nCRITICAL FAIL: Audit Report itself contains forbidden token!"
        failed = True
    else:
        # Append self-scan pass
        report_content += f"\nPASS: {report_path.name} (Self-Scan) clean."
        
    # Write Report
    report_path.write_text(report_content, encoding="utf-8")
    
    print(report_content)
    
    if failed:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
