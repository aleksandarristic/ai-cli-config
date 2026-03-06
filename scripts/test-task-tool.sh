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

# JSON output + idempotent add-task
json_add_1="$(python3 "$TMP_DIR/.task-management/task_tool.py" --json add-task --title "Test Task" --op-id op-add-1)"
json_add_2="$(python3 "$TMP_DIR/.task-management/task_tool.py" --json add-task --title "Test Task duplicate" --op-id op-add-1)"
python3 - <<'PY' "$json_add_1" "$json_add_2"
import json
import sys
first = json.loads(sys.argv[1])
second = json.loads(sys.argv[2])
assert first["id"] == "0001"
assert first["replayed"] is False
assert second["id"] == "0001"
assert second["replayed"] is True
PY

python3 "$TMP_DIR/.task-management/task_tool.py" done-task --id 0001 --note "ok" >/dev/null
rg -q "## 0001 - Test Task" "$TMP_DIR/.task-management/DONE.md"
rg -q -- "- status: done" "$TMP_DIR/.task-management/DONE.md"

# backlog path + remove-task
python3 "$TMP_DIR/.task-management/task_tool.py" add-task --to backlog --title "Backlog Task" >/dev/null
python3 "$TMP_DIR/.task-management/task_tool.py" remove-task --id 0002 --reason "out" >/dev/null
rg -q "## 0002 - Backlog Task" "$TMP_DIR/.task-management/DONE.md"
rg -q -- "- status: removed" "$TMP_DIR/.task-management/DONE.md"

# bug flow + idempotent add-bug
json_bug_1="$(python3 "$TMP_DIR/.task-management/task_tool.py" --json add-bug --title "Test Bug" --op-id op-bug-1)"
json_bug_2="$(python3 "$TMP_DIR/.task-management/task_tool.py" --json add-bug --title "Test Bug duplicate" --op-id op-bug-1)"
python3 - <<'PY' "$json_bug_1" "$json_bug_2"
import json
import sys
first = json.loads(sys.argv[1])
second = json.loads(sys.argv[2])
assert first["id"] == "BUG-0001"
assert first["replayed"] is False
assert second["id"] == "BUG-0001"
assert second["replayed"] is True
PY

python3 "$TMP_DIR/.task-management/task_tool.py" close-bug --id BUG-0001 --resolution "fixed" >/dev/null
rg -q "## BUG-0001 - Test Bug" "$TMP_DIR/.task-management/BUGS_DONE.md"
rg -q -- "- status: resolved" "$TMP_DIR/.task-management/BUGS_DONE.md"

# list + status-task
status_line="$(python3 "$TMP_DIR/.task-management/task_tool.py" status-task --id 0001)"
[[ "$status_line" == *"0001 done DONE.md"* ]]

list_json="$(python3 "$TMP_DIR/.task-management/task_tool.py" --json list --file done)"
python3 - <<'PY' "$list_json"
import json
import sys
payload = json.loads(sys.argv[1])
assert payload["file"] == "done"
assert payload["count"] >= 2
ids = {item["id"] for item in payload["items"]}
assert "0001" in ids and "0002" in ids
PY

# normalize
python3 "$TMP_DIR/.task-management/task_tool.py" normalize >/dev/null

python3 "$TMP_DIR/.task-management/task_tool.py" log --message "milestone" >/dev/null
rg -q "milestone" "$TMP_DIR/.task-management/progress_log.md"

# lock contention: parallel adds must keep unique IDs
(
  cd "$TMP_DIR"
  for i in $(seq 1 12); do
    python3 .task-management/task_tool.py --lock-retries 200 --lock-delay-ms 2 --lock-jitter-ms 2 add-task --title "Parallel $i" >/dev/null &
  done
  wait
)
count="$(rg '^## [0-9]{4} - Parallel ' "$TMP_DIR/.task-management/TODO.md" | wc -l | tr -d ' ')"
uniq_count="$(rg '^## [0-9]{4} - Parallel ' "$TMP_DIR/.task-management/TODO.md" | awk '{print $2}' | sort -u | wc -l | tr -d ' ')"
[[ "$count" == "12" ]]
[[ "$uniq_count" == "12" ]]

echo "task_tool regression check passed"
