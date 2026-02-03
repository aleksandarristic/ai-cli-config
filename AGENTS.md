# Agents & Skills Inventory

This document lists the available AI agents and their corresponding skills maintained in this repository.

## 1. Claude (`.claude`)

Claude skills are stored as individual Markdown files.

- **senior-engineer** (`senior_engineer.md`)
  - *Description*: Activates a senior software engineer persona.

## 2. Gemini (`.gemini`)

Gemini skills are structured as directories containing a `SKILL.md` file and optional resources.

- **senior-engineer**
  - *Location*: `.gemini/skills/senior-engineer/`
  - *Components*: `SKILL.md`, `references/behaviors.md`, `references/patterns.md`, `references/standards.md`

## 3. Codex (`.codex`)

Codex skills are highly specialized, often focusing on specific languages (Go, Python, TypeScript, Node.js) and engineering tasks (Refactoring, Performance, Hygiene).

### Go (Golang)
- **go-api-stability-and-migrations**: Ensure API stability and manage migrations.
- **go-architecture-review**: Review Go project architecture.
- **go-dependency-and-packaging-hygiene**: Manage Go modules and packaging.
- **go-performance-triage**: Triage and resolve performance issues in Go.
- **go-refactor-and-simplify**: Refactor Go code for simplicity.

### Node.js
- **nodejs-api-stability-and-migrations**: API stability for Node.js services.
- **nodejs-architecture-review**: Node.js architectural assessment.
- **nodejs-dependency-and-packaging-hygiene**: NPM/Yarn dependency management.
- **nodejs-performance-triage**: Node.js performance tuning.
- **nodejs-refactor-and-simplify**: Modernize and simplify Node.js code.

### Python
- **python-api-stability-and-migrations**: Python API evolution strategies.
- **python-architecture-review**: Python codebase architectural review.
- **python-dependency-and-packaging-hygiene**: Pip/Poetry dependency management.
- **python-performance-triage**: Python performance optimization.
- **python-refactor-and-simplify**: Refactor Python scripts and modules.

### TypeScript
- **typescript-api-stability-and-migrations**: TypeScript API versioning.
- **typescript-architecture-review**: TypeScript system architecture.
- **typescript-dependency-and-packaging-hygiene**: TypeScript package management.
- **typescript-performance-triage**: TypeScript runtime performance.
- **typescript-refactor-and-simplify**: Refactor TypeScript codebases.

### General Engineering
- **senior-software-engineer-high**: High-level senior engineering guidance.
- **senior-software-engineer-low**: Low-level implementation details and coding standards.
