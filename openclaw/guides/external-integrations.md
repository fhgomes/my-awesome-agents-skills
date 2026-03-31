# External Integrations

A practical guide to connecting OpenClaw agents with Google, Atlassian, Slack, Discord, and other external services.

---

## 1. Google (Calendar, Sheets, Drive, Docs)

### Authentication -- OAuth 2.0

Google APIs use OAuth 2.0 with a locally stored token that auto-refreshes.

**Setup steps:**

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the APIs you need: Calendar, Sheets, Drive, Docs
3. Create OAuth 2.0 credentials (type: **Desktop app**)
4. Download `client_secret.json`
5. Run the authentication script to generate a token (opens browser for consent)
6. Token auto-refreshes via `refresh_token` -- no manual rotation needed

**Required OAuth scopes:**

| Scope | Purpose |
|-------|---------|
| `calendar.readonly` | Read calendar events |
| `calendar.events` | Create/edit calendar events |
| `spreadsheets` | Read/write Google Sheets |
| `drive.readonly` | List and read Drive files |
| `documents` | Read/write Google Docs |

**Token storage:**
```
~/.openclaw/workspace/google_token.json    # chmod 600
```

Add to `.gitignore` -- tokens should never be committed.

### Google Sheets API

Helper scripts typically wrap the Sheets API:

```bash
# Read a range
python3 google_helper.py sheets read <spreadsheet-id> "Sheet1!A1:D10"

# Write a range
python3 google_helper.py sheets write <spreadsheet-id> "Sheet1!A1" '{"values": [["a","b"],["c","d"]]}'
```

### Google Docs API

Direct API calls (if your helper doesn't support Docs natively):

| Operation | Endpoint |
|-----------|----------|
| Read document | `GET https://docs.googleapis.com/v1/documents/{docId}?includeTabsContent=true` |
| Batch update | `POST https://docs.googleapis.com/v1/documents/{docId}:batchUpdate` |

**Known limitation:** The API does not support programmatic tab creation -- create tabs manually in the browser.

### Google Calendar Integration

Typical workflow for a calendar-aware agent:

1. **Skill reads events** via Calendar API (today's agenda, upcoming meetings)
2. **Cron job** triggers a morning briefing that includes calendar data
3. **Periodic check** (heartbeat or cron) scans for upcoming events and sends reminders

```json
{
  "name": "calendar-reminders",
  "schedule": { "kind": "cron", "expr": "*/15 * * * *", "tz": "America/New_York" },
  "payload": { "kind": "agentTurn", "message": "Check for calendar events in the next 30 minutes and send reminders" }
}
```

---

## 2. Atlassian (Jira & Confluence)

### Authentication -- API Token with Basic Auth

Atlassian Cloud uses API tokens with HTTP Basic Auth.

**Setup steps:**

1. Go to [id.atlassian.com](https://id.atlassian.com) -> Security -> Create API token
2. Add to your `.env` file:
   ```
   ATLASSIAN_EMAIL=your-email@example.com
   ATLASSIAN_TOKEN=your-api-token
   ATLASSIAN_BASE_URL=https://your-domain.atlassian.net
   ```
3. Reference in `openclaw.json` via `${ATLASSIAN_EMAIL}`, `${ATLASSIAN_TOKEN}`, etc.

**Token notes:**
- Atlassian API tokens never expire (unless manually revoked)
- Permissions follow the account's Jira/Confluence permissions
- Basic Auth header: `base64(email:token)`

### Jira -- Useful JQL Queries

```sql
-- My open issues
assignee = currentUser() AND status != Done ORDER BY updated DESC

-- Current sprint
project = MYPROJECT AND sprint in openSprints()

-- Recently created
created >= -7d ORDER BY created DESC

-- High priority bugs
project = MYPROJECT AND type = Bug AND priority in (High, Highest) AND status != Done

-- Unassigned in backlog
project = MYPROJECT AND assignee is EMPTY AND sprint is EMPTY
```

### Jira -- Common API Operations

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Search issues | GET | `/rest/api/3/search?jql=<encoded-jql>` |
| Get issue | GET | `/rest/api/3/issue/<key>` |
| Create issue | POST | `/rest/api/3/issue` |
| Update issue | PUT | `/rest/api/3/issue/<key>` |
| Add comment | POST | `/rest/api/3/issue/<key>/comment` |
| Transition | POST | `/rest/api/3/issue/<key>/transitions` |
| Add worklog | POST | `/rest/api/3/issue/<key>/worklog` |

### Confluence

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Search | GET | `/wiki/rest/api/content/search?cql=<query>` |
| Get page | GET | `/wiki/rest/api/content/<id>?expand=body.storage` |
| Create page | POST | `/wiki/rest/api/content` |
| Update page | PUT | `/wiki/rest/api/content/<id>` |

Confluence body format is **storage format** (XHTML subset), not Markdown. Example:

```json
{
  "type": "page",
  "title": "My Page",
  "space": { "key": "MYSPACE" },
  "body": {
    "storage": {
      "value": "<h1>Hello</h1><p>Content here</p>",
      "representation": "storage"
    }
  }
}
```

---

## 3. Slack

### Authentication -- Bot Token with Socket Mode

Slack uses Bot User OAuth Tokens (xoxb-...) with either Socket Mode or HTTP API.

**Setup steps:**

1. Create an app at [api.slack.com/apps](https://api.slack.com/apps)
2. Add required OAuth Bot Token scopes:
   - `chat:write` -- send messages
   - `channels:read` -- list channels
   - `channels:history` -- read channel messages
   - `reactions:write` -- add emoji reactions
   - `pins:read` -- read pinned messages
   - `users:read` -- look up user info
   - `files:read` -- read uploaded files
3. Enable Socket Mode (simpler -- no public URL needed) or set up an HTTP endpoint
4. Install the app in your workspace
5. Copy the Bot User OAuth Token
6. Add to `.env`:
   ```
   SLACK_BOT_TOKEN=xoxb-your-token-here
   ```

### Socket Mode vs HTTP

| Feature | Socket Mode | HTTP API |
|---------|-------------|----------|
| Public URL needed | No | Yes |
| Firewall friendly | Yes (outbound WebSocket) | Needs inbound HTTPS |
| Latency | Slightly higher | Lower |
| Recommended for | Most OpenClaw deployments | High-traffic production |

### Security Policies

```json
{
  "channels": {
    "slack": {
      "dmPolicy": "allowlist",
      "groupPolicy": "allowlist",
      "allowFrom": ["<your-slack-user-id>"]
    }
  }
}
```

**Rule:** Never use `"open"` on any channel connected to agents with exec or filesystem access. Always use `"allowlist"` and explicitly specify which users can interact with the agent.

---

## 4. Discord

### Authentication -- Bot Token with Gateway Intents

Discord uses bot tokens with WebSocket gateway connections.

**Setup steps:**

1. Create an application at [discord.com/developers/applications](https://discord.com/developers/applications)
2. Navigate to Bot section, create a bot, copy the token
3. Enable required Privileged Gateway Intents:
   - `MESSAGE_CONTENT` -- read message text
   - `GUILD_MEMBERS` -- access member lists
   - `GUILD_PRESENCES` -- see online status
4. Generate an invite URL with appropriate permissions (Administrator = `8` for full access, or granular permissions)
5. Add to `.env`:
   ```
   DISCORD_TOKEN_DEFAULT=your-bot-token-here
   ```

### Multiple Bot Accounts

OpenClaw supports multiple Discord bot accounts per instance. Each bot can be bound to a different agent:

```json
{
  "channels": {
    "discord": {
      "accounts": {
        "default": { "token": "${DISCORD_TOKEN_DEFAULT}" },
        "project-bot": { "token": "${DISCORD_TOKEN_PROJECT}" }
      }
    }
  },
  "bindings": [
    { "agentId": "main", "match": { "channel": "discord", "accountId": "default" } },
    { "agentId": "project-agent", "match": { "channel": "discord", "accountId": "project-bot" } }
  ]
}
```

### Security Policies

```json
{
  "dmPolicy": "allowlist",
  "groupPolicy": "allowlist",
  "allowFrom": ["<your-discord-user-id>"],
  "requireMention": true,
  "allowBots": false,
  "guilds": {
    "<guild-id>": {
      "channels": ["<channel-id-1>", "<channel-id-2>"]
    }
  }
}
```

| Setting | Recommended | Why |
|---------|-------------|-----|
| `dmPolicy` | `"allowlist"` | Only specified users can DM the bot |
| `groupPolicy` | `"allowlist"` | Only whitelisted channels/guilds are active |
| `requireMention` | `true` | In group channels, bot only responds when @mentioned |
| `allowBots` | `false` | Prevents other bots from triggering responses (injection risk) |

### Guild Management Beyond the Message Tool

The `message` tool does **not** support: `role-create`, `role-edit`, `role-delete`, `channel-create`, `channel-delete`, or guild settings changes.

For these operations, use a helper script that calls the Discord REST API v10 directly:

```python
# Example: discord_api.py
# Called via exec tool
python3 discord_api.py role-create <guild_id> <name> --color 0xFF0000 --hoist
python3 discord_api.py channel-create <guild_id> <name> --type text
```

**Important:** Set `User-Agent: DiscordBot (https://your-site.com, 1.0)` in HTTP headers. Python's default urllib User-Agent is blocked by Cloudflare.

---

## 5. WhatsApp

OpenClaw supports WhatsApp channels. Configuration is done via the OpenClaw Control UI rather than JSON editing. The agent's workspace policies (DM allowlist, group rules) apply the same as other channels.

---

## 6. General Best Practices

### Secrets Management

All tokens and API keys belong in `.env`, never in `openclaw.json`:

```
# ~/.openclaw/.env (chmod 600)
DISCORD_TOKEN_DEFAULT=MTQ3...
SLACK_BOT_TOKEN=xoxb-...
ATLASSIAN_EMAIL=user@example.com
ATLASSIAN_TOKEN=ATATT3x...
GOOGLE_CLIENT_ID=123456...
```

Reference in JSON using `${VAR}` syntax:
```json
"token": "${DISCORD_TOKEN_DEFAULT}"
```

OpenClaw substitutes `${VAR}` automatically from environment variables loaded via systemd's `EnvironmentFile`.

### Token Lifecycle

| Service | Expiration | Rotation |
|---------|------------|----------|
| Google OAuth | Auto-refreshes via refresh_token | Rarely needs manual rotation |
| Atlassian API Token | Never expires | Revoke/recreate if compromised |
| Discord Bot Token | Never expires | Reset in Developer Portal if compromised |
| Slack Bot Token | Never expires | Rotate in App settings if compromised |

### Rate Limits

| Service | Limit | Recommended |
|---------|-------|-------------|
| Google Sheets | 100 requests / 100 seconds / user | Batch reads/writes |
| Jira API | 10 requests / second (Cloud) | Sequential with small delays |
| Slack | ~1 request / second / method | Max 3 parallel sends |
| Discord | ~5 messages / 5 seconds / channel | Max 3 parallel sends |
| Confluence | Similar to Jira | Sequential |

### Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| `401` / `403` | Invalid or expired token | Inform user, do not retry in a loop |
| `429` | Rate limit exceeded | Wait for `Retry-After` header value, then retry |
| `5xx` | Server error | Retry once after 5 seconds, then inform user |
| Network timeout | Service unreachable | Retry once, then report the failure |

**Critical anti-pattern:** Never retry 401/403 errors in a loop. The token is invalid -- retrying will just burn rate limit quota and block the agent.

### Helper Script Pattern

For integrations that the native tools don't cover, build helper scripts:

```bash
#!/bin/bash
# ~/.openclaw/workspace/helpers/my-integration.sh
set -euo pipefail

ACTION="${1:?Usage: $0 <action> [args...]}"
TOKEN="${MY_API_TOKEN:?Missing MY_API_TOKEN in .env}"
BASE_URL="${MY_API_BASE:?Missing MY_API_BASE in .env}"

case "$ACTION" in
  list)
    curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/items" | python3 -m json.tool
    ;;
  get)
    curl -sf -H "Authorization: Bearer $TOKEN" "$BASE_URL/items/${2:?Missing item ID}" | python3 -m json.tool
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    exit 1
    ;;
esac
```

Call from the agent via the `exec` tool:
```
exec bash ~/.openclaw/workspace/helpers/my-integration.sh list
```
