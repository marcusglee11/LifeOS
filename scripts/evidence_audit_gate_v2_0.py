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
    report_lines.append(f"Run ID: v2.0_FINAL_AUDIT")
    report_lines.append(f"Date: {sys.argv[1] if len(sys.argv) > 1 else 'Unknown'}")
    report_lines.append("")
    
    # Define tokens (without using literal ellipsis)
    triple_dot_token = "." * 3
    unicode_ellipsis = "\u2026"
    
    # Check 1: Triple-Dot Token Scan
    report_lines.append('## 1. Triple-Dot Token Scan')
    report_lines.append('Target token: "."*3')
    report_lines.append("Scanned Files:")
    for f in files_to_check:
        report_lines.append(f"- {f.name}")
    report_lines.append("")
    
    total_triple_dot_hits = 0
    triple_dot_details = []
    
    for f in files_to_check:
        if f == report_path:
            continue # Self-scan later
            
        if not f.exists():
            triple_dot_details.append(f"ERROR: File not found: {f.name}")
            failed = True
            continue
            
        content = f.read_text(encoding="utf-8")
        
        if triple_dot_token in content:
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if triple_dot_token in line:
                    total_triple_dot_hits += 1
                    clean_line = line.strip()
                    safe_context = clean_line[:80].replace(triple_dot_token, "[ELLIPSIS]")
                    if len(clean_line) > 80:
                        safe_context += "(truncated)"
                    triple_dot_details.append(f"  - {f.name}:L{i+1}: {safe_context}")
    
    # Check 2: Unicode Ellipsis Scan (U+2026)
    report_lines.append('## 2. Unicode Ellipsis Scan')
    report_lines.append('Target token: U+2026')
    report_lines.append("")
    
    total_unicode_hits = 0
    unicode_details = []
    
    for f in files_to_check:
        if f == report_path:
            continue # Self-scan later
            
        if not f.exists():
            continue # Already flagged above
            
        content = f.read_text(encoding="utf-8")
        
        if unicode_ellipsis in content:
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if unicode_ellipsis in line:
                    total_unicode_hits += 1
                    clean_line = line.strip()
                    safe_context = clean_line[:80].replace(unicode_ellipsis, "[U+2026]")
                    if len(clean_line) > 80:
                        safe_context += "(truncated)"
                    unicode_details.append(f"  - {f.name}:L{i+1}: {safe_context}")
    
    # Check 3: Output Completeness
    report_lines.append("## 3. Output Completeness Scan")
    evidence_doc = artifacts_dir / "Evidence_Commands_And_Outputs.md"
    completeness_pass = False
    
    if evidence_doc.exists():
        content = evidence_doc.read_text(encoding="utf-8")
        has_100 = "100" in content
        has_l0 = "Line 0: Evidence capture test." in content
        has_l99 = "Line 99: Evidence capture test." in content
        completeness_pass = has_100 and has_l0 and has_l99
        if completeness_pass:
            report_lines.append(f"PASS: Output Completeness Scan (all signatures present)")
        else:
            report_lines.append(f"FAIL: Output Completeness Scan (missing signatures)")
            report_lines.append(f"  - Has '100': {has_100}")
            report_lines.append(f"  - Has Line 0: {has_l0}")
            report_lines.append(f"  - Has Line 99: {has_l99}")
            failed = True
    else:
        report_lines.append(f"FAIL: Output Completeness Scan ({evidence_doc.name} missing)")
        failed = True
    
    report_lines.append("")
    
    # Assemble Results
    report_lines.append("## Results Summary")
    
    if total_triple_dot_hits == 0:
        report_lines.append(f"PASS: Triple-Dot Token Scan (0 hits)")
    else:
        report_lines.append(f"FAIL: Triple-Dot Token Scan ({total_triple_dot_hits} hits)")
        report_lines.extend(triple_dot_details)
        failed = True
    
    if total_unicode_hits == 0:
        report_lines.append(f"PASS: Unicode Ellipsis Scan (0 hits)")
    else:
        report_lines.append(f"FAIL: Unicode Ellipsis Scan ({total_unicode_hits} hits)")
        report_lines.extend(unicode_details)
        failed = True

    # Finalize Content
    report_content = "\n".join(report_lines)
    
    # Self-Scan the generated content
    self_scan_pass = True
    if triple_dot_token in report_content:
        report_content += "\n\nCRITICAL FAIL: Audit Report itself contains triple-dot token!"
        self_scan_pass = False
        failed = True
    if unicode_ellipsis in report_content:
        report_content += "\n\nCRITICAL FAIL: Audit Report itself contains unicode ellipsis!"
        self_scan_pass = False
        failed = True
        
    if self_scan_pass:
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
