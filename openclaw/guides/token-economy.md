# Token Economy — Reducing Costs Without Sacrificing Quality

A practical guide to controlling LLM token spend in OpenClaw while keeping your agents sharp and responsive.

---

## 1. Bootstrap Diet

Every bootstrap file loads into **every** conversation turn for an agent. If your bootstrap payload is bloated, you pay for it on every single request.

### File Budget

| File | Max Size | Purpose |
|------|----------|---------|
| `SOUL.md` | < 3 KB | Core personality, mission, hard rules |
| `AGENTS.md` | < 2 KB | Agent roster and coordination rules |
| `MEMORY.md` | < 5 KB | Routing index to detailed memory files |
| `TOOLS.md` | < 2 KB | Tool usage rules and restrictions |
| `USER.md` | < 1.5 KB | User preferences and context |
| **Total** | **< 15 KB** | Everything the model sees on every turn |

### Golden Rule

> If removing a line does not change the agent's behavior, remove it.

### Silent Truncation

When bootstrap exceeds the model's internal budget, OpenClaw applies truncation: approximately 70% from the head, 20% from the tail, with a cut marker in the middle. **Instructions in the middle of large files will silently vanish.** This is why staying under budget is non-negotiable.

### On-Demand Pattern

Move reference data out of bootstrap files and into `memory/` subdirectories. Keep only pointers in the main files:

```markdown
<!-- In MEMORY.md (lean routing index) -->
## Infrastructure
See memory/infrastructure.md for server details, ports, and services.

## Projects
See memory/projects/<name>.md for per-project context.
```

### Anti-Patterns to Avoid

- Pasting full config dumps into SOUL.md or MEMORY.md
- Listing every tool parameter in TOOLS.md (the model already knows them)
- Duplicating information across multiple bootstrap files
- Storing historical logs in any bootstrap file

---

## 2. Model Selection

Not every task needs your most expensive model. Strategic model assignment is the single biggest cost lever.

| Role | Recommended Model | Rationale |
|------|-------------------|-----------|
| Main agent (user-facing) | Sonnet | Best quality/cost ratio for conversation |
| Specialist agents | Haiku | ~3x cheaper, sufficient for focused tasks |
| Cron jobs | Haiku | Autonomous tasks don't need top-tier reasoning |
| Compaction | Haiku | Summarization is well within Haiku's capability |
| Sub-agents | Haiku | Short-lived, focused tasks |
| Critical analysis | Sonnet or Opus | When accuracy is paramount |

### Configuration

```jsonc
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4-6"  // Main agent default
    },
    "list": [
      {
        "id": "researcher",
        "model": "anthropic/claude-haiku-4-5"  // Per-agent override
      }
    ]
  },
  "subagents": {
    "model": "anthropic/claude-haiku-4-5"  // All sub-agents
  },
  "compaction": {
    "model": "anthropic/claude-haiku-4-5"  // Compaction summarizer
  }
}
```

---

## 3. Context Pruning

Pruning removes old conversation turns to keep the context window manageable. Without it, long sessions balloon in cost.

### Recommended Configuration

```jsonc
{
  "context": {
    "pruning": {
      "mode": "cache-ttl",
      "ttl": "2h",
      "keepLastAssistants": 2,
      "minPrunableToolChars": 20000,
      "tools": {
        "deny": ["exec", "filesystem_write"]
      }
    }
  }
}
```

**Key settings:**

- `mode: "cache-ttl"` — prunes turns older than `ttl`, keeping recent context fresh
- `ttl: "2h"` — 2 hours of conversation history retained. Do not drop below 1 hour
- `keepLastAssistants: 2` — always keep the last 2 assistant responses regardless of age
- `minPrunableToolChars: 20000` — only prune tool results larger than 20K characters (protects small, important results)
- `tools.deny` — never prune results from critical tools (exec output, filesystem writes)

### Hard Clear Mode

For sessions that must stay minimal:

```jsonc
{
  "context": {
    "pruning": {
      "mode": "hard-clear",
      "placeholder": "Previous context cleared. Key decisions preserved in memory."
    }
  }
}
```

---

## 4. Compaction

When a session grows too large, compaction summarizes the conversation to free up context space.

### Recommended Configuration

```jsonc
{
  "compaction": {
    "mode": "safeguard",
    "reserveTokensFloor": 24000,
    "identifierPolicy": "strict",
    "model": "anthropic/claude-haiku-4-5",
    "memoryFlush": {
      "enabled": true,
      "softThresholdTokens": 6000
    }
  }
}
```

**Key settings:**

- `mode: "safeguard"` — chunked summarization that preserves key information. **Never use `aggressive` mode** — it discards too much context and causes agents to repeat work
- `reserveTokensFloor: 24000` — minimum tokens to keep available after compaction
- `identifierPolicy: "strict"` — preserves file paths, IDs, and references during summarization
- `model: haiku` — compaction does not need your most expensive model

### Memory Flush (Critical)

Memory flush saves important data to disk **before** compaction destroys it:

- `enabled: true` — the agent writes key findings to `memory/` files before compaction runs
- `softThresholdTokens: 6000` — triggers flush when context reaches this threshold before compaction

**Without memory flush:** the agent loses information during compaction, then re-discovers it in subsequent turns, doubling your token spend.

---

## 5. Context Size

Choose context window sizes based on the agent's role:

| Agent Type | Context Size | Notes |
|------------|-------------|-------|
| Main (Sonnet) | 128K | Never set below 80K for primary agents |
| Specialist (Haiku) | 50K-80K | Sufficient for focused tasks |
| Cron agents | 50K | Short-lived sessions with clear scope |

**Rules of thumb:**

- Never reduce pruning TTL below 1 hour — agents lose critical recent context
- If an agent consistently hits context limits, check for tool output bloat before increasing the window
- Larger context windows cost more per turn — right-size for the task

---

## 6. Agent Behavioral Rules

Embed these rules in your agent's `SOUL.md` to reduce unnecessary token consumption:

```markdown
## Efficiency Rules
- Never repeat the user's message back to them
- Summarize large tool outputs instead of including them verbatim
- Batch parallel tool calls into a single turn when possible
- Never fetch the same resource twice in one session
- Check loaded context and memory before making external calls
- Daily logs: maximum 30 lines per day
- MEMORY.md: maximum 50 lines total
```

These rules prevent the most common sources of token waste: redundant fetches, verbose responses, and bloated memory files.

---

## 7. Session Management

### Identifying Bloated Sessions

Sessions over 3 MB indicate runaway context growth. Find and clean them:

```bash
# Find large session files
find ~/.openclaw/sessions/ -name "*.jsonl" -size +3M

# Remove specific bloated sessions (agent will start fresh)
rm ~/.openclaw/sessions/<session-id>.jsonl

# Restart the service after cleanup
systemctl restart openclaw
```

### In-Session Commands

| Command | Effect |
|---------|--------|
| `/compact` | Trigger immediate compaction |
| `/new` | Start a new session (preserves memory) |
| `/reset` | Full reset (clears session state) |

### Auto-Maintenance Configuration

```jsonc
{
  "sessions": {
    "maintenance": {
      "enforce": true,
      "prune": "14d",
      "maxEntries": 200,
      "rotate": "5mb",
      "maxDisk": "200mb"
    }
  }
}
```

This automatically prunes sessions older than 14 days, rotates files at 5 MB, and caps total disk usage at 200 MB.

---

## 8. Common Cost Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| High baseline cost | Sonnet assigned to all agents | Use Haiku for specialists, crons, sub-agents |
| Cost spikes on long conversations | No pruning or compaction configured | Enable `cache-ttl` pruning + `safeguard` compaction |
| Oversized bootstrap | SOUL.md or MEMORY.md over budget | Apply bootstrap diet, move data to `memory/` |
| Expensive compaction | Compaction using Sonnet/Opus | Set `compaction.model` to Haiku |
| Double-discovery after compaction | `memoryFlush` disabled | Enable memory flush with `softThresholdTokens: 6000` |
| Repeated tool calls | Agent fetches same resource multiple times | Add "check context first" rule to SOUL.md |
| Verbose agent responses | No efficiency rules in bootstrap | Add behavioral rules from Section 6 |
| Session files growing unbounded | No auto-maintenance | Configure session maintenance with prune/rotate limits |
| Cron jobs burning tokens | Crons using main agent's expensive model | Assign dedicated Haiku agent for cron workloads |
| Sub-agent chains | Deep spawn chains with expensive models | Set `subagents.model` to Haiku, limit `maxSpawnDepth` |

---

## Quick Reference: Minimum Viable Cost Config

```jsonc
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4-6"
    },
    "list": [
      { "id": "<specialist>", "model": "anthropic/claude-haiku-4-5" }
    ]
  },
  "subagents": {
    "model": "anthropic/claude-haiku-4-5"
  },
  "compaction": {
    "mode": "safeguard",
    "reserveTokensFloor": 24000,
    "model": "anthropic/claude-haiku-4-5",
    "memoryFlush": {
      "enabled": true,
      "softThresholdTokens": 6000
    }
  },
  "context": {
    "pruning": {
      "mode": "cache-ttl",
      "ttl": "2h",
      "keepLastAssistants": 2,
      "minPrunableToolChars": 20000
    }
  },
  "sessions": {
    "maintenance": {
      "enforce": true,
      "prune": "14d",
      "maxEntries": 200,
      "rotate": "5mb",
      "maxDisk": "200mb"
    }
  }
}
```
