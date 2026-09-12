# Cron Job Setup — OpenClaw + Ghost

## Via OpenClaw Cron (recommended)

In OpenClaw, cron jobs are configured in `~/.openclaw/config.yaml`:

```yaml
skills:
  entries:
    ghost-content-pipeline:
      enabled: true
      env:
        GHOST_URL: "https://your-ghost.com"
        GHOST_ADMIN_API_KEY: "id:secret"
        SERPER_API_KEY: "xxx"
        INDEXNOW_KEY: "xxx"

# Cron jobs
cron:
  # Content Improver — every hour
  content-improver:
    schedule: "0 * * * *"
    prompt: |
      Run the ghost-content-pipeline Content Improver workflow:
      1. Fetch the oldest post without an update
      2. Research PAA data for the post's topic
      3. Improve the post following the improvement-rules
      4. Update it via the API
      5. Submit it for indexing

  # New Post Creator — every 6 hours
  new-post-creator:
    schedule: "0 */6 * * *"
    prompt: |
      Run the ghost-content-pipeline new-post workflow:
      1. Research a topic in the [your-niche] niche that does not exist on the site yet
      2. Check the competition on Google
      3. Generate the content following the post-template
      4. Publish it as a draft for review

  # Social Distribution — every 3 hours
  social-distribute:
    schedule: "0 */3 * * *"
    prompt: |
      Check recent posts not yet distributed on social networks.
      For each new post, create and publish on Twitter and Pinterest.
```

## Via System Cron (alternative without the OpenClaw daemon)

If you prefer to run the scripts directly from the system crontab:

```bash
# Edit the crontab
crontab -e

# Content Improver — every hour
0 * * * * cd /path/to/ghost-content-pipeline && GHOST_URL=xxx GHOST_ADMIN_API_KEY=xxx node scripts/ghost-content-ops.js posts oldest-updated >> /var/log/ghost-improver.log 2>&1

# Or via Docker Compose (if Ghost runs in a container)
0 * * * * docker exec openclaw-agent openclaw run --skill ghost-content-pipeline --workflow content-improver
```

## Via Docker Compose (integrated into the VPS stack)

Add to your `docker-compose.yaml` or `orquestration-compose.yaml`:

```yaml
services:
  ghost-cron:
    image: node:22-slim
    volumes:
      - ./ghost-content-pipeline:/app
    working_dir: /app
    environment:
      - GHOST_URL=${GHOST_URL}
      - GHOST_ADMIN_API_KEY=${GHOST_ADMIN_API_KEY}
      - SERPER_API_KEY=${SERPER_API_KEY}
      - INDEXNOW_KEY=${INDEXNOW_KEY}
    entrypoint: ["node"]
    # Run with an internal scheduler or use supercronic
    depends_on:
      - ghost
```

## Monitoring

### Logs
```bash
# Tail the latest runs
tail -f /var/log/ghost-content-pipeline.log

# Count posts updated today
grep "$(date +%Y-%m-%d)" /var/log/ghost-improver.log | grep "✅" | wc -l
```

### Notifications (via OpenClaw)
OpenClaw can send Telegram notifications when:
- A post is created/updated successfully
- An error occurs in the pipeline
- Indexing is submitted

Configure in `~/.openclaw/config.yaml`:
```yaml
notifications:
  telegram:
    enabled: true
    bot_token: "xxx"
    chat_id: "xxx"
```

## Recommended Schedule

| Job                  | Frequency     | Time        | Notes |
|---------------------|---------------|-------------|------------|
| Content Improver    | Every hour    | :00         | 24 posts/day improved |
| New Post Creator    | Every 6h      | 00,06,12,18 | 4 new posts/day |
| Social Pinterest    | Every 3h      | :30         | Offset from the creator |
| Social Twitter      | Every 3h      | :45         | Offset from Pinterest |
| Sitemap Indexing    | 1x/day        | 02:00       | Batch IndexNow |
| Content Export      | 1x/week       | Sun 03:00   | Backup |
