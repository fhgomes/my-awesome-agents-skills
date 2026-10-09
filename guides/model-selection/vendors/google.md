---
vendor: Google
family: Gemini
last_verified: 2026-10-09
---

# Google — Gemini

**Best used when:** picking a Gemini model or a thinking level on the Gemini API or on Google Cloud.
**See also:** [../choosing-a-model.md](../choosing-a-model.md) (cross-vendor rules) · [../keeping-it-current.md](../keeping-it-current.md) (how to refresh this file)

Every fact below comes from Google's own docs, changelog and launch posts on the `last_verified` date. Prices are USD per 1M tokens on the Gemini API, Standard tier; output price includes thinking tokens. Google Cloud (Vertex AI, now branded Gemini Enterprise Agent Platform) sets its own lifecycle dates and was not price-checked.

---

## 1. Lineup

| Model | API ID | Stage | Role (Google's words) | Input / output | Context / max output | Thinking | Default level |
|---|---|---|---|---|---|---|---|
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | Preview | Deep reasoning, high-complexity tasks, software engineering, precise tool use | $2.00 / $12.00 (≤200K); $4.00 / $18.00 above | 1M / 65K | **Always on** | `high` |
| Gemini 3.8 Flash | `gemini-3.8-flash` | GA | "Most intelligent Flash": long-horizon software engineering, autonomous agents, complex enterprise workflows | $0.75 / $3.75 (intro, through 2026-12-31; then $1.50 / $7.50) | 1M / 65K | **Always on** | `medium` |
| Gemini 3.7 Flash | `gemini-3.7-flash` | GA | Complex coding and agents when compute efficiency is the priority | $0.75 / $3.75 (same intro terms) | 1M / 65K | **Always on** | `medium` |
| Gemini 3.5 Flash-Lite | `gemini-3.5-flash-lite` | GA | High-throughput, low-cost subagents, document parsing, simple extraction | $0.30 / $2.50 | 1M / 65K | Always on, near zero at `minimal` | `minimal` |
| Gemini 3.1 Flash-Lite | `gemini-3.1-flash-lite` | GA | Simple tasks at scale: translation, classification, JSON extraction, low-cost routing | $0.25 / $1.50 | 1M / 65K | Always on, near zero at `minimal` | `minimal` |

- **Release dates:** 3.8 Flash 2026-09-02, 3.7 Flash 2026-08-13, 3.5 Flash-Lite 2026-07-21, 3.1 Flash-Lite 2026-05-07, 3.1 Pro Preview 2026-02-19.
- **There is no Gemini 3.8 Pro.** The current Pro is still `gemini-3.1-pro-preview` (a `-customtools` variant exists for when the model prefers bash over your own tools).
- **Older Flash models still served:** 3.6 Flash (Vertex retirement 2026-11-19), 3.5 Flash ($1.50 / $9.00, labeled legacy, now pricier than 3.8 Flash at intro rates).
- **Gemini 2.5** (Pro, Flash, Flash-Lite): new projects should not use them. Limited to previous users on the Gemini API since 2026-09-18; **retired on Vertex 2026-10-20**.
- **Batch and Flex** cost about 50% of Standard; **Priority** about 1.8x. Every model above except 3.1 Pro has a free tier.

## 2. When to use, when not to

| Model | Use for | Not for |
|---|---|---|
| 3.1 Pro Preview | The hardest reasoning and software engineering on Gemini | Production paths that need GA stability, high rate limits, or a free tier. Quality may fluctuate on tasks that do not use tools |
| 3.8 Flash | The default for coding, agents and enterprise workflows | Efficiency-first workloads: it uses more tokens than 3.7 Flash |
| 3.7 Flash | Coding and agents when token efficiency matters more than the last bit of quality | — (labeled previous generation, still GA) |
| 3.5 Flash-Lite | Subagents, parsing, extraction where latency and cost dominate | Multi-step reasoning |
| 3.1 Flash-Lite | Translation, transcription, classification, routing at scale | Computer use (not supported) |

Google publishes no single "choose a model" page. The rows above combine the per-model pages, the Gemini 3.8 Flash guides and the 2026-09-18 release note (which points new projects to 3.5 Flash-Lite or 3.8 Flash). Naming rule from the models page: stable for production, preview allowed with tighter limits, `-latest` aliases are hot-swapped, experimental is not for production.

## 3. Thinking and effort

- **Gemini 3.x always thinks.** Thinking cannot be turned off; `minimal` means close to no thinking, not none.
- **Control:** `thinking_level` (`thinkingLevel`): `minimal`, `low`, `medium`, `high`. Not every model accepts every level: 3.8 and 3.7 Flash reject `minimal` with a 400; 3.1 Pro has no `minimal`.
- **Google's guidance:** `minimal`/`low` for fact retrieval, classification and latency-critical work; `medium` for most tasks including complex code and agents; `high` for deep multi-step reasoning, advanced coding, math and planning.
- To cut cost, lower the level rather than `max_output_tokens` (which includes thinking tokens).
- **`thinking_budget` is the old control.** On Gemini 3.x it is deprecated: replace it with `thinking_level`. Sending both returns a 400. Gemini 2.5 still uses budgets (2.5 Pro cannot disable thinking; 2.5 Flash and Flash-Lite can with `0`).

## 4. Traps

- **Defaults differ per model:** `medium` on 3.8/3.7 Flash, `minimal` on the Flash-Lite models, `high` on 3.1 Pro. Set the level explicitly.
- **Sampling parameters are deprecated on 3.8 Flash:** remove `temperature`, `top_p`, `top_k`. Do not end a chat history with a prefilled model turn.
- **Intro pricing ends 2026-12-31.** 3.8, 3.7 and 3.6 Flash double in price on 2027-01-01. Budget with the post-intro rate.
- **The Gemini API and Vertex disagree on lifecycles.** Check the platform you actually call.
- **Stale copies of the thinking page** (with `?authuser=` or `?hl=` in the URL) still describe `thinkingBudget` as current. Use the canonical URL.

## 5. Official sources

| What | URL |
|---|---|
| Models list | https://ai.google.dev/gemini-api/docs/models |
| Per-model pages | `https://ai.google.dev/gemini-api/docs/models/<model-id>` |
| Latest model guide | https://ai.google.dev/gemini-api/docs/latest-model |
| Thinking | https://ai.google.dev/gemini-api/docs/thinking |
| Pricing | https://ai.google.dev/gemini-api/docs/pricing |
| Changelog | https://ai.google.dev/gemini-api/docs/changelog |
| Deprecations | https://ai.google.dev/gemini-api/docs/deprecations |
| Thinking levels per model (Firebase AI Logic) | https://firebase.google.com/docs/ai-logic/thinking |
| Google Cloud model lifecycle | https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions |
| Launch posts | https://blog.google/ (Gemini models section) |
