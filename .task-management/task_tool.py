#!/usr/bin/env python3
"""Lightweight task/bug operations for .task-management markdown files.

This tool avoids manual ID bookkeeping and repetitive move operations.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import random
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

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
OPS_FILE = TM_DIR / ".ops.json"

START_MARKER = "<!-- entries:start -->"
END_MARKER = "<!-- entries:end -->"

TASK_HEADER_RE = re.compile(r"^##\s*(\d{4})\s*-\s*(.+?)\s*$")
BUG_HEADER_RE = re.compile(r"^##\s*(BUG-\d{4})\s*-\s*(.+?)\s*$")
TASK_ANY_ID_RE = re.compile(r"(?<!\d)(\d{4})(?!\d)")
STATUS_RE = re.compile(r"^- status:\s*(.+?)\s*$")

DEFAULT_FILE_CONTENTS: dict[Path, str] = {
    TODO_FILE: "# TODO\n\nActive tasks only.\n\n<!-- entries:start -->\n<!-- entries:end -->\n",
    BACKLOG_FILE: "# BACKLOG\n\nUnscheduled or lower-priority tasks.\n\n<!-- entries:start -->\n<!-- entries:end -->\n",
    DONE_FILE: "# DONE\n\nCompleted or removed tasks.\n\n<!-- entries:start -->\n<!-- entries:end -->\n",
    BUGS_FILE: "# BUGS\n\nOpen bugs only.\n\n<!-- entries:start -->\n<!-- entries:end -->\n",
    BUGS_DONE_FILE: "# BUGS_DONE\n\nResolved bugs with short resolution notes.\n\n<!-- entries:start -->\n<!-- entries:end -->\n",
    PROGRESS_FILE: "# Progress Log\n\nAppend-only milestones. One line per milestone.\n",
}

LIST_FILE_MAP = {
    "todo": (TODO_FILE, TASK_HEADER_RE),
    "backlog": (BACKLOG_FILE, TASK_HEADER_RE),
    "done": (DONE_FILE, TASK_HEADER_RE),
    "bugs": (BUGS_FILE, BUG_HEADER_RE),
    "bugs_done": (BUGS_DONE_FILE, BUG_HEADER_RE),
}


@dataclass
class Entry:
    entry_id: str
    title: str
    body: list[str]


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
    content = path.read_text(encoding="utf-8")
    if path in (TODO_FILE, BACKLOG_FILE, DONE_FILE, BUGS_FILE, BUGS_DONE_FILE):
        return _ensure_markers(content)
    return _normalize(content)


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


def _entry_status(entry: Entry) -> str:
    for line in entry.body:
        m = STATUS_RE.match(line.strip())
        if m:
            return m.group(1).strip()
    return "unknown"


def _emit(args: argparse.Namespace, payload: dict, text: Optional[str] = None) -> None:
    if args.json:
        print(json.dumps(payload, sort_keys=True))
        return
    if text:
        print(text)
        return
    message = payload.get("message")
    if isinstance(message, str) and message:
        print(message)


def _load_ops() -> dict[str, dict]:
    if not OPS_FILE.exists():
        return {}
    try:
        raw = OPS_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TaskToolError(f"Corrupt ops file: {OPS_FILE}: {exc}") from exc
    if not isinstance(data, dict):
        raise TaskToolError(f"Corrupt ops file: {OPS_FILE} must contain a JSON object")
    return data


def _save_ops(ops: dict[str, dict]) -> None:
    _write(OPS_FILE, json.dumps(ops, indent=2, sort_keys=True) + "\n")


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
def _acquire_lock(retries: int, delay_ms: int, jitter_ms: int, notice_ms: int):
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    wait_notice_shown = False

    with LOCK_FILE.open("a+", encoding="utf-8") as lock_handle:
        for attempt in range(retries + 1):
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                waited_ms = int((time.monotonic() - start) * 1000)
                if wait_notice_shown:
                    print(f"acquired task lock after {waited_ms}ms", file=sys.stderr)
                break
            except BlockingIOError:
                waited_ms = int((time.monotonic() - start) * 1000)
                if notice_ms >= 0 and not wait_notice_shown and waited_ms >= notice_ms:
                    print(f"waiting for task lock: {LOCK_FILE}", file=sys.stderr)
                    wait_notice_shown = True
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
    return command in {
        "add-task",
        "done-task",
        "remove-task",
        "add-bug",
        "close-bug",
        "log",
        "normalize",
    }


def cmd_next_task_id(args: argparse.Namespace) -> None:
    task_id = next_task_id()
    _emit(args, {"command": "next-task-id", "id": task_id}, task_id)


def cmd_next_bug_id(args: argparse.Namespace) -> None:
    bug_id = next_bug_id()
    _emit(args, {"command": "next-bug-id", "id": bug_id}, bug_id)


def cmd_add_task(args: argparse.Namespace) -> None:
    target = TODO_FILE if args.to == "todo" else BACKLOG_FILE
    status = "active" if args.to == "todo" else "backlog"

    if args.op_id:
        ops = _load_ops()
        existing = ops.get(args.op_id)
        if existing is not None:
            if existing.get("command") != "add-task":
                raise TaskToolError(f"op-id {args.op_id} already used for {existing.get('command')}")
            payload = {
                "command": "add-task",
                "id": str(existing["id"]),
                "file": str(existing["file"]),
                "title": str(existing["title"]),
                "op_id": args.op_id,
                "replayed": True,
            }
            _emit(args, payload, f"{payload['id']} {payload['file']}")
            return

    entry_id = next_task_id()
    entry = _build_task_entry(entry_id, args.title, args.objective, args.acceptance, status)
    _append_entry(target, TASK_HEADER_RE, entry)

    if args.op_id:
        ops = _load_ops()
        ops[args.op_id] = {
            "command": "add-task",
            "id": entry_id,
            "file": target.name,
            "title": entry.title,
            "created": _today(),
        }
        _save_ops(ops)

    _emit(
        args,
        {
            "command": "add-task",
            "id": entry_id,
            "file": target.name,
            "title": entry.title,
            "op_id": args.op_id,
            "replayed": False,
        },
        f"{entry_id} {target.name}",
    )


def cmd_done_task(args: argparse.Namespace) -> None:
    entry, source = _find_and_remove(args.id, [TODO_FILE, BACKLOG_FILE], TASK_HEADER_RE)
    body = [line for line in entry.body if not line.startswith("- status:")]
    body.append("- status: done")
    body.append(f"- completed: {_today()}")
    if args.note:
        body.append(f"- note: {args.note.strip()}")
    moved = Entry(entry_id=entry.entry_id, title=entry.title, body=body)
    _append_entry(DONE_FILE, TASK_HEADER_RE, moved)
    _emit(
        args,
        {
            "command": "done-task",
            "id": args.id,
            "from": source.name,
            "to": DONE_FILE.name,
            "status": "done",
        },
        f"{args.id} moved {source.name} -> {DONE_FILE.name}",
    )


def cmd_remove_task(args: argparse.Namespace) -> None:
    entry, source = _find_and_remove(args.id, [TODO_FILE, BACKLOG_FILE], TASK_HEADER_RE)
    body = [line for line in entry.body if not line.startswith("- status:")]
    body.append("- status: removed")
    body.append(f"- removed: {_today()}")
    body.append(f"- reason: {args.reason.strip()}")
    moved = Entry(entry_id=entry.entry_id, title=entry.title, body=body)
    _append_entry(DONE_FILE, TASK_HEADER_RE, moved)
    _emit(
        args,
        {
            "command": "remove-task",
            "id": args.id,
            "from": source.name,
            "to": DONE_FILE.name,
            "status": "removed",
        },
        f"{args.id} moved {source.name} -> {DONE_FILE.name}",
    )


def cmd_add_bug(args: argparse.Namespace) -> None:
    if args.op_id:
        ops = _load_ops()
        existing = ops.get(args.op_id)
        if existing is not None:
            if existing.get("command") != "add-bug":
                raise TaskToolError(f"op-id {args.op_id} already used for {existing.get('command')}")
            payload = {
                "command": "add-bug",
                "id": str(existing["id"]),
                "file": str(existing["file"]),
                "title": str(existing["title"]),
                "op_id": args.op_id,
                "replayed": True,
            }
            _emit(args, payload, f"{payload['id']} {payload['file']}")
            return

    entry_id = next_bug_id()
    entry = _build_bug_entry(entry_id, args.title, args.observed, args.expected)
    _append_entry(BUGS_FILE, BUG_HEADER_RE, entry)

    if args.op_id:
        ops = _load_ops()
        ops[args.op_id] = {
            "command": "add-bug",
            "id": entry_id,
            "file": BUGS_FILE.name,
            "title": entry.title,
            "created": _today(),
        }
        _save_ops(ops)

    _emit(
        args,
        {
            "command": "add-bug",
            "id": entry_id,
            "file": BUGS_FILE.name,
            "title": entry.title,
            "op_id": args.op_id,
            "replayed": False,
        },
        f"{entry_id} {BUGS_FILE.name}",
    )


def cmd_close_bug(args: argparse.Namespace) -> None:
    entry, _ = _find_and_remove(args.id, [BUGS_FILE], BUG_HEADER_RE)
    body = [line for line in entry.body if not line.startswith("- status:")]
    body.append("- status: resolved")
    body.append(f"- resolved: {_today()}")
    body.append(f"- resolution: {args.resolution.strip()}")
    moved = Entry(entry_id=entry.entry_id, title=entry.title, body=body)
    _append_entry(BUGS_DONE_FILE, BUG_HEADER_RE, moved)
    _emit(
        args,
        {
            "command": "close-bug",
            "id": args.id,
            "from": BUGS_FILE.name,
            "to": BUGS_DONE_FILE.name,
            "status": "resolved",
        },
        f"{args.id} moved {BUGS_FILE.name} -> {BUGS_DONE_FILE.name}",
    )


def cmd_log(args: argparse.Namespace) -> None:
    if not PROGRESS_FILE.exists():
        raise TaskToolError(f"Missing file: {PROGRESS_FILE}")
    with PROGRESS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"- {_today()}: {args.message.strip()}\n")
    _emit(args, {"command": "log", "message": args.message.strip()}, "logged")


def cmd_status_task(args: argparse.Namespace) -> None:
    for path in (TODO_FILE, BACKLOG_FILE, DONE_FILE):
        if not path.exists():
            continue
        for entry in _load_entries(path, TASK_HEADER_RE):
            if entry.entry_id == args.id:
                status = _entry_status(entry)
                payload = {
                    "command": "status-task",
                    "id": args.id,
                    "file": path.name,
                    "status": status,
                    "title": entry.title,
                }
                _emit(args, payload, f"{args.id} {status} {path.name} {entry.title}")
                return
    raise TaskToolError(f"Task not found: {args.id}")


def cmd_list(args: argparse.Namespace) -> None:
    if args.file == "all":
        files = list(LIST_FILE_MAP.items())
    else:
        files = [(args.file, LIST_FILE_MAP[args.file])]

    items: list[dict] = []
    for label, (path, header_re) in files:
        if not path.exists():
            continue
        for entry in _load_entries(path, header_re):
            items.append(
                {
                    "id": entry.entry_id,
                    "title": entry.title,
                    "status": _entry_status(entry),
                    "file": label,
                }
            )

    payload = {
        "command": "list",
        "file": args.file,
        "count": len(items),
        "items": items,
    }
    if args.json:
        _emit(args, payload)
        return

    if not items:
        print("no entries")
        return

    for item in items:
        print(f"{item['file']}:{item['id']} [{item['status']}] {item['title']}")


def cmd_normalize(args: argparse.Namespace) -> None:
    created = 0
    normalized = 0

    for path, default_content in DEFAULT_FILE_CONTENTS.items():
        if not path.exists():
            _write(path, default_content)
            created += 1
            continue

        current = path.read_text(encoding="utf-8")
        target = _read(path)
        if _normalize(current) != _normalize(target):
            _write(path, target)
            normalized += 1

    payload = {
        "command": "normalize",
        "created": created,
        "normalized": normalized,
    }
    _emit(args, payload, f"normalized (created={created}, updated={normalized})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Task management helper")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
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
    parser.add_argument(
        "--lock-wait-notice-ms",
        type=int,
        default=200,
        help="Show stderr lock-wait notice after this many ms (default: 200; -1 disables)",
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
    p.add_argument("--op-id", default="", help="Optional idempotency key for safe retries")
    p.set_defaults(func=cmd_add_task)

    p = sub.add_parser("done-task", help="Move task to DONE with done status")
    p.add_argument("--id", required=True, help="Task ID, e.g. 0042")
    p.add_argument("--note", default="", help="Optional completion note")
    p.set_defaults(func=cmd_done_task)

    p = sub.add_parser("remove-task", help="Move task to DONE with removed status")
    p.add_argument("--id", required=True, help="Task ID, e.g. 0042")
    p.add_argument("--reason", required=True, help="Removal reason")
    p.set_defaults(func=cmd_remove_task)

    p = sub.add_parser("status-task", help="Show current location/status for a task ID")
    p.add_argument("--id", required=True, help="Task ID, e.g. 0042")
    p.set_defaults(func=cmd_status_task)

    p = sub.add_parser("list", help="List entries from one file or all")
    p.add_argument(
        "--file",
        choices=["todo", "backlog", "done", "bugs", "bugs_done", "all"],
        default="all",
        help="Which file to list (default: all)",
    )
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("add-bug", help="Add open bug")
    p.add_argument("--title", required=True, help="Bug title")
    p.add_argument("--observed", default="Observed incorrect behavior.", help="Observed behavior")
    p.add_argument("--expected", default="Expected behavior.", help="Expected behavior")
    p.add_argument("--op-id", default="", help="Optional idempotency key for safe retries")
    p.set_defaults(func=cmd_add_bug)

    p = sub.add_parser("close-bug", help="Move bug to BUGS_DONE")
    p.add_argument("--id", required=True, help="Bug ID, e.g. BUG-0007")
    p.add_argument("--resolution", required=True, help="Resolution summary")
    p.set_defaults(func=cmd_close_bug)

    p = sub.add_parser("log", help="Append one progress log line")
    p.add_argument("--message", required=True, help="Milestone message")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("normalize", help="Ensure task-management files and markers are valid")
    p.set_defaults(func=cmd_normalize)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.lock_retries < 0 or args.lock_delay_ms < 0 or args.lock_jitter_ms < 0:
        parser.exit(status=1, message="error: lock retry settings must be non-negative\n")
    if args.lock_wait_notice_ms < -1:
        parser.exit(status=1, message="error: --lock-wait-notice-ms must be >= -1\n")

    try:
        if _is_mutation(args.command):
            with _acquire_lock(args.lock_retries, args.lock_delay_ms, args.lock_jitter_ms, args.lock_wait_notice_ms):
                args.func(args)
        else:
            args.func(args)
    except TaskToolError as exc:
        parser.exit(status=1, message=f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
