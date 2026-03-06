# AI CLI Configuration & Skills

This repository serves as a centralized source for AI agent configurations, personas, and skills. It allows you to maintain a consistent set of capabilities across different projects and AI assistants (Gemini, Claude, Codex).

## Features

- **Centralized Management:** Keep all your prompt engineering and agent persona definitions in one place.
- **Multi-Agent Support:** Specific structures for:
  - **Gemini CLI** (`.gemini/`)
  - **Claude Code** (`.claude/`)
  - **OpenAI Codex** (`.codex/`)
- **Flexible Deployment:** A helper script (`copy-config.sh`) to inject specific skills, settings, or entire configurations into your current project's repository.
- **Reusable Task Management:** Optional task/bug tracking standard and templates (`TASK_MANAGEMENT.md`, `.task-management/`) with upgrade support.

## Getting Started

### 1. Clone the Repository

Clone this repository to a known location on your machine (e.g., `~/Code/ai-cli-config`).

```bash
git clone https://github.com/your-username/ai-cli-config.git ~/Code/ai-cli-config
```

### 2. Set up the Alias

To make the `copy-config` script easily accessible from any project, source the provided alias file in your shell configuration.

**For Bash users (`~/.bashrc`):**
```bash
source ~/Code/ai-cli-config/alias.bash
```

**For Zsh users (`~/.zshrc`):**
```bash
source ~/Code/ai-cli-config/alias.zsh
```

*Note: Adjust the path if you cloned the repo elsewhere.*

## Usage

Once the alias `copy-ai-cfg` is set up, you can use it from within any project directory to pull in skills and configurations.

### List Available Skills

View what skills are currently available in this repository:

```bash
# List all skills for all agents
copy-ai-cfg --list

# List skills for a specific agent
copy-ai-cfg --list gemini
```

### Copy Skills and Configuration

The `copy-ai-cfg` command allows you to mix and match what you want to copy.

**Syntax:**
```bash
copy-ai-cfg <cli> [options] [skills...] <destination-path>
```

**Options:**
- `-s`, `--settings`: Copy the global settings file (e.g., `settings.json`) if available.
- `-a`, `--all`: Copy **all** available skills for the selected CLI.
- `--force`: Overwrite existing files in the destination.

### Examples

**1. Copy specific skills:**
Add the 'senior-engineer' skill for Gemini to the current directory (`.`):
```bash
copy-ai-cfg gemini senior-engineer .
```

**2. Copy just the settings:**
Update your project's configuration without adding skills:
```bash
copy-ai-cfg gemini -s .
```

**3. Mix and Match:**
Copy settings, the 'senior-engineer' skill, and the 'code-reviewer' skill:
```bash
copy-ai-cfg gemini -s senior-engineer code-reviewer .
```

**4. Copy Everything:**
Copy all skills and the settings file:
```bash
copy-ai-cfg gemini -a -s .
```

### Task Management Sync

You can also copy or upgrade task-management assets into a target repository:

```bash
# Add task-management files
copy-ai-cfg --task-management-only /path/to/target-repo

# Upgrade task-management templates/docs while preserving task state
copy-ai-cfg --task-management-upgrade /path/to/target-repo
```

Standalone script variant:

```bash
./scripts/sync-task-management.sh --mode copy /path/to/target-repo
./scripts/sync-task-management.sh --mode upgrade /path/to/target-repo
```

### Task Tool Quick Start

After task management exists in a repo, use the helper instead of manual edits:

```bash
# Get next IDs
python3 .task-management/task_tool.py next-task-id
python3 .task-management/task_tool.py next-bug-id

# Create work items
python3 .task-management/task_tool.py add-task --title "Implement X"
python3 .task-management/task_tool.py add-bug --title "Bug in X"

# Close work items
python3 .task-management/task_tool.py done-task --id 0001 --note "Shipped"
python3 .task-management/task_tool.py remove-task --id 0002 --reason "No longer needed"
python3 .task-management/task_tool.py close-bug --id BUG-0001 --resolution "Fixed in parser"

# Milestone log
python3 .task-management/task_tool.py log --message "Completed feature X"
```

Run the lightweight regression check for task-tool behavior:

```bash
./scripts/test-task-tool.sh
```

## Task Management In Another Project

Use this flow when you want to add or update only task management in a target repo.

1. Add task management:

```bash
copy-ai-cfg --task-management-only /path/to/target-repo
```

2. Set a real webhook URL in the target repo:

```json
{
  "webhook_url": "https://discord.com/api/webhooks/..."
}
```

Path: `/path/to/target-repo/.task-management/.webhook.json`

3. Upgrade later without losing active task/bug state:

```bash
copy-ai-cfg --task-management-upgrade /path/to/target-repo
```

## How Agents Use It

Task management is intended for Codex agent execution. Typical prompts:

- `add a new task for implementing search caching`
- `document a bug: API returns 500 when page is empty`
- `do tasks 0007, 0008, and 0009 in sequence`
- `do tasks 0010, 0011, and 0012 in parallel`
- `do tasks 0010, 0011, and 0012 in parallel using worktrees`

Expected behavior:

- tasks and bugs keep stable IDs (`0001`, `BUG-0001`)
- bug reports generate follow-up fix tasks in `TODO.md` or `BACKLOG.md`
- notifications are sent by agent via `.task-management/notify.py` when enabled/configured

## Repository Structure

```text
ai-cli-config/
├── .claude/           # Claude Code specific configurations
│   └── skills/        # Individual Markdown files for skills (e.g., senior_engineer.md)
├── .codex/            # OpenAI Codex specific configurations
│   └── skills/        # Directories containing skill definitions
├── .gemini/           # Gemini CLI specific configurations
│   ├── skills/        # Directories containing skill definitions (SKILL.md + resources)
│   └── settings.json  # Global settings for Gemini CLI
├── scripts/
│   ├── copy-config.sh          # Core logic for skills/settings + task-management sync entry points
│   └── sync-task-management.sh # Standalone task-management sync (copy/upgrade)
├── TASK_MANAGEMENT.md # Reusable task-management standard
├── .task-management/  # Task/bug templates and notifier helpers
├── alias.bash         # Alias definition for Bash
├── alias.zsh          # Alias definition for Zsh
└── README.md          # This file
```

## Contributing

1.  **Create a Branch:** `git checkout -b add-new-skill`
2.  **Add Your Skill:**
    - For **Gemini/Codex**: Create a new directory under `.gemini/skills/` or `.codex/skills/` with a `SKILL.md` file.
    - For **Claude**: Add a new `.md` file under `.claude/skills/`.
3.  **Commit & Push:** Submit a PR to merge your new skill into the main collection.
