#!/usr/bin/env python3
"""
Test just the design mission to see if that's where the problem is.
"""
import time
from pathlib import Path
from runtime.orchestration.missions.design import DesignMission
from runtime.orchestration.missions.base import MissionContext

def main():
    repo_root = Path.cwd()
    run_id = f"design-test-{int(time.time())}"
    
    context = MissionContext(
        repo_root=repo_root,
        baseline_commit="test",
        run_id=run_id,
        operation_executor=None
    )
    
    inputs = {
        "task_spec": "Add a helpful introductory comment at the top of docs/00_foundations/QUICKSTART.md explaining this file is the primary entry point for new LifeOS contributors",
        "context_refs": ["docs/00_foundations/QUICKSTART.md"]
    }
    
    print("=" * 80)
    print("DESIGN MISSION TEST")
    print("=" * 80)
    print(f"Run ID: {run_id}")
    print(f"Task: {inputs['task_spec']}")
    print("=" * 80)
    print()
    
    mission = DesignMission()
    result = mission.run(context, inputs)
    
    print()
    print("=" * 80)
    print("RESULT")
    print("=" * 80)
    print(f"Success: {result.success}")
    print(f"Error: {result.error}")
    print(f"Steps executed: {len(result.executed_steps)}")
    for step in result.executed_steps:
        print(f"  - {step}")
    
    if result.success:
        print(f"\nBuild packet generated:")
        build_packet = result.outputs.get("build_packet", {})
        print(f"  Deliverables: {len(build_packet.get('deliverables', []))}")
        if build_packet.get('deliverables'):
            for i, d in enumerate(build_packet['deliverables']):
                print(f"    {i+1}. {d.get('action')} {d.get('path')}")
    
    print("=" * 80)
    
    return 0 if result.success else 1

if __name__ == "__main__":
    exit(main())
