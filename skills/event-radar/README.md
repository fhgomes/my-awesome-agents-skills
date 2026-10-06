# event-radar

Map tech events and CFPs by **area** (Java, AI, cloud, security, architecture, data, fintech, career, GDG, Microsoft,
Oracle…) and **region** (Brazil, Latin America, US/Canada, Europe, online) over a window of months — with CFP deadlines,
an estimated acceptance chance and a self-contained HTML panel. Skill content in PT-BR.

## Purpose

Answer "where can I go / where can I submit a talk in the next N months?" without a browser: plain-HTTP scraping of
public calendars, deadline verification straight from Sessionize/PaperCall, and a playbook for fanning out parallel
research agents per region when aggregators fall short (local JUGs, meetups, DevFests, LatAm, vendor events).

## Features

- **`scripts/radar.py fetch`** — pulls developers.events, confs.tech, javaconferences.org, eventos.cafebugado.com.br
  (BR) and optional Google Sheet / extra JSON; filters by window, areas and regions; dedupes; scores fit and acceptance;
  writes `events.json` + `summary.md` (CFPs closing in 60 days, P1 list, next 90 days per region). Stdlib only.
- **`scripts/radar.py verify-cfp URL…`** — reads the real deadline (with timezone) from Sessionize, PaperCall or a
  generic CFP page. Organizers extend deadlines; never trust a cached date.
- **`scripts/radar.py panel`** — copies `panel.html` (vanilla JS, dark/light, filters, timeline, sortable table) next
  to `events.json`.
- **`references/`** — source catalog (what works over HTTP, what needs a browser), unified schema + scoring rubric,
  per-region playbook, and the brief template for parallel research agents.

## Quick start

```bash
python scripts/radar.py fetch --areas java,ai --regions BR,LATAM,NA,EU,ONLINE --months 12 --out ./radar
python scripts/radar.py panel --out ./radar
python -m http.server 8768 --directory ./radar   # open http://localhost:8768
python scripts/radar.py verify-cfp https://sessionize.com/devnexus-2027/
```

## Output schema (per event)

`id, name, region, location, format, date, date_end, date_status, organizer, category[], url, cfp_url, cfp_status,
deadline, deadline_status, speaker_perks, cost, talk_fit[], adherence (0-100), adherence_why, acceptance (0-100),
acceptance_why, prestige, competition, action, priority, status, notes, tags[], sources[], confidence, verified_on`

Pass your own research as `--extra file.json` using the same fields (or `start_date`/`end_date`/`cfp_deadline`/
`fit_score`/`accept_prob` — they are mapped). Same `id` forces a merge.

## Origin

Built from a real run (September 2026): 426 events across 5 regions, 5 parallel research agents, one corrected deadline
(a CFP recorded as closed was actually extended by 8 days). See `examples/`.
