# SEO-Optimized Post Template

> The headings, labels and placeholders below are written in English. When the blog
> publishes in another language, localize every visible string (headings such as
> "In short", "Frequently Asked Questions", "Read also", "Conclusion", table headers,
> and the title formats) to the blog's language — the structure stays the same.

## HTML Structure

```html
<!--
  Meta fields (set via API, not in the HTML):
  - meta_title: max 60 chars, includes the primary keyword
  - meta_description: max 155 chars, CTA or clear benefit
  - og_title, og_description: may differ from the meta fields
  - twitter_title, twitter_description: same
  - custom_excerpt: 1-2 sentences, summary of the post
  - feature_image: URL of the main image (1200x630px ideal)
-->

<!-- ANSWER CAPSULE — Featured Snippet bait -->
<blockquote>
  <p><strong>In short:</strong> [Direct answer to the main question in 2-3 sentences.
  This increases the chance of appearing as a featured snippet on Google.]</p>
</blockquote>

<!-- INTRODUCTION — Hook + context -->
<p>[1-2 paragraphs. Open with a hook that sparks curiosity.
Mention the primary keyword naturally.
Establish authority/credibility.]</p>

<!-- MAIN SECTION — H2s as questions -->
<h2>What is [topic]?</h2>
<p>[Clear explanation. Use accessible language.
Include data/statistics if available.]</p>

<h2>How does [main action] work?</h2>
<p>[Step by step or detailed explanation.]</p>

<!-- CONTEXTUAL IMAGE -->
<figure>
  <img src="[image-url]" alt="[detailed description for accessibility]" />
  <figcaption>[Descriptive caption]</figcaption>
</figure>

<h2>Why is [benefit] important?</h2>
<p>[Connect with the reader's pain/need.]</p>

<!-- COMPARISON TABLE (when applicable) -->
<h2>[Topic A] vs [Topic B]: Comparison</h2>
<table>
  <thead>
    <tr>
      <th>Aspect</th>
      <th>[Topic A]</th>
      <th>[Topic B]</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>[Criterion 1]</td>
      <td>[Value]</td>
      <td>[Value]</td>
    </tr>
    <!-- more rows -->
  </tbody>
</table>

<!-- PRACTICAL SECTION — How-to or tips -->
<h2>How to [do the thing]? Step-by-step guide</h2>
<ol>
  <li><strong>[Step 1]:</strong> [Description]</li>
  <li><strong>[Step 2]:</strong> [Description]</li>
  <li><strong>[Step 3]:</strong> [Description]</li>
</ol>

<!-- FAQ — Based on real Google PAA -->
<h2>Frequently Asked Questions</h2>

<h3>[Real Google PAA question 1]?</h3>
<p>[Direct answer, 2-4 sentences.]</p>

<h3>[Real Google PAA question 2]?</h3>
<p>[Direct answer, 2-4 sentences.]</p>

<h3>[Real Google PAA question 3]?</h3>
<p>[Direct answer, 2-4 sentences.]</p>

<!-- Repeat for 5-10 FAQs -->

<!-- INTERNAL LINKS -->
<h2>Read also</h2>
<ul>
  <li><a href="/related-post-1/">Title of related post 1</a></li>
  <li><a href="/related-post-2/">Title of related post 2</a></li>
  <li><a href="/related-post-3/">Title of related post 3</a></li>
</ul>

<!-- CONCLUSION -->
<h2>Conclusion</h2>
<p>[Summary of the main points. Clear CTA — what should the reader do now?]</p>
```

## Quality Rules

### Title (H1)
- Max 60 characters
- Includes the primary keyword
- Preferred formats (localize to the blog's language): "How to [do X]: Complete Guide [year]" or "What is [X]? Everything you need to know"

### Body
- Minimum 1500 words for pillar posts
- Minimum 800 words for regular posts
- H2s written as real user questions
- Short paragraphs (3-4 sentences max)
- Use lists where appropriate
- At least 1 comparison table if the topic allows

### Images
- Feature image: 1200x630px (OG standard)
- Format: WebP preferred, < 200KB
- Descriptive alt text on every image
- At least 2 images per 1500+ word post

### SEO
- Primary keyword in the title, first paragraph, and 1-2 H2s
- Meta description with a CTA (max 155 chars)
- Custom excerpt different from the meta description
- Short, descriptive URLs (slug)

### Internal Linking
- Minimum 2 internal links per post
- Links in relevant context, not only at the end
- Descriptive anchor text (not "click here")

### E-E-A-T Signals
- Named author
- First-person voice where appropriate
- Data/sources cited when available
- Publication date and last-updated date visible
