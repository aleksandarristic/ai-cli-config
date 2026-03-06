# Task Management Standard (Lean v2)

This standard keeps task tracking fast, resumable, and low-overhead.

## Principles

- Stable IDs and clear history.
- Minimal mandatory files.
- Small active context.
- Fast defaults over ceremony.

## Default Files (Required)

Use `.task-management/` with these files:

- `TODO.md`: active tasks only.
- `DONE.md`: completed and removed tasks.
- `BUGS.md`: open bugs only.
- `BUGS_DONE.md`: resolved bugs.
- `progress_log.md`: append-only milestone log.

## Optional Files

Use only when needed:

- `BACKLOG.md`: unscheduled future work.
- `notify.py`, `.notify_config.json`, `.notify_state.json`, `.webhook.json`: agent-driven Discord notifications.
- `TASK_TEMPLATE.md`, `BUG_TEMPLATE.md`: copy/paste helpers.
- `task_counter.md`, `bug_counter.md`: legacy compatibility only.
- `.ops.json`, `.tm.lock`: runtime files created by `task_tool.py` for idempotency/locking (do not commit).

Security:

- `.task-management/.webhook.json` contains secret data.
- Add `.task-management/.webhook.json`, `.task-management/.ops.json`, `.task-management/.tm.lock`, and `.task-management/__pycache__/` to `.gitignore`.

## ID Rules

- Task IDs: `0001`, `0002`, ...
- Bug IDs: `BUG-0001`, `BUG-0002`, ...
- IDs are never reused and never renumbered.
- Next ID should be derived from existing entries (preferred) or read from legacy counters if present.

## Task Lifecycle

1. Add to `TODO.md` (or `BACKLOG.md` if not near-term).
2. Keep entry concise and execution-ready.
3. On completion, move entry to `DONE.md` with status `done`.
4. On cancellation, move entry to `DONE.md` with status `removed` and a short reason.

## Bug Lifecycle

1. Add bug to `BUGS.md`.
2. Link at least one fix task ID when possible.
3. On resolution, move bug to `BUGS_DONE.md` with a short resolution note.

## Entry Format (Compact)

Task entries should include only:

- title
- objective
- acceptance (1-3 checks)
- dependencies (optional)

Bug entries should include only:

- summary
- observed behavior
- expected behavior
- linked fix task IDs (optional early, required before close)

## Execution Defaults

- If tasks are independent: execute in parallel.
- If tasks conflict/depend: execute in sequence.
- Ask for clarification only when risk is non-trivial.
- If unclear and unblocked: default to sequence.

## Validation Defaults

- Run contextual tests needed for changed behavior.
- Run full-suite only when requested or risk justifies it.

## Progress Log Rules

- Append-only.
- Milestones only: start, blocked, done, handoff.
- Keep entries one line with date.

## Context Budget Rules

- Keep `TODO.md` short; move finished/removed quickly.
- Prefer bullets and short fields.
- Keep acceptance criteria concrete and testable.
- Avoid long narrative plans inside task entries.

## Fast Path Tooling

Use `.task-management/task_tool.py` for common operations:

- `python3 .task-management/task_tool.py next-task-id`
- `python3 .task-management/task_tool.py add-task --title "Short title"`
- `python3 .task-management/task_tool.py list --file todo`
- `python3 .task-management/task_tool.py status-task --id 0042`
- `python3 .task-management/task_tool.py done-task --id 0042 --note "Shipped"`
- `python3 .task-management/task_tool.py remove-task --id 0043 --reason "No longer needed"`
- `python3 .task-management/task_tool.py add-bug --title "Short bug title"`
- `python3 .task-management/task_tool.py close-bug --id BUG-0012 --resolution "Fixed race in parser"`
- `python3 .task-management/task_tool.py normalize`
- `python3 .task-management/task_tool.py --json add-task --title "Short title" --op-id task-123`

## Locking and Foreign Edits Policy

- All task-state mutations must go through `python3 .task-management/task_tool.py`.
- Do not manually edit `TODO.md`, `BACKLOG.md`, `DONE.md`, `BUGS.md`, or `BUGS_DONE.md` for normal lifecycle actions.
- Treat `next-task-id` and `next-bug-id` as advisory only; IDs are finalized only by mutating commands.
- If a foreign edit appears while you work, do not revert it.
- Re-read current state, then continue using `task_tool.py` so writes apply on latest locked state.
- If target task/bug is already moved or missing, treat it as already handled, add a short log note, and stop that mutation.
- If status/ownership is unclear after re-read, ask one clarification question before further mutation.
- Never renumber IDs or perform destructive cleanup of entries created by other agents.
- If a mutation command fails, do not patch task files manually; retry via `task_tool.py` (or escalate).
