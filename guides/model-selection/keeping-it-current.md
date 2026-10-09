# Keeping It Current

**Best used when:** a vendor ships a new model, changes a price or a default, or `scripts/check_staleness.py` reports a STALE row.
**Read before:** editing any file in [vendors/](./vendors/), or asking an AI agent to "update the model guide".
**See also:** [README.md](./README.md) · [choosing-a-model.md](./choosing-a-model.md)

Model facts go stale in weeks. A lineup, a default effort level or a price that was right last month can be wrong today, and nothing in a markdown file warns you. This page is the procedure that keeps the vendor files honest: when to refresh, where to look, what to extract, and how to record it.

---

## 1. When to refresh

Refresh a vendor file when **any** of these is true:

| Trigger | How you notice |
|---|---|
| `last_verified` is older than 30 days | `python scripts/check_staleness.py` exits 1 and marks the row STALE |
| Someone names a model that is not in the file | A question, a changelog, a release post, a model ID in an error message |
| The vendor announced a launch, a deprecation or a price change | Their news page, release notes or changelog (section 3) |
| A default changed under you | Behavior shifted after an SDK or client upgrade with no code change on your side |

Refreshing a file you are about to rely on for a decision is always cheaper than acting on a stale row.

## 2. Source hierarchy

Use the highest source available. Never let a lower one override a higher one.

1. **The vendor's API docs:** model pages, models list, pricing page, reasoning/thinking docs.
2. **The vendor's machine-readable endpoints:** a models API (IDs, limits, capabilities) when it exists.
3. **The vendor's own announcements:** news posts, release notes, changelogs, model cards from the vendor's official org on Hugging Face or GitHub.
4. **Third-party pages:** blogs, aggregators, comparison sites, videos. **Only to discover an official URL, never as the source of a fact.** They lag, round prices, and confuse model versions.

If a fact appears only in tier 4, record it as `UNVERIFIED` or leave it out.

## 3. Where to look, per vendor

| Vendor | Start here | Then check | Fetch traps |
|---|---|---|---|
| Anthropic | [Models overview](https://platform.claude.com/docs/en/models/overview) (IDs, prices, thinking, default effort in one table) | [Choosing a model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model) · [Effort](https://platform.claude.com/docs/en/build-with-claude/effort) · [Pricing](https://platform.claude.com/docs/en/about-claude/pricing) · [Deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) · [Models API](https://platform.claude.com/docs/en/api/models/list) | `docs.anthropic.com` redirects (301) to `platform.claude.com`. Follow it |
| OpenAI | [Models list](https://developers.openai.com/api/docs/models) (IDs, prices, effort levels) | [Model selection](https://developers.openai.com/api/docs/guides/model-selection) · [Using the latest model](https://developers.openai.com/api/docs/guides/latest-model) · [Codex models](https://learn.chatgpt.com/docs/models) · `openai.com/index/` posts | `openai.com` returns 403 to plain HTTP fetches: open it in a browser. `developers.openai.com/codex/models` redirects (308) to `learn.chatgpt.com/docs/models` |
| Moonshot (Kimi) | [Model list](https://platform.kimi.ai/docs/models) (IDs, deprecations) | [Pricing](https://platform.kimi.ai/docs/pricing/chat) · [Thinking](https://platform.kimi.ai/docs/guide/use-thinking-models) · [Reasoning effort](https://platform.kimi.ai/docs/guide/use-reasoning-effort) · [Changelog](https://platform.kimi.ai/docs/platform-changelog) · [Blog](https://www.kimi.ai/blog/) · [Hugging Face org](https://huggingface.co/moonshotai) | `platform.moonshot.ai` redirects (301) to `platform.kimi.ai`; `.cn` goes to `platform.kimi.com` (China, CNY prices). Append `.md` to a docs URL for markdown; `docs/llms.txt` indexes every page. The changelog has months, not days. The Kimi Code subscription is a separate API |
| xAI (Grok) | [Models and pricing](https://docs.x.ai/developers/models) | [Reasoning](https://docs.x.ai/developers/model-capabilities/text/reasoning) · [Release notes](https://docs.x.ai/developers/release-notes) · per-model pages `docs.x.ai/developers/models/<id>` · news posts `x.ai/news/<model-slug>` · migration guides under `docs.x.ai/developers/migration/` | Old `docs.x.ai/docs/...` paths redirect (308) to `/developers/...`. `x.ai/news` (index) and `x.ai/api` return 403: open in a browser or go straight to a post URL. Retired model pages redirect (307) to the models list. Release notes give month only. xAI's own pages disagree on some effort levels: record the conflict instead of picking one |
| Google (Gemini) | [Models list](https://ai.google.dev/gemini-api/docs/models) (shows a "last updated" date) | [Thinking](https://ai.google.dev/gemini-api/docs/thinking) · [Pricing](https://ai.google.dev/gemini-api/docs/pricing) · [Changelog](https://ai.google.dev/gemini-api/docs/changelog) · [Deprecations](https://ai.google.dev/gemini-api/docs/deprecations) · [Latest model guide](https://ai.google.dev/gemini-api/docs/latest-model) · [Firebase thinking levels](https://firebase.google.com/docs/ai-logic/thinking) · [Cloud lifecycle](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions) | `cloud.google.com/vertex-ai/...` redirects (301) to `docs.cloud.google.com`. Cloud pages are huge and mostly navigation: read from an offset to reach the tables. Search results surface stale `?authuser=` / `?hl=` copies of the thinking page. The Gemini API and Google Cloud keep separate lifecycle dates: check both |

**Discovering a model you have never heard of:** search the model name restricted to the vendor's domains first (for example `site:platform.claude.com`, `site:developers.openai.com`). If only third-party pages mention it, treat it as a rumor until an official page appears.

## 4. What to extract

Every vendor file uses the same shape so files stay comparable. Fill each field from a tier 1-3 source, or write `UNVERIFIED`.

```markdown
---
vendor: <Vendor>
family: <Model family>
last_verified: YYYY-MM-DD
---

## 1. Lineup
| Model | API ID | Role | Input / output (USD per 1M) | Context / max output | Thinking (always on? can disable?) | Default effort |

## 2. When to use, when not to          # the vendor's own positioning, plus "Not for"
## 3. Thinking / reasoning and effort   # parameter name, levels, default per model, how to turn it off
## 4. Traps                              # defaults that moved, pricing tiers, rejected params
## 5. Official sources                   # every URL you used
```

Checklist per model:

- [ ] Exact API ID, as the docs spell it
- [ ] Positioning in the vendor's words (what it is for)
- [ ] Input, output and cached-input price, plus any long-context tier
- [ ] Context window and max output
- [ ] Whether it reasons by default, and whether reasoning can be turned off
- [ ] The effort / budget parameter: name, levels, default
- [ ] Release date and knowledge cutoff when published
- [ ] Deprecation or retirement dates for models you are leaving in the table

## 5. How to record a refresh

1. Update the facts in the vendor file. Do not leave both old and new numbers.
2. Set `last_verified` to today, **only** if you checked every row against tier 1-3 sources. A partial check keeps the old date and adds a note.
3. If a default, price or lineup changed, add one line to the **Traps** section ("Defaults moved: X now defaults to Y").
4. Update the cross-vendor tier map in [choosing-a-model.md](./choosing-a-model.md) if a tier changed.
5. Run `python scripts/check_staleness.py` and confirm the row says `ok`.
6. Commit with a message that names what changed: `docs(model-selection): Haiku 5.5 added, default effort medium`.

## 6. Adding a new vendor

1. Copy the shape from section 4 into `vendors/<vendor>.md`, with `vendor:` and `last_verified:` in the frontmatter.
2. Add a row to the table in section 3 with the vendor's official start page, the pages to check, and any fetch trap you hit.
3. Add the vendor to the tier map in [choosing-a-model.md](./choosing-a-model.md) and to the file table in [README.md](./README.md).
4. Run the staleness check. The new file must show `ok`.

## 7. Prompt for an agent doing the refresh

Paste this into any coding agent that can browse:

```text
Refresh guides/model-selection/vendors/<vendor>.md.
1. Read guides/model-selection/keeping-it-current.md and follow it.
2. Use only the vendor's official docs, models API, announcements and official
   model cards. Third-party pages may only be used to find official URLs.
3. Check every field in the section 4 checklist for every model in the file,
   and add any current model that is missing. Mark anything you cannot confirm
   as UNVERIFIED.
4. Show me a diff of what changed (lineup, prices, defaults, thinking rules)
   with the official URL for each change before you edit the file.
5. After my OK: update the file, set last_verified to today, add a Traps line
   for any default or price that moved, update the tier map in
   choosing-a-model.md, and run scripts/check_staleness.py.
Do not commit.
```

## 8. Automating the reminder

The staleness check is a plain script with an exit code, so any scheduler can run it:

- **CI:** a weekly scheduled job that runs `python guides/model-selection/scripts/check_staleness.py` and opens an issue when it exits 1.
- **Local cron or a scheduled agent:** run the check, and when it fails, run the section 7 prompt for the STALE vendors.

Keep the human in the loop for the edit itself. A refresh is a set of facts other people will act on; a reviewed diff is worth the minute it costs.
