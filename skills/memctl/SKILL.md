---
name: memctl
description: Memory Alpha project management CLI (zero-token). Use when creating new projects, updating project status, rebuilding indexes, or validating projects. Triggers on "new project", "create project", "project status", "lint projects", "index projects".
---

# memctl — Memory Alpha Control Tool

## Commands

```bash
# Create new project
memctl create <category> <name> [--author "Name"] [--title "Title"]

# Rebuild project index
memctl index [--format json|markdown]

# Update project status
memctl status <project-name> <active|paused|complete|archived>

# Validate all projects
memctl lint [--fix]
```

## Rules

- **Every new project MUST use `memctl create`** — no ad-hoc folders
- Paths ARE the taxonomy
- `meta.yaml` stores only: status, author, stardate, search_tags
