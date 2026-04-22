# Adding Ollama to OpenClaw — Local and Cloud

A step-by-step, paste-ready guide to plug **Ollama** into an existing OpenClaw instance *temporarily*, without removing or breaking your current primary provider (Anthropic, OpenAI, a proxy, etc.).

Covers:

- **Route A** — local Ollama (on your machine, via Docker or native install)
- **Route B** — Ollama Cloud / Turbo (`ollama.com`, paid hosted)
- **Quick test** with a throwaway agent — zero blast radius
- **Rollback** in one shot

Pair with [`providers-and-models.md`](providers-and-models.md) for the conceptual reference.

---

## Before you start

Replace these placeholders throughout the guide:

| Placeholder | Example | What it is |
|-------------|---------|------------|
| `<USER>` | `openclaw` | Linux user that runs OpenClaw |
| `<HOME>` | `/home/openclaw` | That user's home directory |
| `<PORT>` | `55444` | Your gateway port (`gateway.port` in `openclaw.json`) |
| `<UNIT>` | `openclaw.service` | Your systemd unit name |
| `<CONFIG>` | `<HOME>/.openclaw/openclaw.json` | Your main config file |
| `<BIN>` | `<HOME>/.openclaw/local/bin/openclaw` | Your local OpenClaw binary |

If you run OpenClaw as a single user without systemd, drop `sudo -u <USER>` and use whatever start/stop command you normally use instead of `systemctl`.

### Prerequisites check

```bash
# 1. OpenClaw is running
systemctl is-active <UNIT>
curl -s http://127.0.0.1:<PORT>/ready | python3 -m json.tool | head -5

# 2. You can read your config
ls -la <CONFIG>

# 3. Python 3 is available for JSON patches
python3 --version
```

### Back up your config NOW

```bash
sudo -u <USER> cp <CONFIG> <CONFIG>.bak-pre-ollama-$(date +%Y%m%d-%H%M%S)
```

Rollback depends on this file. Do not skip.

---

## Route A — Local Ollama

Runs on the same machine as OpenClaw. Free, offline-capable, but limited by your hardware.

### A.1 Install Ollama

**Option A.1.a — Docker (isolated, recommended):**

```bash
docker run -d \
  --name openclaw-ollama \
  -p 127.0.0.1:11434:11434 \
  -v openclaw-ollama-models:/root/.ollama \
  --restart unless-stopped \
  ollama/ollama
```

Bind to `127.0.0.1` only — you do not want Ollama exposed to the public internet.

**Option A.1.b — Native install:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable --now ollama
```

### A.2 Pull at least one model

Choose based on your hardware. For reference, `3b` runs on most laptops; `7b`/`8b` wants ~8 GB RAM; `14b`+ wants a GPU.

```bash
# If Docker:
docker exec openclaw-ollama ollama pull llama3.2:3b
docker exec openclaw-ollama ollama pull qwen2.5-coder:7b

# If native:
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:7b
```

Verify:

```bash
# Docker
docker exec openclaw-ollama ollama list

# Native / over HTTP
curl -s http://127.0.0.1:11434/api/tags | python3 -m json.tool
```

Write down the **exact** model ids (`llama3.2:3b`, `qwen2.5-coder:7b`) — you must use them verbatim in the config, tags and all.

### A.3 Smoke-test Ollama *before* wiring it into OpenClaw

```bash
curl -s http://127.0.0.1:11434/v1/chat/completions \
  -H "Authorization: Bearer ollama" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Reply with one word: pong"}]
  }' | python3 -m json.tool
```

If you do not get a `"content": "pong"` back, **stop here** and fix Ollama first. There is no point wiring a broken backend.

### A.4 Add the provider to `openclaw.json`

Edit `<CONFIG>` and add a new key under `models.providers`. The schema is a **dict** keyed by provider id.

```jsonc
{
  "models": {
    "providers": {
      // ...your existing providers stay untouched...

      "ollama-local": {
        "baseUrl": "http://127.0.0.1:11434/v1",
        "apiKey": "ollama",
        "api": "openai-completions",
        "models": [
          {
            "id": "llama3.2:3b",
            "name": "Llama 3.2 3B (local)",
            "reasoning": false,
            "input": ["text"],
            "contextWindow": 131072,
            "maxTokens": 4096
          },
          {
            "id": "qwen2.5-coder:7b",
            "name": "Qwen2.5 Coder 7B (local)",
            "reasoning": false,
            "input": ["text"],
            "contextWindow": 32768,
            "maxTokens": 4096
          }
        ]
      }
    }
  }
}
```

Notes:

- `apiKey: "ollama"` is a dummy value. Ollama's OpenAI-compatible endpoint ignores it, but the `openai-completions` client sends an `Authorization: Bearer` header and some clients refuse to omit it. `"ollama"` is the convention used in Ollama's own docs.
- Match `id` **exactly** to what `ollama list` prints, including the tag (`:3b`, `:7b`, `:latest`).
- `contextWindow` / `maxTokens` above reflect defaults at time of writing; adjust to whatever your chosen model actually supports.

### A.5 Add a throwaway "lab" agent — keep blast radius at zero

Rather than repointing a real production agent, add a disposable one under `agents.list[]`:

```jsonc
{
  "id": "ollama-lab",
  "name": "Ollama Lab",
  "description": "Throwaway agent for testing Ollama locally. No tools, no bindings.",
  "model": "ollama-local/llama3.2:3b",
  "system": "You are a minimal test agent. Respond concisely in plain text. When asked, confirm which model and provider served the request.",
  "tools": []
}
```

Why an empty `tools` array? Because this agent should not be able to send messages, run shell commands, browse the web, or write files. We are testing LLM round-trip only.

### A.6 Validate → restart → verify

```bash
# 1. Ownership (required if you are editing as root and OpenClaw runs as <USER>)
chown <USER>:<USER> <CONFIG>

# 2. Schema sanity — this catches unknown keys before they crash the service
sudo -u <USER> <BIN> doctor 2>&1 | tee /tmp/ollama-doctor.log

# 3. Restart only after doctor passes
systemctl restart <UNIT>

# 4. Wait for boot (non-root users take ~60-75 s)
until curl -fs http://127.0.0.1:<PORT>/ready >/dev/null 2>&1; do sleep 3; done
echo "up"

# 5. Confirm provider is registered
cat <CONFIG> | python3 -c "import sys,json; print(list(json.load(sys.stdin)['models']['providers'].keys()))"
```

### A.7 Drive the lab agent and confirm it actually used Ollama

Depending on your OpenClaw version, either:

```bash
# Preferred: CLI entrypoint if your build exposes it
sudo -u <USER> <BIN> agent run ollama-lab \
  "Say exactly: pong from <provider>/<model>. What model are you?"
```

Or use the HTTP gateway:

```bash
curl -s -X POST http://127.0.0.1:<PORT>/gateway/agent-run \
  -H "Authorization: Bearer $OPENCLAW_GATEWAY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agentId":"ollama-lab","input":"ping"}'
```

Then prove the call went to Ollama and *not* to your old provider:

```bash
# You should see traffic to 11434
journalctl -u <UNIT> --since "2 min ago" \
  | grep -iE "127\.0\.0\.1:11434|ollama-local|ollama-lab" | head -20

# And you should NOT see your existing provider handling that turn
journalctl -u <UNIT> --since "2 min ago" \
  | grep -iE "model=|provider=" | head -20
```

If that all checks out, Route A is working.

---

## Route B — Ollama Cloud / Turbo

Uses hosted models at `ollama.com`. Larger models than you could run locally, but paid and requires a network round-trip.

### B.1 Get an API key

Create an account and generate an API key at <https://ollama.com>. Keep it out of version control.

### B.2 Store the key

Prefer environment variables over pasting the key into the JSON.

```bash
# <HOME>/.openclaw/.env — loaded by your systemd unit via EnvironmentFile
echo 'OLLAMA_CLOUD_API_KEY=sk-ollama-...' | sudo -u <USER> tee -a <HOME>/.openclaw/.env >/dev/null
sudo chmod 600 <HOME>/.openclaw/.env
sudo chown <USER>:<USER> <HOME>/.openclaw/.env
```

**Heads-up:** OpenClaw's support for `${VAR}` expansion inside `openclaw.json` has varied across versions. Before relying on it, do a quick test: put a dummy value like `${OLLAMA_CLOUD_API_KEY}` in the config, restart, and check whether the provider call succeeds. If expansion does not happen, paste the key literally into the config (make sure the config file is `chmod 600`).

### B.3 Smoke-test the cloud endpoint first

```bash
export OLLAMA_CLOUD_API_KEY=sk-ollama-...
curl -s https://ollama.com/v1/chat/completions \
  -H "Authorization: Bearer $OLLAMA_CLOUD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-oss:120b","messages":[{"role":"user","content":"ping"}]}' \
  | python3 -m json.tool
```

If you see a `401`, the key is wrong or not active yet. If you see a `404`, the model id may have changed — check the current catalog at <https://docs.ollama.com/cloud>.

### B.4 Add the provider to `openclaw.json`

```jsonc
{
  "models": {
    "providers": {
      "ollama-cloud": {
        "baseUrl": "https://ollama.com/v1",
        "apiKey": "${OLLAMA_CLOUD_API_KEY}",
        "api": "openai-completions",
        "models": [
          {
            "id": "gpt-oss:120b",
            "name": "GPT-OSS 120B (Ollama Cloud)",
            "reasoning": true,
            "input": ["text"],
            "contextWindow": 131072,
            "maxTokens": 8192
          },
          {
            "id": "qwen3-coder:480b",
            "name": "Qwen3 Coder 480B (Ollama Cloud)",
            "reasoning": true,
            "input": ["text"],
            "contextWindow": 262144,
            "maxTokens": 8192
          }
        ]
      }
    }
  }
}
```

Model ids and limits above are examples. Validate against the current catalog before relying on them.

### B.5 Cloud lab agent

```jsonc
{
  "id": "ollama-lab-cloud",
  "name": "Ollama Lab (Cloud)",
  "description": "Throwaway agent for testing Ollama Cloud. No tools, no bindings.",
  "model": "ollama-cloud/gpt-oss:120b",
  "system": "You are a minimal test agent. Respond concisely in plain text.",
  "tools": []
}
```

### B.6 Same restart/verify dance as Route A

```bash
chown <USER>:<USER> <CONFIG>
sudo -u <USER> <BIN> doctor
systemctl restart <UNIT>
until curl -fs http://127.0.0.1:<PORT>/ready >/dev/null 2>&1; do sleep 3; done
sudo -u <USER> <BIN> agent run ollama-lab-cloud "Say exactly: pong. What model are you?"
```

Confirm in logs that the outbound call went to `ollama.com`, not to your existing provider.

---

## Rollback (any route)

One-shot revert: restore the backup, re-apply ownership, validate, restart.

```bash
# 1. Restore the config you backed up at the top of this guide
BACKUP=$(ls -t <CONFIG>.bak-pre-ollama-* | head -1)
sudo -u <USER> cp "$BACKUP" <CONFIG>
chown <USER>:<USER> <CONFIG>

# 2. Re-validate
sudo -u <USER> <BIN> doctor --fix

# 3. Restart and wait
systemctl restart <UNIT>
until curl -fs http://127.0.0.1:<PORT>/ready >/dev/null 2>&1; do sleep 3; done
curl -s http://127.0.0.1:<PORT>/ready | python3 -m json.tool | head -40

# 4. (Route A only) stop the local Ollama container if you no longer want it running
docker stop openclaw-ollama && docker rm openclaw-ollama
# Drop the models volume only if you are sure — it can be several GB
# docker volume rm openclaw-ollama-models
```

Post-rollback checklist:

- [ ] `systemctl is-active <UNIT>` → `active`
- [ ] `curl :<PORT>/ready` shows all channels `ready: true`
- [ ] `journalctl -u <UNIT> -n 100` is free of `UnknownKey` or `provider not found`
- [ ] Your previous provider still answers a normal request

---

## Troubleshooting cheat sheet

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `openclaw doctor` rejects the config with "unknown key" | Typo in the `providers` dict or an extra comma | Re-read the JSON around the edit; OpenClaw **crashes on unknown keys** |
| Agent replies with an empty string | Model id does not match what Ollama serves | Compare `id` in config to the exact output of `ollama list` / `/api/tags` |
| `401 Unauthorized` from local Ollama | Missing `Authorization: Bearer` header | Keep `apiKey: "ollama"` in the provider block |
| `401` from Ollama Cloud | Key not pasted, not expanded, or not active | Smoke-test the key directly with `curl` first |
| Response times look strange (seconds for trivial prompts) | Local model is swapping or Ollama is cold-loading it | Pull a smaller model, or pre-warm with one `curl` before the real test |
| `/ready` returns `Unauthorized` right after restart | Non-root user boot takes ~60 s | Wait, then retry — it is not an auth problem |
| Turn seems to still hit the old provider | Lab agent has a `model` string that does not match any provider id in the registry | `cat <CONFIG> \| jq '.models.providers \| keys'` and check the prefix matches exactly |

---

## References

- Ollama OpenAI compatibility: <https://github.com/ollama/ollama/blob/main/docs/openai.md>
- Ollama Cloud docs: <https://docs.ollama.com/cloud>
- Related guide in this repo: [`providers-and-models.md`](providers-and-models.md)
- Companion skill: [`skills/openclaw-specialist/SKILL.md`](../../skills/openclaw-specialist/SKILL.md)

---

## Copy-paste prompt for your AI agent

If you prefer to delegate the whole thing to your own coding/ops agent, paste the following as your instruction:

> I want to temporarily add Ollama (local and/or cloud) as a provider to my OpenClaw instance without breaking my current primary provider. Follow the guide at `openclaw/guides/ollama-setup.md` from `my-awesome-agents-skills`. Do Route A first (local via Docker), then Route B (cloud) if Route A works. Use a throwaway `ollama-lab` agent with `tools: []` instead of repointing any real agent. Always back up `openclaw.json` before editing, run `openclaw doctor` before every restart, `chown` the config back to my OpenClaw user after edits, wait ~60 s after restart, and verify `/ready` before testing. Confirm with me before applying each JSON patch and before restarting the service. Produce a Diagnosis / Fix / Verification / Rollback report at each step.

Adapt placeholders (`<USER>`, `<PORT>`, paths) to your actual values before you send it.
