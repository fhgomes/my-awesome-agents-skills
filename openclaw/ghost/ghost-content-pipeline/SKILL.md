---
name: ghost-content-pipeline
description: >
  Automated pipeline for creating, publishing and optimizing content on Ghost CMS.
  Use whenever you need to: create posts automatically, schedule publications, improve
  existing posts for SEO, generate images for posts, distribute content to social networks,
  submit URLs for indexing (Google/Bing/IndexNow), monitor content performance,
  run bulk operations on posts (mass-update tags, meta descriptions, feature images),
  build a content calendar, or any variation of "publish on Ghost", "automate posts",
  "improve post SEO", "create content", "content pipeline". Also trigger when the user
  mentions: "ghost cron job", "auto publish", "content automation", "ghost posts",
  "ghost SEO", "indexnow", "google indexing", "bulk update posts", "content calendar",
  "repurpose content", "social media automation ghost". Also triggers on the equivalent
  phrases in other languages.
metadata:
  openclaw:
    emoji: "📝"
    requires:
      env: ["GHOST_URL", "GHOST_ADMIN_API_KEY"]
      binaries: ["node"]
    primaryEnv: "GHOST_ADMIN_API_KEY"
    files: ["scripts/*"]
---

# Ghost Content Pipeline

Automated pipeline for creating, publishing, optimizing and distributing content on a self-hosted Ghost CMS. Designed to run as cron jobs or to be invoked by agents.

## Dependencies

### Required
```bash
GHOST_URL=https://your-ghost.com
GHOST_ADMIN_API_KEY=id:secret
```

### Optional (per feature)
```bash
# SEO Research
SERPER_API_KEY=xxx              # Google SERP data (serper.dev)

# Indexing
GOOGLE_INDEXING_KEY_FILE=/path  # Google Indexing API service account
INDEXNOW_KEY=xxx                # IndexNow API key

# Image generation
OPENAI_API_KEY=xxx              # DALL-E
IDEOGRAM_API_KEY=xxx            # Ideogram
# or any other configured image API

# Social distribution
TWITTER_BEARER_TOKEN=xxx        # X/Twitter API
PINTEREST_TOKEN=xxx             # Pinterest API
```

### Setup
```bash
cd $SKILL_DIR && npm install
```

## Workflows

### 1. Create and Publish a New Post

Full content-creation pipeline:

```
1. Research the topic
   → scripts/content-research.js --topic="topic" --check-competition
   Output: { keyword, difficulty, paa_questions[], related_topics[], existing_posts[] }

2. Check whether it already exists on the site
   → scripts/ghost-content-ops.js posts search --query="topic"
   If it exists: abort or suggest an update

3. Generate the content
   → The agent (LLM) generates the post HTML following the template in references/post-template.md
   Input: research from step 1
   Output: { title, html, meta_title, meta_description, tags[], custom_excerpt }

4. Generate a feature image (optional)
   → scripts/generate-image.js --prompt="..." --output=/tmp/feature.webp
   → scripts/ghost-content-ops.js images upload --file=/tmp/feature.webp

5. Publish
   → scripts/ghost-content-ops.js posts create --json='{...}'
   Status: "published" (immediate) or "scheduled" with published_at

6. Submit for indexing
   → scripts/submit-indexing.js --url="https://your-ghost.com/new-post/"

7. Distribute on social networks (optional)
   → scripts/social-distribute.js --post-url="..." --platforms=twitter,pinterest
```

### 2. Improve an Existing Post (Content Improver)

To run as a cron job, improving the oldest post on each execution:

```
1. Fetch the oldest / most outdated post
   → scripts/ghost-content-ops.js posts list --order=updated_at+asc --limit=1 --status=published

2. Analyze current quality
   → scripts/content-analyzer.js --url="post-url" --check-seo --check-readability
   Output: { score, missing_h2s, missing_faq, word_count, missing_images, suggestions[] }

3. Research fresh data
   → scripts/content-research.js --topic="post-topic" --paa-only
   Output: { paa_questions[], fresh_data }

4. Generate the improved version (via LLM)
   Rules: references/improvement-rules.md
   - Keep the original URL/slug
   - Add an FAQ with real PAA data
   - Improve the H2 structure
   - Add internal links
   - Improve the meta description

5. Generate new images if needed
   → scripts/generate-image.js + upload

6. Update the post
   → scripts/ghost-content-ops.js posts update --id=xxx --json='{...}'

7. Resubmit for indexing
   → scripts/submit-indexing.js --url="post-url"
```

### 3. Bulk Operations

For mass operations on existing posts:

```
# Update meta descriptions of every post that has none
→ scripts/ghost-content-ops.js posts list --filter="meta_description:null" --limit=all
→ For each: generate a meta description via LLM → update

# Add a tag to posts matching a filter
→ scripts/ghost-content-ops.js posts bulk-tag --filter="tag:-optimized" --add-tag="optimized"

# Reprocess every feature image to WebP
→ scripts/ghost-content-ops.js posts list --fields=id,feature_image --limit=all
→ For each: download → convert to WebP → re-upload → update post

# Generate custom_excerpt for posts without an excerpt
→ scripts/ghost-content-ops.js posts list --filter="custom_excerpt:null" --limit=all
→ For each: extract the first paragraph → generate an excerpt via LLM → update
```

### 4. Content Calendar

Content planning and scheduling:

```
1. Generate a topic calendar
   → scripts/content-research.js --generate-calendar --weeks=4 --niche="your-niche"
   Output: calendar.json with topics, dates, keywords

2. For each calendar item:
   → Run the "Create and Publish a New Post" workflow
   → Use status "scheduled" with the published_at from the calendar

3. Monitor scheduled publications
   → scripts/ghost-content-ops.js posts list --status=scheduled --order=published_at+asc
```

## Recommended Post Structure

See `references/post-template.md` for the full template. Summary (headings shown in English — localize them to the blog's language):

```html
<!-- Answer Capsule (featured snippet bait) -->
<div class="answer-capsule">
  <p><strong>Quick answer:</strong> ...</p>
</div>

<!-- H2s written as real user questions -->
<h2>What is [topic]?</h2>
<p>...</p>

<h2>How does [action] work?</h2>
<p>...</p>

<!-- Comparison table -->
<table>...</table>

<!-- FAQ with real PAA data -->
<h2>Frequently Asked Questions</h2>
<h3>Real question from Google PAA?</h3>
<p>Answer...</p>

<!-- Internal links -->
<h2>Read also</h2>
<ul>
  <li><a href="/related-post/">Title</a></li>
</ul>
```

## Shared Library

Content ops scripts import JWT/HTTP utilities from the selfhost-admin shared lib:
```
require('../../ghost-selfhost-admin/lib/ghost-api')
```

## References

- SEO-optimized post template → `references/post-template.md`
- Content improvement rules → `references/improvement-rules.md`
- Cron job setup → `references/cron-setup.md`
- Ghost Admin API reference → `../ghost-selfhost-admin/references/ghost-admin-api.md`

## Integration with the Celebrity Dev Agent Team

This skill is the engine of the Celebrity Dev **Content Pipeline sub-team**:
- **Topic Scout** uses `content-research.js` to discover topics
- **SEO Optimizer** uses `content-analyzer.js` for audits and improvements
- **Long-form/Short-form Draft Writers** produce content following `post-template.md`
- **Repurposer** uses `social-distribute.js` for distribution
- **Visual Director** uses `generate-image.js` for visual assets

The Brand Voice Guardian and Content Strategist (Claude API) validate the output before publishing.

## Golden Rules

1. **Never publish without review** — drafts first, publish after validation
2. **Real PAA data, never invented** — use Serper/SERP API for FAQs
3. **Optimized images** — always WebP, max 1280px, < 200KB
4. **Internal linking** — every post must link to at least 2 related posts
5. **updated_at is mandatory** — Ghost requires it for conflict detection on updates
6. **Social rate limits** — respect the limits of the social network APIs
7. **Monitor indexing** — check that posts were indexed after submission
8. **Backup before bulk ops** — export content before mass operations
