# Claude Code Role Evaluation Plan

**Objective**: Assess `claude-code-mcp` capabilities for specific "Architect" and "Builder" roles in the LifeOS ecosystem.

## 1. Test Harness Setup

A mock repository `mock_repo` will be created with:

- `utils.py`: A bloated python file containing mixed string and math utilities (legacy code).
- `main.py`: A script importing from `utils`.
- `README.md`: Context describing the project.

## 2. Architect Role Test

**Goal**: Analyze code and produce a structured refactoring plan in strict Markdown format.

**Prompt**:
> "You are a Senior Architect. Analyze `utils.py`. The goal is to split it into `string_utils.py` and `math_utils.py`.
> Output a file named `REFACTOR_PLAN.md` containing:
>
> 1. Summary of changes.
> 2. List of functions to move to `string_utils.py`.
> 3. List of functions to move to `math_utils.py`.
> 4. Risk assessment.
> Do NOT execute the refactor. Only plan it."

**Verification**:

- Check if `REFACTOR_PLAN.md` is created.
- Check if it contains the correct function mapping.
- Check if it adheres to the structure.

## 3. Builder Role Test

**Goal**: Execute a provided plan to modify the codebase.

**Prompt** (Chain):
> "You are a Builder. Read `REFACTOR_PLAN.md`.
>
> 1. Create `string_utils.py` and `math_utils.py` with the functions identified in the plan.
> 2. Remove `utils.py`.
> 3. Update `main.py` to import from the new modules.
> 4. Ensure `main.py` still runs (verify with `python main.py`)."

**Verification**:

- `utils.py` does NOT exist.
- `string_utils.py` and `math_utils.py` exist and contain correct code.
- `main.py` imports updated.
- `python main.py` exits with code 0.

## 4. Execution Logic

- **Driver**: `test_roles.js` (Node.js) using the `ClaudeCodeClient` pattern.
- **Config**: Usage of `env.example` keys (Zen/GLM).
- **Latency**: Measurement of "Architect" phase vs "Builder" phase.

## 5. Success Criteria

- **Architect**: Can read multiple files and synthesize a NEW file (`REFACTOR_PLAN.md`) without hallucinating files that don't exist.
- **Builder**: Can perform multi-step file operations (Create, Delete, Edit) and run a shell command (`python`) to verify.
