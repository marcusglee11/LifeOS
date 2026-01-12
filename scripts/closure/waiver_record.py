
import os
import sys
import json
import argparse
from datetime import datetime, timedelta

# Scoring Table (Reason Code -> Score)
SCORING_TABLE = {
    "SHA256_MISMATCH": 90,
    "ZIP_PATH_NON_CANONICAL": 50,
    "TRUNCATION_TOKEN_FOUND": 80,
    "REQUIRED_FILE_MISSING": 95,
    "MANIFEST_INVALID_JSON": 95,
    "EVIDENCE_MISSING": 90,
    "PROFILE_MISSING": 70,
    "DEFAULT": 50
}

BACKLOG_PATH = os.path.join("docs", "11_admin", "BACKLOG.md")

def calculate_score(reason_code):
    return SCORING_TABLE.get(reason_code, SCORING_TABLE["DEFAULT"])

def ingest_to_backlog(debt_items, waiver_path, closure_id, repayment_trigger):
    if not os.path.exists(BACKLOG_PATH):
        print(f"Warning: Backlog not found at {BACKLOG_PATH}. Skipping ingestion.")
        return

    entry_lines = []
    for item in debt_items:
        # Format: - [ ] [DEBT] [Score: <Int>] [DUE: <Date>] <Summary>
        line = f"- [ ] [DEBT] [Score: {item['score']}] [DUE: {repayment_trigger}] {item['reason_code']}: {item['description']} (Ref: {closure_id})"
        entry_lines.append(line)
    
    with open(BACKLOG_PATH, 'a') as f:
        f.write("\n" + "\n".join(entry_lines) + "\n")
    
    print(f"Ingested {len(entry_lines)} debt items into {BACKLOG_PATH}")

def main():
    parser = argparse.ArgumentParser(description="G-CBS Waiver Record Generator")
    parser.add_argument("--closure-id", required=True, help="Closure ID")
    parser.add_argument("--reason-codes", nargs='+', required=True, help="List of reason codes being waived")
    parser.add_argument("--rationale", required=True, help="Why are we waiving this?")
    parser.add_argument("--repayment-days", type=int, default=14, help="Days until repayment due")
    parser.add_argument("--owner", default="CEO", help="Risk acceptance owner")
    parser.add_argument("--output", default="WAIVER.md", help="Output path")
    
    args = parser.parse_args()

    repayment_date = (datetime.now() + timedelta(days=args.repayment_days)).strftime("%Y-%m-%d")
    
    debt_items = []
    for code in args.reason_codes:
        score = calculate_score(code)
        debt_items.append({
            "reason_code": code,
            "score": score,
            "description": f"Waived failure for {code}"
        })
        
    waiver_data = {
        "closure_id": args.closure_id,
        "waived_checks": args.reason_codes,
        "rationale": args.rationale,
        "risk_acceptance_owner": args.owner,
        "repayment_trigger": repayment_date,
        "debt_items": debt_items
    }
    
    # Generate Markdown
    lines = []
    lines.append(f"# WAIVER RECORD: {args.closure_id}")
    lines.append(f"**Date**: {datetime.now().isoformat()}")
    lines.append(f"**Owner**: {args.owner}")
    lines.append(f"**Repayment Due**: {repayment_date}")
    lines.append(f"\n## Rationale")
    lines.append(args.rationale)
    lines.append(f"\n## Waived Items (Debt)")
    lines.append("| Code | Score | Description |")
    lines.append("|------|-------|-------------|")
    
    for item in debt_items:
        lines.append(f"| {item['reason_code']} | {item['score']} | {item['description']} |")
        
    with open(args.output, "w") as f:
        f.write("\n".join(lines))
        
    print(f"Waiver generated at {args.output}")
    
    # Ingest to Backlog
    # Assume running from repo root
    ingest_to_backlog(debt_items, args.output, args.closure_id, repayment_date)

if __name__ == "__main__":
    main()
