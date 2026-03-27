# obsidian-daily

Manage Obsidian Daily Notes via `obsidian-cli`.

## Features

- Create and open daily notes by date
- Append journal entries, tasks, timestamped logs
- Read notes from past dates (supports relative dates like "yesterday", "last Friday")
- Search vault content across all notes
- Support for custom vaults and date formats

## Quick Start

```bash
# Open today's daily note
obsidian-cli daily

# Append a journal entry
obsidian-cli create "$(date +%Y-%m-%d).md" --content "$(printf '\n%s' "- Meeting notes here")" --append

# Read yesterday's note
obsidian-cli print "$(date -d yesterday +%Y-%m-%d).md"

# Search vault
obsidian-cli search-content "keyword"
```

## Requirements

- `obsidian-cli` binary installed
- Obsidian vault configured (local Markdown notes)

## See Also

- [SKILL.md](SKILL.md) — Full documentation with setup and advanced usage
