# BUGS_DONE

Resolved bugs with short resolution notes.

<!-- entries:start -->

## BUG-0001 - No regression test for task_tool ID+move flow
- observed: ID allocation and move behavior can regress unnoticed
- expected: A small repeatable test validates ID and state transitions
- reproduction:
- links:
- updated: 2026-03-04
- status: resolved
- resolved: 2026-03-04
- resolution: Added scripts/test-task-tool.sh to cover ID allocation and move transitions (task 0001)
<!-- entries:end -->
