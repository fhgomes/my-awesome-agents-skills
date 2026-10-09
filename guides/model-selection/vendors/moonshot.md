---
vendor: Moonshot AI
family: Kimi
last_verified: 2026-10-09
---

# Moonshot AI — Kimi

**Best used when:** picking a Kimi model on the Kimi API, or deciding whether to self-host Kimi open weights.
**See also:** [../choosing-a-model.md](../choosing-a-model.md) (cross-vendor rules) · [../keeping-it-current.md](../keeping-it-current.md) (how to refresh this file)

Every fact below comes from Moonshot's own docs, blog and official Hugging Face model cards on the `last_verified` date. Prices are USD per 1M tokens on the international platform.

---

## 1. Lineup (Kimi API)

| Model | API ID | Role | Input cache hit / miss / output | Context | Thinking | Effort |
|---|---|---|---|---|---|---|
| Kimi K3 | `kimi-k3` | Flagship. Long-horizon coding, knowledge work, deep reasoning, vision | $0.30 / $3.00 / $15.00 | 1M (1,048,576) | **Always on** | `reasoning_effort`: `low`, `high`, `max` (default `max`) |
| Kimi K2.7 Code | `kimi-k2.7-code` | Purpose-built for coding and agentic tool use | $0.19 / $0.95 / $4.00 | 256K | **Always on** | Not supported |
| Kimi K2.7 Code HighSpeed | `kimi-k2.7-code-highspeed` | Same model, faster serving (about 180 tok/s), limited capacity | $0.38 / $1.90 / $8.00 | 256K | **Always on** | Not supported |
| Kimi K2.6 | `kimi-k2.6` | General purpose: dialogue, agents, vision with tools | $0.16 / $0.95 / $4.00 | 256K | On by default, **can be disabled** | Not supported |

- **K3 cache writes** cost $3.00 (5-minute TTL, default) or $6.00 (1-hour TTL). A hit refreshes the TTL. Flat pricing, no context-length tiers.
- **Release dates:** K3 2026-07-16, K2.7 Code June 2026, K2.6 2026-04-20.
- **Retired:** `kimi-k2.5` and all `moonshot-v1-*` (shut off 2026-08-31, now 404), the K2 preview, turbo and thinking IDs (2026-05-25), `kimi-latest` (2026-01-28). All point to `kimi-k3`.

### Open weights

| Hugging Face repo (`moonshotai/`) | Size (total / active) | License |
|---|---|---|
| `Kimi-K3` | 2.8T / 104B MoE, native MXFP4 weights | Kimi K3 License: commercial use allowed; separate agreement for a hosted-API business over $20M revenue in 12 months; visible "Kimi K3" credit above 100M MAU or $20M monthly revenue |
| `Kimi-K2.7-Code` | 1T / 32B MoE, native INT4 | Modified MIT |
| `Kimi-K2.6` | 1T / 32B MoE, native INT4 | Modified MIT |

Recommended engines: vLLM and SGLang for all three.

## 2. When to use, when not to

| Model | Use for | Not for |
|---|---|---|
| K3 | The hardest coding and reasoning, large codebases, coding with visual feedback (frontend, games, CAD), 1M-token context | Vague tasks without explicit limits (Moonshot warns it can be too proactive), switching models partway through a session, production web search for now |
| K2.7 Code | Coding agents and multi-step tool calls at a fraction of K3's price. About 30% fewer thinking tokens than K2.6 on coding | Writing, analysis, conversation (Moonshot points to K2.6 instead). Anything needing thinking off |
| K2.7 Code HighSpeed | Interactive coding where latency matters | Cost-sensitive batch work (2x the price of K2.7 Code) |
| K2.6 | General work, chat, and **the only option** when you need thinking off or the built-in `$web_search` tool | Hardest coding (K2.7 Code or K3) |

Moonshot publishes no direct K3 versus K2.7 Code comparison. Measure on your own tasks.

## 3. Thinking and effort

- **K3:** always thinks. Do **not** send a `thinking` parameter (remove it when migrating from K2.x). Control depth with top-level `reasoning_effort`: `low`, `high`, `max`; default `max`. Lower it if reasoning takes too long.
- **K2.7 Code:** always thinks. `thinking.type` accepts only `"enabled"`; `"disabled"` returns an error. No effort parameter.
- **K2.6:** `thinking: {"type": "enabled" | "disabled", "keep": null | "all"}`, default enabled with past reasoning dropped. With the OpenAI SDK, pass it via `extra_body`. Self-hosted: `chat_template_kwargs: {"thinking": false}`.
- No thinking-budget parameter exists on any model.
- Reasoning tokens are billed and count toward `max_tokens`. Use at least 16K `max_tokens` for tool-calling workflows, and stream.

## 4. Traps

- **K3 defaults to `max` effort**, the opposite of most vendors. Set `reasoning_effort` explicitly if latency or cost matters.
- **Pass reasoning back.** K3 and K2.7 Code require the full previous assistant message (`reasoning_content` and `tool_calls`) on every turn. Harnesses that strip reasoning get unstable output.
- **Fixed sampling parameters.** Non-default `temperature` (1.0; 0.6 for K2.6 without thinking), `top_p` (0.95), `n` and penalties return an error. Leave them out.
- **`tool_choice: "required"`** works only on K3.
- **Images and video** must be base64 or uploaded file IDs, not public URLs.
- **Kimi Code is a different API.** The coding subscription uses `kimi-for-coding` and is not interchangeable with the platform API. A K2.8 Preview shipped there on 2026-09-11 and is not on the platform API (UNVERIFIED outside Kimi Code).
- **Third-party docs still list retired K2 IDs.** Trust the platform model list only.

## 5. Official sources

| What | URL |
|---|---|
| Model list | https://platform.kimi.ai/docs/models |
| Thinking | https://platform.kimi.ai/docs/guide/use-thinking-models |
| Reasoning effort | https://platform.kimi.ai/docs/guide/use-reasoning-effort |
| Parameter reference | https://platform.kimi.ai/docs/api/models-overview |
| Pricing (USD) | https://platform.kimi.ai/docs/pricing/chat |
| Platform changelog | https://platform.kimi.ai/docs/platform-changelog |
| Docs index (machine-readable) | https://platform.kimi.ai/docs/llms.txt |
| Blog | https://www.kimi.ai/blog/ |
| Open weights | https://huggingface.co/moonshotai |
| Kimi Code changelog | https://www.kimi.com/code/docs/en/kimi-code/whats-new.html |
