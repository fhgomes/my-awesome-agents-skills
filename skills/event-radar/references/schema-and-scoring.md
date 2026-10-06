# Esquema unificado e rubrica de pontuação

## Esquema (um objeto por evento no `events.json`)

| Campo | Valores | Observação |
|---|---|---|
| `id` | slug-ano | estável; `--extra` com o mesmo `id` força merge |
| `name` | texto | nome oficial, com ano se for edição |
| `region` | `BR` · `LATAM` · `NA` · `EU` · `ONLINE` · `OTHER` | derivado de país/cidade/local; `ONLINE` se formato online |
| `location` | "Cidade, País" ou "online" | |
| `format` | `presencial` · `online` · `hibrido` | |
| `date`, `date_end` | ISO `YYYY-MM-DD` ou `null` | `YYYY-MM` aceito quando só o mês é conhecido |
| `date_status` | `confirmado` · `estimado (padrão histórico)` · `rolling` · `desconhecido` | `rolling` = meetup/podcast/programa sem data fixa |
| `organizer` | texto | |
| `category[]` | `java, jvm, jug, ai, cloud, devops, security, architecture, data, fintech, career, gdg, microsoft, oracle, meetup, podcast, program, general-dev` | |
| `url`, `cfp_url` | links | |
| `cfp_status` | `aberto` · `fechado` · `nao_anunciado` · `estimado` · `sem_cfp` · `convite` · `contatar` · `aceito` · `desconhecido` | `contatar` = JUG/meetup sem CFP formal |
| `deadline`, `deadline_status` | ISO + `confirmado`/`estimado`/`desconhecido` | sempre com fuso nas notas quando vier do Sessionize |
| `speaker_perks` | `viagem+hotel` · `hotel` · `passe` · `nada` · `desconhecido` | decisivo para priorizar |
| `cost` | texto livre | custo para a pessoa |
| `talk_fit[]` | ids das talks da pessoa | opcional |
| `adherence` (0-100), `adherence_why` | fit | |
| `acceptance` (0-100), `acceptance_why` | chance estimada **para a pessoa hoje** | |
| `prestige`, `competition` | 1-5 | renome do evento; concorrência no CFP |
| `action` | `submeter` · `so_ir` · `monitorar_cfp` · `contatar_organizador` · `ignorar` · `feito` | |
| `priority` | `P1` · `P2` · `P3` | |
| `status` | texto | situação da pessoa (submetido, aceito, confirmado…) |
| `notes`, `tags[]`, `sources[]` | | `sources` sempre com URL ou nome da fonte |
| `confidence` | `alta` (site oficial/Sessionize lido hoje) · `media` (agregador) · `baixa` (estimativa) | |
| `verified_on` | ISO | |

Campos de entrada aceitos no `--extra` e mapeados: `start_date→date`, `end_date→date_end`, `cfp_deadline→deadline`,
`cfp_deadline_status→deadline_status`, `fit_score→adherence`, `accept_prob→acceptance`, `accept_rationale→acceptance_why`,
`city`+`country→location`.

## Como o script pontua (ponto de partida, não veredito)

**Fit** = soma por área pedida: área no **nome** do evento +45, área só em tag/local/notas +25; teto 100; nenhuma área = 10.
Com `--min-fit 40` (padrão) um evento precisa ter pelo menos uma área no nome ou duas em tags para entrar.

**Chance de aceite** = base por porte (regex no nome) ± 10 pelo fit:

| Porte | Exemplos | Prestígio | Concorrência | Base |
|---|---|---|---|---|
| Top-tier / convite | Devoxx Belgium, JavaOne, QCon, GOTO, KubeCon, Google I/O, Build, re:Invent, Web Summit | 5 | 5 | 8 |
| Grande | Spring I/O, Devnexus, Jfokus, JavaLand, JavaZone, Devoxx UK/FR/PL, AI Engineer, NDC Oslo/London, LeadDev | 4 | 4 | 20 |
| Média | Voxxed Days, JCON, J-Fall, jPrime, GeeCON, JNation, DevBcn, Java Day, JAX, Øredev, BaselOne, NDC regionais, ConFoo, CodeMash, KCDC, Devoxx Greece/Morocco, JConf, Nerdearla | 3 | 3 | 35 |
| Comunitária | TDC, Codecon, DevFest, DevOpsDays, KCD, Conf42, Agile Trends, JakartaOne | 3 | 3 | 50 |
| JUG / meetup / live | qualquer "JUG", "meetup", "user group", "community", "webinar", vJUG | 1 | 1 | 80 |
| Não classificado | — | 2 | 2 | 45 |

**Ação**: CFP aberto → `submeter`; fechado → `so_ir`; convite/contatar → `contatar_organizador`; sem CFP e porte JUG →
`contatar_organizador`, senão `so_ir`; prazo estimado/não anunciado → `monitorar_cfp`.

**Prioridade**: `P1` se fit ≥ 70 e chance ≥ 45; `P2` se fit ≥ 50; senão `P3`.

## Revisão humana (obrigatória antes de entregar)

1. **Track record da pessoa** muda tudo: aceite recorrente num circuito (ex.: TDC) sobe a base daquele circuito para 60–70;
   zero palestra internacional presencial mantém Devoxx BE em ≤ 12 mesmo com fit 95.
2. **Trilhas**: leia as trilhas do ano (elas mudam). Fit real = trilha que recebe a talk, não o nome do evento.
3. **Formato do CFP**: "uma proposta por pessoa" (DevPR) ou "trilha única com 7 vagas" derruba a chance; "10 trilhas, 100+
   sessões" (Devnexus) sobe; "até 5 propostas" (GIDS, Dutch AI) sobe.
4. **Custo real**: evento que paga viagem+hotel vale P1 mesmo com chance 20; evento que não paga nada do outro lado do
   oceano com chance 30 é P2/P3 a não ser que já esteja na rota.
5. **Escada**: sem histórico internacional, a sequência que funciona é JUG online em inglês → conferência regional/LatAm
   → Voxxed/JCON/DevBcn → Devnexus/Jfokus/Spring I/O → Devoxx BE. Diga isso em vez de prometer o topo.
6. **Regra dos 3**: em CFP multi-trilha, 2–3 propostas em trilhas diferentes dobram a chance sem dobrar o esforço.
7. **Registrar o desfecho** (submetido/aceito/recusado) no tracker da pessoa; CFP fechado sem submissão = chance 0 por
   definição e vira `feito`/`perdido`, não fica como "aberto" para sempre.
