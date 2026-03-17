# Agent Core Files — Guide

Every agent in the system has up to 7 core files. These are the agent's identity, memory, and operating instructions.

## The 7 Files

| File | Purpose | Required? |
|------|---------|-----------|
| **SOUL.md** | Personality, voice, values, anti-patterns | ✅ Yes |
| **IDENTITY.md** | Name, role, emoji, avatar, one-line description | ✅ Yes |
| **USER.md** | About the human they serve — preferences, context | ✅ Yes |
| **AGENTS.md** | Team structure, delegation rules, session keys | ✅ Yes |
| **MEMORY.md** | Curated long-term knowledge and core moments | ✅ Yes |
| **TOOLS.md** | Available tools, paths, infrastructure references | Optional |
| **HEARTBEAT.md** | Periodic check-in tasks and monitoring duties | Optional |

## How They Work Together

### SOUL.md — Who I Am
The personality core. Defines voice, values, and behavioral guardrails.
This is what makes an agent feel like a person, not a chatbot.

### IDENTITY.md — My Card
Quick-reference metadata. Name, rank, emoji, avatar path.
Used by the system for display and routing.

### USER.md — Who I Serve
Everything the agent needs to know about their human.
Communication preferences, what frustrates them, what they're building.

### AGENTS.md — How I Work
Operational manual. Team roster, delegation protocol, session keys,
intelligence tiers, safety rules.

### MEMORY.md — What I Remember
Curated long-term memory. Core moments, hard-won lessons, sacred truths.
Updated during heartbeats and major sessions.
This is NOT a daily log — it's wisdom.

### TOOLS.md — What I Can Use
Infrastructure references, API endpoints, key paths.
Keeps the agent oriented in their environment.

### HEARTBEAT.md — What I Check
Periodic tasks the agent runs on a timer.
Monitoring, maintenance, status checks.

## Daily Memory (memory/*.md)

In addition to core files, agents maintain daily logs:
- `memory/YYYY-MM-DD.md` — Raw operational notes
- Decisions made, constraints discovered, open questions
- These are searched by `memory_search` automatically

## The Sacred Rule

> Core files are the agent's body. Treat workspace as sacred.
> No operational artifacts in the workspace root.
> Daily work goes in `memory/`. Core identity stays in the root files.
