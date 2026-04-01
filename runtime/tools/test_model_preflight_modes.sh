#!/usr/bin/env bash
# Test script to verify model preflight enforcement modes
set -euo pipefail

echo "=== Model Preflight Enforcement Mode Test ==="
echo

# Create a temp state dir with invalid config
TEST_STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_STATE_DIR"' EXIT

TEST_CONFIG="$TEST_STATE_DIR/openclaw.json"

# Create an INVALID config with empty ladder
cat > "$TEST_CONFIG" <<'JSON'
{
  "agents": {
    "list": [
      {
        "id": "main",
        "model": {
          "primary": "",
          "fallbacks": []
        }
      }
    ]
  }
}
JSON

echo "Test 1: Policy assert with EMPTY ladder (should not crash)"
echo "---"
if python3 runtime/tools/openclaw_model_policy_assert.py \
  --config "$TEST_CONFIG" \
  --models-list-file /dev/null \
  --json 2>&1 | head -5; then
  echo "Exit code: 0 (unexpected - should fail with structured error)"
else
  rc=$?
  echo "Exit code: $rc (expected)"
fi
echo

echo "Test 2: Verify structured error output (no tracebacks)"
echo "---"
if output=$(python3 runtime/tools/openclaw_model_policy_assert.py \
  --config "$TEST_CONFIG" \
  --models-list-file /dev/null \
  --json 2>&1); then
  echo "Unexpected success"
else
  # Check that output is JSON, not a traceback
  if echo "$output" | python3 -m json.tool >/dev/null 2>&1; then
    echo "✓ Output is valid JSON (structured error)"
    echo "$output" | python3 -m json.tool | head -15
  else
    echo "✗ Output is not JSON - may contain traceback:"
    echo "$output" | head -10
  fi
fi
echo

echo "Test 3: Interactive mode enforcement (OPENCLAW_MODELS_PREFLIGHT_OUT_DIR)"
echo "---"
export OPENCLAW_STATE_DIR="$TEST_STATE_DIR"
export OPENCLAW_CONFIG_PATH="$TEST_CONFIG"
export OPENCLAW_BIN="$(which openclaw 2>/dev/null || echo /usr/bin/openclaw)"
export COO_ENFORCEMENT_MODE=interactive
export OPENCLAW_MODELS_PREFLIGHT_OUT_DIR="$TEST_STATE_DIR/preflight_interactive"

if [ -x "$OPENCLAW_BIN" ]; then
  echo "OpenClaw binary exists, running preflight in interactive mode..."
  if runtime/tools/openclaw_models_preflight.sh 2>&1 | head -20; then
    echo "✓ Interactive mode: Exited successfully despite invalid config"
  else
    echo "✗ Interactive mode: Failed (should warn but not block)"
  fi
else
  echo "⊘ Skipping (openclaw binary not found)"
fi
echo

echo "Test 4: Mission mode enforcement"
echo "---"
export COO_ENFORCEMENT_MODE=mission
export OPENCLAW_MODELS_PREFLIGHT_OUT_DIR="$TEST_STATE_DIR/preflight_mission"

if [ -x "$OPENCLAW_BIN" ]; then
  echo "Running preflight in mission mode..."
  if runtime/tools/openclaw_models_preflight.sh 2>&1 | head -20; then
    echo "✗ Mission mode: Should have failed"
  else
    echo "✓ Mission mode: Blocked as expected (fail-closed)"
  fi
else
  echo "⊘ Skipping (openclaw binary not found)"
fi
echo

echo "Test 5: Model ladder fix (dry-run)"
echo "---"
if python3 runtime/tools/openclaw_model_ladder_fix.py \
  --config "$TEST_CONFIG" \
  --dry-run 2>&1 | head -25; then
  echo "✓ Fix script ran successfully"
else
  echo "✗ Fix script failed"
fi
echo

echo "=== Test Summary ==="
echo "Tests completed. Review output above for pass/fail indicators."
