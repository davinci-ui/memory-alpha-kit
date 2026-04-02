# Memory Alpha Kit

A portable long-term memory, identity, and semantic recall system for [OpenClaw](https://github.com/openclaw/openclaw) agents.

Give your AI agents persistent memory across sessions, semantic search over all conversations, and a structured identity that survives restarts.

## Features

- **Agent Identity System** — 7 core files that define who your agent is
- **Semantic Search** — Vector-based recall across all conversations (Qdrant + Ollama)
- **Realtime Indexing** — Auto-stores new session turns as they happen
- **Fact Extraction** — Distills daily logs into atomic, searchable facts
- **Hybrid Search** — Combines vector similarity + keyword matching
- **Disaster Recovery** — `git clone` and you're back in business

## Quick Start

### 1. Start Infrastructure

```bash
cd docker
docker compose up -d
bash setup-qdrant.sh
```

This gives you:
- **Qdrant** (vector DB) on port 6333
- **Ollama** (embeddings) on port 11434
- **snowflake-arctic-embed2** model (1024-dim, zero API cost)

### 2. Create Your Agent

Copy the templates and customize:

```bash
cp -r templates/agent/ my-agent/
# Edit each file — SOUL.md, IDENTITY.md, USER.md, etc.
```

### 3. Configure OpenClaw

Add to your `openclaw.json`:

```json5
{
  agents: {
    defaults: {
      workspace: "/path/to/my-agent",
      memorySearch: {
        enabled: true,
        sources: ["memory", "sessions"],
        provider: "local",
        query: {
          hybrid: {
            enabled: true,
            vectorWeight: 0.7,
            textWeight: 0.3
          }
        }
      },
      compaction: {
        memoryFlush: {
          enabled: true,
          softThresholdTokens: 32000
        }
      }
    }
  },
  skills: {
    load: {
      extraDirs: ["/path/to/memory-alpha-kit/skills"],
      watch: true
    }
  }
}
```

See `docs/openclaw-config.md` for full config reference.

### 4. Index Existing Sessions

```bash
cd scripts/qdrant
python3 harvest_sessions.py
```

### 5. Start the Watcher

```bash
cd scripts/watcher
bash start_watcher.sh
```

Now every conversation turn is automatically embedded and searchable.

## Structure

```
memory-alpha-kit/
├── templates/agent/       # Blank starter files for new agents
│   ├── SOUL.md            # Personality, voice, values
│   ├── IDENTITY.md        # Name, role, emoji
│   ├── USER.md            # About the human
│   ├── AGENTS.md          # Team structure, delegation
│   ├── MEMORY.md          # Long-term curated knowledge
│   ├── TOOLS.md           # Infrastructure references
│   └── HEARTBEAT.md       # Periodic check-in tasks
├── scripts/
│   ├── qdrant/            # 18 Python scripts for vector search
│   └── watcher/           # Realtime session indexer
├── skills/                # OpenClaw skills (plug and play)
├── docker/                # Qdrant + Ollama docker-compose
└── docs/                  # Architecture, guides, config reference
```

## The 7 Core Files

| File | Purpose |
|------|---------|
| **SOUL.md** | Personality, voice, values — what makes the agent *them* |
| **IDENTITY.md** | Name, role, emoji — quick-reference metadata |
| **USER.md** | About the human — preferences, context, communication style |
| **AGENTS.md** | Team structure, delegation rules, operational manual |
| **MEMORY.md** | Curated long-term knowledge — wisdom, not logs |
| **TOOLS.md** | Available tools, paths, infrastructure |
| **HEARTBEAT.md** | Periodic monitoring tasks |

## Requirements

- [OpenClaw](https://github.com/openclaw/openclaw) gateway
- Docker (for Qdrant + Ollama)
- Python 3.10+

## Philosophy

> **Files ARE memory.** Sessions reset, but files persist.  
> **If it's not written down, it didn't happen.**  
> **Git is the disaster recovery kit.** Clone and you're back.

## License

MIT

## Document Processing Capabilities (2026-04-02)

### Apple iWork Documents
- **.pages**: Direct text extraction + PDF fallback → markdown
- **.numbers**: Multi-sheet CSV export + markdown summaries
- **Dual output**: Raw data preservation + human-readable summaries

### Processing Performance
- .pages: ~2 seconds, perfect text quality
- .numbers: ~3-5 seconds, complete data integrity
- Zero cost, 100% local processing

### Integration Ready
All pipelines tested and documented for Memory Alpha file-mirror-system integration.
