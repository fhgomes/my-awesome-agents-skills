# Template de brief para pesquisa paralela (um subagente por região)

Salve como `BRIEF.md` numa pasta de trabalho, preencha os `{…}`, e dispare um agente por região com o escopo específico
(lista de eventos a verificar + fontes). Cada agente grava `{regiao}.json` (array no schema abaixo) e `{regiao}.md`
(quantos, 10 destaques, CFPs em 60 dias, o que não conseguiu verificar). Junte tudo com
`python radar.py fetch ... --extra br.json --extra eu.json --extra na.json --extra latam.json --extra online.json`.

---

# BRIEF — Mapeamento de eventos tech ({data_inicio} → {data_fim})

## Para quem
{Nome/perfil público: área, senioridade, cidade. Track record real de palestras (eventos, datas, se foi por CFP ou convite).
Idiomas. Zero/alguma experiência internacional. NÃO inclua dados pessoais além do perfil público de palestrante.}

## Arsenal de talks (o que pode submeter)
- **T1** — {título} ({stack}, estado: pronta/rascunho, idiomas). Trilhas onde cabe: {…}
- **T2** — …

## Interesses declarados (para "só ir")
{áreas: Java, IA aplicada, GDG/DevFest, Microsoft, Oracle, Codecon, TDC, fintech dev…}

## Janela
Eventos com data entre **{data_inicio} e {data_fim}**, OU cujo **CFP tenha prazo nessa janela** (mesmo que o evento seja
depois — INCLUIR).

## O que registrar por evento (JSON, um objeto por evento, campos EXATAMENTE assim)
```json
{
  "id": "slug-curto-ano",
  "name": "Nome oficial",
  "region": "BR | LATAM | NA | EU | ONLINE | OTHER",
  "country": "BR", "city": "São Paulo",
  "format": "presencial | online | hibrido",
  "start_date": "YYYY-MM-DD ou null", "end_date": "YYYY-MM-DD ou null",
  "date_status": "confirmado | estimado (padrão histórico) | desconhecido",
  "organizer": "quem organiza",
  "category": ["java","jvm","ai","cloud","devops","gdg","microsoft","oracle","general-dev","fintech","career","meetup","jug","security","architecture"],
  "url": "site oficial", "cfp_url": "url do CFP ou null",
  "cfp_status": "aberto | fechado | nao_anunciado | sem_cfp (só ir) | convite/curadoria | estimado | contatar",
  "cfp_open_date": "YYYY-MM-DD ou null", "cfp_deadline": "YYYY-MM-DD ou null",
  "cfp_deadline_status": "confirmado | estimado | desconhecido",
  "speaker_perks": "viagem+hotel | hotel | passe | nada | desconhecido",
  "size": "pequeno (<200) | medio (200-1000) | grande (1000-3000) | enorme (>3000)",
  "ticket": "gratis | pago (valor aprox) | desconhecido",
  "talk_fit": ["T1","T3"],
  "fit_score": 0-100,
  "prestige": 1-5,
  "competition": 1-5,
  "accept_prob": 0-100,
  "accept_rationale": "1 frase: por que essa probabilidade",
  "action": "submeter | so_ir | monitorar_cfp | contatar_organizador | ignorar",
  "priority": "P1 | P2 | P3",
  "notes": "trilhas, formato, idioma, custo, observações",
  "sources": ["url1","url2"],
  "confidence": "alta | media | baixa",
  "verified_on": "{hoje}"
}
```

Referência de `accept_prob` para quem ainda não é conhecido no circuito: JUG remoto 75–90 · TDC/DevFest/JConf 50–70 ·
Voxxed/JCON/DevBcn 35–50 · Devnexus/Jfokus/Spring I/O 15–30 · Devoxx BE 5–12 · QCon/GOTO por convite ~5.

## Regras
1. **Verifique no site oficial / Sessionize / cfp.dev** com WebFetch antes de afirmar data ou prazo. Só agregador
   (cfp.watch, confs.tech, javaconferences.org, developers.events, papercall) → `confidence: media` e cite. Estimativa por
   padrão histórico → `estimado` e explique.
2. Datas passadas NÃO entram, exceto como referência de padrão para estimar a próxima edição.
3. Nada inventado: sem CFP achado → `cfp_status: nao_anunciado`, `cfp_deadline: null`.
4. Inclua eventos "só ir" relevantes (vendor events, DevFests, meetups recorrentes) com `cfp_status: sem_cfp`.
5. Quantidade > polimento: 40–80 eventos por região, cada um com pelo menos URL + data ou prazo.
6. A cota de WebSearch esgota em ~100 buscas: use WebFetch direto nas fontes oficiais. Registre o que ficou sem verificar.
7. Sem prosa longa. Salve JSON válido (array) + um .md curto (quantos, top 10 por prioridade, CFPs em 60 dias, lacunas).

## Escopo deste agente: {REGIÃO}
{Lista de eventos/famílias a cobrir e fontes — copie o bloco da região em `region-playbook.md`.}
Salve em `{pasta}/{regiao}.json` e `{pasta}/{regiao}.md`. Ao terminar, responda só com: quantidade, 10 destaques, lacunas.
