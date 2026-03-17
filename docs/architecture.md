# Memory Alpha — Architecture

## Overview

Memory Alpha is a long-term memory and identity system for OpenClaw agents. It provides:

1. **Agent Identity** — Core personality files (SOUL, MEMORY, AGENTS, etc.)
2. **Semantic Search** — Vector-based recall across all conversations
3. **Realtime Indexing** — Auto-stores new session turns as they happen
4. **Fact Extraction** — Distills daily logs into atomic, searchable facts
5. **Hybrid Search** — Combines vector similarity + keyword matching

## Components

```
┌─────────────────────────────────────────────────┐
│                  OpenClaw Agent                   │
│                                                   │
│  SOUL.md  MEMORY.md  AGENTS.md  USER.md  etc.   │
│  (Identity files — who the agent IS)              │
└─────────────┬───────────────────┬─────────────────┘
              │                   │
              │ memory_search     │ skills
              │ (built-in)        │ (memory-logs, etc.)
              │                   │
┌─────────────▼───────────────────▼─────────────────┐
│              Qdrant Vector DB                      │
│                                                    │
│  conversation_logs  — session conversations          │
│  memories_tr      — extracted facts & knowledge    │
│                                                    │
│  Embeddings: snowflake-arctic-embed2 (1024-dim)     │
│  Via: Ollama (local, zero API cost)                │
└────────────────────────────────────────────────────┘
```

## Data Flow

### Ingestion
1. **Realtime Watcher** monitors OpenClaw session files
2. New conversation turns → embedded via Ollama → stored in Qdrant
3. Daily `harvest_sessions.py` catches anything the watcher missed
4. `extract_facts.py` distills daily logs into atomic facts

### Retrieval
1. Agent receives a question about past work/decisions
2. `memory-logs` skill triggers semantic search
3. Query → embedded → Qdrant similarity search
4. Top results returned with source citations

### Identity
- 7 core files per agent define who they are
- MEMORY.md = curated long-term knowledge
- memory/*.md = daily operational logs
- These persist across session resets (files ARE memory)

## Infrastructure

| Service | Purpose | Default URL |
|---------|---------|-------------|
| Qdrant | Vector database | http://localhost:6333 |
| Ollama | Embedding model | http://localhost:11434 |

Both run as Docker containers. See `docker/docker-compose.yml`.

## Collections

| Collection | Content | Use Case |
|------------|---------|----------|
| `conversation_logs` | Raw conversation turns | "What did we discuss about X?" |
| `memories_tr` | Extracted facts & knowledge | "What do we know about Y?" |

## Embedding Model

**snowflake-arctic-embed2** (via Ollama)
- 1024 dimensions
- Cosine similarity
- Zero API cost (runs locally)
- ~1.1GB model size
