# Content Improvement Rules (Content Improver)

## Core Principle

Improve existing posts WITHOUT breaking what already works.
Never change the URL/slug. Never remove content that ranks well.
Always ADD value — never subtract.

## Analysis Checklist (before improving)

1. **Word count** — If < 800 words, expand significantly
2. **H2 structure** — Are there H2s? Are they real questions?
3. **FAQ section** — Does it exist? Does it use real PAA data?
4. **Feature image** — Does it exist? Is it optimized (WebP, < 200KB)?
5. **Meta description** — Does it exist? Is it compelling? Does it have a CTA?
6. **Custom excerpt** — Does it exist? Is it different from the meta description?
7. **Internal links** — How many? Minimum 2.
8. **Tables** — Are there comparisons that would benefit from a table?
9. **Alt text** — Do all images have descriptive alt text?
10. **Answer capsule** — Is there a quick answer at the top?

## Improvement Rules

### DO
- Add an answer capsule if there is none
- Convert generic H2s into real questions
- Add an FAQ with 5-10 Google PAA questions (real data, via Serper)
- Add a comparison table when the topic allows
- Add internal links to related posts
- Expand short paragraphs with more context
- Add data/statistics when available
- Improve the meta description with a CTA
- Generate new images if the current ones are low quality
- Add structured data markup where appropriate

### DON'T
- Never change the slug/URL
- Never remove content that may be ranking
- Never change the tone/voice drastically
- Never invent FAQs — use real Google data
- Never force keywords in (keyword stuffing)
- Never remove existing internal links
- Never change the author
- Never reset the original publication date
- Never use generic stock images without context

## Priority Order

1. **High priority**: Empty meta description, no FAQ, no answer capsule
2. **Medium priority**: Few internal links, no tables, < 1000 words
3. **Low priority**: Improve H2s, add more images, expand sections

## Selection Criteria (which post to improve first)

For the content improver cron job, select posts by:

```
ORDER BY updated_at ASC  → Oldest post without an update
```

This guarantees every post gets attention over time.

Alternatives:
- Posts with the most traffic but no FAQ → biggest impact
- Posts with an empty meta_description → quick win
- Posts with < 800 words → biggest improvement potential

## Post-Improvement Validation

After improving the post, verify:

1. The HTML is valid (nothing broke)
2. Internal links point to posts that exist
3. Images load correctly
4. Meta description is < 155 chars
5. Title is < 60 chars
6. The post renders correctly in Ghost
