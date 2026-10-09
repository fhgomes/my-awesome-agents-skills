# Choosing a Model

**Best used when:** you are picking a model and a reasoning level for an API integration, a coding agent or a pipeline, and you want rules that survive the next model launch.
**Read before:** switching to a bigger model because "the answers got worse", or copying a model ID and effort setting from an older project.
**See also:** [vendors/](./vendors/) (per-vendor facts) · [keeping-it-current.md](./keeping-it-current.md) (refresh procedure)

This page holds the positions that do not change when a vendor ships a new model. The numbers live in the vendor files, each with a `last_verified` date. If a vendor file is stale, refresh it before you trust a number from it.

---

## 1. The rules

**1. Turn the effort dial before you switch models.**
Anthropic's docs say it directly: tuning effort is often a better lever than switching models. OpenAI frames model and reasoning level as one intelligence/price trade-off. Effort changes how many tokens the model spends on the whole response (reasoning, answer and tool calls), and it is cheaper to move than a model migration.

**2. Most flagships always reason. The question is how much.**
Claude Opus 5.5 and Fable 5.1 cannot turn thinking off. GPT-6 Astra and GPT-6.1 Sol have no `none` level. Every Gemini 3.x model thinks. Grok 4.5 and later, Kimi K3 and K2.7 Code always reason. Asking "does it use deep thinking?" gets a boring yes. Ask what level it runs at, and set it.

**3. Default to the middle tier. The flagship is an escalation path.**
Anthropic and OpenAI both point you at a model below their top one for real engineering work (Opus 5.5 below Fable 5.1, GPT-6.1 Sol below Astra), and Google's GA workhorse is 3.8 Flash, not the preview Pro. Move up only when the middle model at its highest effort still fails your evals.

**4. Push routine work down.**
Extraction, classification, routing, structured summaries and most subagent calls belong on the cheapest tier at low effort. That is where most tokens are spent, so that is where most money is saved.

**5. Set effort explicitly. Defaults move between generations.**
Claude Opus 5.5 defaults to `medium`; Opus 5 defaulted to `high`. Kimi K3 defaults to `max`. Gemini defaults range from `minimal` to `high` depending on the model. Swapping the model ID without setting effort silently runs one notch lower. Never carry effort settings across model generations: re-run the sweep.

**6. Compare cost per successful task, not price per token.**
A pricier model that finishes in fewer tokens and fewer retries can cost less per task. Tokenizers also differ across generations, so the same text can count as more tokens on a newer model.

**7. Speed is a separate axis.**
Fast or priority modes buy latency at a premium price, independently of effort. Do not lower effort to fix latency until you have checked whether a speed tier fits the budget.

## 2. Tier map

Rough equivalence across vendors on the `last_verified` date of each vendor file. Tiers are positioning, not benchmark parity.

<!-- tier-map:start -->
| Tier | Anthropic | OpenAI | Google | xAI | Moonshot | Use for |
|---|---|---|---|---|---|---|
| Ceiling (escalation only) | Fable 5.1 | GPT-6 Astra | 3.1 Pro (preview) | Grok 4.7 | Kimi K3 | Hours-long agents, deepest reasoning, when the default tier at max effort fails |
| Default for engineering work | Opus 5.5 | GPT-6.1 Sol | 3.8 Flash | Grok 4.7 | K2.7 Code (coding) / K3 | Agentic coding, refactors, research, computer use |
| Fast everyday | Sonnet 5.5 | — | 3.7 Flash | Grok 4.3 | K2.6 | Everyday coding and agents where speed or token efficiency matters |
| Volume and subagents | Haiku 5.5 | GPT-6 Luna | 3.5 / 3.1 Flash-Lite | Grok 4.3 (effort `none`) | K2.6 (thinking off) | Classification, extraction, routing, subagents |

## 3. Can reasoning be turned off?

| Vendor | Always reasons (no off switch) | Can turn it off | Control and default |
|---|---|---|---|
| Anthropic | Fable 5.1, Opus 5.5 | Sonnet 5.5 (`between_tools` skips up-front thinking) | `output_config.effort`; `medium` on Opus 5.5 and Haiku 5.5, `high` elsewhere |
| OpenAI | GPT-6 Astra, GPT-6.1 Sol (floor `low`) | GPT-6 Luna (`none`) | `reasoning.effort`; `medium` |
| Google | All Gemini 3.x (`minimal` is near zero, not off) | Gemini 2.5 Flash / Flash-Lite (budget `0`, being retired) | `thinking_level`; per model, `minimal` to `high` |
| xAI | Grok 4.7, 4.6, 4.5 | Grok 4.3 (`none`), Grok 4.20 non-reasoning | `reasoning.effort` / `reasoning_effort`; `high` on 4.5+, `low` on 4.3 |
| Moonshot | Kimi K3, K2.7 Code | Kimi K2.6 (`thinking.type: disabled`) | K3 only: `reasoning_effort`, default **`max`** |
<!-- tier-map:end -->

## 4. The evaluation protocol

A model or effort decision without a measurement is a guess. This one fits in an afternoon.

1. Pick 10 to 20 **real** tasks from your backlog or logs, with a pass/fail check for each. Not benchmark prompts.
2. Run them on the default-tier model at **two** effort levels (its default and one step up or down).
3. Record for each run: pass or fail, wall-clock latency, input and output tokens, cost.
4. Compute **cost per successful task** and p50/p95 latency per configuration.
5. Change one thing at a time: effort first, then model tier, then speed tier.
6. Escalate the model only when the highest effort on the current tier still fails tasks you care about.
7. Write the winning configuration (model ID **and** effort) into config, not into someone's memory.

## 5. Multi-model patterns

Two shapes keep most tokens on a cheap model while a frontier model makes the hard calls:

| Pattern | How it works | Good for |
|---|---|---|
| Executor + advisor | A cheap model does the work and escalates hard decisions to a frontier model | Pipelines with rare hard cases |
| Orchestrator + workers | A frontier model plans and delegates bulk work to cheap subagents | Large codebases, research fan-out |

Anthropic documents both with measured examples in its cost-and-intelligence guide (linked in [vendors/anthropic.md](./vendors/anthropic.md)). OpenAI's GPT-6.1 Sol supports multi-agent delegation in the Responses API (beta).

## 6. Quick answers

| Question | Answer |
|---|---|
| "Which model should I start with?" | The default tier in the tier map, at its default effort, then run the section 3 protocol |
| "Answers got worse after an upgrade" | Check whether the default effort changed before blaming the model. Set it explicitly |
| "It's too slow" | Lower effort for simple tasks, move routine calls down a tier, or try a speed tier |
| "It's too expensive" | Push subagents and routine calls to the volume tier at low effort. Cache stable context |
| "Can I turn reasoning off?" | On most flagships, no. See section 3 |
