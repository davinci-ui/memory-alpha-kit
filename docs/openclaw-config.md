# OpenClaw Configuration for Memory Alpha

## Required Config Snippets

### Enable Memory Search (built-in)

```json5
{
  agents: {
    defaults: {
      memorySearch: {
        enabled: true,
        sources: ["memory", "sessions"],
        provider: "local",
        query: {
          hybrid: {
            enabled: true,
            vectorWeight: 0.7,
            textWeight: 0.3,
            candidateMultiplier: 4
          }
        },
        cache: {
          enabled: true,
          maxEntries: 50000
        }
      }
    }
  }
}
```

### Memory Flush on Compaction

When context gets too long, auto-write important notes to daily memory:

```json5
{
  agents: {
    defaults: {
      compaction: {
        mode: "safeguard",
        memoryFlush: {
          enabled: true,
          softThresholdTokens: 32000,
          prompt: "Write a durable session note to memory/YYYY-MM-DD.md. Capture: decisions made, constraints discovered, open questions, task owners, and any state that would break the plan if forgotten. If nothing meaningful happened, write NO_FLUSH.",
          systemPrompt: "Be terse. Prefer bullet points. Do not rewrite the conversation."
        }
      }
    }
  }
}
```

### Load Custom Skills

Point OpenClaw at your skills directory:

```json5
{
  skills: {
    load: {
      extraDirs: ["/path/to/your/pattern-buffer/skills"],
      watch: true
    }
  }
}
```

### Agent Heartbeat

Regular check-ins to process HEARTBEAT.md tasks:

```json5
{
  agents: {
    defaults: {
      heartbeat: {
        every: "1h",
        activeHours: {
          start: "07:00",
          end: "02:00",
          timezone: "Asia/Tokyo"
        }
      }
    }
  }
}
```

## Environment Variables

Scripts expect these (or use defaults):

| Variable | Default | Purpose |
|----------|---------|---------|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant REST API |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API |
| `OPENCLAW_SESSIONS_DIR` | `~/.openclaw/workspace/sessions/` | Session files to index |
