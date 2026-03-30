---
name: ghost-selfhost-admin
description: >
  Administração completa de instância Ghost CMS self-hosted via Admin API e Playwright.
  Use SEMPRE que precisar: configurar Ghost (título, descrição, logo, favicon, social links, 
  timezone, language), gerenciar temas (upload, ativar, preview, customizar design settings), 
  configurar SEO (meta tags, Open Graph, Twitter cards, structured data), gerenciar navigation 
  menus, code injection (header/footer scripts), configurar newsletters e email (Mailgun/SMTP), 
  gerenciar members e tiers, configurar Portal (signup/signin), upload de imagens, gerenciar 
  integrações e API keys, configurar routes.yaml, gerenciar staff users e roles, 
  configurar Labs features, ou qualquer variação de "configurar meu Ghost", "mudar o tema", 
  "ajustar SEO", "adicionar script no header". Também acione quando o usuário mencionar: 
  "ghost admin", "ghost settings", "ghost theme", "ghost config", "code injection", 
  "ghost newsletter", "ghost members", "ghost portal", "ghost routes".
metadata:
  openclaw:
    emoji: "👻"
    requires:
      env: ["GHOST_URL", "GHOST_ADMIN_API_KEY"]
      binaries: ["node", "npx"]
    primaryEnv: "GHOST_ADMIN_API_KEY"
    files: ["scripts/*"]
---

# Ghost Self-Host Admin

Skill especialista em administração de instância Ghost CMS self-hosted.
Combina Ghost Admin API (para operações programáticas) com Playwright (para configurações que só existem na UI admin).

## Arquitetura de Dois Canais

### Canal 1: Ghost Admin API (preferencial)
Para tudo que a API suporta. Mais rápido, confiável, scriptável.

**Endpoints disponíveis:**
- `POST/PUT/GET/DELETE /posts/` — CRUD de posts
- `POST/PUT/GET/DELETE /pages/` — CRUD de pages
- `GET/PUT /settings/` — Site settings (título, descrição, etc.)
- `POST /images/upload/` — Upload de imagens
- `POST /themes/upload/` — Upload de temas (zip)
- `PUT /themes/{name}/activate/` — Ativar tema
- `POST/PUT/GET/DELETE /tags/` — CRUD de tags
- `GET/PUT /users/` — Gerenciar users
- `POST/PUT/GET/DELETE /members/` — CRUD de members
- `POST/PUT/GET/DELETE /newsletters/` — CRUD de newsletters
- `POST/PUT/GET/DELETE /tiers/` — CRUD de tiers
- `POST/PUT/GET/DELETE /offers/` — CRUD de offers
- `POST/PUT/GET/DELETE /webhooks/` — CRUD de webhooks
- `GET /site/` — Info do site

### Canal 2: Playwright (fallback para UI-only)
Para configurações que NÃO têm endpoint na API estável.

**Operações UI-only que requerem Playwright:**
- Design settings (cores, tipografia, brand)
- Code injection (header/footer)
- Navigation menus (primary/secondary)
- Portal settings (signup form, plans, button style)
- Email settings (Mailgun config, from address)
- Labs features toggles
- Routes.yaml editor
- Custom theme settings
- Social accounts configuration
- Analytics/tracking settings

## Pré-requisitos

### Obrigatórios
```bash
# Variáveis de ambiente
GHOST_URL=https://seu-ghost.com        # URL da instância Ghost
GHOST_ADMIN_API_KEY=id:secret          # Admin API key (Settings > Integrations)
```

### Para operações Playwright (UI-only)
```bash
GHOST_ADMIN_EMAIL=admin@seu-ghost.com  # Email do admin
GHOST_ADMIN_PASSWORD=sua-senha         # Senha do admin
```

### Setup inicial
```bash
# Instalar dependências
cd $SKILL_DIR && npm run setup

# Verificar conexão com Ghost
cd $SKILL_DIR && node scripts/ghost-api-check.js
```

## Workflows

### 1. Configuração Inicial do Site
Quando o usuário quer configurar um Ghost do zero ou reconfigurar:

```
1. Verificar conexão → scripts/ghost-api-check.js
2. Configurar settings básicos via API:
   - Título, descrição, timezone, language
   - Meta title, meta description
   - Social links (Twitter, Facebook)
3. Upload de logo e favicon via API → POST /images/upload/
4. Configurar navigation via Playwright → playbooks/configure-navigation.md
5. Configurar code injection via Playwright → playbooks/code-injection.md
```

### 2. Gerenciamento de Temas
```
1. Listar temas instalados → GET /themes/
2. Upload de tema (arquivo .zip) → POST /themes/upload/
3. Ativar tema → PUT /themes/{name}/activate/
4. Configurar design settings via Playwright → playbooks/theme-design.md
5. Configurar custom theme settings via Playwright → playbooks/theme-custom-settings.md
```

### 3. SEO e Meta Tags
```
1. Configurar meta title/description globais via API → PUT /settings/
2. Configurar OG/Twitter cards por post → PUT /posts/{id}/
3. Code injection para structured data → playbooks/code-injection.md
4. Verificar robots.txt e sitemap → GET {GHOST_URL}/robots.txt
```

### 4. Newsletter e Email Setup
```
1. Criar/editar newsletters via API → POST/PUT /newsletters/
2. Configurar Mailgun/SMTP via Playwright → playbooks/email-config.md
3. Configurar sender name/email via API → PUT /newsletters/{id}/
4. Testar envio
```

### 5. Members e Monetização
```
1. Configurar tiers via API → POST/PUT /tiers/
2. Criar offers via API → POST /offers/
3. Configurar Portal via Playwright → playbooks/portal-config.md
4. Gerenciar members via API → POST/PUT/DELETE /members/
```

### 6. Integrações e Webhooks
```
1. Criar integração via Playwright → playbooks/create-integration.md
2. Configurar webhooks via API → POST /webhooks/
3. Gerenciar API keys
```

## Referências

- Para detalhes da Ghost Admin API → `references/ghost-admin-api.md`
- Para scripts de automação Playwright → `references/playwright-recipes.md`
- Para JWT token generation → `references/jwt-auth.md`
- Para troubleshooting comum → `references/troubleshooting.md`

## Regras de Ouro

1. **API primeiro, Playwright segundo** — sempre prefira a API quando disponível
2. **Backup antes de mudanças destrutivas** — exportar content antes de bulk operations
3. **Validar tema antes de ativar** — usar gscan localmente se possível
4. **Nunca expor API keys** — usar variáveis de ambiente, nunca hardcode
5. **Respeitar rate limits** — a Ghost Admin API não documenta limites explícitos, mas evite burst requests
6. **Testar em staging primeiro** — se disponível, testar mudanças de tema/design em ambiente separado
