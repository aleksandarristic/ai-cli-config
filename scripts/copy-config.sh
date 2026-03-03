#!/usr/bin/env bash
set -euo pipefail

# copy-config.sh
#
# Supports:
#   - List skills:            --list [cli]
#   - Copy config:            [--force] <cli> [options] [skills...] <dest_repo_path>
#   - Sync task management:   [--force] --task-management-only <dest_repo_path>
#                             [--force] --task-management-upgrade <dest_repo_path>
#
# Repo layout assumed:
#   - claude:  .claude/skills/<name>.md
#   - codex:   .codex/skills/<skill-dir>/...
#   - gemini:  .gemini/skills/<skill-dir>/...
#              .gemini/settings.json (optional)
#
# Auto-map for claude skill names:
#   - Accepts senior-engineer / senior_engineer / senior engineer (spaces -> dashes)
#   - Tries both <name>.md and <name_with_underscores>.md when locating source

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  copy-config.sh -l|--list [cli]
  copy-config.sh [--force] --task-management-only <dest_repo_path>
  copy-config.sh [--force] --task-management-upgrade <dest_repo_path>
  copy-config.sh [--force] <cli> [options] [skills...] <dest_repo_path>

CLIs:
  claude | gemini | codex

List:
  -l, --list          List skills.
                       If [cli] is provided, list only that CLI's skills.

Copy Options:
  -s, --settings      Copy settings.json (if available).
  -a, --all, --all-skills
                      Copy all skills.
  --task-management-only
                      Copy TASK_MANAGEMENT.md and .task-management into destination.
  --task-management-upgrade
                      Upgrade task-management templates/docs while preserving state.
  --force             Overwrite destination if it already exists.

Arguments:
  <cli>               Which CLI to copy for.
  [skills...]         Specific skill names to copy.
  <dest_repo_path>    Target repo root.

Examples:
  copy-config.sh gemini -s /tmp/my-repo
  copy-config.sh gemini senior-engineer /tmp/my-repo
  copy-config.sh gemini -a -s /tmp/my-repo
  copy-config.sh gemini senior-engineer -s /tmp/my-repo
  copy-config.sh --task-management-only /tmp/my-repo
  copy-config.sh --task-management-upgrade /tmp/my-repo
USAGE
}

die() {
  echo "Error: $*" >&2
  exit 1
}

to_abs_dir() {
  local p="$1"
  if command -v realpath >/dev/null 2>&1;
    then
    realpath "$p"
  else
    (cd "$p" && pwd)
  fi
}

is_valid_cli() {
  case "$1" in
    claude|codex|gemini) return 0 ;;
    *) return 1 ;;
  esac
}

trim() {
  local s="$1"
  # shellcheck disable=SC2001
  s="$(echo "$s" | sed -e 's/^[[:space:]]\+//' -e 's/[[:space:]]\+$//')"
  printf '%s' "$s"
}

slugify() {
  # conservative: keep letters/digits, convert spaces to '-', keep '_' and '-'
  local s
  s="$(trim "$1")"
  s="$(echo "$s" | tr '[:upper:]' '[:lower:]')"
  s="$(echo "$s" | sed -E 's/[[:space:]]+/-/g')"
  printf '%s' "$s"
}

claude_candidates() {
  # Given a user-provided skill string, output candidate basenames (without .md)
  # in preferred order. E.g.:
  #   "Senior-Engineer" -> senior-engineer, senior_engineer
  #   "senior_engineer" -> senior_engineer, senior-engineer
  #   "senior engineer" -> senior-engineer, senior_engineer
  local raw="$1"
  local s
  s="$(slugify "$raw")"

  local dash="$s"
  local under="${s//-/}"

  if [[ "$dash" == "$under" ]]; then
    printf '%s\n' "$dash"
  else
    # Prefer what the user likely meant:
    # - if input contains '_' first, prefer underscore variant; else prefer dash variant
    if [[ "$raw" == *"_"* ]]; then
      printf '%s\n%s\n' "$under" "$dash"
    else
      printf '%s\n%s\n' "$dash" "$under"
    fi
  fi
}

list_claude_skills() {
  local base="$ROOT_DIR/.claude/skills"
  [[ -d "$base" ]] || return 0
  find "$base" -maxdepth 1 -type f -name '*.md' -print 2>/dev/null \
    | sed -E 's#.*/##' \
    | sed -E 's/\.md$//' \
    | sort
}

list_codex_skills() {
  local base="$ROOT_DIR/.codex/skills"
  [[ -d "$base" ]] || return 0
  find "$base" -maxdepth 1 -mindepth 1 -type d -print 2>/dev/null \
    | sed -E 's#.*/##' \
    | sort
}

list_gemini_skills() {
  local base="$ROOT_DIR/.gemini/skills"
  [[ -d "$base" ]] || return 0
  find "$base" -maxdepth 1 -mindepth 1 -type d -print 2>/dev/null \
    | sed -E 's#.*/##' \
    | sort
}

list_all() {
  echo "claude:"
  list_claude_skills | sed 's/^/  /'
  echo
  echo "gemini:"
  list_gemini_skills | sed 's/^/  /'
  echo
  echo "codex:"
  list_codex_skills | sed 's/^/  /'
}

list_one() {
  local cli="$1"
  case "$cli" in
    claude) list_claude_skills ;;
    gemini) list_gemini_skills ;;
    codex)  list_codex_skills ;;
    *) die "Invalid cli for list: $cli" ;;
  esac
}

copy_path() {
  local src="$1"
  local dst="$2"
  local force="$3"

  [[ -e "$src" ]] || die "Source does not exist: $src"

  if [[ -e "$dst" ]]; then
    if [[ "$force" -ne 1 ]]; then
      die "Destination exists: $dst (use --force to overwrite)"
    fi
    rm -rf "$dst"
  fi

  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
}

copy_settings() {
  local cli="$1"
  local dest_repo="$2"
  local force="$3"

  local src="$ROOT_DIR/.${cli}/settings.json"
  local dst="$dest_repo/.${cli}/settings.json"

  if [[ -f "$src" ]]; then
    copy_path "$src" "$dst" "$force"
    echo "Copied ${cli} settings -> ${dst}"
  else
    echo "Warning: No settings.json found for ${cli} at $src"
  fi
}

copy_claude_one() {
  local user_skill="$1"
  local dest_repo="$2"
  local force="$3"

  local base_src="$ROOT_DIR/.claude/skills"
  local base_dst="$dest_repo/.claude/skills"

  local found_src=""
  local found_name=""

  while IFS= read -r cand; do
    local p="$base_src/${cand}.md"
    if [[ -f "$p" ]]; then
      found_src="$p"
      found_name="$cand"
      break
    fi
  done < <(claude_candidates "$user_skill")

  [[ -n "$found_src" ]] || die "Claude skill not found under $base_src for: '$user_skill'"

  local dst="$base_dst/${found_name}.md"
  copy_path "$found_src" "$dst" "$force"
  echo "Copied claude skill '${found_name}' -> ${dst}"
}

copy_dir_one() {
  local cli="$1"
  local skill="$2"
  local dest_repo="$3"
  local force="$4"

  local src="$ROOT_DIR/.${cli}/skills/${skill}"
  local dst="$dest_repo/.${cli}/skills/${skill}"
  copy_path "$src" "$dst" "$force"
  echo "Copied ${cli} skill '${skill}' -> ${dst}"
}

copy_all_skills_for_cli() {
  local cli="$1"
  local dest_repo="$2"
  local force="$3"

  local src_base="$ROOT_DIR/.${cli}/skills"
  local dst_base="$dest_repo/.${cli}/skills"

  [[ -d "$src_base" ]] || die "No skills directory for ${cli}: $src_base"

  mkdir -p "$dst_base"

  if [[ "$cli" == "claude" ]]; then
    # Copy each .md file individually to allow --force overwrite per file.
    local any=0
    while IFS= read -r f; do
      any=1
      local name
      name="$(basename "$f")"
      copy_path "$f" "$dst_base/$name" "$force"
    done < <(find "$src_base" -maxdepth 1 -type f -name '*.md' -print | sort)

    [[ "$any" -eq 1 ]] || die "No claude skills found in $src_base"
    echo "Copied all claude skills -> ${dst_base}"
    return 0
  fi

  # codex/gemini: copy skill directories under skills/
  local any=0
  while IFS= read -r d; do
    any=1
    local name
    name="$(basename "$d")"
    copy_path "$d" "$dst_base/$name" "$force"
  done < <(find "$src_base" -maxdepth 1 -mindepth 1 -type d -print | sort)

  [[ "$any" -eq 1 ]] || die "No ${cli} skills found in $src_base"
  echo "Copied all ${cli} skills -> ${dst_base}"
}

force=0
mode="copy"
list_cli=""
task_management_mode=""

# Parse global options up front
while [[ $# -gt 0 ]]; do
  case "$1" in
    -l|--list)
      mode="list"
      shift
      if [[ $# -gt 0 && "${1:-}" != -* ]]; then
        list_cli="$1"
        shift
      fi
      ;;
    --force)
      force=1
      shift
      ;;
    --task-management-only)
      if [[ -n "$task_management_mode" ]]; then
        die "--task-management-only and --task-management-upgrade are mutually exclusive"
      fi
      task_management_mode="copy"
      shift
      ;;
    --task-management-upgrade)
      if [[ -n "$task_management_mode" ]]; then
        die "--task-management-only and --task-management-upgrade are mutually exclusive"
      fi
      task_management_mode="upgrade"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      die "Unknown global option or invalid placement: $1"
      ;;
    *)
      break
      ;;
  esac
done

if [[ "$mode" == "list" ]]; then
  if [[ -n "$task_management_mode" ]]; then
    die "--list cannot be combined with task-management sync options"
  fi
  if [[ -z "$list_cli" ]]; then
    list_all
    exit 0
  fi
  is_valid_cli "$list_cli" || die "Unknown cli: $list_cli (expected: claude|gemini|codex)"
  list_one "$list_cli"
  exit 0
fi

# Task-management mode
if [[ -n "$task_management_mode" ]]; then
  [[ $# -eq 1 ]] || { usage; exit 1; }
  dest="$(to_abs_dir "$1")"
  [[ -d "$dest" ]] || die "Destination is not a directory: $dest"

  cmd=("$SCRIPT_DIR/sync-task-management.sh" "--mode" "$task_management_mode" "--source-root" "$ROOT_DIR")
  if [[ "$force" -eq 1 ]]; then
    cmd+=("--force")
  fi
  cmd+=("$dest")
  "${cmd[@]}"
  exit 0
fi

# Copy mode
[[ $# -ge 2 ]] || { usage; exit 1; }

cli="$1"
is_valid_cli "$cli" || die "Unknown cli: $cli (expected: claude|gemini|codex)"
shift

do_settings=0
do_all_skills=0
declare -a specific_skills=()

# Parse copy arguments
# We iterate until $# == 1 (which is dest)
while [[ $# -gt 1 ]]; do
  case "$1" in
    -s|--settings)
      do_settings=1
      ;;
    -a|--all|--all-skills)
      do_all_skills=1
      ;;
    -*)
      die "Unknown option: $1"
      ;;
    *)
      specific_skills+=("$1")
      ;;
  esac
  shift
done

dest="$(to_abs_dir "$1")"
[[ -d "$dest" ]] || die "Destination is not a directory: $dest"

if [[ "$do_settings" -eq 0 && "$do_all_skills" -eq 0 && "${#specific_skills[@]}" -eq 0 ]]; then
  die "Nothing to copy specified. Provide a skill name, -a (all skills), or -s (settings)."
fi

# 1. Settings
if [[ "$do_settings" -eq 1 ]]; then
  copy_settings "$cli" "$dest" "$force"
fi

# 2. Skills
if [[ "$do_all_skills" -eq 1 ]]; then
  copy_all_skills_for_cli "$cli" "$dest" "$force"
else
  for skill in "${specific_skills[@]}"; do
    case "$cli" in
      claude)
        copy_claude_one "$skill" "$dest" "$force"
        ;;
      gemini|codex)
        copy_dir_one "$cli" "$skill" "$dest" "$force"
        ;;
    esac
  done
fi
