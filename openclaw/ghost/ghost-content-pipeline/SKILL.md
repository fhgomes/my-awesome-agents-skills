---
name: ghost-content-pipeline
description: >
  Pipeline automatizado de criação, publicação e otimização de conteúdo no Ghost CMS.
  Use SEMPRE que precisar: criar posts automaticamente, agendar publicações, melhorar posts 
  existentes com SEO, gerar imagens para posts, distribuir conteúdo em redes sociais,
  submeter para indexação (Google/Bing/IndexNow), monitorar performance de conteúdo,
  fazer bulk operations em posts (atualizar tags, meta descriptions, feature images em massa),
  criar content calendar, ou qualquer variação de "publicar no Ghost", "automatizar posts", 
  "melhorar SEO dos posts", "criar conteúdo", "pipeline de conteúdo". Também acione quando 
  o usuário mencionar: "cron job ghost", "auto publish", "content automation", "ghost posts", 
  "ghost SEO", "indexnow", "google indexing", "bulk update posts", "content calendar",
  "repurpose content", "social media automation ghost".
metadata:
  openclaw:
    emoji: "📝"
    requires:
      env: ["GHOST_URL", "GHOST_ADMIN_API_KEY"]
      binaries: ["node"]
    primaryEnv: "GHOST_ADMIN_API_KEY"
    files: ["scripts/*"]
---

# Ghost Content Pipeline

Pipeline automatizado para criação, publicação, otimização e distribuição de conteúdo em Ghost CMS self-hosted. Projetado para rodar como cron jobs ou ser invocado por agentes.

## Dependências

### Obrigatórias
```bash
GHOST_URL=https://seu-ghost.com
GHOST_ADMIN_API_KEY=id:secret
```

### Opcionais (por feature)
```bash
# SEO Research
SERPER_API_KEY=xxx              # Google SERP data (serper.dev)

# Indexação
GOOGLE_INDEXING_KEY_FILE=/path  # Google Indexing API service account
INDEXNOW_KEY=xxx                # IndexNow API key

# Geração de imagens
OPENAI_API_KEY=xxx              # DALL-E
IDEOGRAM_API_KEY=xxx            # Ideogram
# ou qualquer API de imagem configurada

# Distribuição social
TWITTER_BEARER_TOKEN=xxx        # X/Twitter API
PINTEREST_TOKEN=xxx             # Pinterest API
```

### Setup
```bash
cd $SKILL_DIR && npm install
```

## Workflows

### 1. Criar e Publicar Post Novo

Pipeline completo de criação de conteúdo:

```
1. Pesquisar tópico
   → scripts/content-research.js --topic="tema" --check-competition
   Saída: { keyword, difficulty, paa_questions[], related_topics[], existing_posts[] }

2. Verificar se já existe no site
   → scripts/ghost-content-ops.js posts search --query="tema"
   Se existe: abortar ou sugerir atualização

3. Gerar conteúdo
   → O agente (LLM) gera o HTML do post seguindo o template em references/post-template.md
   Input: pesquisa do passo 1
   Output: { title, html, meta_title, meta_description, tags[], custom_excerpt }

4. Gerar feature image (opcional)
   → scripts/generate-image.js --prompt="..." --output=/tmp/feature.webp
   → scripts/ghost-content-ops.js images upload --file=/tmp/feature.webp

5. Publicar
   → scripts/ghost-content-ops.js posts create --json='{...}'
   Status: "published" (imediato) ou "scheduled" com published_at

6. Submeter para indexação
   → scripts/submit-indexing.js --url="https://seu-ghost.com/novo-post/"

7. Distribuir em redes sociais (opcional)
   → scripts/social-distribute.js --post-url="..." --platforms=twitter,pinterest
```

### 2. Melhorar Post Existente (Content Improver)

Para rodar como cron job, melhorando o post mais antigo a cada execução:

```
1. Buscar post mais antigo/desatualizado
   → scripts/ghost-content-ops.js posts list --order=updated_at+asc --limit=1 --status=published

2. Analisar qualidade atual
   → scripts/content-analyzer.js --url="post-url" --check-seo --check-readability
   Saída: { score, missing_h2s, missing_faq, word_count, missing_images, suggestions[] }

3. Pesquisar dados frescos
   → scripts/content-research.js --topic="post-topic" --paa-only
   Saída: { paa_questions[], fresh_data }

4. Gerar versão melhorada (via LLM)
   Regras: references/improvement-rules.md
   - Manter URL/slug original
   - Adicionar FAQ com PAA data real
   - Melhorar estrutura de H2s
   - Adicionar internal links
   - Melhorar meta description

5. Gerar novas imagens se necessário
   → scripts/generate-image.js + upload

6. Atualizar post
   → scripts/ghost-content-ops.js posts update --id=xxx --json='{...}'

7. Resubmeter para indexação
   → scripts/submit-indexing.js --url="post-url"
```

### 3. Bulk Operations

Para operações em massa em posts existentes:

```
# Atualizar meta descriptions de todos os posts sem meta
→ scripts/ghost-content-ops.js posts list --filter="meta_description:null" --limit=all
→ Para cada: gerar meta description via LLM → update

# Adicionar tag a posts por filtro
→ scripts/ghost-content-ops.js posts bulk-tag --filter="tag:-optimized" --add-tag="optimized"

# Reprocessar todas as feature images para WebP
→ scripts/ghost-content-ops.js posts list --fields=id,feature_image --limit=all
→ Para cada: baixar → converter WebP → re-upload → update post

# Gerar custom_excerpt para posts sem excerpt
→ scripts/ghost-content-ops.js posts list --filter="custom_excerpt:null" --limit=all
→ Para cada: extrair primeiro parágrafo → gerar excerpt via LLM → update
```

### 4. Content Calendar

Planejamento e agendamento de conteúdo:

```
1. Gerar calendario de tópicos
   → scripts/content-research.js --generate-calendar --weeks=4 --niche="seu-nicho"
   Saída: calendar.json com tópicos, datas, keywords

2. Para cada item do calendário:
   → Executar workflow "Criar e Publicar Post Novo"
   → Usar status "scheduled" com published_at do calendário

3. Monitorar publicações agendadas
   → scripts/ghost-content-ops.js posts list --status=scheduled --order=published_at+asc
```

## Estrutura de Post Recomendada

Ver `references/post-template.md` para o template completo. Resumo:

```html
<!-- Answer Capsule (featured snippet bait) -->
<div class="answer-capsule">
  <p><strong>Resposta rápida:</strong> ...</p>
</div>

<!-- H2s como perguntas reais do usuário -->
<h2>O que é [tópico]?</h2>
<p>...</p>

<h2>Como [ação] funciona?</h2>
<p>...</p>

<!-- Tabela comparativa -->
<table>...</table>

<!-- FAQ com PAA data real -->
<h2>Perguntas Frequentes</h2>
<h3>Pergunta real do Google PAA?</h3>
<p>Resposta...</p>

<!-- Internal links -->
<h2>Leia também</h2>
<ul>
  <li><a href="/post-relacionado/">Título</a></li>
</ul>
```

## Shared Library

Content ops scripts import JWT/HTTP utilities from the selfhost-admin shared lib:
```
require('../../ghost-selfhost-admin/lib/ghost-api')
```

## Referências

- Template de post otimizado → `references/post-template.md`
- Regras de melhoria de conteúdo → `references/improvement-rules.md`
- Configuração de cron jobs → `references/cron-setup.md`
- Ghost Admin API reference → `../ghost-selfhost-admin/references/ghost-admin-api.md`

## Integração com Celebrity Dev Agent Team

Este skill é o motor do **Content Pipeline sub-team** do Celebrity Dev:
- **Topic Scout** usa `content-research.js` para descobrir tópicos
- **SEO Optimizer** usa `content-analyzer.js` para audit e melhorias
- **Long-form/Short-form Draft Writers** produzem conteúdo seguindo `post-template.md`
- **Repurposer** usa `social-distribute.js` para distribuição
- **Visual Director** usa `generate-image.js` para assets visuais

O Brand Voice Guardian e Content Strategist (Claude API) validam o output antes de publicar.

## Regras de Ouro

1. **Nunca publicar sem revisar** — drafts primeiro, publish depois de validação
2. **PAA data real, não inventada** — usar Serper/SERP API para FAQs
3. **Imagens otimizadas** — sempre WebP, max 1280px, < 200KB
4. **Internal linking** — todo post deve linkar para pelo menos 2 posts relacionados
5. **updated_at obrigatório** — Ghost requer para conflict detection em updates
6. **Rate limit social** — respeitar limites das APIs de redes sociais
7. **Monitorar indexação** — verificar se posts foram indexados após submissão
8. **Backup antes de bulk ops** — exportar content antes de operações em massa
