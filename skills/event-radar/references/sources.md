# Fontes de eventos — o que funciona por HTTP puro e o que exige navegador

Verificado em 2026-10-05. Quando uma fonte mudar de formato, o `radar.py` registra `FAIL <fonte>` no `summary.md`; o
resto continua.

## Funcionam com `urllib`/`curl` (usadas pelo `radar.py fetch`)

| Fonte | URL | Formato | Cobertura | Campos úteis |
|---|---|---|---|---|
| developers.events | `https://developers.events/all-events.json` e `all-cfps.json` | JSON (datas em epoch ms) | global, ~6k eventos (2019→), forte em EU/NA | `name, date[], hyperlink, location, city, country, cfp{link,until,untilDate}, tags[{key,value}]` |
| confs.tech | `https://raw.githubusercontent.com/tech-conferences/conference-data/main/conferences/<ano>/<topico>.json` | JSON por ano/tópico | global; tópicos: java, kotlin, groovy, data, devops, sre, security, general, api, leadership, javascript, typescript, css, ux, python, rust, dotnet, android, ios, iot, php, testing, networking, opensource, accessibility, tech-comm, performance, product, clojure, cpp, graphql | `name, url, startDate, endDate, city, country, online, locales, cfpUrl, cfpEndDate` |
| javaconferences.org | `https://raw.githubusercontent.com/javaconferences/javaconferences.github.io/main/README.md` | tabela Markdown por ano | Java/JVM no mundo | nome+link, local, híbrido, data por extenso, link do CFP com "(Closed dd Month yyyy)" |
| eventos.cafebugado.com.br | `https://eventos.cafebugado.com.br/eventos?page=1` | HTML Next.js com payload RSC `\"events\":[…]` (todos os eventos vêm na página 1) | Brasil (SP pesado), meetups, workshops, conferências, DevFests | `nome, slug, descricao, data_evento (dd/mm/aaaa), horario, periodo, modalidade, endereco, cidade, estado, link, tags[{nome,cor}]` |
| Planilha Google pública | `https://docs.google.com/spreadsheets/d/<ID>/export?format=csv&gid=<gid>` (ou `format=xlsx` para o arquivo inteiro) | CSV/XLSX | calendários comunitários | colunas livres; o script procura nome/evento, data, local, link |
| Sessionize | `https://sessionize.com/<slug>/` | HTML server-side | prazo do CFP com fuso ("Call closes at 11:59 PM 30 Sep 2026", "(UTC-04:00)"), "open, N days left", datas do evento | `verify-cfp` |
| Páginas genéricas de CFP | ex.: `ndcsecurity.com/call-for-papers` | HTML | "Deadline: 18 October 2026" | `verify-cfp` (regex deadline/closes/until) |
| GitHub API | `https://api.github.com/repos/<owner>/<repo>/contents/<path>` | JSON | listar tópicos/anos disponíveis nas fontes acima | — |

## Funcionam no servidor (WebFetch), mas bloqueiam o PC às vezes

| Fonte | Sintoma | Saída |
|---|---|---|
| PaperCall (`papercall.io/<slug>`) | `urllib` recebe `SSL: UNEXPECTED_EOF`; `curl` pode voltar vazio/403 | usar WebFetch (roda no servidor) ou o navegador do usuário; o texto tem "CFP closes at September 28, 2026 20:38 UTC" |
| cfp.watch, confs.tech site, javaconferences.org site | páginas renderizadas por JS | ir direto aos repositórios/JSON acima |

## Exigem navegador (claude-in-chrome) — não gaste tentativas com HTTP puro

| Fonte | Como ler |
|---|---|
| **cfp.dev** (Devoxx/Voxxed: `vdz27.cfp.dev`, `dvbe26.cfp.dev`) | SPA; abrir no navegador e ler o cabeçalho (datas, "CFP open until…") |
| **cfp.ninja** (Conf42 e outros) | SPA; deadlines aparecem só renderizados |
| **Luma** (`luma.com/<cidade>`, `luma.com/<slug>`) | SPA; na página de cidade, rolar (3×10 ticks) e extrair `a[href]` com `h3`; `get_page_text` pega só o cabeçalho |
| **GDG Community** (`gdg.community.dev/<capitulo>/`) e **advocu** (CFP de DevFest) | SPA; listar eventos do capítulo no navegador |
| **Oracle Eloqua** (`engage.oracle.com/...`) | página de campanha, conteúdo bloqueado para leitura anônima; tratar como programa, não como evento |
| **Meetup.com** | listagem de grupo carrega por JS; a página do evento individual às vezes é SSR |
| **LinkedIn Events** | só logado; usar o Chrome do usuário |
| Café Bugado (alternativa) | se o payload RSC mudar: a paginação é botão MUI; no navegador, `[...document.querySelectorAll('button.MuiPaginationItem-page')].find(b=>b.textContent.trim()==='2').click()` + `get_page_text` por página |

## Fontes por região para a pesquisa paralela (subagentes)

- **Brasil**: thedevconf.com/call4papers (TDC), eventos.codecon.dev, devpr.org, gambiconf.dev, devopsdays.org (cidades BR),
  community.cncf.io (KCD), gdg.community.dev (DevFests), sympla/doity/even3 (busca por "meetup java"), Café Bugado,
  Luma SP, soujava.org.br + encontros.soujava.org.br, Meetup (Java SP, Quarkus Club, AWS UG SP), páginas de vendor
  (Oracle SP: AICamp, Café com AI, Leitura Dev; Microsoft; Google Cloud; AWS Summit).
- **América Latina**: JConf (Peru, Guatemala, Dominicana, México, Colômbia — verificar quais ainda existem), nerdearla.com,
  DevFests (advocu/GDG), DevOpsDays (Bogotá, Medellín, Lima, BA, CDMX), KCD LatAm (community.cncf.io), Talent Land,
  JUGs: Mexico City JVM, Guate-JUG, PeruJUG, JavaDominicano, EcuadorJUG, j4Guanatos.
- **EUA/Canadá**: Sessionize (Devnexus, KCDC, CodeMash, Code Remix, DevFests), devnexus.com, oracle.com/javaone, fintechdevcon.io,
  confoo.ca, socallinuxexpo.org, JUGs (GSJUG, NYJavaSIG, CJUG, Denver, Toronto, Dallas JavaMUG, Philly, Atlanta, Seattle).
- **Europa**: devoxx.com/events (cfp.dev), jfokus.se, javaland.eu, jcon.one, springio.net, jnation.pt, devbcn.com, javazone.no,
  jprime.io, geecon.org, javaday.istanbul, ndcconferences.com, dawn.is (Dutch AI Conference), wearedevelopers.com,
  JUGs (vJUG, LJC, JUG Switzerland, Barcelona JUG, Coimbra JUG, NLJUG, JUG Frankfurt/Munich, Madrid JUG).
- **Online**: vjug (Sessionize rolling), jakartaone.jakarta.ee + Jakarta Tech Talks, conf42.com (CFP em cfp.ninja/PaperCall),
  jchampionsconf.com (só Java Champions), Microsoft Reactor, Red Hat DevNation, podcasts (airhacks.fm, Foojay, Java Off-Heap,
  Bootiful, Hipsters Ponto Tech), programas (Oracle ACE, Java Champions, GDE, MVP, AWS Community Builders).
