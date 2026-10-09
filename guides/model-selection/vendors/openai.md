---
vendor: OpenAI
family: GPT-6
last_verified: 2026-10-09
---

# OpenAI — GPT-6 family and Codex

**Best used when:** picking a GPT-6 model or a reasoning effort for an API integration, Codex, or an agent.
**See also:** [../choosing-a-model.md](../choosing-a-model.md) (cross-vendor rules) · [../keeping-it-current.md](../keeping-it-current.md) (how to refresh this file)

Every fact below comes from OpenAI's own pages on the `last_verified` date. Prices are USD per 1M tokens, standard processing.

---

## 1. Lineup

| Model | API ID | Role | Input / cached / output | Context / max output | Reasoning floor | Knowledge cutoff |
|---|---|---|---|---|---|---|
| GPT-6 Astra | `gpt-6-astra` | Most intelligent, hardest work | $10 / $1 / $50 | 1.05M / 128K | `low` (no `none`) | 2026-04-30 |
| GPT-6.1 Sol | `gpt-6.1-sol` | Near-Astra at a fifth of the price. Recommended for Codex | $2 / $0.10 / $10 | 1.05M / 128K | `low` (no `none`) | 2026-04-30 |
| GPT-6 Luna | `gpt-6-luna` | Fast and efficient, high volume | $0.10 / $0.01 / $0.50 | 1.05M / 128K | `none` allowed | 2026-05-18 |

- **Long context on Astra:** requests over 272K input tokens cost 2x on input and 1.5x on output.
- The earlier **GPT-6 Sol** (not 6.1) also accepts `none`. GPT-6.1 Sol was introduced 2026-09-29.

## 2. When to use, when not to

| Model | Use for | Not for |
|---|---|---|
| Astra | The hardest reasoning, when maximum intelligence matters more than cost and latency. Multi-step workflows across code, browsers and professional software | Everyday coding where 6.1 Sol gets close for far less. Workloads that need reasoning fully off. EU data residency with Fast mode (not available there) |
| GPT-6.1 Sol | Complex coding, research, computer use, multi-agent work in the Responses API (beta). The default pick in Codex | Simple extraction or classification at volume |
| Luna | Focused, repeated work with a clear goal: extracting invoice fields, classifying requests, structured summaries, focused coding | Open-ended or ambiguous tasks |

OpenAI notes that Astra often finishes a task with far fewer output tokens than earlier models, so its cost per task can be lower than its per-token price suggests. Measure cost per successful task, not price per token.

## 3. Reasoning effort

API parameter: `reasoning.effort`. Levels on Astra and 6.1 Sol: `low`, `medium` (default), `high`, `xhigh`, `max`. Luna adds `none`.

| Level | Use for |
|---|---|
| `low` | Routine work: extracting facts, small edits |
| `medium` | Work that needs judgment: planning a feature, comparing options |
| `high` | Hard debugging, deeper analysis, careful review |
| `xhigh` / `max` | Only when `high` falls short, and keep it only if the gain pays for the time and cost |

- Reasoning effort can change mid-conversation in the API without breaking the cache.
- **Speed is a separate axis.** Fast mode (API) gives lower, steadier latency at a higher per-token price. Ultrafast (Codex and API, Astra only) speeds up token generation independently of effort.

### Codex

Codex labels its levels **Light, Medium, High, Extra High, Max, Ultra**. Ultra splits the task across subagents in parallel. Start with the model's default level, go down for simple tasks, go up for deep analysis. Default levels in the ChatGPT desktop and web clients depend on the plan. Pin a model with the `model` key in `config.toml`.

## 4. Traps

- **"Does it think by default?"** On Astra and 6.1 Sol, always. The floor is `low`. Plan latency budgets with that in mind.
- **Do not reuse effort settings from earlier GPT generations.** Re-run the sweep.
- **`openai.com` blocks plain HTTP fetches (403).** Read those pages in a browser. `developers.openai.com/codex/models` redirects to `learn.chatgpt.com/docs/models`.

## 5. Official sources

| What | URL |
|---|---|
| GPT-6 family model guide (2026-10-02) | https://openai.com/index/practical-guide-building-gpt-6/ |
| Model selection | https://developers.openai.com/api/docs/guides/model-selection |
| Using GPT-6 (per-model guidance) | https://developers.openai.com/api/docs/guides/latest-model |
| Models list (IDs, prices, efforts) | https://developers.openai.com/api/docs/models |
| Astra model page | https://developers.openai.com/api/docs/models/gpt-6-astra |
| Codex models | https://learn.chatgpt.com/docs/models |
| Fast mode | https://developers.openai.com/api/docs/guides/fast-mode |
