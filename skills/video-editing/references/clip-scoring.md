# Choosing WHICH segment becomes a clip (scoring rubric)

Adapted from `claude-shorts` (MIT) + signals from `clipify` (MIT). For when the
request is "find the best moments in this video" rather than "cut from X to Y".

Use it with the word-level JSON the skill already produces (`word_captions_map.py
--words-json`) — the same timestamps that plan the cut on exact word
boundaries (rule 6 of SKILL.md).

## The 5 dimensions (0-100 each)

```
score = hook*0.30 + coherence*0.25 + emotion*0.20 + value*0.15 + payoff*0.10
```

### 1. Hook — the first 3 seconds (weight 0.30)

| Archetype | Example | Range |
|---|---|---|
| Contrarian | "Everything you've been told about X is wrong" | 80-100 |
| Curiosity gap | "There's one thing nobody tells you about..." | 75-95 |
| Value promise | "The exact framework I used to..." | 70-90 |
| Pattern interrupt | "Wait, let me show you something" | 70-90 |
| Payoff preview | "By the end of this you'll know..." | 65-85 |
| Starts mid-motion | [enters mid-sentence, with energy] | 60-80 |
| Generic | "So today I want to talk about..." | 10-40 |

Bonus (+5-10 each): a specific number ("3 steps", "$50k"), a recognizable
name (person/company/tool), first-hand experience ("I tested it").

### 2. Standalone coherence (weight 0.25)

It has to make sense to someone who has NOT seen the rest.

| Criterion | Score |
|---|---|
| Complete arc (setup → development → resolution) | 85-100 |
| Complete idea with a gap the viewer can infer | 65-84 |
| References earlier content ("as I said") | 40-64 |
| Needs the earlier context to be understood | 10-39 |
| Fragment — starts or ends mid-thought | 0-9 |

**Red flags (automatic low score)**: "as I said before", "going back to
that point", a pronoun with no referent ("he said that..."), a cut in the
middle of a sentence at the end.

### 3. Emotional intensity (weight 0.20)

| Signal | Range |
|---|---|
| Rant / strong opinion delivered with conviction | 80-100 |
| Surprising reveal / twist | 75-95 |
| Genuine humor / laughter | 70-90 |
| Vulnerability / honest failure story | 70-90 |
| Enthusiastic explanation of something fascinating | 60-80 |
| Calm but sharp observation | 40-60 |
| Monotone recitation of facts | 10-30 |

### 4. Value density (weight 0.15)

| Type | Range |
|---|---|
| Step by step / exact method | 80-100 |
| Framework / mental model with an example | 75-95 |
| Specific data point / research finding | 70-90 |
| Counter-intuitive insight, explained | 65-85 |
| General advice with some specifics | 40-60 |
| Platitude ("work harder", "be consistent") | 10-30 |

Penalize if >30% of the time is filler, repetition or tangent.

### 5. Payoff — how it ends (weight 0.10)

| Ending | Range |
|---|---|
| Punchline / satisfying reveal | 85-100 |
| Clear CTA with a next step | 75-90 |
| Complete thought, natural stop | 65-80 |
| Dissolves into the next topic (can be cut cleanly) | 40-60 |
| Cuts mid-thought / no resolution | 10-30 |

## Selection rules

1. Aim for **8-12 candidates** in a 30-60 min video
2. **Duration**: 15-55s (engagement peaks at 25-40s)
3. **Minimum cutoff: 60.** Below that, skip it
4. **Diversity**: don't pick 5 segments from the same subtopic
5. **Spacing**: prefer segments ≥2 min apart in the original
6. **Boundaries**: align start/end on sentence boundaries, never mid-word —
   use the `--words-json` to get the real start (the rule 6 trap: a word
   stretched across the boundary)

## Mechanical signals (cheap; run before the LLM reads anything)

From `clipify` — they pre-filter and reduce what the model has to read:

- **Audio peaks**: `ffmpeg -af volumedetect`, or rapid alternation of short
  Whisper segments (banter/reaction)
- **Laughter**: "haha", "lol", swearing, "no way", "I can't believe it"
- **Awkward pause**: long gap between Whisper segments
- **Reversal**: question in the setup → unexpected answer
- **Quotable one-liner**: short declarative sentence that stands on its own

## Hook text (overlay for the first ~3.5s)

- **Line 1**: 4-8 words, the claim that stops the scroll
- **Line 2**: 3-6 words, context
- ⚠️ Do **NOT** repeat the first spoken words — the overlay complements the
  audio, it doesn't duplicate it. Pairs with the punch-in from the transition
  recipe.
