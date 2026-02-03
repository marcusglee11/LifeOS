#!/usr/bin/env bash
# Audit all branches and stashes for merge planning

echo "=== Branch Inventory ==="
for branch in $(git branch | sed 's/\*//'); do
  ahead=$(git log main..$branch --oneline 2>/dev/null | wc -l)
  behind=$(git log $branch..main --oneline 2>/dev/null | wc -l)
  last_commit=$(git log -1 --format="%ar" $branch 2>/dev/null)
  echo "$branch: +$ahead -$behind (last: $last_commit)"
done

echo -e "\n=== Stash Inventory ==="
git stash list --format="%gd: %gs (saved %ar)"

echo -e "\n=== Test Status (LifeOS) ==="
current_branch=$(git branch --show-current)
for branch in $(git branch | sed 's/\*//'); do
  git checkout $branch 2>/dev/null
  test_count=$(pytest runtime/tests -q 2>&1 | grep -oP '\d+(?= passed)' || echo "ERROR")
  echo "$branch: $test_count passing tests"
done
git checkout $current_branch

echo -e "\n=== LifeOS State Check ==="
if [[ -f "docs/11_admin/LIFEOS_STATE.md" ]]; then
  echo "Current Focus: $(grep -A1 'Current Focus:' docs/11_admin/LIFEOS_STATE.md | tail -1)"
  echo "Active WIP: $(grep -A1 'Active WIP:' docs/11_admin/LIFEOS_STATE.md | tail -1)"
else
  echo "WARNING: LIFEOS_STATE.md not found"
fi
