# CLAUDE.md — rules for working in this repository

This repository is **public**. Everything committed here is visible to anyone.
These rules exist to keep it useful to strangers and safe for its author.
They apply to Claude Code and to any other agent editing this repo (see
[AGENTS.md](AGENTS.md), which is the same contract in vendor-neutral form).

## 1. English only

- All content is written in **English**: skill names and folder names, SKILL.md
  frontmatter and body, references, READMEs, code comments, docstrings, CLI
  help, printed messages, commit messages.
- Trigger phrases in a skill `description:` are English. If a skill should also
  fire on other languages, end the description with
  "Also triggers on the equivalent phrases in other languages." — do not list
  them.
- If a source you are porting is in another language, translate it before
  committing. Never commit a file "to translate later".

## 2. No personal or machine-specific data

Skills describe **procedures**; they must run unchanged on any machine.
Machine facts belong in the agent's memory on that machine, not here.

Never commit:

- Real names of people other than credited open-source authors (no
  interviewees, colleagues, family members, clients, private characters or
  project code names).
- Personal filesystem paths: `C:\Users\<name>`, `/mnt/c/Users/<name>`,
  `/home/<name>`, session scratchpad IDs, private drive letters. Use
  placeholders (`/path/to/input.mp4`, `C:\Users\<you>\...`) or variables.
- Hardware ownership or inventory ("my GPU", "a family member's laptop",
  driver versions). Describe hardware as an example class: "a 4 GB Turing
  card".
- Private repo names, vault folder structures, internal hostnames, IPs,
  e-mails, phone numbers, IDs, credentials, tokens, `.env` contents.
- Verbatim conversation or footage content from private or published
  recordings. Lessons yes, transcripts no.
- Production scripts with real inputs. Publish a **parameterized example** with
  placeholder variables instead.

Taste and review verdicts are fine as anonymous facts ("a review with a human
viewer rated…"), never attributed to a named person.

## 3. Security pass before every commit

Run both bundled auditors on the whole tree and read their output. They are
stdlib-only and take seconds:

```bash
python skills/redact/scripts/scan_secrets.py . --history --severity medium
python skills/warden/scripts/scan_tree.py . --min-score 3
```

- `redact` answers "if this is public, what leaks?" (secrets, PII, internal
  infra, in the working tree **and git history**).
- `warden` answers "is anything here malicious or suspicious?" (obfuscation,
  droppers, exec of decoded payloads).

Then do the manual pass the scanners cannot: grep for first names, user paths,
and the phrases listed in section 2. Fix findings before committing; never
commit with an unexplained high/critical finding. Documentation examples
(the official AWS example key, gateway test card numbers) are the known
accepted findings.

Anything that reached a public commit must be treated as leaked: rotate
secrets, then remove, then rewrite history if it matters
(`skills/redact/references/history-rewrite.md`).

## 4. Skill structure

Every item is self-contained (see README.md). A skill folder has:

```
skills/<kebab-case-name>/
  SKILL.md        # frontmatter: name (matches folder), description (triggers)
  README.md       # Purpose, Features, Quick Start, See Also
  references/     # optional, loaded on demand
  scripts/        # optional, must run without machine-specific constants
  assets/         # optional, small binary assets
  examples/       # optional, parameterized and anonymized
```

Scripts resolve binaries from PATH or an environment variable
(e.g. `FFMPEG_BIN`), never from a hardcoded absolute path.

## 5. Commits and git

- Conventional Commits in English:
  `feat(video-editing): add xfade catalog`, `fix(redact): ...`,
  `docs: ...`, `chore: ...`, `refactor: ...`, `security: ...`.
- One logical change per commit. Describe *what* and *why*, not the session.
- Never commit, push or open a PR unless the user asks. When they do, run the
  section 3 pass first.
- Do not rewrite public history on your own initiative; propose it and let the
  user decide.

## 6. Publishing from a private source

When a skill is maintained elsewhere and published here, publish a
**sanitized copy**: strip the private origin banner, private repo links,
character/project names, and any "edit it over there" instructions. The
published copy must stand alone.
