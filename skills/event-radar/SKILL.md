---
name: event-radar
description: >
  Mapeia eventos tech (conferências, meetups, JUGs, DevFests, CFPs) por ÁREA (Java, IA, cloud, segurança, arquitetura,
  dados, fintech, carreira, GDG, Microsoft, Oracle…) e por REGIÃO (Brasil, América Latina, EUA/Canadá, Europa, online)
  numa janela de meses, com prazo de CFP, chance estimada de aceite e um painel HTML. Raspa fontes públicas por HTTP puro
  (developers.events, confs.tech, javaconferences.org, eventos.cafebugado.com.br, planilha Google) sem navegador, verifica
  prazos direto no Sessionize/PaperCall e orienta a pesquisa paralela por região com subagentes quando a cobertura
  automática não basta. Use SEMPRE que o usuário pedir "mapeia os eventos de X", "quais conferências de Java/IA nos
  próximos 12 meses", "que CFP está aberto", "onde eu posso palestrar / submeter talk", "eventos pra ir em São Paulo",
  "JUGs que aceitam palestrante remoto", "me dá um calendário de eventos", "monta um radar/painel de eventos",
  "quando fecha o CFP do Devoxx", "me avisa dos prazos", ou qualquer variação de descobrir, listar, comparar ou
  monitorar eventos e call for papers. Também aciona em inglês ("tech conferences in Europe next year", "CFP deadlines",
  "where can I speak about Java and AI") e espanhol ("eventos de Java en LATAM").
---

# Event Radar — eventos e CFPs por área e região

## O que esta skill entrega

1. **`events.json` + `summary.md`** com todos os eventos da janela, deduplicados, com região, categorias, prazo de CFP,
   fit (aderência às áreas pedidas), chance estimada de aceite e ação (`submeter` · `so_ir` · `contatar_organizador` ·
   `monitorar_cfp`).
2. **Painel HTML** (`index.html`) com "agir agora", linha do tempo por mês, filtros e tabela ordenável — mesma página para
   qualquer área ou pessoa.
3. **Verificação de prazo na fonte** (`verify-cfp`) para Sessionize, PaperCall e páginas genéricas.
4. **Playbook de pesquisa paralela** por região (subagentes) para cobrir o que os agregadores não têm: JUGs locais, meetups,
   eventos de vendor, DevFests regionais, LatAm.

## Fluxo padrão (siga nesta ordem)

### 1. Entender o pedido em 4 variáveis

| Variável | Pergunte só se não estiver claro | Padrão |
|---|---|---|
| **Áreas** | "java, ai, security…" (lista em `AREAS` no script) | `java,ai` |
| **Regiões** | BR, LATAM, NA, EU, ONLINE, OTHER | todas |
| **Janela** | a partir de quando, quantos meses | hoje + 12 meses |
| **Objetivo** | só ir? submeter talk? os dois? | os dois |

Se a pessoa quer **submeter**, pergunte (ou leve do contexto) quais talks ela tem prontas e qual o track record atual:
isso muda a chance de aceite e a prioridade. Não invente perfil.

### 2. Rodar a coleta automática primeiro

```bash
python scripts/radar.py fetch --areas java,ai,security --regions BR,LATAM,NA,EU,ONLINE --months 12 --out ./radar
python scripts/radar.py panel --out ./radar
python -m http.server 8768 --directory ./radar      # abrir http://localhost:8768 (file:// bloqueia o fetch do JSON)
```

Opções úteis: `--sheet ID[:gid,gid]` (planilha Google pública exportada como CSV), `--extra arquivo.json` (pesquisa manual
ou de agentes no mesmo esquema; pode repetir), `--skip cafebugado`, `--min-fit 25`, `--all-areas` (não filtra por fit).

Leia o `summary.md`: ele diz quais fontes falharam, quantos eventos por região e quais CFPs fecham em 60 dias.

### 3. Completar com pesquisa paralela (quando a cobertura automática não basta)

Os agregadores cobrem bem conferências médias/grandes da Europa e EUA. **Faltam sistematicamente:** JUGs e meetups locais,
DevFests e DevOpsDays regionais, eventos de vendor (Oracle, Microsoft, Google, AWS), LatAm fora das capitais, Brasil fora
de SP, eventos online (Conf42, vJUG, JakartaOne) e tudo que ainda não publicou data (edições do ano seguinte).

Dispare **um subagente por região** com o template `references/fanout-brief-template.md` (schema JSON idêntico ao do
script), peça 40–80 entradas por região, e junte os resultados com `--extra`. Regras que valem para os agentes:

- Verificar no site oficial / Sessionize / cfp.dev antes de afirmar data ou prazo; agregador = `confidence: media`;
  padrão histórico = `date_status: estimado`.
- Datas passadas não entram, exceto como referência para estimar a próxima edição.
- Nada inventado: sem CFP achado → `cfp_status: nao_anunciado`, `cfp_deadline: null`.
- Cota de WebSearch costuma esgotar na metade: priorize fontes oficiais via WebFetch e registre o que ficou sem verificar.

Playbook por região com as fontes que funcionam (e as que exigem navegador): `references/region-playbook.md`.

### 4. Verificar todo prazo antes de dizer "fechou" ou "abre"

```bash
python scripts/radar.py verify-cfp https://sessionize.com/<evento>/ https://www.papercall.io/<evento>
```

Organizadores **estendem prazos**. Um prazo anotado há uma semana pode estar errado nos dois sentidos. Para páginas que
não respondem a HTTP puro (cfp.dev do Devoxx/Voxxed, cfp.ninja, Luma, Oracle Eloqua), use o navegador do usuário
(claude-in-chrome) e leia a página; nunca deduza o status.

### 5. Pontuar e priorizar (revisão humana obrigatória)

O script dá um ponto de partida (`references/schema-and-scoring.md`). Antes de entregar, revise à mão:

- **Fit**: área no nome vale mais que em tag; trilha específica do evento vale mais que o nome.
- **Chance de aceite** para a pessoa hoje: JUG remoto 75–90 · conferência comunitária (TDC, DevFest, JConf) 50–70 ·
  Voxxed/JCON/DevBcn 35–50 · Devnexus/Jfokus/Spring I/O 15–30 · Devoxx BE 5–12 · QCon/GOTO por convite ~5. Sem track
  record internacional, não prometa topo da pirâmide: monte a escada (JUG online → regional → média → grande).
- **Custo**: destaque quem paga viagem/hotel (raro e decisivo). Padrão: só passe.
- **Prioridade**: P1 = submeter/ir sem discussão; P2 = se sobrar banda; P3 = só se estiver no caminho.

### 6. Entregar

- `summary.md` (prazos em 60 dias, P1, próximos 90 dias por região) + painel.
- Sempre liste **o que não foi verificado** (eventos estimados, fontes que falharam). Confiança baixa precisa aparecer.
- Se a pessoa mantém um tracker próprio (JSON), gere no mesmo esquema e deixe o caminho de merge claro (`--extra`).

## Fontes que esta skill usa (HTTP puro, sem login)

| Fonte | Cobre | Observação |
|---|---|---|
| developers.events (`all-events.json`, `all-cfps.json`) | global, tags `topic:`/`tech:`, prazo de CFP | melhor cobertura EU/NA; LatAm e BR fracos |
| confs.tech (`conference-data/conferences/<ano>/<topico>.json`) | global por tópico (java, security, devops, data…) | tem `cfpEndDate` quando conhecido |
| javaconferences.org (README do repo) | Java no mundo, status "(Closed dd Mon yyyy)" | ótimo para a próxima edição + link do CFP |
| eventos.cafebugado.com.br | Brasil (SP pesado), meetups e conferências | o HTML da página 1 embute o JSON de todos os eventos |
| Planilha Google pública | calendários comunitários (ex.: "Eventos 2026/2" de SP) | precisa ser pública; `export?format=csv` |
| Sessionize / PaperCall / páginas de CFP | prazo exato com fuso | `verify-cfp` |

Detalhes, fontes que exigem navegador e truques (paginação MUI do Café Bugado, Luma, cfp.dev): `references/sources.md`.

## Armadilhas aprendidas

- **Prazo anotado no seu tracker ≠ prazo real.** Devnexus 2027 constava "fechado em 22/09"; o Sessionize mostrava aberto até
  30/09. Verifique na fonte antes de afirmar.
- **Dois eventos com o mesmo nome em anos diferentes** não são duplicata; **o mesmo evento com nomes diferentes** (TDC
  Porto Alegre vs. TDCx Porto Alegre, JNation vs. JNation/Commit) é. O script deduplica por nome normalizado + ano; use
  `id` iguais no `--extra` para forçar merge.
- **Tags de agregador superestimam IA**: quase tudo tem `topic:ai` em 2026. O nome do evento pesa mais que a tag.
- **Windows**: o script força UTF-8 no stdout; se um script seu derivado imprimir "→" ou acento sem isso, quebra em cp1252.
- **PaperCall derruba o TLS do urllib**; o script cai para o `curl` do sistema automaticamente.
- **Luma, cfp.dev, cfp.ninja, GDG community, Oracle Eloqua** renderizam por JS: não desperdice tentativas com HTTP puro.
- Subagentes de pesquisa gastam a cota de WebSearch em ~100 buscas; diga a eles para usar WebFetch nas fontes oficiais.
