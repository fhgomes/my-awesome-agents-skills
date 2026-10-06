# andela-profile

Fill in, rewrite or audit a talent profile on the Andela talent platform through the user's logged-in browser.

## Purpose

Bring an Andela profile in line with the user's current CV — Overview, Work experience, Education — with content taken from the user's own sources, saved through the UI, and verified after a reload. Andela computes the "years of experience" header and the skill chips from the experience entries, so a stale profile quietly lowers matching; this skill fixes that without inventing anything.

## Features

- **Page map** — every section, how to open its editor, field list, required fields and character limits (Overview 1000 plain text, job description 2500 markdown)
- **Content shapes** — an Overview template that fits the limit and a job-description template whose `Tech:` line feeds Andela's automatic skill extraction
- **Automation traps** — Enter in the skills box submits the form, the "currently work here" checkbox ignores programmatic input, extension iframes blocking screenshots/scripts, pencils that only scroll when clicked by reference
- **Procedure** — gather sources, snapshot, experience first, overview, education, reload-and-verify, before/after report
- **Ground rules** — edit only what the user named, never invent dates or metrics, use the UI not the private API

## Quick Start

```
"Update my Andela profile from my latest CV"
"Add my current job to Andela and rewrite the old experiences"
```

The agent reads the CV, snapshots the current profile, edits each entry in the browser, reloads, and reports what changed.

## See Also

- [SKILL.md](SKILL.md) — full procedure, field map and traps
