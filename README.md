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
│   ├── copy-config.sh         # Core logic for skills/settings + task-management sync entry points
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
    *   For **Gemini/Codex**: Create a new directory under `.gemini/skills/` or `.codex/skills/` with a `SKILL.md` file.
    *   For **Claude**: Add a new `.md` file under `.claude/skills/`.
3.  **Commit & Push:** Submit a PR to merge your new skill into the main collection.
