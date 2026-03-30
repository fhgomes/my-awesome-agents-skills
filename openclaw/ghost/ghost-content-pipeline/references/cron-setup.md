# Configuração de Cron Jobs — OpenClaw + Ghost

## Via OpenClaw Cron (recomendado)

No OpenClaw, cron jobs são configurados no `~/.openclaw/config.yaml`:

```yaml
skills:
  entries:
    ghost-content-pipeline:
      enabled: true
      env:
        GHOST_URL: "https://seu-ghost.com"
        GHOST_ADMIN_API_KEY: "id:secret"
        SERPER_API_KEY: "xxx"
        INDEXNOW_KEY: "xxx"

# Cron jobs
cron:
  # Content Improver — a cada hora
  content-improver:
    schedule: "0 * * * *"
    prompt: |
      Execute o workflow de Content Improver do ghost-content-pipeline:
      1. Busque o post mais antigo sem update
      2. Pesquise PAA data para o tópico do post
      3. Melhore o post seguindo as improvement-rules
      4. Atualize via API
      5. Submeta para indexação

  # New Post Creator — a cada 6 horas
  new-post-creator:
    schedule: "0 */6 * * *"
    prompt: |
      Execute o workflow de criar post novo do ghost-content-pipeline:
      1. Pesquise um tópico no nicho [seu-nicho] que não existe no site
      2. Verifique competição no Google
      3. Gere o conteúdo seguindo o post-template
      4. Publique como draft para revisão

  # Social Distribution — a cada 3 horas
  social-distribute:
    schedule: "0 */3 * * *"
    prompt: |
      Verifique posts recentes não distribuídos em redes sociais.
      Para cada post novo, crie e publique em Twitter e Pinterest.
```

## Via System Cron (alternativa sem OpenClaw daemon)

Se preferir rodar scripts diretamente via crontab do sistema:

```bash
# Editar crontab
crontab -e

# Content Improver — a cada hora
0 * * * * cd /path/to/ghost-content-pipeline && GHOST_URL=xxx GHOST_ADMIN_API_KEY=xxx node scripts/ghost-content-ops.js posts oldest-updated >> /var/log/ghost-improver.log 2>&1

# Ou via Docker Compose (se Ghost roda em container)
0 * * * * docker exec openclaw-agent openclaw run --skill ghost-content-pipeline --workflow content-improver
```

## Via Docker Compose (integrado ao stack do VPS)

Adicionar ao seu `docker-compose.yaml` ou `orquestration-compose.yaml`:

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
    # Rodar com um scheduler interno ou usar supercronic
    depends_on:
      - ghost
```

## Monitoramento

### Logs
```bash
# Ver últimas execuções
tail -f /var/log/ghost-content-pipeline.log

# Contar posts atualizados hoje
grep "$(date +%Y-%m-%d)" /var/log/ghost-improver.log | grep "✅" | wc -l
```

### Notificações (via OpenClaw)
OpenClaw pode enviar notificações via Telegram quando:
- Um post é criado/atualizado com sucesso
- Um erro ocorre na pipeline
- Indexação é submetida

Configure em `~/.openclaw/config.yaml`:
```yaml
notifications:
  telegram:
    enabled: true
    bot_token: "xxx"
    chat_id: "xxx"
```

## Schedule Recomendado

| Job                  | Frequência    | Horário     | Observação |
|---------------------|---------------|-------------|------------|
| Content Improver    | A cada hora   | :00         | 24 posts/dia melhorados |
| New Post Creator    | A cada 6h     | 00,06,12,18 | 4 posts/dia novos |
| Social Pinterest    | A cada 3h     | :30         | Defasado do creator |
| Social Twitter      | A cada 3h     | :45         | Defasado do Pinterest |
| Sitemap Indexing    | 1x/dia        | 02:00       | Batch IndexNow |
| Content Export      | 1x/semana     | Dom 03:00   | Backup |
