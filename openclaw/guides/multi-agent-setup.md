# Multi-Agent Setup Guide

A comprehensive guide to designing, configuring, and operating multiple AI agents in OpenClaw.

---

## Concepts

Each agent in OpenClaw is an **isolated instance** with its own:

- **ID** — unique identifier used in config, bindings, and inter-agent communication
- **Workspace** — directory containing the agent's files and state
- **Model** — the LLM powering the agent (can differ per agent)
- **Permissions** — what tools, channels, and agents it can access
- **Identity** — persona and behavioral rules loaded from bootstrap files

Agents communicate through OpenClaw's message bus, not directly. This ensures isolation, auditability, and loop prevention.

---

## Workspace Structure

Each agent needs a dedicated directory under your OpenClaw config:

```
~/.openclaw/
  agents/
    <agent-id>/
      SOUL.md          # Core personality, mission, hard rules
      AGENTS.md        # Roster of all agents and coordination rules
      IDENTITY.md      # Detailed persona (optional, for complex agents)
      USER.md          # User preferences relevant to this agent
      TOOLS.md         # Tool usage rules and restrictions
      HEARTBEAT.md     # Periodic self-check instructions (optional)
      memory/          # Agent's persistent memory
        YYYY-MM-DD.md  # Daily logs
        decisions.md   # Key decisions
        lessons.md     # Learned patterns
```

**Key principles:**

- SOUL.md must be under 3 KB — it loads on every turn
- Each agent should have a clear, focused mission
- Shared context goes in AGENTS.md (same file across all agents)
- Agent-specific context goes in SOUL.md and IDENTITY.md

---

## Configuration (openclaw.json)

### Agent List

Define each agent in the `agents.list` array:

```jsonc
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4-6",
      "thinking": "adaptive"
    },
    "list": [
      {
        "id": "jarvis",
        "workspace": "~/.openclaw/agents/jarvis",
        "agentDir": "~/.openclaw/agents/jarvis",
        "model": "anthropic/claude-sonnet-4-6",
        "identity": "Main assistant — general purpose, orchestration",
        "subagents": {
          "allowAgents": ["researcher", "coder", "reviewer"]
        }
      },
      {
        "id": "researcher",
        "workspace": "~/.openclaw/agents/researcher",
        "agentDir": "~/.openclaw/agents/researcher",
        "model": "anthropic/claude-haiku-4-5",
        "identity": "Web research specialist"
      },
      {
        "id": "coder",
        "workspace": "~/.openclaw/agents/coder",
        "agentDir": "~/.openclaw/agents/coder",
        "model": "anthropic/claude-sonnet-4-6",
        "identity": "Software development specialist"
      },
      {
        "id": "reviewer",
        "workspace": "~/.openclaw/agents/reviewer",
        "agentDir": "~/.openclaw/agents/reviewer",
        "model": "anthropic/claude-haiku-4-5",
        "identity": "Code review and QA specialist"
      }
    ]
  }
}
```

### Per-Agent Model Overrides

Model overrides go **inside** the `agents.list` entry, NOT as top-level keys under `agents`. OpenClaw rejects unknown JSON keys and will crash on startup if you place them incorrectly.

---

## Inter-Agent Communication

### Enabling Agent-to-Agent Messaging

```jsonc
{
  "tools": {
    "agentToAgent": {
      "enabled": true,
      "allow": ["jarvis", "researcher", "coder", "reviewer"]
    }
  }
}
```

### Available Communication Tools

| Tool | Purpose |
|------|---------|
| `sessions_send` | Send a message to another agent's active session |
| `sessions_spawn` | Create a new session for another agent with a specific task |
| `sessions_list` | List active sessions across agents |

### Loop Detection

**Always enabled.** OpenClaw automatically detects and breaks circular agent-to-agent message chains. If Agent A spawns Agent B, which sends back to Agent A, which spawns Agent B again, the loop detector intervenes after the configured depth limit.

Never disable loop detection. It prevents runaway token consumption and infinite agent chains.

---

## Bindings

Bindings map communication channels to specific agents. This controls which agent responds in which context.

### Discord Bindings

```jsonc
{
  "channels": {
    "discord": [
      {
        "account": "<bot-name>",
        "bindings": [
          {
            "guildId": "<guild-id>",
            "channelId": "<channel-id>",
            "agent": "jarvis"
          },
          {
            "guildId": "<guild-id>",
            "channelId": "<dev-channel-id>",
            "agent": "coder"
          }
        ]
      }
    ]
  }
}
```

### Slack Bindings

```jsonc
{
  "channels": {
    "slack": [
      {
        "workspace": "<workspace-name>",
        "bindings": [
          {
            "channelId": "<channel-id>",
            "agent": "jarvis"
          }
        ]
      }
    ]
  }
}
```

### Multiple Bots

You can run multiple Discord bots, each bound to different agents:

```jsonc
{
  "channels": {
    "discord": [
      {
        "account": "main-bot",
        "bindings": [
          { "guildId": "<id>", "channelId": "<id>", "agent": "jarvis" }
        ]
      },
      {
        "account": "dev-bot",
        "bindings": [
          { "guildId": "<id>", "channelId": "<id>", "agent": "coder" }
        ]
      }
    ]
  }
}
```

---

## Permission Graph Design

The permission graph controls which agents can spawn or message other agents. Design it with security in mind.

### Core Principles

1. **Public-facing agents must NOT spawn the main agent.** If a Discord channel agent can spawn your orchestrator, any user in that channel can indirectly control your entire system.

2. **Main agent can spawn all specialists.** The orchestrator needs access to delegate work.

3. **Specialists available to coordinators only.** Coding agents should be reachable from project management agents, not directly from public channels.

### Example Permission Graph

```
                    +---------+
                    | jarvis  | (main orchestrator)
                    +----+----+
                         |
            +------------+------------+
            |            |            |
       +----+----+ +----+----+ +-----+----+
       |researcher| | coder  | | reviewer |
       +---------+ +----+----+ +----------+
                         |
                    +----+----+
                    | tester  | (sub-agent of coder)
                    +---------+

  Public channels → jarvis only
  jarvis → can spawn researcher, coder, reviewer
  coder → can spawn tester
  researcher, reviewer, tester → cannot spawn anyone
```

### Configuration

```jsonc
{
  "agents": {
    "list": [
      {
        "id": "jarvis",
        "subagents": {
          "allowAgents": ["researcher", "coder", "reviewer"]
        }
      },
      {
        "id": "coder",
        "subagents": {
          "allowAgents": ["tester"]
        }
      },
      {
        "id": "researcher",
        "subagents": {
          "allowAgents": []
        }
      }
    ]
  }
}
```

---

## Sub-Agent Limits

Prevent runaway agent spawning with these controls:

```jsonc
{
  "subagents": {
    "maxConcurrent": 4,
    "maxSpawnDepth": 3,
    "maxChildrenPerAgent": 5,
    "model": "anthropic/claude-haiku-4-5"
  }
}
```

| Setting | Purpose | Recommended |
|---------|---------|-------------|
| `maxConcurrent` | Max sub-agents running at once | 3-5 |
| `maxSpawnDepth` | Max chain depth (A spawns B spawns C) | 2-3 |
| `maxChildrenPerAgent` | Max children per parent agent | 3-5 |
| `model` | Default model for all sub-agents | Haiku (cost control) |

---

## Message Queues

When multiple messages arrive in rapid succession (common in group chats), the message queue prevents the agent from processing each one individually.

```jsonc
{
  "channels": {
    "messageQueue": {
      "mode": "collect",
      "debounceMs": 2000,
      "cap": 10,
      "drop": "summarize"
    }
  }
}
```

- `mode: "collect"` — batches incoming messages within the debounce window
- `debounceMs: 2000` — waits 2 seconds for additional messages before processing
- `cap: 10` — maximum messages to collect in one batch
- `drop: "summarize"` — if cap is exceeded, summarize the overflow instead of dropping it silently

---

## Event Bus

OpenClaw provides two event types for different use cases:

### systemEvent

Injects into the **main agent's active session**. Has access to the full conversation context.

**Use for:** heartbeats, context-aware status checks, follow-up actions within an ongoing conversation.

```jsonc
{
  "type": "systemEvent",
  "agent": "jarvis",
  "payload": "Check the status of the deployment we discussed earlier."
}
```

### agentTurn

Creates an **isolated session** for the target agent. Clean context, no conversation history.

**Use for:** periodic autonomous tasks, cron jobs, independent operations.

```jsonc
{
  "type": "agentTurn",
  "agent": "researcher",
  "payload": "Summarize today's tech news."
}
```

### Thread Binding (Discord)

When an agent responds in a Discord thread, subsequent messages in that thread route to the same agent session, maintaining conversation continuity.

---

## Example: Creating a New Specialist Agent

### Step 1: Create the Workspace

```bash
mkdir -p ~/.openclaw/agents/<new-agent>/memory
```

### Step 2: Write Bootstrap Files

**SOUL.md** (under 3 KB):
```markdown
# <Agent Name>

You are <agent-name>, a specialist in <domain>.

## Mission
<One-sentence mission statement.>

## Rules
- <Rule 1>
- <Rule 2>
- Always save important findings to memory/ before session ends
```

**AGENTS.md** (under 2 KB):
```markdown
# Agent Roster

| ID | Role | When to Contact |
|----|------|----------------|
| jarvis | Main orchestrator | Escalation, cross-domain questions |
| <new-agent> | <Domain> specialist | <When this agent is relevant> |
```

**IDENTITY.md**:
```markdown
# Identity

Name: <Agent Name>
Tone: <professional/casual/technical>
Specialization: <domain details>
```

### Step 3: Add to openclaw.json

```jsonc
{
  "agents": {
    "list": [
      // ... existing agents ...
      {
        "id": "<new-agent>",
        "workspace": "~/.openclaw/agents/<new-agent>",
        "agentDir": "~/.openclaw/agents/<new-agent>",
        "model": "anthropic/claude-haiku-4-5",
        "identity": "<One-line description>"
      }
    ]
  }
}
```

### Step 4: Update Permissions

Add the new agent to the appropriate `allowAgents` lists and `agentToAgent.allow`.

### Step 5: Set Ownership and Restart

```bash
chown -R <your-user>:<your-user> ~/.openclaw/agents/<new-agent>
openclaw doctor --fix
systemctl restart openclaw
```

---

## Ready-to-Use Prompts

### 1. Create a New Agent

> Create a new OpenClaw agent called `<name>` that specializes in `<domain>`. It should use Haiku, have its own workspace at `~/.openclaw/agents/<name>/`, and be spawnable by the main agent. Write SOUL.md, AGENTS.md, and IDENTITY.md. Add it to openclaw.json and update the permission graph.

### 2. Bind an Agent to a Discord Channel

> Bind the `<agent-id>` agent to Discord channel `<channel-id>` in guild `<guild-id>` using the `<bot-name>` bot account. Update the bindings in openclaw.json.

### 3. Create a Cron Job for an Agent

> Create a cron job that runs every day at 9:00 AM (timezone `<tz>`) using the `<agent-id>` agent. It should `<task description>` and announce results to Discord channel `<channel-id>`. Use agentTurn type with Haiku.

### 4. Design a Permission Graph

> I have these agents: `<list>`. Design a permission graph where `<main-agent>` can spawn all specialists, `<coordinator>` can spawn `<subset>`, and public-facing agents cannot spawn anyone. Show me the openclaw.json config.

### 5. Complete Multi-Agent Setup from Scratch

> Set up a complete multi-agent OpenClaw installation with: a main orchestrator (Sonnet), a researcher (Haiku), a coder (Sonnet), and a reviewer (Haiku). Include workspace directories, bootstrap files, openclaw.json config, Discord bindings, permission graph, and cron jobs for daily summaries.

---

## Best Practices

1. **Use Haiku for auxiliary agents** — specialists, cron agents, and sub-agents rarely need Sonnet-level reasoning. This cuts costs significantly.

2. **Write clear, focused SOUL.md files** — each agent should have a single, well-defined mission. Vague instructions lead to confused behavior and wasted tokens.

3. **Enable passphrase guard everywhere** — any agent with exec, filesystem, or config access should require passphrase validation for sensitive operations.

4. **Keep loop detection enabled** — never disable it. The cost of a single agent loop can exceed your entire daily budget.

5. **Store tokens in .env files** — never hardcode API keys or bot tokens in openclaw.json. Use `${VAR}` references.

6. **Validate JSON before restart** — OpenClaw rejects unknown keys and crashes on startup. Always run `openclaw doctor` before restarting.

7. **Design permissions defensively** — assume any public channel user will try to escalate. Public-facing agents should have minimal spawn permissions.

8. **Use agentTurn for autonomous tasks** — systemEvent injects into active sessions, which can disrupt ongoing conversations. Use agentTurn for independent work.

9. **Set file ownership correctly** — if your CLI runs as root but the service runs as a dedicated user, always `chown` files after editing.

10. **Test new agents in isolation** — before integrating a new agent into your permission graph, test it with `/new` sessions to verify its behavior matches your SOUL.md intent.
