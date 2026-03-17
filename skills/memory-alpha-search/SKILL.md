---
name: memory-alpha-search
description: Search the Memory Alpha knowledge base. Use when recalling information, decisions, or context. Triggers on "search memory alpha", "find in memory", "search knowledge base", or any question about stored knowledge.
---

# Memory Alpha Search — Knowledge Base Query

## Quick Search

```bash
# Semantic search (Qdrant)
python3 <pattern-buffer>/skills/memory-alpha-search/search_memory_alpha.py --query "your search terms" --limit 5

# Search with context
python3 <pattern-buffer>/skills/memory-alpha-search/search_memory_alpha.py --query "your search terms" --context "additional context" --limit 5
```

## Environment

Requires services running:
- Qdrant at `${QDRANT_URL:-http://localhost:6333}`
- Ollama at `${OLLAMA_URL:-http://localhost:11434}` (snowflake-arctic-embed2)

## Response Format

Search results include:
- File path where the information was found
- Relevant text chunk (with context)
- Similarity score (0.0-1.0)
- Last modified timestamp
