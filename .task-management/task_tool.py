#!/usr/bin/env python3
"""Lightweight task/bug operations for .task-management markdown files.

This tool avoids manual ID bookkeeping and repetitive move operations.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import random
import re
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional

TM_DIR = Path(__file__).resolve().parent
TODO_FILE = TM_DIR / "TODO.md"
BACKLOG_FILE = TM_DIR / "BACKLOG.md"
DONE_FILE = TM_DIR / "DONE.md"
BUGS_FILE = TM_DIR / "BUGS.md"
BUGS_DONE_FILE = TM_DIR / "BUGS_DONE.md"
PROGRESS_FILE = TM_DIR / "progress_log.md"
TASK_COUNTER_FILE = TM_DIR / "task_counter.md"
BUG_COUNTER_FILE = TM_DIR / "bug_counter.md"
LOCK_FILE = TM_DIR / ".tm.lock"

START_MARKER = "<!-- entries:start -->"
END_MARKER = "<!-- entries:end -->"

TASK_HEADER_RE = re.compile(r"^##\s*(\d{4})\s*-\s*(.+?)\s*$")
BUG_HEADER_RE = re.compile(r"^##\s*(BUG-\d{4})\s*-\s*(.+?)\s*$")
TASK_ANY_ID_RE = re.compile(r"(?<!\d)(\d{4})(?!\d)")


@dataclass
class Entry:
    entry_id: str
    title: str
    body: List[str]


class TaskToolError(RuntimeError):
    pass


def _today() -> str:
    return date.today().isoformat()


def _normalize(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _ensure_markers(text: str) -> str:
    if START_MARKER in text and END_MARKER in text:
        return _normalize(text)
    base = _normalize(text).rstrip("\n")
    return f"{base}\n\n{START_MARKER}\n{END_MARKER}\n"


def _read(path: Path) -> str:
    if not path.exists():
        raise TaskToolError(f"Missing file: {path}")
    return _ensure_markers(path.read_text(encoding="utf-8"))


def _write(path: Path, text: str) -> None:
    data = _normalize(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    ) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def _split_sections(text: str) -> tuple[str, str, str]:
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise TaskToolError("Entries markers are missing or malformed")
    prefix = text[: start + len(START_MARKER)]
    entries = text[start + len(START_MARKER) : end]
    suffix = text[end:]
    return prefix, entries, suffix


def _parse_entries(entries_text: str, header_re: re.Pattern[str]) -> list[Entry]:
    lines = entries_text.splitlines()
    out: list[Entry] = []
    current: Optional[Entry] = None

    for raw in lines:
        line = raw.rstrip("\n")
        m = header_re.match(line.strip())
        if m:
            if current is not None:
                out.append(current)
            current = Entry(entry_id=m.group(1), title=m.group(2).strip(), body=[line])
            continue

        if current is None:
            if line.strip() == "":
                continue
            # Non-entry content in entries section is ignored to keep parser tolerant.
            continue

        current.body.append(line)

    if current is not None:
        out.append(current)

    return out


def _render_entries(entries: Iterable[Entry]) -> str:
    blocks: list[str] = []
    for entry in entries:
        block = "\n".join(entry.body).rstrip()
        blocks.append(block)
    if not blocks:
        return "\n"
    return "\n\n" + "\n\n".join(blocks) + "\n"


def _replace_entries(path: Path, new_entries: Iterable[Entry]) -> None:
    text = _read(path)
    prefix, _, suffix = _split_sections(text)
    rendered = _render_entries(new_entries)
    _write(path, f"{prefix}{rendered}{suffix}")


def _load_entries(path: Path, header_re: re.Pattern[str]) -> list[Entry]:
    text = _read(path)
    _, entries_text, _ = _split_sections(text)
    return _parse_entries(entries_text, header_re)


def _collect_existing_task_ids() -> set[int]:
    ids: set[int] = set()
    for path in (TODO_FILE, BACKLOG_FILE, DONE_FILE):
        if not path.exists():
            continue
        for entry in _load_entries(path, TASK_HEADER_RE):
            ids.add(int(entry.entry_id))

    legacy = TM_DIR / "REMOVED.md"
    if legacy.exists():
        text = legacy.read_text(encoding="utf-8")
        for match in TASK_ANY_ID_RE.findall(text):
            ids.add(int(match))

    if TASK_COUNTER_FILE.exists():
        text = TASK_COUNTER_FILE.read_text(encoding="utf-8")
        latest = re.search(r"latest_task_id:\s*(\d{4})", text)
        if latest:
            ids.add(int(latest.group(1)))
        nxt = re.search(r"next_task_id:\s*(\d{4})", text)
        if nxt:
            value = int(nxt.group(1))
            if value > 0:
                ids.add(value - 1)
    return ids


def _collect_existing_bug_ids() -> set[int]:
    ids: set[int] = set()
    for path in (BUGS_FILE, BUGS_DONE_FILE):
        if not path.exists():
            continue
        for entry in _load_entries(path, BUG_HEADER_RE):
            ids.add(int(entry.entry_id.split("-")[1]))

    if BUG_COUNTER_FILE.exists():
        text = BUG_COUNTER_FILE.read_text(encoding="utf-8")
        latest = re.search(r"latest_bug_id:\s*BUG-(\d{4})", text)
        if latest:
            ids.add(int(latest.group(1)))
        nxt = re.search(r"next_bug_id:\s*BUG-(\d{4})", text)
        if nxt:
            value = int(nxt.group(1))
            if value > 0:
                ids.add(value - 1)
    return ids


def next_task_id() -> str:
    existing = _collect_existing_task_ids()
    nxt = max(existing) + 1 if existing else 1
    return f"{nxt:04d}"


def next_bug_id() -> str:
    existing = _collect_existing_bug_ids()
    nxt = max(existing) + 1 if existing else 1
    return f"BUG-{nxt:04d}"


def _build_task_entry(entry_id: str, title: str, objective: str, acceptance: list[str], status: str) -> Entry:
    checks = acceptance or ["Primary behavior works.", "Relevant tests pass."]
    body = [
        f"## {entry_id} - {title.strip()}",
        f"- status: {status}",
        f"- objective: {objective.strip()}",
        "- acceptance:",
    ]
    body.extend([f"  - [ ] {item.strip()}" for item in checks])
    body.extend(["- dependencies:", "- links:", f"- updated: {_today()}"])
    return Entry(entry_id=entry_id, title=title.strip(), body=body)


def _build_bug_entry(entry_id: str, title: str, observed: str, expected: str) -> Entry:
    body = [
        f"## {entry_id} - {title.strip()}",
        "- status: open",
        f"- observed: {observed.strip()}",
        f"- expected: {expected.strip()}",
        "- reproduction:",
        "- links:",
        f"- updated: {_today()}",
    ]
    return Entry(entry_id=entry_id, title=title.strip(), body=body)


def _append_entry(path: Path, header_re: re.Pattern[str], entry: Entry) -> None:
    entries = _load_entries(path, header_re)
    entries.append(entry)
    _replace_entries(path, entries)


def _find_and_remove(task_id: str, paths: list[Path], header_re: re.Pattern[str]) -> tuple[Entry, Path]:
    for path in paths:
        entries = _load_entries(path, header_re)
        remaining: list[Entry] = []
        found: Optional[Entry] = None
        for entry in entries:
            if entry.entry_id == task_id and found is None:
                found = entry
            else:
                remaining.append(entry)
        if found is not None:
            _replace_entries(path, remaining)
            return found, path
    raise TaskToolError(f"Entry not found: {task_id}")


@contextmanager
def _acquire_lock(retries: int, delay_ms: int, jitter_ms: int):
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("a+", encoding="utf-8") as lock_handle:
        for attempt in range(retries + 1):
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if attempt == retries:
                    raise TaskToolError(
                        f"Could not acquire lock at {LOCK_FILE} after {retries + 1} attempts"
                    ) from None
                sleep_ms = delay_ms + random.randint(0, max(0, jitter_ms))
                time.sleep(sleep_ms / 1000.0)
        try:
            yield
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _is_mutation(command: str) -> bool:
    return command in {"add-task", "done-task", "remove-task", "add-bug", "close-bug", "log"}


def cmd_next_task_id(_: argparse.Namespace) -> None:
    print(next_task_id())


def cmd_next_bug_id(_: argparse.Namespace) -> None:
    print(next_bug_id())


def cmd_add_task(args: argparse.Namespace) -> None:
    entry_id = next_task_id()
    target = TODO_FILE if args.to == "todo" else BACKLOG_FILE
    status = "active" if args.to == "todo" else "backlog"
    entry = _build_task_entry(entry_id, args.title, args.objective, args.acceptance, status)
    _append_entry(target, TASK_HEADER_RE, entry)
    print(f"{entry_id} {target.name}")


def cmd_done_task(args: argparse.Namespace) -> None:
    entry, source = _find_and_remove(args.id, [TODO_FILE, BACKLOG_FILE], TASK_HEADER_RE)
    body = [line for line in entry.body if not line.startswith("- status:")]
    body.append("- status: done")
    body.append(f"- completed: {_today()}")
    if args.note:
        body.append(f"- note: {args.note.strip()}")
    moved = Entry(entry_id=entry.entry_id, title=entry.title, body=body)
    _append_entry(DONE_FILE, TASK_HEADER_RE, moved)
    print(f"{args.id} moved {source.name} -> {DONE_FILE.name}")


def cmd_remove_task(args: argparse.Namespace) -> None:
    entry, source = _find_and_remove(args.id, [TODO_FILE, BACKLOG_FILE], TASK_HEADER_RE)
    body = [line for line in entry.body if not line.startswith("- status:")]
    body.append("- status: removed")
    body.append(f"- removed: {_today()}")
    body.append(f"- reason: {args.reason.strip()}")
    moved = Entry(entry_id=entry.entry_id, title=entry.title, body=body)
    _append_entry(DONE_FILE, TASK_HEADER_RE, moved)
    print(f"{args.id} moved {source.name} -> {DONE_FILE.name}")


def cmd_add_bug(args: argparse.Namespace) -> None:
    entry_id = next_bug_id()
    entry = _build_bug_entry(entry_id, args.title, args.observed, args.expected)
    _append_entry(BUGS_FILE, BUG_HEADER_RE, entry)
    print(f"{entry_id} {BUGS_FILE.name}")


def cmd_close_bug(args: argparse.Namespace) -> None:
    entry, _ = _find_and_remove(args.id, [BUGS_FILE], BUG_HEADER_RE)
    body = [line for line in entry.body if not line.startswith("- status:")]
    body.append("- status: resolved")
    body.append(f"- resolved: {_today()}")
    body.append(f"- resolution: {args.resolution.strip()}")
    moved = Entry(entry_id=entry.entry_id, title=entry.title, body=body)
    _append_entry(BUGS_DONE_FILE, BUG_HEADER_RE, moved)
    print(f"{args.id} moved {BUGS_FILE.name} -> {BUGS_DONE_FILE.name}")


def cmd_log(args: argparse.Namespace) -> None:
    if not PROGRESS_FILE.exists():
        raise TaskToolError(f"Missing file: {PROGRESS_FILE}")
    with PROGRESS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"- {_today()}: {args.message.strip()}\n")
    print("logged")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Task management helper")
    parser.add_argument(
        "--lock-retries",
        type=int,
        default=40,
        help="How many times to retry lock acquisition for mutating commands (default: 40)",
    )
    parser.add_argument(
        "--lock-delay-ms",
        type=int,
        default=20,
        help="Base delay in ms between lock retries (default: 20)",
    )
    parser.add_argument(
        "--lock-jitter-ms",
        type=int,
        default=40,
        help="Extra random jitter in ms added to lock retry delay (default: 40)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("next-task-id", help="Print next task ID")
    p.set_defaults(func=cmd_next_task_id)

    p = sub.add_parser("next-bug-id", help="Print next bug ID")
    p.set_defaults(func=cmd_next_bug_id)

    p = sub.add_parser("add-task", help="Add task to TODO/BACKLOG")
    p.add_argument("--title", required=True, help="Task title")
    p.add_argument("--objective", default="Implement the task outcome.", help="One-line objective")
    p.add_argument("--acceptance", action="append", default=[], help="Acceptance check (repeatable)")
    p.add_argument("--to", choices=["todo", "backlog"], default="todo")
    p.set_defaults(func=cmd_add_task)

    p = sub.add_parser("done-task", help="Move task to DONE with done status")
    p.add_argument("--id", required=True, help="Task ID, e.g. 0042")
    p.add_argument("--note", default="", help="Optional completion note")
    p.set_defaults(func=cmd_done_task)

    p = sub.add_parser("remove-task", help="Move task to DONE with removed status")
    p.add_argument("--id", required=True, help="Task ID, e.g. 0042")
    p.add_argument("--reason", required=True, help="Removal reason")
    p.set_defaults(func=cmd_remove_task)

    p = sub.add_parser("add-bug", help="Add open bug")
    p.add_argument("--title", required=True, help="Bug title")
    p.add_argument("--observed", default="Observed incorrect behavior.", help="Observed behavior")
    p.add_argument("--expected", default="Expected behavior.", help="Expected behavior")
    p.set_defaults(func=cmd_add_bug)

    p = sub.add_parser("close-bug", help="Move bug to BUGS_DONE")
    p.add_argument("--id", required=True, help="Bug ID, e.g. BUG-0007")
    p.add_argument("--resolution", required=True, help="Resolution summary")
    p.set_defaults(func=cmd_close_bug)

    p = sub.add_parser("log", help="Append one progress log line")
    p.add_argument("--message", required=True, help="Milestone message")
    p.set_defaults(func=cmd_log)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.lock_retries < 0 or args.lock_delay_ms < 0 or args.lock_jitter_ms < 0:
        parser.exit(status=1, message="error: lock retry settings must be non-negative\n")
    try:
        if _is_mutation(args.command):
            with _acquire_lock(args.lock_retries, args.lock_delay_ms, args.lock_jitter_ms):
                args.func(args)
        else:
            args.func(args)
    except TaskToolError as exc:
        parser.exit(status=1, message=f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
