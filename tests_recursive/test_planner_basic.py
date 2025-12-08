import pytest
import yaml
import os
from recursive_kernel.planner import Planner

def test_planner_basic(tmpdir):
    config = tmpdir.join("config.yaml")
    backlog = tmpdir.join("backlog.yaml")
    
    config.write(yaml.dump({"safe_domains": ["safe"]}))
    backlog.write(yaml.dump({
        "tasks": [
            {"id": "1", "domain": "unsafe", "status": "todo", "type": "x", "description": "x"},
            {"id": "2", "domain": "safe", "status": "done", "type": "x", "description": "x"},
            {"id": "3", "domain": "safe", "status": "todo", "type": "x", "description": "x"}
        ]
    }))
    
    p = Planner(str(config), str(backlog))
    task = p.plan_next_task()
    
    assert task is not None
    assert task.id == "3"
    assert task.domain == "safe"

def test_planner_real_config():
    # Smoke test for real files
    if os.path.exists("config/recursive_kernel_config.yaml") and os.path.exists("config/backlog.yaml"):
        p = Planner("config/recursive_kernel_config.yaml", "config/backlog.yaml")
        # should not crash
        p.plan_next_task()
