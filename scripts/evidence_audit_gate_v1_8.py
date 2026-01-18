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
    report_lines.append(f"Run ID: v1.8_FINAL_AUDIT")
    report_lines.append(f"Date: {sys.argv[1] if len(sys.argv) > 1 else 'Unknown'}")
    report_lines.append("")
    
    # Check 1: Ellipsis Token Scan (Zero Tolerance for literal three dots)
    # Reference as "."*3 to avoid self-flagging
    elision_token = "." * 3
    
    report_lines.append(f"## 1. Ellipsis Token Scan (Target: '{elision_token}')")
    
    for f in files_to_check:
        if not f.exists():
            report_lines.append(f"FAIL: File not found: {f}")
            failed = True
            continue
            
        content = f.read_text(encoding="utf-8")
        
        # Check for literal token
        if elision_token in content:
            lines = content.splitlines()
            found_hits = []
            for i, line in enumerate(lines):
                if elision_token in line:
                    # Capture context (up to 80 chars)
                    clean_line = line.strip()
                    context = clean_line[:80] + ("..." if len(clean_line) > 80 else "") # Wait, don't use ellipsis in report!
                    context = clean_line[:80] + ("(truncated)" if len(clean_line) > 80 else "")
                    found_hits.append(f"Line {i+1}: {context}")

            if found_hits:
                report_lines.append(f"FAIL: {f.name} contains forbidden token.")
                for hit in found_hits:
                    report_lines.append(f"  - {hit}")
                failed = True
            else:
                 # Should not happen if 'in content' was true but not loops?
                 pass
        else:
            report_lines.append(f"PASS: {f.name} clean.")

    report_lines.append("")
    
    # Check 2: Output Completeness
    report_lines.append("## 2. Output Completeness Scan")
    evidence_doc = artifacts_dir / "Evidence_Commands_And_Outputs.md"
    if evidence_doc.exists():
        content = evidence_doc.read_text(encoding="utf-8")
        has_100 = "100" in content
        has_l0 = "Line 0: Evidence capture test." in content
        has_l99 = "Line 99: Evidence capture test." in content
        
        if has_100 and has_l0 and has_l99:
            report_lines.append(f"PASS: {evidence_doc.name} contains required output signatures.")
        else:
            report_lines.append(f"FAIL: {evidence_doc.name} missing required outputs.")
            report_lines.append(f"  - Has '100': {has_100}")
            report_lines.append(f"  - Has Line 0: {has_l0}")
            report_lines.append(f"  - Has Line 99: {has_l99}")
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
