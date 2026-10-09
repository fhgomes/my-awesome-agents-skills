---
vendor: xAI
family: Grok
last_verified: 2026-10-09
---

# xAI — Grok

**Best used when:** picking a Grok model or a reasoning effort on the xAI API.
**See also:** [../choosing-a-model.md](../choosing-a-model.md) (cross-vendor rules) · [../keeping-it-current.md](../keeping-it-current.md) (how to refresh this file)

Every fact below comes from xAI's own docs and news posts on the `last_verified` date. Prices are USD per 1M tokens for prompts under 200K tokens. xAI's own docs disagree with each other in places; those spots are flagged.

---

## 1. Lineup

| Model | API ID | Role (xAI's words) | Input / cached / output | Context | Reasoning | Default effort |
|---|---|---|---|---|---|---|
| Grok 4.7 | `grok-4.7` | Frontier model for coding, agentic tasks, knowledge work. "Use Grok 4.7 for everything else, including code" | $2.00 / $0.50 / $6.00 | 500K | **Always on** | `high` |
| Grok 4.6 | `grok-4.6` | Same positioning, previous release. Long-running agents, visual work | $2.00 / $0.50 / $6.00 | 500K | **Always on** | `high` |
| Grok 4.5 | `grok-4.5` | Coding model for agentic software and engineering work | $2.00 / $0.30 / $6.00 | 500K | **Always on** | `high` |
| Grok 4.3 | `grok-4.3` | Fast, reliable, strong tool calling. Replacement for the retired fast models | $1.25 / $0.20 / $2.50 | 1M | Configurable, **can be off** (`none`) | `low` |
| Grok 4.20 reasoning | `grok-4.20-0309-reasoning` | Speed, agentic tool calling, low hallucination rate | $1.25 / $0.20 / $2.50 | 1M | Yes | not documented |
| Grok 4.20 non-reasoning | `grok-4.20-0309-non-reasoning` | Same, without reasoning | $1.25 / $0.20 / $2.50 | 1M | **No** | — |
| Grok 4.20 multi-agent | `grok-4.20-multi-agent-0309` | Parallel agents for deep research | $1.25 / $0.20 / $2.50 | 1M | Yes; effort sets agent count | — |
| Grok Build 0.1 | `grok-build-0.1` (alias `grok-code-fast-1`) | Coding model for agentic workflows, early access | $1.00 / $0.20 / $2.00 | 256K | Yes | not documented |

- **Long context:** once a prompt reaches 200K tokens, **every** token in that request is billed at 2x.
- **Batch API:** 20% off, on Grok 4.3, 4.20 and multi-agent only. The US regional endpoint costs 10% more.
- **Release dates:** Grok 4.7 2026-09-21, 4.6 2026-08-12, 4.5 2026-07-16, 4.20 March 2026, Build 0.1 May 2026 (early access).
- **Grok 4.7 Fast** (same model, 2x price) exists only inside partner coding tools, not on the public API.
- **Retired 2026-05-15:** `grok-4-1-fast-*`, `grok-4-fast-*`, `grok-4-0709` and `grok-3` still resolve but are served by Grok 4.3 (low or none effort) and billed at its rates.

## 2. When to use, when not to

| Model | Use for | Not for |
|---|---|---|
| Grok 4.7 | The default for complex coding, agents and knowledge work | Workloads that need reasoning off; high-volume simple calls (4.3 is cheaper and allows `none`) |
| Grok 4.3 | Fast, cheap tool calling and instruction following; non-reasoning workloads with effort `none`; 1M context; batch jobs | The hardest reasoning |
| Grok 4.20 multi-agent | Deep research: 4 agents for focused questions, 16 for broad topics | Simple lookups (it multiplies cost by the agent count) |
| Grok Build 0.1 | Coding agents at the lowest price | General knowledge work. Still early access |

xAI publishes no "choosing a model" page and no explicit "not for" guidance. The rows above combine the models page and the May retirement guide. On code, the two disagree: the models page says Grok 4.7, the retirement guide says Grok Build 0.1. Measure both on your tasks.

## 3. Reasoning and effort

- **Grok 4.7, 4.6, 4.5 always reason.** The reasoning guide says reasoning cannot be disabled.
- **Grok 4.3** is the model that can turn it off: effort `none`.
- Levels: `low`, `medium`, `high` (default), `xhigh` (Grok 4.6 and later). On Grok 4.5, `xhigh` is treated as `high` per the reasoning guide, though its model page lists `xhigh` (doc conflict).
- **Parameter name differs per API:** Responses API `reasoning: {"effort": ...}`, xAI SDK `reasoning_effort`.
- **Multi-agent:** `low`/`medium` = 4 agents, `high`/`xhigh` = 16; the xAI SDK takes `agent_count` directly.
- Reasoning tokens are billed as output.

## 4. Traps

- **Encrypted reasoning must round-trip.** Grok 4.7 always returns `reasoning.encrypted_content` on the Responses API; pass it back unchanged. Chat Completions has no field for it.
- **Rejected parameters on reasoning models:** `presencePenalty`, `frequencyPenalty`, `stop` return errors. `logprobs` is silently ignored on Grok 4.20 and newer.
- **Retired IDs still answer.** A request to `grok-4-fast-reasoning` succeeds, but you are now on Grok 4.3 at Grok 4.3 prices. Update the ID so the config says what actually runs.
- **The 200K pricing cliff** bills the whole request at the higher rate, not just the tokens above 200K.
- **Default effort differs:** `high` on 4.5 to 4.7, `low` on 4.3.

## 5. Official sources

| What | URL |
|---|---|
| Models and pricing | https://docs.x.ai/developers/models |
| Reasoning | https://docs.x.ai/developers/model-capabilities/text/reasoning |
| Multi-agent | https://docs.x.ai/developers/model-capabilities/text/multi-agent |
| Release notes | https://docs.x.ai/developers/release-notes |
| Grok 4.7 developer guide | https://docs.x.ai/developers/grok-4-7 |
| May 2026 retirement guide | https://docs.x.ai/developers/migration/may-15-retirement |
| News posts | https://x.ai/news/grok-4-7 (pattern: `x.ai/news/<model-slug>`) |
