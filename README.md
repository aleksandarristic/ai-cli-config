# AI CLI Configuration & Skills

This repository serves as a centralized source for AI agent configurations, personas, and skills. It allows you to maintain a consistent set of capabilities across different projects and AI assistants (Gemini, Claude, Codex).

## Features

- **Centralized Management:** Keep all your prompt engineering and agent persona definitions in one place.
- **Multi-Agent Support:** Specific structures for:
  - **Gemini CLI** (`.gemini/`)
  - **Claude Code** (`.claude/`)
  - **OpenAI Codex** (`.codex/`)
- **Easy Deployment:** A helper script (`copy-config.sh`) to quickly inject specific skills into your current project's repository.

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

Once the alias `copy-ai-cfg` is set up, you can use it from within any project directory to pull in skills.

### List Available Skills

View what skills are currently available in this repository:

```bash
# List all skills for all agents
copy-ai-cfg --list

# List skills for a specific agent
copy-ai-cfg --list gemini
```

### Copy a Skill

To copy a specific skill into your current project (or another target directory):

```bash
# Syntax: copy-ai-cfg <cli> <skill-name> <destination-path>

# Example: Add the 'senior-engineer' skill for Gemini to the current directory
copy-ai-cfg gemini senior-engineer .

# Example: Add 'refactor' skill for Claude to a specific project
copy-ai-cfg claude refactor ~/Code/my-new-project
```

### Copy All Skills

To import all available skills for a specific agent:

```bash
copy-ai-cfg gemini --all .
```

### Overwriting

If a skill already exists in the destination, use the `--force` flag to overwrite it:

```bash
copy-ai-cfg --force gemini senior-engineer .
```

## Repository Structure

```text
ai-cli-config/
├── .claude/           # Claude Code specific configurations
│   └── skills/        # Individual Markdown files for skills (e.g., senior_engineer.md)
├── .codex/            # OpenAI Codex specific configurations
│   └── skills/        # Directories containing skill definitions
├── .gemini/           # Gemini CLI specific configurations
│   └── skills/        # Directories containing skill definitions (SKILL.md + resources)
├── scripts/
│   └── copy-config.sh # Core logic for the deployment tool
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