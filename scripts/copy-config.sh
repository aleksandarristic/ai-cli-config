#!/usr/bin/env bash
set -euo pipefail

# copy-config.sh
#
# Supports:
#   - List skills:            --list [cli]
#   - Copy one skill:         [--force] <cli> <skill> <dest_repo_path>
#   - Copy all skills:        [--force] <cli> --all <dest_repo_path>
#
# Repo layout assumed:
#   - claude:  .claude/skills/<name>.md
#   - codex:   .codex/skills/<skill-dir>/...
#   - gemini:  .gemini/skills/<skill-dir>/...
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
  copy-config.sh [--force] <cli> <skill> <dest_repo_path>
  copy-config.sh [--force] <cli> --all <dest_repo_path>

CLIs:
  claude | gemini | codex

List:
  -l, --list          List skills.
                       If [cli] is provided, list only that CLI's skills.

Copy:
  <cli>               Which CLI to copy for.
  <skill>             Skill name:
                        - claude: accepts senior-engineer / senior_engineer; maps to .md file
                        - gemini: skill directory name
                        - codex:  skill directory name
  --all               Copy all skills for the CLI.
  <dest_repo_path>    Target repo root.

Options:
  --force             Overwrite destination if it already exists.
  -h, --help          Show help.
USAGE
}

die() {
  echo "Error: $*" >&2
  exit 1
}

to_abs_dir() {
  local p="$1"
  if command -v realpath >/dev/null 2>&1; then
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
  local under="${s//-/_}"

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

copy_all_for_cli() {
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

# Parse options up front
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
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      die "Unknown option: $1"
      ;;
    *)
      break
      ;;
  esac
done

if [[ "$mode" == "list" ]]; then
  if [[ -z "$list_cli" ]]; then
    list_all
    exit 0
  fi
  is_valid_cli "$list_cli" || die "Unknown cli: $list_cli (expected: claude|gemini|codex)"
  list_one "$list_cli"
  exit 0
fi

# Copy mode:
#   [--force] <cli> <skill> <dest>
#   [--force] <cli> --all <dest>
[[ $# -ge 3 ]] || { usage; exit 1; }

cli="$1"
is_valid_cli "$cli" || die "Unknown cli: $cli (expected: claude|gemini|codex)"
shift

if [[ "${1:-}" == "--all" ]]; then
  shift
  [[ $# -eq 1 ]] || { usage; exit 1; }
  dest="$(to_abs_dir "$1")"
  [[ -d "$dest" ]] || die "Destination is not a directory: $dest"
  copy_all_for_cli "$cli" "$dest" "$force"
  exit 0
fi

[[ $# -eq 2 ]] || { usage; exit 1; }
skill="$1"
dest="$2"

dest="$(to_abs_dir "$dest")"
[[ -d "$dest" ]] || die "Destination is not a directory: $dest"

case "$cli" in
  claude)
    copy_claude_one "$skill" "$dest" "$force"
    ;;
  gemini|codex)
    copy_dir_one "$cli" "$skill" "$dest" "$force"
    ;;
  *)
    die "Invalid cli: $cli"
    ;;
esac
