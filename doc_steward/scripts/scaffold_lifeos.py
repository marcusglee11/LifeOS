import os
import pathlib

# Define the target root relative to this script (assumed to be in docs/)
# If this script is in LifeOS/docs/, then root is ..
ROOT_DIR = pathlib.Path(__file__).parent.parent.resolve()

DIRS_TO_CREATE = [
    "runtime",
    "runtime/tests",
    "docs",
    "docs/00_foundations",
    "docs/01_governance",
    "docs/02_alignment",
    "docs/03_runtime",
    "docs/04_project_builder",
    "docs/05_agents",
    "docs/06_user_surface",
    "docs/07_testing",
    "docs/08_manuals",
    "docs/09_prompts",
    "docs/99_archive",
    "doc_steward",
    "tests_doc",
    "config",
    "recursive_kernel",
    "tests_recursive",
    "logs/recursive_runs",
    "scripts",
    ".github/workflows",
]

FILES_TO_CREATE = {
    "runtime/__init__.py": "",
    "runtime/engine.py": "# Core Runtime Engine (FSM)",
    "runtime/state_store.py": "# Persistence layer",
    "runtime/freeze.py": "# Freeze logic",
    "runtime/sign.py": "# Signing logic",
    "runtime/invariants.py": "# Invariant checks",
    "runtime/cli.py": "# CLI entrypoint",
    "runtime/tests/__init__.py": "",
    "runtime/tests/test_engine.py": "",
    "runtime/tests/test_state_store.py": "",
    "runtime/tests/test_invariants.py": "",
    "runtime/tests/test_freeze_sign.py": "",
    
    "doc_steward/__init__.py": "",
    "doc_steward/rules.py": "",
    "doc_steward/index_checker.py": "",
    "doc_steward/link_checker.py": "",
    "doc_steward/dap_validator.py": "",
    
    "tests_doc/__init__.py": "",
    "tests_doc/test_index_consistency.py": "",
    "tests_doc/test_links.py": "",
    "tests_doc/test_dap_compliance.py": "",
    
    "recursive_kernel/__init__.py": "",
    "recursive_kernel/planner.py": "",
    "recursive_kernel/builder.py": "",
    "recursive_kernel/verifier.py": "",
    "recursive_kernel/autogate.py": "",
    "recursive_kernel/runner.py": "",
    
    "tests_recursive/__init__.py": "",
    "tests_recursive/test_planner_basic.py": "",
    "tests_recursive/test_verifier_mock.py": "",
    "tests_recursive/test_autogate_rules.py": "",
    
    "config/recursive_kernel_config.yaml": "# Recursive Kernel Config",
    "config/backlog.yaml": "# Project Backlog",
    
    "scripts/run_recursive_kernel_nightly.sh": "#!/bin/bash\n# Nightly run script",
    
    ".github/workflows/recursive_kernel_nightly.yml": "# GitHub Action Workflow",
    
    "README_RUNTIME.md": "# Runtime Documentation",
    "README_Recursive_Kernel_v0.1.md": "# Recursive Kernel Documentation",
    "pyproject.toml": "# Project Metadata", 
}

def scaffold():
    print(f"Scaffolding LifeOS in: {ROOT_DIR}")
    
    # Create directories
    for d in DIRS_TO_CREATE:
        path = ROOT_DIR / d
        if not path.exists():
            print(f"Creating directory: {d}")
            path.mkdir(parents=True, exist_ok=True)
        else:
            print(f"Directory exists: {d}")

    # Create files
    for rel_path, content in FILES_TO_CREATE.items():
        path = ROOT_DIR / rel_path
        if not path.exists():
            print(f"Creating file: {rel_path}")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            print(f"File exists (skipping): {rel_path}")
            
    print("Scaffolding complete.")

if __name__ == "__main__":
    scaffold()
