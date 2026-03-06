#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

mkdir -p "$TMP_DIR/.task-management"
cp "$ROOT_DIR/.task-management/task_tool.py" "$TMP_DIR/.task-management/task_tool.py"

cat > "$TMP_DIR/.task-management/TODO.md" <<'DOC'
# TODO

Active tasks only.

<!-- entries:start -->
<!-- entries:end -->
DOC

cat > "$TMP_DIR/.task-management/BACKLOG.md" <<'DOC'
# BACKLOG

Unscheduled tasks.

<!-- entries:start -->
<!-- entries:end -->
DOC

cat > "$TMP_DIR/.task-management/DONE.md" <<'DOC'
# DONE

Completed tasks.

<!-- entries:start -->
<!-- entries:end -->
DOC

cat > "$TMP_DIR/.task-management/BUGS.md" <<'DOC'
# BUGS

Open bugs.

<!-- entries:start -->
<!-- entries:end -->
DOC

cat > "$TMP_DIR/.task-management/BUGS_DONE.md" <<'DOC'
# BUGS_DONE

Resolved bugs.

<!-- entries:start -->
<!-- entries:end -->
DOC

cat > "$TMP_DIR/.task-management/progress_log.md" <<'DOC'
# Progress Log
DOC

next_task_id="$(python3 "$TMP_DIR/.task-management/task_tool.py" next-task-id)"
[[ "$next_task_id" == "0001" ]]

next_bug_id="$(python3 "$TMP_DIR/.task-management/task_tool.py" next-bug-id)"
[[ "$next_bug_id" == "BUG-0001" ]]

python3 "$TMP_DIR/.task-management/task_tool.py" add-task --title "Test Task" >/dev/null
python3 "$TMP_DIR/.task-management/task_tool.py" done-task --id 0001 --note "ok" >/dev/null

rg -q "## 0001 - Test Task" "$TMP_DIR/.task-management/DONE.md"
rg -q -- "- status: done" "$TMP_DIR/.task-management/DONE.md"

python3 "$TMP_DIR/.task-management/task_tool.py" add-bug --title "Test Bug" >/dev/null
python3 "$TMP_DIR/.task-management/task_tool.py" close-bug --id BUG-0001 --resolution "fixed" >/dev/null

rg -q "## BUG-0001 - Test Bug" "$TMP_DIR/.task-management/BUGS_DONE.md"
rg -q -- "- status: resolved" "$TMP_DIR/.task-management/BUGS_DONE.md"

python3 "$TMP_DIR/.task-management/task_tool.py" log --message "milestone" >/dev/null
rg -q "milestone" "$TMP_DIR/.task-management/progress_log.md"

echo "task_tool regression check passed"
