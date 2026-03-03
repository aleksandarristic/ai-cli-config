# Task Management Standard

This document defines a lightweight, reusable workflow for tracking engineering tasks with stable IDs and low maintenance overhead.

## Goals

- Keep planning resumable across sessions/agents.
- Preserve traceability of completed/removed work.
- Keep active context small to reduce token usage.
- Keep task documentation execution-mode agnostic (linear or parallel).

## File Layout

Use a dedicated directory (default in this repo: `.task-management/`) with these files:

- `TODO.md`: active tasks only.
- `DONE.md`: completed tasks moved from TODO.
- `BACKLOG.md`: future ideas not scheduled soon.
- `REMOVED.md`: abandoned/cancelled tasks (never silently delete).
- `task_counter.md`: source of truth for the latest/next task ID.
- `BUGS.md`: active/open bugs.
- `BUGS_DONE.md`: resolved/closed bugs moved from `BUGS.md`.
- `bug_counter.md`: source of truth for the latest/next bug ID.
- `progress_log.md`: append-only, high-level execution log.
- `TASK_TEMPLATE.md`: canonical template for new tasks.
- `BUG_TEMPLATE.md`: canonical template for new bugs.
- `notify.py`: Discord notification helper for task progress updates.
- `.notify_config.json`: notification formatting/runtime config.
- `.notify_state.json`: persisted on/off toggle for notifications.
- `.webhook.json`: webhook URL config (must be set to a real URL per repo).

Security note:

- `.task-management/.webhook.json` contains secret data and must be ignored by git.
- Add `.task-management/.webhook.json` to `.gitignore` in each target repository.
- The copy script in this repo does this automatically when task management is copied/upgraded.

## ID Rules

- Task IDs are stable, persistent, and never reused.
- Use zero-padded 4-digit IDs: `0001`, `0002`, ...
- Recommended task header format:

`0001 - Task Title`

- Never renumber existing tasks, even if tasks are removed or reordered.
- Bugs use a separate, stable ID sequence and are never reused.
- Use zero-padded bug IDs with prefix: `BUG-0001`, `BUG-0002`, ...
- Bug IDs are tracked in `bug_counter.md` and are independent from task IDs.

## Task Lifecycle

1. Add new work to `TODO.md` using `next_task_id` from `task_counter.md`.
2. Update `task_counter.md` when a new task ID is created.
3. When finished:
   - remove task from `TODO.md`
   - move it to `DONE.md` with the same ID
4. If dropped/cancelled:
   - remove from `TODO.md` or `BACKLOG.md`
   - move to `REMOVED.md` with reason
5. Optional ideas that are not near-term go to `BACKLOG.md`.

## Bug Lifecycle

1. Add new bug reports to `BUGS.md` using `next_bug_id` from `bug_counter.md`.
2. Update `bug_counter.md` when a new bug ID is created.
3. Each bug entry should include:
   - description/symptoms
   - assumptions about likely trigger/root cause
   - assumptions about likely fix area
4. For each bug, create at least one follow-up fix item in `TODO.md` or `BACKLOG.md`.
5. When resolved:
   - remove bug from `BUGS.md`
   - move to `BUGS_DONE.md` with the same bug ID and resolution note

## Task Notifications

Notification files live in `.task-management/`:

- `notify.py`
- `.notify_config.json`
- `.notify_state.json`
- `.webhook.json`

These notifications are intended to be sent by the Codex agent during task execution. End users are not expected to run `notify.py` manually.

Agent invocation examples:

- `python3 .task-management/notify.py --status`
- `python3 .task-management/notify.py --toggle off`
- `python3 .task-management/notify.py --task "Task 0042" --level done --message "Completed and verified."`
- `python3 .task-management/notify.py --task "Task 0078" --track "Read Experience" --level info --message "Implementing filter wiring."`

After copying task management into a repo, users should set a real webhook URL in `.task-management/.webhook.json`.

## Task Content Template

Each TODO entry should be implementation-resumable and concise:

- objective
- scope
- subtasks
- acceptance criteria
- dependencies (optional)
- risks/unknowns (optional)
- linked bugs (optional)

Keep details at the level needed to resume without re-discovery, but avoid unnecessary prose.

Use `.task-management/TASK_TEMPLATE.md` as the default structure.

## Bug Content Template

Each bug entry should be concise and implementation-resumable:

- bug summary
- observed behavior
- expected behavior
- reproduction hints (if known)
- likely cause assumptions
- likely fix area assumptions
- linked fix task IDs

Use `.task-management/BUG_TEMPLATE.md` as the default structure.

## Execution Mode Protocol

Tasks are documented once and executed in one of these modes based on user instruction:

- sequence: execute selected tasks one by one.
- parallel: execute selected tasks in parallel when safe.
- parallel_worktrees: execute selected tasks in parallel with one worktree/branch per task.

Rules:

1. If the user explicitly names an execution mode, follow it.
2. If multiple tasks are requested without a mode, ask one concise clarification question before execution.
3. If dependencies/conflicts make parallel execution unsafe, propose sequence mode and explain why.
4. Keep task documentation mode-agnostic; only status/progress should change during execution.
5. If no clarification is possible, default to `sequence`.

Examples of valid execution instructions:

- `do tasks 1 through 3 in parallel using worktrees`
- `do tasks 1, 2, 3 in sequence`
- `do tasks 1, 2, 3, 4` (agent asks: sequence or parallel?)

Prompt examples for multi-task execution:

- Sequential: `do tasks 0041, 0042, and 0043 in sequence`
- Parallel (shared workspace): `do tasks 0041, 0042, and 0043 in parallel`
- Parallel (worktrees): `do tasks 0041, 0042, and 0043 in parallel using worktrees`

## Progress Log Rules

- `progress_log.md` is append-only.
- Log high-level milestones, not every command.
- Use timestamps and concise entries.
- Never rewrite or delete historical log lines; add corrections as new lines.

## Validation Strategy

- By default, run only necessary and contextual tests for the change being made.
- Run broader/full test suites only when explicitly requested or when risk requires it.

## Token/Usability Guidance

- Keep `TODO.md` focused on active tasks only; move done/removed items out quickly.
- Prefer concise bullets over long narrative text.
- Use `DONE.md`/`REMOVED.md` as archival history to keep active planning small.
- Use `BUGS_DONE.md` as archival bug history to keep active bug context small.
- Keep execution instructions short and explicit so agents can act with fewer tool calls.
