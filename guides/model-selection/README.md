# Model Selection

**Best used when:** you have to pick an LLM and a reasoning level for an API integration, a coding agent or a pipeline, across Anthropic, OpenAI, Google, xAI or Moonshot, and you want the choice to survive the next model launch.
**Read before:** switching to a bigger model because "the answers got worse", copying a model ID from an old project, or asking "does this model think by default?".
**See also:** [../../openclaw/guides/providers-and-models.md](../../openclaw/guides/providers-and-models.md) (wiring providers into OpenClaw) · [../performance/](../performance/) (measure before you claim)

Two kinds of content live here, and they age at different speeds:

| Kind | Files | Changes when |
|---|---|---|
| **Positions** that hold across launches | [choosing-a-model.md](./choosing-a-model.md) | Rarely. A rule changes only when the vendors' guidance changes |
| **Facts** that go stale in weeks | [vendors/](./vendors/) | Every launch, price change or new default. Each file carries a `last_verified` date |

The rule every file in this folder shares: **turn the effort dial before you switch models**, and measure cost per successful task before you believe any of it.

---

## Start here

| Your situation | Read, in order | First thing to do today |
|---|---|---|
| **Picking a model for something new** | [choosing-a-model.md](./choosing-a-model.md) sections 1-2, then the vendor file | Start on the default tier at its default effort, set effort explicitly in config, and run the section 4 evaluation protocol on 10 real tasks |
| **"It got worse after the upgrade"** | [choosing-a-model.md](./choosing-a-model.md) rule 5, then the vendor file's Traps section | Check whether the new model's default effort is lower than the old one's before you blame the model |
| **"Does model X think by default?"** | [choosing-a-model.md](./choosing-a-model.md) section 3 | Look up the row. Most flagships cannot turn reasoning off; the question is how much |
| **A vendor launched something / a file is stale** | [keeping-it-current.md](./keeping-it-current.md) | Run `python scripts/check_staleness.py`, then follow the refresh procedure for each STALE row |
| **Adding a vendor** | [keeping-it-current.md](./keeping-it-current.md) section 6 | Copy the vendor file shape, add its sources to the section 3 table, add it to the tier map |

## Files

| File | One line |
|---|---|
| [choosing-a-model.md](./choosing-a-model.md) | Seven vendor-neutral rules, the cross-vendor tier map, which models can turn reasoning off, the evaluation protocol, multi-model patterns, quick answers |
| [keeping-it-current.md](./keeping-it-current.md) | When to refresh, source hierarchy (official docs only), where to look per vendor with fetch traps, the per-model checklist, how to record a refresh, adding a vendor, a copy-paste prompt for an agent, automating the reminder |
| [vendors/anthropic.md](./vendors/anthropic.md) | Claude Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5: lineup, when to use, adaptive thinking, effort levels and defaults, traps |
| [vendors/openai.md](./vendors/openai.md) | GPT-6 Astra, GPT-6.1 Sol, GPT-6 Luna: lineup, when to use, reasoning effort, Codex levels, speed tiers, traps |
| [vendors/google.md](./vendors/google.md) | Gemini 3.1 Pro, 3.8 / 3.7 Flash, Flash-Lite: lineup, when to use, `thinking_level`, intro pricing, Gemini API vs Google Cloud lifecycles |
| [vendors/xai.md](./vendors/xai.md) | Grok 4.7, 4.6, 4.5, 4.3, 4.20 (incl. multi-agent), Build 0.1: lineup, when to use, reasoning effort, retired-ID redirects, the 200K pricing cliff |
| [vendors/moonshot.md](./vendors/moonshot.md) | Kimi K3, K2.7 Code, K2.6: lineup, open weights and licenses, thinking rules, K3's `max` default, reasoning round-trip |
| [scripts/check_staleness.py](./scripts/check_staleness.py) | Stdlib script: prints each vendor file's age and exits 1 when any is older than `--max-age-days` (default 30) |

## Keeping this folder honest

Every number in `vendors/` came from the vendor's own docs on the file's `last_verified` date, and anything that could not be confirmed is marked `UNVERIFIED`. Nothing here is a benchmark: tiers are the vendors' own positioning. When a file goes stale, refresh it with [keeping-it-current.md](./keeping-it-current.md) before acting on it.

```bash
python guides/model-selection/scripts/check_staleness.py
```

_Last reviewed: 2026-10-09._
