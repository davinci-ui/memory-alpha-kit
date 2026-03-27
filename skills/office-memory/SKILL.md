---
name: office-memory
description: Universal memory search — auto-routes across Hindsight (facts/entities), Memory Alpha (conversations), Documents (files), and Workspace (agent memory files). Use FIRST for ANY question about people, decisions, facts, history, documents, or preferences.
trigger: remember, recall, what do we know, look up, find, search, who is, when did, check memory, do we have info on
---

# Office Memory — Unified Search

Search ALL memory layers with one command. Use this FIRST for any recall, knowledge lookup, or document search.

## Quick Start

```bash
# Search everything (auto-routed)
python3 /Users/davinci/Projects/memory-alpha-kit/scripts/office-memory/search.py --query "What do we know about ASER?"

# Search specific layer
python3 /Users/davinci/Projects/memory-alpha-kit/scripts/office-memory/search.py --query "training manual" --layer documents
python3 /Users/davinci/Projects/memory-alpha-kit/scripts/office-memory/search.py --query "March 17 decisions" --layer qdrant
python3 /Users/davinci/Projects/memory-alpha-kit/scripts/office-memory/search.py --query "brand strategy" --layer hindsight

# Store a memory
python3 /Users/davinci/Projects/memory-alpha-kit/scripts/office-memory/search.py --retain "ASER committed to 4 containers/month of Angel Pita" --bank office --context "sales lead"
```

## Auto-Routing

When using `--layer auto` (the default), queries are automatically routed to the most relevant layers:

| Signal | Route to |
|--------|----------|
| "who", "what is", people names, "entity", "about [X]" | `hindsight` first, then `qdrant` |
| "when did we", "decided", "conversation", "discussed", "last time", "remember when" | `qdrant` first, then `hindsight` |
| "document", "manual", "file", "PDF", "checklist", "SOP", "find the" | `documents` first |
| "preference", "rule", "identity", "tone", "how do we", "our approach" | `workspace` first, then `hindsight` |
| Anything else / ambiguous | all layers |

## When to Use Which Layer

| Question Type | Layer | Example |
|--------------|-------|---------|
| Facts, entities, patterns | `hindsight` | "What do we know about Gate Gourmet?" |
| Past conversations, decisions | `qdrant` | "When did we decide to use Docker?" |
| Documents, manuals, files | `documents` | "Find the HR onboarding checklist" |
| Preferences, rules, identity | `workspace` | "What's our approach to customer service?" |
| Any / unsure | `auto` (default) | "What's our tahini pricing?" |

## Hindsight Banks

| Bank | Purpose |
|------|---------|
| `office` | Shared team memory (default) |
| `davinci` | DaVinci's personal memory |
| `hal` | HAL's personal memory |
| `sherry` | Sherry's personal memory |
| `foodex` | Foodex sales intelligence |

## Storing Memories

When you learn something important, store it:

```bash
python3 /Users/davinci/Projects/memory-alpha-kit/scripts/office-memory/search.py \
  --retain "Kobe Bussan has 1,000+ stores and showed interest in bulk tahini" \
  --bank office \
  --context "foodex sales lead"
```

## Output

Returns JSON array with results tagged by layer:
```json
[
  {"layer": "hindsight", "type": "world", "text": "...", "entities": [...]},
  {"layer": "qdrant", "text": "..."},
  {"layer": "documents", "method": "vector", "path": "/Shared Documents/...", "similarity": 0.42},
  {"layer": "workspace", "source": "MEMORY.md", "text": "...", "match_type": "keyword"}
]
```

## Verbose Mode

Use `--verbose` to see routing information:

```bash
python3 /Users/davinci/Projects/memory-alpha-kit/scripts/office-memory/search.py --query "Falafel Brothers" --verbose
```

This will include a `_routing` key in the output showing how the query was classified and which layers were searched.
