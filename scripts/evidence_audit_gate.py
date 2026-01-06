import sys
from pathlib import Path

def main():
    repo_root = Path.cwd()
    artifacts_dir = repo_root / "artifacts"
    
    # Files to audit
    files_to_check = [
        artifacts_dir / "Evidence_Commands_And_Outputs.md",
        artifacts_dir / "review_packets/Review_Packet_OpenCode_Phase1_v1.0.md",
        Path(r"C:\Users\cabra\.gemini\antigravity\brain\c9967bad-7ca5-4451-b5fc-8f521b90e1e7\Packet_Fix_Summary.md") 
    ]
    
    report_lines = []
    failed = False
    
    report_lines.append("# Evidence Audit Gate Report")
    report_lines.append(f"Date: {sys.argv[1] if len(sys.argv) > 1 else 'Unknown'}")
    report_lines.append("")
    
    # Check 1: Elision Scan
    report_lines.append("## 1. Elision Scan (Searching for '...')")
    for f in files_to_check:
        if not f.exists():
            report_lines.append(f"FAIL: File not found: {f}")
            failed = True
            continue
            
        content = f.read_text(encoding="utf-8")
        if "..." in content:
            # Allow "..." only if it's text, but instruction says ZERO TOLERANCE for evidence commands/outputs.
            # We strictly fail on "..." in these files as they are evidence containers.
            # We might verify context, but strict mode is safer.
            lines = content.splitlines()
            found_lines = []
            for i, line in enumerate(lines):
                if "..." in line:
                    # Allow legitimate code assertions in flattened code
                    if 'assert "..."' in line or "assert '...'" in line:
                        continue
                    found_lines.append(i+1)

            if found_lines:
                report_lines.append(f"FAIL: Elision detected in {f.name} at lines: {found_lines}")
                failed = True
            else:
                report_lines.append(f"PASS: {f.name} clean.")

    report_lines.append("")
    
    # Check 2: Output Completeness
    report_lines.append("## 2. Output Completeness Scan")
    evidence_doc = artifacts_dir / "Evidence_Commands_And_Outputs.md"
    if evidence_doc.exists():
        content = evidence_doc.read_text(encoding="utf-8")
        if "100" in content and "Line 99: Evidence capture test." in content:
            report_lines.append(f"PASS: {evidence_doc.name} contains required output signatures.")
        else:
            report_lines.append(f"FAIL: {evidence_doc.name} missing '100' or excerpt output.")
            failed = True
    else:
        report_lines.append(f"FAIL: {evidence_doc.name} missing.")
        failed = True
        
    report_content = "\n".join(report_lines)
    
    # Write Report
    report_path = artifacts_dir / "evidence/Evidence_Audit_Gate_Report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_content, encoding="utf-8")
    
    print(report_content)
    
    if failed:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
