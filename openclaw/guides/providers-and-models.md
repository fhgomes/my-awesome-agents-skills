# LLM Providers & Model Configuration

How to configure, authenticate, and optimize LLM providers in OpenClaw.

---

## Supported Providers

### Anthropic (Claude)

| Model | Use Case | Relative Cost |
|-------|----------|---------------|
| claude-haiku-4-5 | Specialists, crons, sub-agents, compaction | 1x (baseline) |
| claude-sonnet-4-6 | Main agent, complex reasoning, coding | ~3x Haiku |
| claude-opus-4-6 | Critical analysis, high-stakes decisions | ~15x Haiku |

**Authentication:** API key or OAuth (monthly plan via Anthropic Console).

### OpenAI / Codex

| Model | Use Case | Notes |
|-------|----------|-------|
| gpt-4o | General purpose alternative | Good all-rounder |
| gpt-4o-mini | Cost-efficient alternative | Comparable to Haiku |
| o1 | Complex reasoning | Extended thinking |
| gpt-5.1-codex-mini | Code generation fallback | Optimized for code |

**Authentication:** OAuth from ChatGPT plan. Token expires approximately every 10 days and must be renewed via browser flow.

### Google Gemini

| Model | Use Case | Notes |
|-------|----------|-------|
| gemini-2.0-flash | Fast, cost-efficient tasks | Very fast inference |
| gemini-2.5-pro | Complex tasks | Strong reasoning |

**Authentication:** API key from Google AI Studio.

### Ollama (Local)

| Model | Use Case | Notes |
|-------|----------|-------|
| Any supported model | Local inference, privacy-sensitive tasks | Free, no quota, no network dependency |

**Authentication:** None required. Runs locally.

---

## Authentication Setup

### Anthropic — Setup Token

```bash
# Generate a setup token (interactive)
claude setup-token

# Register with OpenClaw
openclaw models auth setup-token --provider anthropic
```

### Anthropic — API Key

1. Generate a key at your Anthropic Console
2. Add to your `.env` file:

```bash
# ~/.openclaw/.env
ANTHROPIC_API_KEY=sk-ant-api03-...
```

3. Reference in config:

```jsonc
{
  "providers": {
    "anthropic": {
      "apiKey": "${ANTHROPIC_API_KEY}"
    }
  }
}
```

### OpenAI — OAuth

```bash
# Interactive browser login (~10 day token validity)
openclaw models auth login --provider openai-codex
```

**Important:** OpenAI OAuth tokens expire approximately every 10 days. This is an authentication renewal, not a quota issue. Set a reminder to re-authenticate.

### Google Gemini — API Key

1. Generate a key at Google AI Studio
2. Add to `.env`:

```bash
GEMINI_API_KEY=AIza...
```

3. Reference in config:

```jsonc
{
  "providers": {
    "google": {
      "apiKey": "${GEMINI_API_KEY}"
    }
  }
}
```

---

## Model Selection Guide

| Role | Recommended Model | Rationale |
|------|-------------------|-----------|
| Main agent (user-facing) | Sonnet | Best quality-to-cost ratio for conversation |
| Specialist agents | Haiku | ~3x cheaper, sufficient for focused tasks |
| Cron jobs | Haiku | Autonomous tasks with clear scope |
| Compaction | Haiku | Summarization is well within capability |
| Sub-agents | Haiku | Short-lived, focused tasks |
| Critical analysis | Sonnet or Opus | When accuracy is paramount |
| Code generation (primary) | Sonnet | Strong coding with good reasoning |
| Code generation (fallback) | Codex Mini | Cost-efficient code-specific model |

---

## Model Aliases

OpenClaw supports shorthand aliases:

| Alias | Resolves To |
|-------|-------------|
| `claude` | Latest Claude Sonnet |
| `haiku` | Latest Claude Haiku |
| `opus` | Latest Claude Opus |
| `sonnet` | Latest Claude Sonnet |

Use full model identifiers (e.g., `anthropic/claude-sonnet-4-6`) in production configs for reproducibility. Aliases may resolve to newer versions after updates.

---

## Fallback Configuration

Configure primary and fallback models so agents automatically switch on errors or quota exhaustion:

```jsonc
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4-6",
      "fallbackModel": "openai-codex/gpt-5.1-codex-mini"
    }
  }
}
```

### How Fallback Works

1. Agent attempts the primary model
2. On error (401, 429, timeout, quota exceeded), switches to fallback
3. Fallback is used for the remainder of the session or until the primary recovers
4. Next new session retries the primary first

### Multi-Level Fallback

```jsonc
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4-6",
      "fallbackModel": "openai-codex/gpt-5.1-codex-mini",
      "fallbackModel2": "google/gemini-2.0-flash"
    }
  }
}
```

---

## Thinking (Extended Reasoning)

The `thinking` parameter controls whether the model uses extended reasoning (chain-of-thought) before responding.

| Value | Behavior | Use Case |
|-------|----------|----------|
| `"adaptive"` | Model decides when to think deeply | Default for main agents |
| `"off"` | No extended reasoning (saves tokens) | Haiku specialists, simple tasks |

### Configuration

```jsonc
{
  "agents": {
    "defaults": {
      "thinking": "adaptive"
    },
    "list": [
      {
        "id": "researcher",
        "model": "anthropic/claude-haiku-4-5",
        "thinking": "off"
      }
    ]
  }
}
```

**Guidelines:**
- Never disable thinking for the main Sonnet agent — it significantly degrades complex reasoning
- Safe to disable for Haiku agents doing focused, routine tasks
- `adaptive` lets the model skip thinking on simple requests, saving tokens naturally

---

## Provider Configuration Example

```jsonc
{
  "providers": {
    "anthropic": {
      "apiKey": "${ANTHROPIC_API_KEY}"
    },
    "openai-codex": {
      "auth": "oauth"
    },
    "google": {
      "apiKey": "${GEMINI_API_KEY}"
    },
    "ollama": {
      "baseUrl": "http://127.0.0.1:11434"
    }
  }
}
```

---

## Quotas & Cost Management

### Anthropic (Monthly Plan / API)

- Monthly plans have daily and weekly quota allocation
- Sonnet drains quota significantly faster than Haiku (~3x per token)
- Opus drains quota very fast (~15x Haiku per token)
- When approaching limits, switch specialist agents to Haiku

### OpenAI (OAuth)

- Token expires approximately every 10 days — this is NOT a quota issue
- Re-authenticate via: `openclaw models auth login --provider openai-codex`
- Set calendar reminders for renewal

### Relative Cost Comparison

| Model | Relative Cost | Notes |
|-------|--------------|-------|
| Haiku | 1x | Baseline |
| Sonnet | ~3x | Primary workhorse |
| Opus | ~15x | Use sparingly |
| GPT-4o-mini | ~1x | Comparable to Haiku |
| GPT-4o | ~3x | Comparable to Sonnet |
| Gemini Flash | ~0.5x | Very cost-efficient |

### Cost Reduction Strategies

1. **Use Haiku for all auxiliary agents** — specialists, crons, sub-agents, compaction
2. **Keep bootstrap under 15 KB** — every KB costs tokens on every turn
3. **Enable context pruning** — `cache-ttl` with 2-hour TTL
4. **Enable memory flush** — prevents double-discovery after compaction
5. **Set thinking to "off" for Haiku** — extended reasoning adds cost without benefit on simple tasks
6. **Monitor session sizes** — bloated sessions multiply cost per turn

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `401 Unauthorized` | Invalid or expired API key/token | Regenerate key or re-authenticate OAuth |
| `429 Too Many Requests` | Quota exceeded or rate limit | Wait, switch to fallback model, or upgrade plan |
| Timeout on requests | Model overloaded or network issue | Check provider status page, verify fallback is configured |
| Thinking not working | `thinking: "off"` in config | Set to `"adaptive"` for agents that need reasoning |
| Compaction too expensive | Compaction using Sonnet/Opus | Set `compaction.model` to Haiku |
| Fallback not triggering | No `fallbackModel` configured | Add fallback to `agents.defaults` |
| OpenAI "auth expired" | OAuth token past ~10 day validity | Re-run `openclaw models auth login --provider openai-codex` |
| Ollama connection refused | Ollama server not running | Start Ollama: `ollama serve` or check container |
| Provider unknown key error | Typo in provider config | Validate config with `openclaw doctor` |
| Model not found | Wrong model identifier | Use full `provider/model-name` format, check provider docs |

---

## Quick Reference

```jsonc
{
  "providers": {
    "anthropic": { "apiKey": "${ANTHROPIC_API_KEY}" },
    "openai-codex": { "auth": "oauth" },
    "google": { "apiKey": "${GEMINI_API_KEY}" },
    "ollama": { "baseUrl": "http://127.0.0.1:11434" }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4-6",
      "fallbackModel": "openai-codex/gpt-5.1-codex-mini",
      "thinking": "adaptive"
    },
    "list": [
      {
        "id": "<specialist>",
        "model": "anthropic/claude-haiku-4-5",
        "thinking": "off"
      }
    ]
  },
  "subagents": {
    "model": "anthropic/claude-haiku-4-5"
  },
  "compaction": {
    "model": "anthropic/claude-haiku-4-5"
  }
}
```
