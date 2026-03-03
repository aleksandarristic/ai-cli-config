#!/usr/bin/env python3
"""Task notification helper for Discord webhooks.

Default behavior:
- Notifications are enabled unless explicitly toggled off.
- Webhook is read from --webhook, then .task-management/.webhook.json,
  then the env var configured in .task-management/.notify_config.json.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from urllib import error, request

STATE_FILE = Path(__file__).with_name(".notify_state.json")
WEBHOOK_FILE = Path(__file__).with_name(".webhook.json")
CONFIG_FILE = Path(__file__).with_name(".notify_config.json")

DEFAULT_CONFIG: dict[str, object] = {
    "title": "Codex Task Update",
    "default_level": "info",
    "allowed_levels": ["start", "done", "blocked", "final", "info"],
    "default_task_name": "General",
    "status_label": "Status",
    "task_label": "Task",
    "track_label": "Track",
    "message_label": "Message",
    "time_label": "Time",
    "time_label_overflow": "Time (Local)",
    "timestamp_format": "%Y-%m-%d %H:%M:%S",
    "include_timezone_name": True,
    "include_utc_offset": True,
    "include_timestamp": True,
    "max_content_length": 2000,
    "request_timeout_seconds": 10,
    "user_agent": "codex-task-notify/1.0",
    "webhook_env_var": "DISCORD_WEBHOOK_URL",
    "webhook_keys": ["webhook_url", "webhook", "url"],
    "username": "",
    "avatar_url": "",
}


def _normalize_webhook_value(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return ""
    upper = candidate.upper()
    placeholder_markers = (
        "REPLACE_WITH_REAL",
        "REAL WEBHOOK URL",
        "YOUR_WEBHOOK",
        "<WEBHOOK>",
    )
    if any(marker in upper for marker in placeholder_markers):
        return ""
    if not (candidate.startswith("http://") or candidate.startswith("https://")):
        return ""
    return candidate


def _read_json(path: Path) -> object | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _as_string(value: object, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _as_bool(value: object, default: bool) -> bool:
    return bool(value) if isinstance(value, bool) else default


def _as_int(value: object, default: int, minimum: int = 1) -> int:
    if isinstance(value, int):
        return value if value >= minimum else default
    return default


def _as_string_list(value: object, default: list[str]) -> list[str]:
    if not isinstance(value, list):
        return list(default)
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            item = item.strip()
            if item:
                items.append(item)
    return items or list(default)


def _read_config(config_path: Path) -> dict[str, object]:
    config = dict(DEFAULT_CONFIG)
    payload = _read_json(config_path)
    if not isinstance(payload, dict):
        return config

    string_keys = [
        "title",
        "default_level",
        "default_task_name",
        "status_label",
        "task_label",
        "track_label",
        "message_label",
        "time_label",
        "time_label_overflow",
        "timestamp_format",
        "user_agent",
        "webhook_env_var",
        "username",
        "avatar_url",
    ]
    bool_keys = ["include_timezone_name", "include_utc_offset", "include_timestamp"]

    for key in string_keys:
        config[key] = _as_string(payload.get(key), str(config[key]))
    for key in bool_keys:
        config[key] = _as_bool(payload.get(key), bool(config[key]))

    config["max_content_length"] = _as_int(payload.get("max_content_length"), int(config["max_content_length"]), 200)
    config["request_timeout_seconds"] = _as_int(payload.get("request_timeout_seconds"), int(config["request_timeout_seconds"]), 1)
    config["allowed_levels"] = [lvl.lower() for lvl in _as_string_list(payload.get("allowed_levels"), list(config["allowed_levels"]))]
    config["webhook_keys"] = _as_string_list(payload.get("webhook_keys"), list(config["webhook_keys"]))

    default_level = str(config["default_level"]).lower()
    allowed_levels = list(config["allowed_levels"])
    if default_level not in allowed_levels:
        config["default_level"] = allowed_levels[0]
    else:
        config["default_level"] = default_level

    return config


def _read_state() -> dict[str, object]:
    payload = _read_json(STATE_FILE)
    if not isinstance(payload, dict):
        return {"enabled": True}
    enabled = bool(payload.get("enabled", True))
    return {"enabled": enabled}


def _write_state(enabled: bool) -> None:
    STATE_FILE.write_text(
        json.dumps({"enabled": enabled}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _is_enabled() -> bool:
    return bool(_read_state().get("enabled", True))


def _read_webhook_from_file(config: dict[str, object]) -> str:
    payload = _read_json(WEBHOOK_FILE)
    if isinstance(payload, str):
        return _normalize_webhook_value(payload)
    if not isinstance(payload, dict):
        return ""

    for key in config["webhook_keys"]:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            normalized = _normalize_webhook_value(value)
            if normalized:
                return normalized
    return ""


def _resolve_webhook(cli_webhook: str | None, config: dict[str, object]) -> str:
    if cli_webhook:
        return _normalize_webhook_value(cli_webhook)
    file_value = _read_webhook_from_file(config)
    if file_value:
        return file_value
    env_var = str(config["webhook_env_var"])
    return _normalize_webhook_value(os.getenv(env_var, ""))


def _format_local_timestamp(config: dict[str, object]) -> str:
    local_now = datetime.now().astimezone()
    timestamp_format = str(config["timestamp_format"])
    try:
        base = local_now.strftime(timestamp_format)
    except Exception:
        base = local_now.strftime("%Y-%m-%d %H:%M:%S")

    parts = [base]
    if bool(config["include_timezone_name"]):
        parts.append(local_now.tzname() or "Local")
    if bool(config["include_utc_offset"]):
        offset_raw = local_now.strftime("%z")
        if len(offset_raw) == 5:
            offset_formatted = f"{offset_raw[:3]}:{offset_raw[3:]}"
        else:
            offset_formatted = offset_raw or "+00:00"
        parts.append(f"(UTC{offset_formatted})")
    return " ".join(parts)


def _build_content(
    task: str | None,
    track: str | None,
    level: str | None,
    message: str,
    config: dict[str, object],
) -> str:
    normalized_level = (level or str(config["default_level"])).lower()
    normalized_task = (task or str(config["default_task_name"]))
    normalized_track = (track or "").strip()
    normalized_message = message.strip()
    title = str(config["title"])

    status_label = str(config["status_label"])
    task_label = str(config["task_label"])
    track_label = str(config["track_label"])
    message_label = str(config["message_label"])
    time_label = str(config["time_label"])
    time_label_overflow = str(config["time_label_overflow"])
    max_content_length = int(config["max_content_length"])

    timestamp = _format_local_timestamp(config)

    def _lines(msg: str, current_time_label: str) -> list[str]:
        lines = [
            f"**{title}**",
            f"- **{status_label}:** `{normalized_level.upper()}`",
            f"- **{task_label}:** `{normalized_task.strip()}`",
        ]
        if normalized_track:
            lines.append(f"- **{track_label}:** `{normalized_track}`")
        lines.append(f"- **{message_label}:** {msg}")
        if bool(config["include_timestamp"]):
            lines.append(f"- **{current_time_label}:** `{timestamp}`")
        return lines

    content = "\n".join(_lines(normalized_message, time_label))
    if len(content) <= max_content_length:
        return content

    overflow = len(content) - max_content_length
    trim_to = max(0, len(normalized_message) - overflow - 3)
    trimmed_message = normalized_message[:trim_to].rstrip()
    if trimmed_message:
        trimmed_message += "..."
    else:
        trimmed_message = "..."

    content = "\n".join(_lines(trimmed_message, time_label_overflow))
    if len(content) > max_content_length:
        content = content[: max_content_length - 3] + "..."
    return content


def _send(webhook_url: str, content: str, config: dict[str, object]) -> tuple[bool, str]:
    payload_dict: dict[str, object] = {"content": content}
    username = str(config["username"])
    avatar_url = str(config["avatar_url"])
    if username:
        payload_dict["username"] = username
    if avatar_url:
        payload_dict["avatar_url"] = avatar_url

    payload = json.dumps(payload_dict).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": str(config["user_agent"]),
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=float(config["request_timeout_seconds"])) as response:
            status = getattr(response, "status", None) or response.getcode()
            return True, f"sent: status={status}"
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return False, f"http_error: status={exc.code} body={body}"
    except Exception as exc:  # pragma: no cover - runtime/network variance
        return False, f"request_failed: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Send Discord task notifications.")
    parser.add_argument("--message", help="Notification message body.")
    parser.add_argument("--task", help="Optional task label, e.g. 'Task 47'.")
    parser.add_argument("--track", help="Optional track label, e.g. 'Unified Read Experience'.")
    parser.add_argument("--level", help="Optional status level prefix.")
    parser.add_argument("--webhook", help="Discord webhook URL (overrides file and env).")
    parser.add_argument("--config", help="Optional path to JSON config file.")
    parser.add_argument("--toggle", choices=["on", "off"], help="Persist notification toggle state.")
    parser.add_argument("--status", action="store_true", help="Print current toggle and webhook status and exit.")
    parser.add_argument("--preview", action="store_true", help="Print formatted message without sending.")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser() if args.config else CONFIG_FILE
    config = _read_config(config_path)

    if args.toggle:
        enabled = args.toggle == "on"
        _write_state(enabled)
        print(f"notifications: {'on' if enabled else 'off'}")
        return 0

    if args.status:
        enabled = "on" if _is_enabled() else "off"
        webhook = "configured" if _resolve_webhook(args.webhook, config) else "missing"
        print(f"notifications: {enabled}")
        print(f"webhook: {webhook}")
        return 0

    allowed_levels = [str(v).lower() for v in list(config["allowed_levels"])]
    default_level = str(config["default_level"])
    level = (args.level or default_level).lower()
    if level not in allowed_levels:
        print(f"error: invalid --level '{level}'. allowed: {', '.join(allowed_levels)}")
        return 2

    if not args.message:
        print("error: --message is required when sending notifications")
        return 2

    content = _build_content(args.task, args.track, level, args.message, config)
    if args.preview:
        print(content)
        return 0

    if not _is_enabled():
        print("notifications: off (skipped)")
        return 0

    webhook_url = _resolve_webhook(args.webhook, config)
    if not webhook_url:
        print("error: missing webhook (use --webhook, .webhook.json, or configured env var)")
        return 2

    ok, detail = _send(webhook_url, content, config)
    print(detail)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
