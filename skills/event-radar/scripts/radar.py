#!/usr/bin/env python3
"""radar.py — raspa calendários públicos de eventos tech por ÁREA e REGIÃO e consolida num events.json + summary.md.

Só biblioteca padrão (urllib, json, re, csv, html). Sem Selenium, sem navegador: usa apenas fontes servidas por HTTP puro.

Subcomandos
  fetch       baixa todas as fontes, filtra pela janela/áreas/regiões, deduplica, pontua e grava events.json + summary.md
  verify-cfp  lê uma página de CFP (Sessionize, PaperCall ou genérica) e imprime status, prazo e datas do evento
  panel       copia o painel HTML (panel.html) para a pasta de saída (abrir via http.server, não via file://)

Exemplos
  python radar.py fetch --areas java,ai,security --regions BR,EU,NA,LATAM,ONLINE --months 12 --out ./radar
  python radar.py fetch --areas java --regions BR --from 2026-10-05 --months 6 --extra minha-pesquisa.json --out ./radar
  python radar.py verify-cfp https://sessionize.com/devnexus-2027/ https://www.papercall.io/conf42-mlops-2026
  python radar.py panel --out ./radar && python -m http.server 8768 --directory ./radar

Fontes (todas públicas, leitura anônima):
  developers.events   https://developers.events/all-events.json + all-cfps.json (global, tags, prazos de CFP)
  confs.tech          https://github.com/tech-conferences/conference-data (JSON por ano e tópico)
  javaconferences.org README.md do repositório javaconferences/javaconferences.github.io (tabela Java com status de CFP)
  cafebugado          https://eventos.cafebugado.com.br/eventos (Brasil; o HTML embute o JSON de todos os eventos)
  gsheet (opcional)   planilha Google pública exportada como CSV (--sheet ID[:gid,gid])
  extra (opcional)    JSON seu (pesquisa manual, agentes, overrides) no mesmo esquema de saída
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import shutil
import sys
import unicodedata
import urllib.error
import urllib.request

for _stream in (sys.stdout, sys.stderr):  # Windows: console cp1252 engasga com acentos
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

UA = "event-radar/1.0 (+https://github.com/fhgomes/my-awesome-agents-skills)"
TIMEOUT = 40

# ----------------------------------------------------------------------------- áreas
# área -> (palavras-chave no nome/tags, tópicos do confs.tech)
AREAS = {
    "java": (r"\bjava\b|jvm|jug\b|devoxx|voxxed|jfokus|javaland|jcon\b|jakarta|spring|javazone|jnation|j-fall|jprime|geecon|javaone|devnexus|soujava|quarkus|kotlin|jalba|jcrete|j-spring|jdd\b|javacro|confitura|java day|jconf", ["java", "kotlin", "groovy"]),
    "ai": (r"\bai\b|\bia\b|artificial|machine learning|\bml\b|llm|gen ?ai|agent|rag\b|mlops|data science|deep learning|prompt|evals?\b|nlp", ["data"]),
    "cloud": (r"cloud|kubernetes|kubecon|kcd\b|cncf|devops|sre\b|platform eng|container|aws|azure|gcp|serverless|observab", ["devops", "sre", "networking"]),
    "security": (r"secur|seguran|owasp|hack|ndc security|appsec|defcon|bsides|pentest|cyber", ["security"]),
    "architecture": (r"architect|arquitet|qcon|goto\b|infoq|ddd\b|microservice|system design|software design|craft", ["general", "api"]),
    "frontend": (r"javascript|\bjs\b|react|angular|vue|frontend|front-end|css|web dev|node", ["javascript", "typescript", "css", "ux"]),
    "data": (r"\bdata\b|dados|big data|databricks|snowflake|postgres|pgday|sql|kafka|flink|lakehouse", ["data"]),
    "fintech": (r"fintech|money20|febraban|banking|payments?|pagamento|open finance|pix\b", []),
    "career": (r"career|carreira|leadership|lideran|leaddev|mentor|soft skills", ["leadership"]),
    "gdg": (r"\bgdg\b|devfest|google (developer|cloud|i/o)|build with ai", []),
    "microsoft": (r"microsoft|\bmvp\b|azure|\.net|dotnet|ignite|build 20", ["dotnet"]),
    "oracle": (r"oracle|javaone|cloudworld|oci\b", []),
    "python": (r"python|pycon|django|pydata", ["python"]),
    "mobile": (r"android|ios\b|flutter|mobile|droidcon", ["android", "ios"]),
    "general": (r".", ["general"]),
}

# ----------------------------------------------------------------------------- regiões
EU = {"germany", "france", "belgium", "netherlands", "the netherlands", "luxembourg", "switzerland", "austria", "spain", "portugal", "italy", "united kingdom", "uk", "england", "scotland", "wales", "ireland", "sweden", "norway", "denmark", "finland", "iceland", "poland", "czech republic", "czechia", "slovakia", "hungary", "romania", "bulgaria", "greece", "turkey", "türkiye", "turkiye", "croatia", "slovenia", "serbia", "bosnia", "estonia", "latvia", "lithuania", "ukraine", "morocco", "israel", "cyprus", "malta", "montenegro", "north macedonia", "albania", "georgia", "armenia", "belarus", "moldova", "kosovo"}
NA = {"usa", "united states", "us", "united states of america", "canada"}
LATAM = {"argentina", "chile", "uruguay", "paraguay", "peru", "colombia", "ecuador", "mexico", "méxico", "guatemala", "costa rica", "panama", "panamá", "dominican republic", "bolivia", "venezuela", "honduras", "el salvador", "nicaragua", "cuba", "puerto rico"}
BR = {"brazil", "brasil"}
EU_WORDS = ("alemanha", "holanda", "belgica", "bélgica", "suica", "suíça", "espanha", "portugal", "reino unido", "londres", "suecia", "suécia", "noruega", "dinamarca", "polonia", "polônia", "franca", "frança", "italia", "itália", "escocia", "marrocos", "turquia", "luxemburgo", "irlanda", "austria", "grecia", "grécia", "romenia", "bulgaria", "finlandia", "hungria", "israel", "germany", "france", "belgium", "netherlands", "switzerland", "spain", "sweden", "norway", "denmark", "poland", "italy", "uk", "united kingdom", "ireland", "greece", "turkey", "czech", "austria", "portugal", "morocco")
NA_WORDS = ("eua", "estados unidos", "usa", "united states", "canada", "canadá", "montreal", "atlanta", "california", "san francisco", "new york", "nova york", "miami", "boston", "chicago", "seattle", "toronto", "vancouver", "redwood", "austin", "denver", "las vegas", "tx", "ca,", "ny")
LATAM_WORDS = ("america latina", "américa latina", "latam", "peru", "colombia", "colômbia", "mexico", "méxico", "argentina", "chile", "uruguai", "uruguay", "paraguai", "paraguay", "equador", "ecuador", "guatemala", "costa rica", "panama", "panamá", "dominican", "bolivia", "bolívia", "venezuela", "lima", "bogota", "bogotá", "medellin", "medellín", "buenos aires", "santiago", "cdmx", "guadalajara", "montevideo")
BR_WORDS = ("brasil", "brazil", "são paulo", "sao paulo", " sp", "rio de janeiro", "porto alegre", "recife", "florianópolis", "florianopolis", "belo horizonte", "brasília", "brasilia", "curitiba", "campinas", "maringá", "maringa", "salvador", "fortaleza", "goiânia", "goiania", "manaus", "belém", "belem", "vitória", "vitoria", "pinhais", "joinville")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")


def region_of(country=None, city=None, location=None, online=False):
    if online:
        return "ONLINE"
    c = norm(country)
    if c:
        if c in BR:
            return "BR"
        if c in NA:
            return "NA"
        if c in EU:
            return "EU"
        if c in LATAM:
            return "LATAM"
    loc = norm(" ".join([x for x in (city, location, country) if x]))
    if not loc:
        return "OTHER"
    if loc.startswith("online") or "virtual" in loc or "remote" in loc:
        return "ONLINE"
    if any(w in loc for w in BR_WORDS):
        return "BR"
    if any(w in loc for w in LATAM_WORDS):
        return "LATAM"
    if any(w in loc for w in NA_WORDS):
        return "NA"
    if any(w in loc for w in EU_WORDS):
        return "EU"
    return "OTHER"


# ----------------------------------------------------------------------------- http
def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = r.read()
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, OSError) as e:
        # alguns hosts (ex.: papercall.io) derrubam o TLS do urllib; o curl do sistema costuma passar
        import subprocess
        try:
            data = subprocess.run(["curl", "-sL", "--max-time", str(TIMEOUT), "-A", UA, url], check=True, capture_output=True).stdout
        except Exception:  # noqa: BLE001
            raise e
        if not data:
            raise e
    return data if binary else data.decode("utf-8", "replace")


def get_json(url):
    return json.loads(get(url))


def safe(fn, label, log):
    try:
        out = fn()
        log.append(f"OK   {label}: {len(out)} itens")
        return out
    except Exception as e:  # noqa: BLE001 — queremos seguir com as outras fontes
        log.append(f"FAIL {label}: {type(e).__name__}: {e}")
        return []


# ----------------------------------------------------------------------------- datas
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS.update({"sept": 9})


def ms_to_iso(ms):
    try:
        return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return None


def parse_date_text(text):
    """'2-4 February 2026' | '31 January-1 February 2026' | '17–19 March 2026' | '19 July 2026' | '30 Sep 2026' -> (start, end)"""
    t = norm(text).replace("–", "-").replace("—", "-")
    m = re.search(r"(\d{1,2})\s*([a-z]+)?\s*-\s*(\d{1,2})\s+([a-z]+)\s+(\d{4})", t)
    if m:
        d1, m1, d2, m2, y = m.groups()
        m1 = MONTHS.get((m1 or m2)[:4].rstrip(), MONTHS.get((m1 or m2)[:3]))
        m2v = MONTHS.get(m2[:4].rstrip(), MONTHS.get(m2[:3]))
        if m1 and m2v:
            return f"{y}-{m1:02d}-{int(d1):02d}", f"{y}-{m2v:02d}-{int(d2):02d}"
    m = re.search(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", t)
    if m:
        d, mo, y = m.groups()
        mv = MONTHS.get(mo[:4].rstrip(), MONTHS.get(mo[:3]))
        if mv:
            return f"{y}-{mv:02d}-{int(d):02d}", f"{y}-{mv:02d}-{int(d):02d}"
    m = re.search(r"([a-z]+)\s+(\d{1,2}),?\s+(\d{4})", t)  # September 30, 2026
    if m:
        mo, d, y = m.groups()
        mv = MONTHS.get(mo[:4].rstrip(), MONTHS.get(mo[:3]))
        if mv:
            return f"{y}-{mv:02d}-{int(d):02d}", f"{y}-{mv:02d}-{int(d):02d}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return m.group(0), m.group(0)
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", t)  # dd/mm/yyyy
    if m:
        d, mo, y = m.groups()
        return f"{y}-{mo}-{d}", f"{y}-{mo}-{d}"
    return None, None


# ----------------------------------------------------------------------------- fontes
def src_developers_events():
    data = get_json("https://developers.events/all-events.json")
    out = []
    for e in data:
        dates = e.get("date") or []
        start = ms_to_iso(dates[0]) if dates else None
        end = ms_to_iso(dates[-1]) if dates else None
        cfp = e.get("cfp") or {}
        tags = []
        for t in e.get("tags") or []:
            if isinstance(t, dict):
                tags.append(f"{t.get('key')}:{t.get('value')}")
            else:
                tags.append(str(t))
        # "Cidade, País" (o painel lê o país do último trecho; o campo location bruto vem como "City, CA (USA)")
        loc = ", ".join([x for x in (e.get("city"), e.get("country")) if x]) or (e.get("location") or "")
        online = norm(loc).startswith("online") or norm(e.get("city")) == "online"
        out.append({
            "name": e.get("name"), "url": e.get("hyperlink"), "date": start, "date_end": end,
            "city": e.get("city"), "country": e.get("country"), "location": loc, "online": online,
            "cfp_url": cfp.get("link"), "deadline": ms_to_iso(cfp["untilDate"]) if cfp.get("untilDate") else None,
            "tags": tags, "status": e.get("status"), "_src": "developers.events",
        })
    return out


def src_confs_tech(topics, years):
    out = []
    for y in years:
        for t in topics:
            url = f"https://raw.githubusercontent.com/tech-conferences/conference-data/main/conferences/{y}/{t}.json"
            try:
                arr = get_json(url)
            except urllib.error.HTTPError:
                continue
            for e in arr:
                out.append({
                    "name": e.get("name"), "url": e.get("url"), "date": e.get("startDate"), "date_end": e.get("endDate"),
                    "city": e.get("city"), "country": e.get("country"), "location": ", ".join([x for x in (e.get("city"), e.get("country")) if x]),
                    "online": bool(e.get("online")), "cfp_url": e.get("cfpUrl"), "deadline": e.get("cfpEndDate"),
                    "tags": [f"topic:{t}"] + ([f"locale:{e.get('locales')}"] if e.get("locales") else []), "_src": "confs.tech",
                })
    return out


def src_javaconferences():
    md = get("https://raw.githubusercontent.com/javaconferences/javaconferences.github.io/main/README.md")
    out = []
    for line in md.splitlines():
        if not line.startswith("| [") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", cells[0])
        name, url = (m.group(1), m.group(2)) if m else (cells[0], None)
        loc, hybrid, date_txt, cfp_txt = cells[1], cells[2], cells[3], cells[4]
        start, end = parse_date_text(date_txt)
        cm = re.search(r"\]\(([^)]+)\)", cfp_txt)
        cfp_url = cm.group(1) if cm else None
        closed = re.search(r"closed\s*([0-9]{1,2} [A-Za-z]+ [0-9]{4})?", cfp_txt, re.I)
        deadline = None
        status = None
        if closed:
            status = "fechado"
            if closed.group(1):
                deadline, _ = parse_date_text(closed.group(1))
        elif cfp_url:
            um = re.search(r"until\s*([0-9]{1,2} [A-Za-z]+ [0-9]{4})", cfp_txt, re.I)
            if um:
                deadline, _ = parse_date_text(um.group(1))
            status = "aberto" if (deadline is None or deadline >= TODAY) else "fechado"
        online = norm(loc) == "online"
        out.append({
            "name": name, "url": url, "date": start, "date_end": end, "location": loc, "online": online,
            "cfp_url": cfp_url, "deadline": deadline, "cfp_status": status,
            "tags": ["topic:java"] + (["hybrid"] if norm(hybrid) == "yes" else []), "_src": "javaconferences.org",
        })
    return out


def src_cafebugado():
    html = get("https://eventos.cafebugado.com.br/eventos?page=1")
    # O Next.js embute o JSON em self.__next_f.push([1,"...\"events\":[{...}]..."]) com aspas escapadas.
    i = html.find('\\"events\\":[')
    if i < 0:
        raise RuntimeError("payload 'events' nao encontrado (layout mudou?)")
    start = html.rfind('.push([1,"', 0, i)
    end = html.find('"])', i)
    if start < 0 or end < 0:
        raise RuntimeError("delimitadores do payload RSC nao encontrados")
    txt = json.loads('"' + html[start + len('.push([1,"'):end] + '"')
    k = txt.find('"events":[')
    arr, _ = json.JSONDecoder().raw_decode(txt, k + len('"events":'))
    out = []
    for e in arr:
        d, _ = parse_date_text(e.get("data_evento") or "")
        tags = [t.get("nome") if isinstance(t, dict) else str(t) for t in (e.get("tags") or [])]
        city = e.get("cidade")
        online = norm(e.get("modalidade")) in ("online", "remoto")
        out.append({
            "name": e.get("nome"), "url": e.get("link") or f"https://eventos.cafebugado.com.br/eventos/{e.get('slug')}",
            "date": d, "date_end": d, "city": city, "country": "Brazil",
            "location": ", ".join([x for x in (city, e.get("estado")) if x]), "online": online,
            "tags": [f"tag:{t}" for t in tags if t] + [f"periodo:{e.get('periodo')}", f"modalidade:{e.get('modalidade')}"],
            "notes": f"{e.get('horario') or ''} · {e.get('endereco') or ''}".strip(" ·"),
            "_src": "cafebugado",
        })
    return out


def src_gsheet(spec):
    """spec = 'SHEET_ID' ou 'SHEET_ID:gid1,gid2'. Espera colunas com nome/evento, data, local/cidade, link (qualquer ordem)."""
    sid, _, gids = spec.partition(":")
    gids = [g for g in gids.split(",") if g] or [None]
    out = []
    for gid in gids:
        url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv" + (f"&gid={gid}" if gid else "")
        text = get(url)
        rows = list(csv.reader(io.StringIO(text)))
        if not rows:
            continue
        head = [norm(h) for h in rows[0]]

        def col(*names):
            for n in names:
                for i, h in enumerate(head):
                    if n in h:
                        return i
            return None
        ci = {"name": col("evento", "nome", "name", "title"), "date": col("data", "date", "quando"), "loc": col("local", "cidade", "city", "onde"), "url": col("link", "url")}
        if ci["name"] is None:
            continue
        for r in rows[1:]:
            def v(k):
                i = ci[k]
                return r[i].strip() if i is not None and i < len(r) else ""
            if not v("name"):
                continue
            d, _ = parse_date_text(v("date"))
            out.append({"name": v("name"), "url": v("url") or None, "date": d, "date_end": d, "location": v("loc") or None, "tags": ["src:gsheet"], "_src": f"gsheet:{sid[:8]}"})
    return out


def src_extra(path):
    data = json.load(open(path, encoding="utf-8"))
    arr = data.get("events") if isinstance(data, dict) else data
    out = []
    for e in arr:
        e = dict(e)
        e.setdefault("date", e.get("start_date"))
        e.setdefault("date_end", e.get("end_date"))
        e.setdefault("deadline", e.get("cfp_deadline"))
        e.setdefault("location", ", ".join([x for x in (e.get("city"), e.get("country")) if x]) or None)
        e.setdefault("online", e.get("format") == "online")
        e.setdefault("tags", [f"cat:{c}" for c in (e.get("category") or [])])
        e["_src"] = e.get("_src") or f"extra:{os.path.basename(path)}"
        out.append(e)
    return out


# ----------------------------------------------------------------------------- verify-cfp
def verify_cfp(url):
    html = get(url)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    res = {"url": url, "platform": None, "status": None, "deadline": None, "deadline_text": None, "event_dates": None, "location": None}
    if "sessionize.com" in url:
        res["platform"] = "sessionize"
        m = re.search(r"Call (?:closes|closed) (?:at|on) ([0-9:]+ ?[AP]M)?\s*([0-9]{1,2} [A-Z][a-z]{2} [0-9]{4})", text)
        if m:
            res["deadline_text"] = m.group(0)
            res["deadline"], _ = parse_date_text(m.group(2))
        st = re.search(r"open, \d+ days? left", text, re.I)
        if st:
            res["status"] = "aberto (" + st.group(0).lower() + ")"
        elif re.search(r"not yet open|opens? (at|on)", text, re.I) and not re.search(r"Call closes", text):
            res["status"] = "ainda nao abriu"
        tz = re.search(r"\(UTC[+-][0-9:]+\)[^.]{0,40}", text)
        if tz:
            res["deadline_text"] = (res["deadline_text"] or "") + " " + tz.group(0).strip()
        ev = re.search(r"event starts\s*([0-9]{1,2} [A-Z][a-z]{2} [0-9]{4})\s*event ends\s*([0-9]{1,2} [A-Z][a-z]{2} [0-9]{4})", text, re.I)
        if ev:
            res["event_dates"] = f"{parse_date_text(ev.group(1))[0]} .. {parse_date_text(ev.group(2))[0]}"
        loc = re.search(r"location\s+([A-Za-z ,.'-]{3,80}?)\s+(?:event starts|$)", text, re.I)
        if loc:
            res["location"] = loc.group(1).strip()
    elif "papercall.io" in url:
        res["platform"] = "papercall"
        m = re.search(r"CFP closes at ([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})( [0-9:]+ [A-Z]{3,4})?", text)
        if m:
            res["deadline_text"] = m.group(0)
            res["deadline"], _ = parse_date_text(m.group(1))
            res["status"] = "aberto" if res["deadline"] >= TODAY else "fechado"
    else:
        res["platform"] = "generic"
        m = re.search(r"(deadline|closes?|until|prazo|ate|até|submissions? (?:close|due))[^0-9]{0,40}((\d{1,2} [A-Za-z]+ \d{4})|([A-Za-z]+ \d{1,2},? \d{4})|(\d{4}-\d{2}-\d{2})|(\d{2}/\d{2}/\d{4}))", text, re.I)
        if m:
            res["deadline_text"] = m.group(0)
            res["deadline"], _ = parse_date_text(m.group(2))
            res["status"] = "aberto" if res["deadline"] and res["deadline"] >= TODAY else "fechado?"
    if res["platform"] == "sessionize" and res["status"] is None and res["deadline"]:
        res["status"] = "aberto" if res["deadline"] >= TODAY else "fechado"
    return res


# ----------------------------------------------------------------------------- normalização, filtro, score
TIERS = [  # (regex no nome, prestígio 1-5, concorrência 1-5, chance base 0-100)
    (r"devoxx belgium|devoxx be\b", 5, 5, 8),
    (r"javaone|qcon|goto\b|kubecon|google i/o|microsoft build|aws re:invent|web summit|infoq", 5, 5, 8),
    (r"spring i/o|devnexus|jfokus|javaland|javazone|devoxx (uk|france|poland)|ai engineer|all things open|ndc oslo|ndc london|leaddev", 4, 4, 20),
    (r"voxxed|jcon|j-fall|jprime|geecon|jnation|devbcn|java day|jax\b|w-jax|oredev|baselone|ndc |confoo|codemash|kcdc|devoxx (greece|morocco)|jconf|nerdearla|devoxx uk", 3, 3, 35),
    (r"\btdc\b|codecon|devfest|devopsdays|kcd\b|conf42|agile trends|jakartaone|python brasil|the developer's conference", 3, 3, 50),
    (r"\bjug\b|user group|meetup|soujava|community|comunidade|tech talk|webinar|live\b|vjug", 1, 1, 80),
]


def tier_of(name):
    n = norm(name)
    for rx, p, c, base in TIERS:
        if re.search(rx, n):
            return p, c, base
    return 2, 2, 45


def unify(e, areas_rx):
    name = (e.get("name") or "").strip()
    hay = norm(" ".join([name, " ".join(e.get("tags") or []), e.get("location") or "", e.get("notes") or ""]))
    nm = norm(name)
    cats, score = [], 0
    for a, rx in areas_rx.items():
        if a == "general":
            continue
        if re.search(rx, nm):
            cats.append(a); score += 45
        elif re.search(rx, hay):
            cats.append(a); score += 25
    fit = e.get("fit_score") if e.get("fit_score") is not None else (min(100, score) if cats else 10)
    p, c, base = tier_of(name)
    accept = e.get("accept_prob") if e.get("accept_prob") is not None else max(0, min(100, base + (10 if fit >= 70 else (-10 if fit < 40 else 0))))
    region = e.get("region") or region_of(e.get("country"), e.get("city"), e.get("location"), e.get("online"))
    deadline = e.get("deadline")
    cfp_status = e.get("cfp_status")
    if not cfp_status:
        if deadline:
            cfp_status = "aberto" if deadline >= TODAY else "fechado"
        elif e.get("cfp_url"):
            cfp_status = "desconhecido"
        else:
            cfp_status = "sem_cfp"
    if cfp_status == "aberto":
        action = "submeter"
    elif cfp_status == "fechado":
        action = "so_ir"
    elif cfp_status in ("convite", "contatar"):
        action = "contatar_organizador"
    elif cfp_status == "sem_cfp":
        action = "contatar_organizador" if p == 1 else "so_ir"
    else:
        action = "monitorar_cfp"
    priority = e.get("priority") or ("P1" if (fit >= 70 and accept >= 45) else ("P2" if fit >= 50 else "P3"))
    return {
        "id": e.get("id") or f"{slug(name)}-{(e.get('date') or deadline or '')[:4]}".strip("-"),
        "name": name,
        "region": region,
        "location": e.get("location") or ", ".join([x for x in (e.get("city"), e.get("country")) if x]) or ("online" if e.get("online") else None),
        "format": e.get("format") or ("online" if e.get("online") else "presencial"),
        "date": e.get("date"), "date_end": e.get("date_end") or e.get("date"),
        "date_status": e.get("date_status") or ("confirmado" if e.get("date") else "desconhecido"),
        "organizer": e.get("organizer"),
        "category": sorted(set((e.get("category") or []) + cats)) or ["general-dev"],
        "url": e.get("url"), "cfp_url": e.get("cfp_url"),
        "cfp_status": cfp_status, "deadline": deadline,
        "deadline_status": e.get("deadline_status") or ("confirmado" if deadline else "desconhecido"),
        "speaker_perks": e.get("speaker_perks"), "cost": e.get("cost") or e.get("speaker_perks"),
        "talk_fit": e.get("talk_fit") or [],
        "adherence": fit, "adherence_why": e.get("adherence_why") or (f"áreas detectadas: {', '.join(cats)}" if cats else "nenhuma área-alvo detectada no nome/tags"),
        "acceptance": accept, "acceptance_why": e.get("acceptance_why") or f"heurística por porte (prestígio {p}/5, concorrência {c}/5, base {base}) ± fit — revisar manualmente",
        "prestige": p, "competition": c,
        "action": e.get("action") or action, "priority": priority,
        "status": e.get("status"), "notes": e.get("notes"), "tags": e.get("tags") or [],
        "sources": sorted(set((e.get("sources") or []) + [e.get("_src") or "?"])),
        "confidence": e.get("confidence") or ("alta" if e.get("_src") in ("cafebugado", "javaconferences.org", "confs.tech") else "media"),
        "verified_on": e.get("verified_on") or TODAY,
    }


def in_window(ev, start, end):
    d = ev.get("date")
    dl = ev.get("deadline")
    if d and start <= d <= end:
        return True
    if dl and start <= dl <= end:
        return True
    if not d and not dl and ev.get("date_status") == "rolling":
        return True
    return False


def merge(a, b):
    out = dict(a)
    for k, v in b.items():
        if k in ("sources", "tags", "category", "talk_fit"):
            out[k] = sorted(set((a.get(k) or []) + (v or [])))
        elif out.get(k) in (None, "", [], "desconhecido", "sem_cfp") and v not in (None, "", []):
            out[k] = v
    if b.get("deadline") and (not a.get("deadline") or (a.get("deadline_status") != "confirmado" and b.get("deadline_status") == "confirmado")):
        out["deadline"] = b["deadline"]
        out["cfp_status"] = b.get("cfp_status") or out["cfp_status"]
    return out


def dedupe(events):
    by = {}
    order = []
    for ev in events:
        key = re.sub(r"-(20\d\d|\d+(st|nd|rd|th|a|o)|edition|edicao)(-|$)", "-", slug(ev["name"])).strip("-") + "|" + (ev.get("date") or ev.get("deadline") or "")[:4]
        if key in by:
            by[key] = merge(by[key], ev)
        else:
            by[key] = ev
            order.append(key)
    return [by[k] for k in order]


# ----------------------------------------------------------------------------- summary
def summary_md(events, args, log):
    from collections import Counter
    lines = [f"# Event radar — {TODAY}", "",
             f"Janela: {args.start} → {args.end} · áreas: {', '.join(args.areas)} · regiões: {', '.join(args.regions)}", "",
             "## Fontes", ""] + [f"- {l}" for l in log] + ["", f"## Total: {len(events)} eventos", ""]
    lines.append("Por região: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(e['region'] for e in events).items())))
    lines.append("Por ação: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(e['action'] for e in events).items())))
    lim = (dt.date.fromisoformat(TODAY) + dt.timedelta(days=60)).isoformat()
    due = sorted([e for e in events if e.get("deadline") and TODAY <= e["deadline"] <= lim], key=lambda e: e["deadline"])
    lines += ["", f"## CFPs que fecham em até 60 dias ({len(due)})", "", "| Fecha | Evento | Região | Evento em | Fit | Chance | CFP |", "|---|---|---|---|---|---|---|"]
    for e in due:
        lines.append(f"| {e['deadline']} | {e['name']} | {e['region']} | {e.get('date') or '?'} | {e['adherence']} | {e['acceptance']} | {e.get('cfp_url') or e.get('url') or ''} |")
    top = sorted([e for e in events if e["priority"] == "P1" and e["action"] != "feito"], key=lambda e: (-(e["adherence"] or 0), e.get("date") or "9"))[:30]
    lines += ["", f"## P1 (fit alto e chance razoável) — top {len(top)}", "", "| Data | Evento | Região | Ação | Fit | Chance | Link |", "|---|---|---|---|---|---|---|"]
    for e in top:
        lines.append(f"| {e.get('date') or '?'} | {e['name']} | {e['region']} | {e['action']} | {e['adherence']} | {e['acceptance']} | {e.get('url') or ''} |")
    lines += ["", "## Próximos 90 dias por região", ""]
    lim90 = (dt.date.fromisoformat(TODAY) + dt.timedelta(days=90)).isoformat()
    for reg in args.regions:
        sub = sorted([e for e in events if e["region"] == reg and e.get("date") and TODAY <= e["date"] <= lim90], key=lambda e: e["date"])
        lines.append(f"### {reg} ({len(sub)})")
        for e in sub[:40]:
            lines.append(f"- {e['date']} · {e['name']} · {e.get('location') or ''} · {e['action']} · fit {e['adherence']}")
        lines.append("")
    lines += ["", "> Fit = palavras-chave das áreas no nome/tags (0-100). Chance = heurística por porte do evento; revise à mão antes de decidir.",
              "> Prazos vindos de agregadores devem ser confirmados na fonte: `python radar.py verify-cfp <url>`."]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- main
TODAY = dt.date.today().isoformat()


def cmd_fetch(args):
    os.makedirs(os.path.join(args.out, "raw"), exist_ok=True)
    log = []
    areas_rx = {a: AREAS[a][0] for a in args.areas if a in AREAS}
    unknown = [a for a in args.areas if a not in AREAS]
    if unknown:
        log.append(f"AVISO áreas desconhecidas ignoradas: {unknown} (válidas: {', '.join(AREAS)})")
    topics = sorted({t for a in args.areas for t in AREAS.get(a, ("", []))[1]})
    y0, y1 = int(args.start[:4]), int(args.end[:4])
    years = list(range(y0, y1 + 1))
    raw = []
    if "developers.events" not in args.skip:
        raw += safe(src_developers_events, "developers.events", log)
    if "confs.tech" not in args.skip and topics:
        raw += safe(lambda: src_confs_tech(topics, years), f"confs.tech {topics} {years}", log)
    if "javaconferences" not in args.skip and ("java" in args.areas):
        raw += safe(src_javaconferences, "javaconferences.org", log)
    if "cafebugado" not in args.skip and ("BR" in args.regions):
        raw += safe(src_cafebugado, "cafebugado (BR)", log)
    if args.sheet:
        raw += safe(lambda: src_gsheet(args.sheet), f"gsheet {args.sheet}", log)
    for p in args.extra or []:
        raw += safe(lambda p=p: src_extra(p), f"extra {p}", log)
    with open(os.path.join(args.out, "raw", "all-sources.json"), "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=1)
    events = [unify(e, areas_rx) for e in raw if e.get("name")]
    events = [e for e in events if in_window(e, args.start, args.end)]
    events = [e for e in events if e["region"] in args.regions]
    if not args.all_areas:
        events = [e for e in events if e["adherence"] >= args.min_fit or any(s.startswith("extra") or s.startswith("gsheet") for s in e["sources"])]
    events = dedupe(events)
    events.sort(key=lambda e: (e.get("date") or "9999", e["name"]))
    data = {"generated": TODAY, "owner": args.owner, "window": {"from": args.start, "to": args.end}, "areas": args.areas, "regions": args.regions,
            "talks": [], "scoring_notes": {"adherence": "palavras-chave das áreas no nome/tags/local (heurística)", "acceptance": "heurística por porte/tier do evento; revisar manualmente"},
            "sources_log": log, "events": events}
    with open(os.path.join(args.out, "events.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8") as f:
        f.write(summary_md(events, args, log))
    print("\n".join(log))
    print(f"events.json: {len(events)} eventos -> {args.out}")


def cmd_verify(args):
    for u in args.urls:
        try:
            print(json.dumps(verify_cfp(u), ensure_ascii=False, indent=1))
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"url": u, "error": f"{type(e).__name__}: {e}"}))


def cmd_panel(args):
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel.html")
    os.makedirs(args.out, exist_ok=True)
    shutil.copy(src, os.path.join(args.out, "index.html"))
    print(f"painel copiado para {args.out}/index.html — abrir com: python -m http.server 8768 --directory {args.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--areas", default="java,ai", help=f"lista separada por vírgula: {', '.join(AREAS)}")
    f.add_argument("--regions", default="BR,LATAM,NA,EU,ONLINE,OTHER")
    f.add_argument("--from", dest="start", default=TODAY)
    f.add_argument("--months", type=int, default=12)
    f.add_argument("--out", default="./radar")
    f.add_argument("--sheet", help="ID da planilha Google pública (ou ID:gid1,gid2)")
    f.add_argument("--extra", action="append", help="JSON extra (pesquisa manual/agentes/overrides); pode repetir")
    f.add_argument("--skip", default="", help="fontes a pular: developers.events,confs.tech,javaconferences,cafebugado")
    f.add_argument("--min-fit", type=int, default=40, help="descarta eventos abaixo deste fit (exceto extra/gsheet)")
    f.add_argument("--all-areas", action="store_true", help="não filtra por fit (traz tudo da janela/região)")
    f.add_argument("--owner", default="")
    v = sub.add_parser("verify-cfp")
    v.add_argument("urls", nargs="+")
    p = sub.add_parser("panel")
    p.add_argument("--out", default="./radar")
    args = ap.parse_args()
    if args.cmd == "fetch":
        args.areas = [a.strip() for a in args.areas.split(",") if a.strip()]
        args.regions = [r.strip().upper() for r in args.regions.split(",") if r.strip()]
        args.skip = [s.strip() for s in args.skip.split(",") if s.strip()]
        d0 = dt.date.fromisoformat(args.start)
        m = d0.month - 1 + args.months
        args.end = dt.date(d0.year + m // 12, m % 12 + 1, min(d0.day, 28)).isoformat()
        cmd_fetch(args)
    elif args.cmd == "verify-cfp":
        cmd_verify(args)
    else:
        cmd_panel(args)


if __name__ == "__main__":
    main()
