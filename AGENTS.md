# Repository guide for coding agents

This repository contains reusable skills and engineering guides, not one
application. Start with [README.md](README.md), then read the `SKILL.md` or guide
for the item you are changing and only its relevant references.

- Keep every item self-contained: copying one skill or OpenClaw area must not
  require files from another tree. Preserve the layout documented in the README.
- `skills/` holds universal skills, `claude/skills/` holds Claude variants, and
  `openclaw/` holds runtime-specific material. A file describing a runtime or
  hook is an artifact being maintained, not proof that it is active in Codex.
- Keep public-facing instructions in English, use portable paths and
  parameterized examples, and preserve license and author credits. Do not add
  private project context, machine details, credentials or transcripts.
- Do not install skills, enable hooks, or apply infrastructure examples as a
  side effect of editing documentation. Do not synchronize another checkout
  without an explicit task to do so.

There is no root application build or repository-wide test command. Validate
the changed item's frontmatter, local links and referenced resources; inspect
its scripts before choosing relevant checks. Guides under
[testing](guides/testing/README.md) and
[performance](guides/performance/README.md) describe reusable procedures, not
mandatory commands to execute against this repository.

For Codex, this file is the entry point. Skill sources under `skills/` and
`claude/skills/` should be read explicitly when relevant; their presence here
does not mean that they are installed or enabled in the current session.
