# Content workflow: drafts, review loop, voice

## Ground rules

1. **Agents create drafts, the owner publishes.** `status: "draft"` on every
   create; never `published` from a script.
2. **Technical posts are born from real data.** Put a "ground truth (do not
   drift)" block in the writing prompt with the verified numbers, paths and
   dates. Agents may not invent, round or "improve" them.
3. **The canonical text is the one in Ghost.** After manual edits in the
   editor the published post diverges from any draft file; record the URL,
   post id and publish date in the pipeline notes and treat the draft as
   history.

## Review loop with inline comments

1. Create the post as a draft via the API (`?source=html`).
2. The owner edits in the Ghost editor and leaves comments as paragraphs
   starting with `//`.
3. Fetch the current HTML (`?formats=html`), read every `//` line (intent over
   wording), rewrite the whole article honoring the owner's own edits, PUT it
   back with `?source=html` and a fresh `updated_at`, with the `//` lines
   removed.
4. Repeat until the owner publishes.
5. If `updated_at` changed without your PUT, the editor is open and
   autosaving. Re-fetch, merge, and only then write. `post_revisions` in the
   database holds the history if something was lost.

## Voice rules for a senior technical audience

Learned by review, applied on every draft:

- **No em-dashes.** They read as machine text. Rewrite the sentence with a
  comma, a colon, parentheses or a second sentence; do not just swap the
  character. Arrows (`→`) are fine.
- **Contractions** in conversational passages; formal only in bold maxims.
- **Solution-first.** Show the system working in steady state, not the
  chronology of the problem. The real case enters as an example in the middle.
- Antitheses ("not X, it is Y") at most two or three per post; more becomes a
  teleprompter rhythm.
- Concrete numbers and evidence; honest "still pending" items are part of the
  voice, not something to hide.
- CTA with a direct link to the resource; no "steal my ..." phrasing.
- No client or brand names as credentials unless the author was employed
  there; no cheesy taglines.
- One language for public content (English by default); other languages only
  for content tied to an event in that language.

## Optional gates

If a multi-agent pipeline exists (ICP fit, editor, voice guardian, SEO),
the voice gate should be blocking with a threshold, combining a mechanical
banned-phrase check with a qualitative read against a written voice profile.
After publication, notify the pipeline with URL, post id and history so it
closes its log and moves the note to "published".
