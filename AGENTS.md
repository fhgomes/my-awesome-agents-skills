# AGENTS.md — contract for any AI agent editing this repository

Vendor-neutral entry point (OpenClaw, Codex, Cursor, Copilot, Claude Code and
others). [CLAUDE.md](CLAUDE.md) holds the same rules with more detail; read it
before changing anything. The short version:

## The repository is public

Assume every byte you commit will be read by strangers and indexed by bots.

## Non-negotiables

1. **English only.** File and folder names, frontmatter, prose, comments,
   docstrings, CLI help, printed messages, commit messages. Trigger phrases in
   skill descriptions are English; add "Also triggers on the equivalent phrases
   in other languages." instead of listing translations.
2. **No personal or machine-specific data.** No real names (except credited
   open-source authors), no user paths (`C:\Users\<name>`, `/home/<name>`,
   `/mnt/c/Users/<name>`, scratchpad IDs), no hardware inventory or ownership,
   no private repo or project names, no internal hosts/IPs/e-mails, no
   credentials, no verbatim recording content. Procedures go in skills;
   machine facts go in the agent's memory on that machine.
3. **Scripts are portable.** Resolve tools from PATH or an environment
   variable (`FFMPEG_BIN`), never from a hardcoded absolute path. Examples are
   parameterized with placeholder variables.
4. **Security pass before every commit**, and read the output:

   ```bash
   python skills/redact/scripts/scan_secrets.py . --history --severity medium
   python skills/warden/scripts/scan_tree.py . --min-score 3
   ```

   Then grep manually for first names, user paths and the items in rule 2.
   Known accepted findings: the documentation examples inside
   `skills/redact/references/` (official AWS example key, gateway test cards).
5. **Conventional Commits in English** (`feat(scope): ...`, `fix:`, `docs:`,
   `chore:`, `refactor:`, `security:`). Never commit, push, or open a PR
   without being asked. Never rewrite public history on your own.

## Layout

- `skills/<name>/` — universal, self-contained skills (SKILL.md + README.md,
  optional references/, scripts/, assets/, examples/).
- `claude/skills/<name>/` — Claude-format variants.
- `openclaw/` — OpenClaw agents, guides and areas, each self-contained.

Each item must work when copied out alone; cross-links are optional pointers,
never prerequisites.

## When publishing from a private source

Publish a sanitized, standalone copy: no origin banner, no private links, no
project or character names, no "edit it over there" notes.
