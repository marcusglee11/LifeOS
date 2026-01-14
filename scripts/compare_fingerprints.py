import json
import sys
import os

def load_fingerprints(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)
    # Return as dict keyed by nodeid for easy comparison
    return {item["nodeid"]: item for item in data}

def main():
    base_file = sys.argv[1]
    head_file = sys.argv[2]
    
    base_data = load_fingerprints(base_file)
    head_data = load_fingerprints(head_file)
    
    base_nodeids = sorted(base_data.keys())
    head_nodeids = sorted(head_data.keys())
    
    report = []
    report.append("# Test Baseline Comparison Report")
    report.append(f"- **BASE File**: {base_file}")
    report.append(f"- **HEAD File**: {head_file}")
    report.append(f"- **BASE Failures**: {len(base_nodeids)}")
    report.append(f"- **HEAD Failures**: {len(head_nodeids)}")
    report.append("")
    
    added = [nid for nid in head_nodeids if nid not in base_data]
    removed = [nid for nid in base_nodeids if nid not in head_data]
    
    if not added and not removed:
        report.append("## Result: IDENTICAL NODEIDS")
    else:
        if added:
            report.append(f"## REGRESSION DETECTED: {len(added)} new failures")
            for nid in added:
                report.append(f"- NEW: {nid}")
        if removed:
            report.append(f"## IMPROVEMENT DETECTED: {len(removed)} failures resolved")
            for nid in removed:
                report.append(f"- FIXED: {nid}")
    
    report.append("")
    report.append("## Signature Comparison")
    
    mismatched = []
    for nid in base_nodeids:
        if nid in head_data:
            b_sig = base_data[nid]["signature"]
            h_sig = head_data[nid]["signature"]
            if b_sig != h_sig:
                mismatched.append((nid, b_sig, h_sig))
                
    if not mismatched:
        report.append("All failing signatures match exactly across BASE and HEAD.")
    else:
        report.append(f"## SIGNATURE MISMATCH DETECTED: {len(mismatched)} nodeids")
        for nid, b, h in mismatched:
            report.append(f"- {nid}: BASE({b}) != HEAD({h})")
            
    report.append("")
    report.append("## Detailed Failure List (HEAD)")
    report.append("| NodeID | Type | Signature |")
    report.append("| :--- | :--- | :--- |")
    for nid in head_nodeids:
        item = head_data[nid]
        report.append(f"| {nid} | {item['type']} | {item['signature']} |")
        
    final_result = "baseline proof PASS" if not added and not mismatched else "baseline proof FAIL"
    report.append(f"\n# FINAL VERDICT: {final_result}")
    
    with open("artifacts/evidence/baseline_comparison_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"Comparison report written to artifacts/evidence/baseline_comparison_report.md")
    print(f"Verdict: {final_result}")

if __name__ == "__main__":
    main()
