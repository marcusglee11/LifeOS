#!/usr/bin/env python3
"""
Test design + review to see what verdict we get.
"""
import time
from pathlib import Path
from runtime.orchestration.missions.design import DesignMission
from runtime.orchestration.missions.review import ReviewMission
from runtime.orchestration.missions.base import MissionContext

def main():
    repo_root = Path.cwd()
    run_id = f"review-test-{int(time.time())}"
    
    context = MissionContext(
        repo_root=repo_root,
        baseline_commit="test",
        run_id=run_id,
        operation_executor=None
    )
    
    inputs = {
        "task_spec": "Add a comment '# LifeOS Quickstart Guide' at line 1 of docs/00_foundations/QUICKSTART.md",
        "context_refs": ["docs/00_foundations/QUICKSTART.md"]
    }
    
    print("=" * 80)
    print("DESIGN + REVIEW TEST")
    print("=" * 80)
    print(f"Task: {inputs['task_spec']}")
    print("=" * 80)
    print()
    
    # Run design
    print("Running DesignMission...")
    design = DesignMission()
    d_res = design.run(context, inputs)
    
    print(f"  Success: {d_res.success}")
    print(f"  Error: {d_res.error}")
    
    if not d_res.success:
        print("Design failed, stopping.")
        return 1
    
    build_packet = d_res.outputs["build_packet"]
    print(f"  Build packet keys: {list(build_packet.keys())}")
    print()
    
    # Run review
    print("Running ReviewMission on design...")
    review = ReviewMission()
    r_res = review.run(context, {
        "subject_packet": build_packet,
        "review_type": "build_review"
    })
    
    print(f"  Success: {r_res.success}")
    print(f"  Error: {r_res.error}")
    print(f"  Verdict: {r_res.outputs.get('verdict')}")
    print(f"  Output keys: {list(r_res.outputs.keys())}")
    
    if r_res.outputs.get("verdict") != "approved":
        print(f"\n  ⚠️  Design was REJECTED")
        print(f"  Council decision: {r_res.outputs.get('council_decision', {})}")
    else:
        print(f"\n  ✅ Design was APPROVED")
    
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    exit(main())
