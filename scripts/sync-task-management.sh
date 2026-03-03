#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_SOURCE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: sync-task-management.sh [--mode copy|upgrade] [--source-root <path>] [--force] <dest_repo_path>

Synchronizes task-management assets into a destination repository.

Modes:
  copy      Copy TASK_MANAGEMENT.md and .task-management (default)
  upgrade   Upgrade task-management templates/docs while preserving task state

Options:
  --mode         Sync mode: copy or upgrade (default: copy)
  --source-root  Source root containing TASK_MANAGEMENT.md and .task-management (default: parent of this script)
  --force        Overwrite destination paths in copy mode
  -h, --help     Show this help
USAGE
}

print_webhook_reminder() {
  local destination="$1"
  echo "Reminder: set a real webhook URL in $destination/.task-management/.webhook.json (webhook_url)."
}

ensure_webhook_gitignore() {
  local destination="$1"
  local gitignore_file="$destination/.gitignore"
  local webhook_path=".task-management/.webhook.json"

  if [[ ! -e "$gitignore_file" ]]; then
    printf "%s\n" "$webhook_path" > "$gitignore_file"
    echo "Updated $gitignore_file: added $webhook_path"
    return 0
  fi

  if grep -qxF "$webhook_path" "$gitignore_file"; then
    return 0
  fi

  if [[ -s "$gitignore_file" ]]; then
    printf "\n%s\n" "$webhook_path" >> "$gitignore_file"
  else
    printf "%s\n" "$webhook_path" >> "$gitignore_file"
  fi
  echo "Updated $gitignore_file: added $webhook_path"
}

ensure_agents_task_management_reference() {
  local destination="$1"
  local agents_file="$destination/AGENTS.md"
  local marker_line="- Follow the shared task-tracking standard in \`TASK_MANAGEMENT.md\`."

  if [[ ! -e "$agents_file" ]]; then
    cat > "$agents_file" <<'EOF'
# AGENTS.md

## Task Management Rules
- Follow the shared task-tracking standard in `TASK_MANAGEMENT.md`.
- Use `.task-management/` for task/bug tracking state and templates.
- If guidance conflicts, repository-specific files (`AGENTS.md` and `.task-management/*`) take precedence.
EOF
    echo "Created $agents_file with task management reference."
    return 0
  fi

  if grep -qF -- "$marker_line" "$agents_file"; then
    return 0
  fi

  cat >> "$agents_file" <<'EOF'

## Task Management Rules
- Follow the shared task-tracking standard in `TASK_MANAGEMENT.md`.
- Use `.task-management/` for task/bug tracking state and templates.
- If guidance conflicts, repository-specific files (`AGENTS.md` and `.task-management/*`) take precedence.
EOF
  echo "Updated $agents_file: added task management reference."
}

copy_item() {
  local src="$1"
  local dst="$2"
  local force="$3"

  if [[ ! -e "$src" ]]; then
    echo "Missing source path: $src" >&2
    return 1
  fi

  if [[ -e "$dst" ]]; then
    if [[ "$force" -ne 1 ]]; then
      echo "Destination exists: $dst (use --force to overwrite)" >&2
      return 1
    fi
    rm -rf "$dst"
  fi

  cp -R "$src" "$dst"
}

validate_source_assets() {
  local source_root="$1"
  local -a required_paths=(
    "$source_root/TASK_MANAGEMENT.md"
    "$source_root/.task-management/TODO.md"
    "$source_root/.task-management/BACKLOG.md"
    "$source_root/.task-management/BUGS.md"
    "$source_root/.task-management/TASK_TEMPLATE.md"
    "$source_root/.task-management/BUG_TEMPLATE.md"
    "$source_root/.task-management/notify.py"
    "$source_root/.task-management/.notify_config.json"
    "$source_root/.task-management/DONE.md"
    "$source_root/.task-management/BUGS_DONE.md"
    "$source_root/.task-management/REMOVED.md"
    "$source_root/.task-management/progress_log.md"
    "$source_root/.task-management/task_counter.md"
    "$source_root/.task-management/bug_counter.md"
    "$source_root/.task-management/.notify_state.json"
    "$source_root/.task-management/.webhook.json"
  )

  local missing=0
  local path
  for path in "${required_paths[@]}"; do
    if [[ ! -e "$path" ]]; then
      echo "Missing source asset: $path" >&2
      missing=1
    fi
  done

  if [[ "$missing" -ne 0 ]]; then
    echo "Aborting: source task-management assets are incomplete under $source_root" >&2
    return 1
  fi
}

overwrite_file() {
  local src="$1"
  local dst="$2"
  [[ -f "$src" ]] || return 0
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
}

copy_file_if_missing() {
  local src="$1"
  local dst="$2"
  [[ -f "$src" ]] || return 0
  if [[ ! -e "$dst" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
  fi
}

merge_template_with_existing_entries() {
  local template="$1"
  local existing="$2"
  local merged="$3"
  local start_line="$4"
  local tmp_old
  local tmp_tail

  tmp_old="$(mktemp)"
  tmp_tail="$(mktemp)"
  cp "$existing" "$tmp_old"

  tail -n +"$start_line" "$tmp_old" > "$tmp_tail"

  cp "$template" "$merged"
  if [[ -s "$tmp_tail" ]]; then
    printf "\n" >> "$merged"
    cat "$tmp_tail" >> "$merged"
  fi

  rm -f "$tmp_old" "$tmp_tail"
}

find_first_entry_line_after_anchor() {
  local file="$1"
  local entry_pattern="$2"
  local anchor_pattern="$3"
  local anchor_line
  local search_start=1
  local relative_line

  anchor_line="$(grep -nE "$anchor_pattern" "$file" | tail -n1 | cut -d: -f1 || true)"
  if [[ -n "$anchor_line" ]]; then
    search_start=$((anchor_line + 1))
  fi

  relative_line="$(tail -n +"$search_start" "$file" | grep -nE "$entry_pattern" | head -n1 | cut -d: -f1 || true)"
  if [[ -n "$relative_line" ]]; then
    echo $((search_start + relative_line - 1))
  fi
}

copy_task_management() {
  local source_root="$1"
  local destination="$2"
  local force="$3"

  copy_item "$source_root/TASK_MANAGEMENT.md" "$destination/TASK_MANAGEMENT.md" "$force"
  copy_item "$source_root/.task-management" "$destination/.task-management" "$force"
}

upgrade_task_management() {
  local source_root="$1"
  local destination="$2"
  local src_tm_dir="$source_root/.task-management"
  local dst_tm_dir="$destination/.task-management"

  overwrite_file "$source_root/TASK_MANAGEMENT.md" "$destination/TASK_MANAGEMENT.md"
  mkdir -p "$dst_tm_dir"

  # Always keep canonical templates current.
  overwrite_file "$src_tm_dir/TASK_TEMPLATE.md" "$dst_tm_dir/TASK_TEMPLATE.md"
  overwrite_file "$src_tm_dir/BUG_TEMPLATE.md" "$dst_tm_dir/BUG_TEMPLATE.md"
  overwrite_file "$src_tm_dir/notify.py" "$dst_tm_dir/notify.py"
  overwrite_file "$src_tm_dir/.notify_config.json" "$dst_tm_dir/.notify_config.json"

  # Preserve runtime state where possible; only seed missing files.
  copy_file_if_missing "$src_tm_dir/DONE.md" "$dst_tm_dir/DONE.md"
  copy_file_if_missing "$src_tm_dir/BUGS_DONE.md" "$dst_tm_dir/BUGS_DONE.md"
  copy_file_if_missing "$src_tm_dir/REMOVED.md" "$dst_tm_dir/REMOVED.md"
  copy_file_if_missing "$src_tm_dir/progress_log.md" "$dst_tm_dir/progress_log.md"
  copy_file_if_missing "$src_tm_dir/task_counter.md" "$dst_tm_dir/task_counter.md"
  copy_file_if_missing "$src_tm_dir/bug_counter.md" "$dst_tm_dir/bug_counter.md"
  copy_file_if_missing "$src_tm_dir/.notify_state.json" "$dst_tm_dir/.notify_state.json"
  copy_file_if_missing "$src_tm_dir/.webhook.json" "$dst_tm_dir/.webhook.json"

  # Upgrade TODO/BACKLOG/BUGS structure but keep existing entries.
  local dst_todo="$dst_tm_dir/TODO.md"
  local dst_backlog="$dst_tm_dir/BACKLOG.md"
  local dst_bugs="$dst_tm_dir/BUGS.md"
  local merged
  local task_entry_pattern='^[[:space:]]*([-*][[:space:]]*)?`?[0-9][0-9][0-9][0-9][[:space:]]*-[[:space:]]'
  local bug_entry_pattern='^[[:space:]]*([-*][[:space:]]*)?`?BUG-[0-9][0-9][0-9][0-9][[:space:]]*-[[:space:]]'
  merged="$(mktemp)"

  if [[ -f "$dst_todo" ]]; then
    local todo_start_line
    todo_start_line="$(find_first_entry_line_after_anchor "$dst_todo" "$task_entry_pattern" '^Copy `\.task-management/TASK_TEMPLATE\.md` when creating new tasks\.$' || true)"
    if [[ -n "$todo_start_line" ]]; then
      merge_template_with_existing_entries "$src_tm_dir/TODO.md" "$dst_todo" "$merged" "$todo_start_line"
      cp "$merged" "$dst_todo"
    else
      echo "Warning: no parseable task entries found in $dst_todo; leaving existing file unchanged." >&2
    fi
  else
    overwrite_file "$src_tm_dir/TODO.md" "$dst_todo"
  fi

  if [[ -f "$dst_backlog" ]]; then
    local backlog_start_line
    backlog_start_line="$(grep -nE "$task_entry_pattern" "$dst_backlog" | head -n1 | cut -d: -f1 || true)"
    if [[ -n "$backlog_start_line" ]]; then
      merge_template_with_existing_entries "$src_tm_dir/BACKLOG.md" "$dst_backlog" "$merged" "$backlog_start_line"
      cp "$merged" "$dst_backlog"
    else
      echo "Warning: no parseable task entries found in $dst_backlog; leaving existing file unchanged." >&2
    fi
  else
    overwrite_file "$src_tm_dir/BACKLOG.md" "$dst_backlog"
  fi

  if [[ -f "$dst_bugs" ]]; then
    local bugs_start_line
    bugs_start_line="$(find_first_entry_line_after_anchor "$dst_bugs" "$bug_entry_pattern" '^Copy `\.task-management/BUG_TEMPLATE\.md` when creating new bugs\.$' || true)"
    if [[ -n "$bugs_start_line" ]]; then
      merge_template_with_existing_entries "$src_tm_dir/BUGS.md" "$dst_bugs" "$merged" "$bugs_start_line"
      cp "$merged" "$dst_bugs"
    else
      echo "Warning: no parseable bug entries found in $dst_bugs; leaving existing file unchanged." >&2
    fi
  else
    overwrite_file "$src_tm_dir/BUGS.md" "$dst_bugs"
  fi

  rm -f "$merged"
}

mode="copy"
force=0
source_root="$DEFAULT_SOURCE_ROOT"
dest=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --mode=*)
      mode="${1#*=}"
      shift
      ;;
    --source-root)
      source_root="${2:-}"
      shift 2
      ;;
    --source-root=*)
      source_root="${1#*=}"
      shift
      ;;
    --force)
      force=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -* )
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      dest="$1"
      shift
      ;;
  esac
done

if [[ "$mode" != "copy" && "$mode" != "upgrade" ]]; then
  echo "Invalid --mode: $mode (expected copy or upgrade)" >&2
  exit 1
fi

if [[ -z "$dest" ]]; then
  usage
  exit 1
fi

if command -v realpath >/dev/null 2>&1; then
  source_root="$(realpath "$source_root")"
  dest="$(realpath "$dest")"
else
  source_root="$(cd "$source_root" && pwd)"
  dest="$(cd "$dest" && pwd)"
fi

if [[ ! -d "$dest" ]]; then
  echo "Destination is not a directory: $dest" >&2
  exit 1
fi

validate_source_assets "$source_root"

if [[ "$mode" == "copy" ]]; then
  copy_task_management "$source_root" "$dest" "$force"
  ensure_agents_task_management_reference "$dest"
  ensure_webhook_gitignore "$dest"
  echo "Copied task management files to $dest"
  print_webhook_reminder "$dest"
else
  upgrade_task_management "$source_root" "$dest"
  ensure_agents_task_management_reference "$dest"
  ensure_webhook_gitignore "$dest"
  echo "Upgraded task management files in $dest (preserved task state)"
  print_webhook_reminder "$dest"
fi
