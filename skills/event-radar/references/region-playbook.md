# Playbook por região — o que procurar, onde, e o que costuma dar errado

Use depois do `radar.py fetch`. Cada bloco lista o que os agregadores NÃO trazem e precisa de pesquisa dirigida
(subagente por região com `fanout-brief-template.md`).

## Brasil (BR)

- **Calendário anual que decide o ano seguinte**: TDC roda 6–8 edições (Summit AI abr · Floripa jul · Rio/São Carlos/
  Santa Rita ago–set · SP set · Recife nov · POA dez); o CFP abre ~3 meses antes e `thedevconf.com/call4papers` só mostra
  a safra corrente. Edições do ano seguinte: estimar pelo padrão e marcar `estimado`. TDC não paga viagem/hotel.
- **Codecon Summit** (Pinhais/PR, jul–ago; CFP ~mar–mai) + meetups Codecon mensais (SP na Oracle, Floripa, Goiânia).
- **DevFests** (out–dez): capítulos GDG publicam CFP via advocu ~2 meses antes; SP, Campinas, BH, Rio, Brasília, Floripa ("Sul"),
  Nordeste. `gdg.community.dev` é SPA.
- **DevOpsDays BR** (SP, BH, POA, Recife, Floripa, Brasília, Curitiba, Vitória, Belém…): `devopsdays.org/events` lista por
  cidade com CFP em cfp.ninja (SPA) ou Sessionize.
- **KCD Brasil / São Paulo** (set; CFP mai–jul via Sessionize), PGDay, GambiConf (nov, SP), DevPR Conf (Maringá, nov; uma
  proposta por pessoa), Agile Trends (abr, SP; CFP aberto cedo), SP/Rio Innovation Week (curadoria/patrocínio, não CFP).
- **Vendor em SP (só ir, mas ótimo networking)**: Oracle (AICamp, Café com AI, Leitura Dev, meetups de comunidades),
  Microsoft (AI Tour fev, Elevate), Google (Cloud Summit set, Builder Connect, I/O Extended), AWS Summit (set), Red Hat
  Summit Connect (nov), OpenAI DevDay Exchange, Databricks, Snowflake.
- **JUGs**: SouJava (mensal, Oracle SP + Campinas + Rio), Brasil JUG (lives online), Meetup Java SP (FIAP), Quarkus Club (IBM),
  DevParaná; JUGs regionais (DFJUG, GOJava, RSJUG, JUG Vale, Java Bahia, JavaMG, Java Ceará, PernambucoJUG) exigem checar
  atividade no ano — muitos estão dormentes. Pergunte no Slack/Discord do SouJava.
- **Fontes BR que funcionam por HTTP**: Café Bugado (tudo em uma página), planilhas comunitárias públicas, Sympla (página do
  evento é SSR). **Exigem navegador**: Luma SP, GDG community, advocu, Meetup listagens.

## América Latina (LATAM)

- **JConf** é a família Java regional: Peru (Lima, out–nov; Sessionize; hotel 2 noites), Guatemala (nov; gratuita; form próprio),
  Dominicana (jul; CFP jan–mar), México e Colômbia (verificar se ainda existem — sites caíram em 2025/26). Idioma ES/EN; aceitam
  remoto às vezes.
- **Nerdearla** (Argentina set; Chile abr; México nov): CFP ~4–5 meses antes, aceita talk remota/gravada, sem verba de viagem.
- **DevFests LatAm** (Santiago, Bogotá, Lima, CDMX, Guadalajara, Montevideo, Asunción, La Paz, Guatemala, Panamá) — CFP via Sessionize/advocu
  ~1 mês antes; temas bilíngues.
- **DevOpsDays** (Bogotá, Medellín, Lima, BA, CDMX) e **KCD** (Panamá jan, Guadalajara abr, Cali jun, Lima jul, Argentina out) — a CNCF
  publica o mês; datas exatas chegam tarde.
- **Grandes de vendor/curadoria**: Talent Land (Guadalajara/CDMX abr), Microsoft AI Tour e Oracle AI World Tour (CDMX, Bogotá, Santiago,
  BA — sites JS), AWS Summit (CDMX, Bogotá, Santiago). Só ir.
- **JUGs ativos (2026)**: Mexico City JVM Group (online), Guate-JUG, PeruJUG, JavaDominicano, EcuadorJUG, j4Guanatos, JUG Argentina
  (Córdoba, online). Bogotá/Medellín/Chile/Uruguai/Costa Rica/Panamá: sem prova de atividade — não liste como ativos.
- **Armadilha**: buscadores devolvem CAPTCHA para agentes; use fetch direto nos sites oficiais e Sessionize.

## EUA / Canadá (NA)

- **Java**: Devnexus (Atlanta, mar; CFP set — prazo costuma ser estendido), JavaOne (Redwood, mar; CFP set–nov, portal Oracle com login),
  KCDC (Kansas City, ago; CFP ~fev–mar), CodeMash (jan; CFP ago), THAT Conference (TX jan / WI jul), Code Remix / AI Software Factory
  Summit (Miami fev; hotel + verba), dev up (St. Louis), Nebraska.Code, Beer City Code, Prairie Dev Con, Open Source North.
- **IA/arquitetura**: AI Engineer World's Fair (SF jun; CFP jan–mar) e AIE Code/NYC, QCon SF (nov) / QCon AI NY (dez) / QCon AI Boston (jul)
  — convite com "speaker inquiry form", ODSC, SCaLE (CFP nov), SREcon Americas, All Things Open (Raleigh out; CFP mar), DeveloperWeek (fev; CFP set),
  fintech_devcon (Boulder ago; CFP até mar).
- **Vendor (só ir)**: AWS re:Invent (dez), GitHub Universe (out), Oracle AI World (out), Google I/O e Cloud Next (abr–mai), Microsoft Build (mai).
- **JUGs que recebem remoto**: Garden State JUG (híbrido, speakers internacionais), NYJavaSIG, Chicago JUG, Denver JUG, Toronto JUG, Dallas JavaMUG,
  Philly JUG, Atlanta JUG (organiza o Devnexus), Seattle JUG, Montréal/Ottawa JUG. Houston/Vancouver dormentes.
- **ConFoo Montreal** (fev; CFP set do ano anterior; **paga viagem+hotel**; aceita 3–5 propostas) é a melhor porta de entrada NA que paga.

## Europa (EU)

- **Família Devoxx/Voxxed** (cfp.dev, SPA): Devoxx BE (out; CFP mai–jul; ~5–10% para desconhecidos), UK (mai; CFP dez–jan; edição 2027 em
  consulta), FR (abr; CFP nov–jan), PL (jun), GR (abr; CFP out–nov), MA (nov; aceita speakers novos). Voxxed Days Zürich/CERN/Ticino (fev–mar;
  CFP fecha ~23/10), Luxembourg (jun), Amsterdam, Brussels, Bucharest, Crete, Thessaloniki.
- **Java**: Jfokus (fev; CFP até ~1/10), JavaLand (mar; CFP até ~14/9), JCON Europe (abr; CFP até ~23/10; sem viagem), Spring I/O (mai; CFP
  dez–jan), JNation (jun; CFP jan–mar), DevBcn (jun), jPrime (mai; CFP fev), GeeCON (mai), JavaZone (set; CFP abr), Java Day Istanbul (abr;
  CFP out), J-Fall (nov; CFP jul–set), J-Spring (jun), JAX/W-JAX (mai/nov), BaselOne (out), JavaCro, JDD, Confitura, Java Forum Stuttgart/Nord,
  JAlba (unconference), JCrete (convite).
- **IA/geral**: Dutch AI Conference / Dawn (Amsterdã mar; CFP dez; **voo+hotel**), NDC Security (Oslo fev; CFP out; **viagem+hotel**),
  NDC Oslo/London/Copenhagen/Porto, nor(DEV):con (Norwich fev; CFP set; viagem+hotel), WeAreDevelopers (Berlim jul; rolling), Craft (Budapeste),
  Infoshare (Gdańsk), KubeCon EU (mar; CFP out), QCon London (convite), GOTO Amsterdam/Copenhagen (convite), LeadDev London (jun; CFP jan),
  Booster (Bergen mar; CFP out), Swetugg (Estocolmo fev; viagem+hotel), DevDays Europe (Vilnius mai), Codemotion (Milão/Madri).
- **JUGs com online/híbrido**: vJUG, LJC (Sessionize), JUG Switzerland, Barcelona JUG (Luma), Coimbra JUG, NLJUG, JUG Frankfurt/Munich/Cologne,
  Madrid JUG, Bucharest JUG, BeJUG. Muitos sites de JUG alemães/italianos estão fora do ar; confiança baixa.

## Online (ONLINE)

- **Conferências**: vJUG (Sessionize rolling), JakartaOne Livestream (dez; CFP até ~set; edições por idioma), Jakarta Tech Talks (contínuo),
  Conf42 (série: Platform, MLOps, Prompt Eng, DevOps, ML, DevSecOps, SRE, Cloud Native, LLMs, Observability, AI Agents — CFP ~30 dias antes,
  pré-gravado), jChampions Conference (jan; só Java Champions), Global Azure (abr), IntelliJ IDEA Conf (convite), Microsoft Reactor
  (e-mail), Red Hat DevNation, InfoQ Live (convite), DevFest global (temporada out–dez, capítulos online).
- **Podcasts que aceitam convidados**: airhacks.fm (botão "Be on the Podcast"), Foojay Podcast (Slack #podcast), Java Off-Heap, Java Pub House,
  Bootiful Podcast, SE Radio, Hipsters Ponto Tech e Os Agilistas (PT), Inside Java (convite Oracle).
- **Programas que mudam o aceite**: Oracle ACE (nomeação aberta), Java Champions (indicação + voto), Google Developer Experts, Microsoft MVP,
  AWS Community Builders (janela anual), Foojay author, JUG Leaders list (jugs.groups.io; pedir intro).

## Ásia / Oceania / África (OTHER) — só se pagar viagem

GIDS (Bengaluru abr; CFP set; fundo de viagem limitado e esgota cedo), YOW! Australia (dez; convite; paga viagem), NDC Sydney/Melbourne
(paga viagem; CFP ~dez), JJUG CCC (Tóquio, mai/nov), JCConf Taiwan, KubeCon India/Japan/China, Devoxx Morocco (contado em EU).
