---
name: memory-logs
description: Search agent conversation logs across Qdrant vector DB. Use when recalling past work, decisions, conversations, or context. Triggers on "remember when", "what did we decide", "search logs", "find in logs", or any question about history.
---

# Memory Logs — Conversation Recall

## Quick Search

```bash
# Semantic search (Qdrant)
python3 <pattern-buffer>/scripts/qdrant/search_memories.py --query "your search terms" --limit 5

# Smart search (hybrid)
python3 <pattern-buffer>/scripts/qdrant/smart_search.py "your search terms"
```

## Environment

Requires services running:
- Qdrant at `${QDRANT_URL:-http://localhost:6333}`
- Ollama at `${OLLAMA_URL:-http://localhost:11434}` (snowflake-arctic-embed2)

## Search Strategy

1. **Qdrant semantic search** — all conversation turns embedded via Ollama
2. Cite sources in responses

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `search_memories.py` | Semantic vector search |
| `smart_search.py` | Hybrid search |
| `harvest_sessions.py` | Batch session → Qdrant |
| `extract_facts.py` | Daily logs → atomic facts |

## Realtime Watcher

The watcher daemon monitors session files and stores turns to Qdrant automatically:
```bash
bash <pattern-buffer>/scripts/watcher/start_watcher.sh
```
