---
vendor: Anthropic
family: Claude
last_verified: 2026-10-09
---

# Anthropic — Claude

**Best used when:** picking a Claude model or an effort level for an API integration, Claude Code, or an agent.
**See also:** [../choosing-a-model.md](../choosing-a-model.md) (cross-vendor rules) · [../keeping-it-current.md](../keeping-it-current.md) (how to refresh this file)

Every fact below comes from Anthropic's own docs on the `last_verified` date. Prices are USD per 1M tokens, base rate, synchronous API.

---

## 1. Lineup

| Model | API ID | Role | Input / output | Context / max output | Thinking | Default effort |
|---|---|---|---|---|---|---|
| Claude Fable 5.1 | `claude-fable-5-1` | Highest capability open to all customers | $10 / $50 | 1M / 128K | Adaptive, **always on** | `high` |
| Claude Opus 5.5 | `claude-opus-5-5` | The recommended starting point for most work | $4 / $20 | 1M / 128K | Adaptive, **always on** | `medium` |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | Speed plus capability for everyday work | $2 / $10 | 1M / 128K | Adaptive (can drop up-front thinking) | `high` |
| Claude Haiku 5.5 | `claude-haiku-5-5` | Lowest latency and price (released 2026-10-07) | from $0.10 / $0.50 (see note) | 1M / 128K | Adaptive | `medium` |

- **Haiku 5.5 pricing is tiered by prompt length:** $0.10 / $0.50 up to 100K input tokens, $0.50 / $2.50 above that.
- **Batch API:** 50% off. **Cache reads:** 10% of base input (5% on Opus 5.5 and Sonnet 5.5, 2.5% on Fable 5.1).
- **Claude Mythos 5.1** has Fable 5.1's capabilities but is limited to organizations verified through Anthropic's verification programs.
- Still available as legacy: Fable 5, Opus 5, Opus 4.8, 4.7, 4.6, 4.5, Sonnet 5, Sonnet 4.6, Haiku 4.5.

## 2. When to use, when not to

| Need | Start with | Typical work | Not for |
|---|---|---|---|
| Highest available capability | Fable 5.1 | Agent sessions that run for hours, multistep deep research, analysis carried to a finished document or deck | A starting point. Move here only when Opus 5.5 at `xhigh`/`max` still fails your evals |
| Complex agentic coding and enterprise work | Opus 5.5 | Multihour coding agents, large refactors, systems engineering, vision-heavy work, computer use | High-volume simple tasks where Haiku clears the bar |
| Everyday coding, agents, enterprise work | Sonnet 5.5 | Code generation, data analysis, content, agentic tool use | Tasks that need max effort. Escalate to Opus instead of forcing Sonnet to `max` |
| Lowest latency and price | Haiku 5.5 | Classification, routing, extraction, real-time apps, subagents | Long-horizon reasoning |

Anthropic describes two starting strategies:

- **Efficiency-first:** start on Haiku 5.5, upgrade only for a measured capability gap. Good for prototypes, tight latency, high volume.
- **Capability-first:** start on Opus 5.5, then lower effort or downgrade as the workflow matures. Good for complex reasoning, science, advanced coding, high-autonomy agents.

## 3. Thinking and effort

- **Adaptive thinking:** the model decides when and how much to think. Effort steers it.
- **Opus 5.5 and Fable 5.1 cannot turn thinking off.** `thinking: {"type": "disabled"}` returns a 400 error. Effort is the only control.
- **Sonnet 5.5:** to skip up-front thinking, send `thinking: {"type": "between_tools"}`. Valid at `low`, `medium` and `high` only.
- The Models API reports per model whether `thinking.types.disabled` is supported. Check it instead of guessing.
- Manual extended thinking (`budget_tokens`) is the older mode. Later models reject it.

Effort (`output_config.effort`) applies to every output token: thinking, text and tool calls.

| Level | Use for |
|---|---|
| `low` | Simple tasks, speed and cost first, subagents |
| `medium` | Balanced agentic work. Default on Opus 5.5 and Haiku 5.5 |
| `high` | Complex reasoning, hard coding. Default on Fable 5.1 and Sonnet 5.5 |
| `xhigh` | Long-running agentic and coding tasks (over 30 minutes, millions of tokens) |
| `max` | Deepest reasoning, no spending limit. Often adds cost for small gains, and can overthink structured tasks |

Rules from the docs:

- **Tuning effort is often a better lever than switching models.**
- At `high` and above, set a large `max_tokens`: it is a hard cap on thinking plus response. Around 64K is a reasonable start for `xhigh`/`max`.
- Effort controls thinking volume, not visible answer length. Prompt for length.
- Changing top-level effort between requests breaks the prompt cache. Fable 5.1, Opus 5.5, Opus 5 and Sonnet 5.5 support a per-message effort change (beta header `mid-conversation-output-config-2026-07-01`) that keeps the cache.
- **Speed is a separate axis:** fast mode (research preview, premium price) on Opus 5.5, Opus 5 and Opus 4.8.

## 4. Traps

- **Defaults moved.** Opus 5 and earlier defaulted to `high`. Opus 5.5 defaults to `medium`. Swapping the model ID without setting effort runs one notch lower.
- **Do not carry effort settings across generations.** Sonnet 5.5's levels were recalibrated against Sonnet 5. Run a fresh sweep.
- **New tokenizer.** Since Opus 4.7, the same text counts as roughly 30% more tokens than on older models. Price per token is not cost per task.
- **Haiku 5.5** rejects non-default `temperature`, `top_p` and `top_k` with a 400.
- **Opus 5.5 breaking changes** around forced tool use, disabled thinking and the older computer-use tool. Read the migration guide before switching.

## 5. Official sources

| What | URL |
|---|---|
| Choosing a model | https://platform.claude.com/docs/en/about-claude/models/choosing-a-model |
| Models overview (IDs, prices, defaults) | https://platform.claude.com/docs/en/models/overview |
| Effort | https://platform.claude.com/docs/en/build-with-claude/effort |
| Thinking | https://platform.claude.com/docs/en/build-with-claude/thinking |
| Pricing | https://platform.claude.com/docs/en/about-claude/pricing |
| Deprecations | https://platform.claude.com/docs/en/about-claude/model-deprecations |
| Cost and intelligence strategies | https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence |
| Models API (machine-readable) | https://platform.claude.com/docs/en/api/models/list |
