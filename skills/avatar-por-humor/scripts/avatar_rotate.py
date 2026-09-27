#!/usr/bin/env python3
"""
pepper_avatar.py — troca o avatar da Pepper NO SERVIDOR do Fernando conforme o dia.

Usa `PATCH /guilds/{guild}/members/@me` (avatar por servidor), não `PATCH /users/@me`:
não mexe no perfil global do bot e escapa do cooldown opaco de troca de avatar global.

Escolha do "humor" do dia, em ordem de prioridade:
  1. --mood <nome>            → forçado na mão
  2. agenda cheia (>= BUSY)   → "foco"
  3. segunda-feira            → "briefing" (modo plano da semana)
  4. resto                    → sorteio entre os humores disponíveis, evitando os 8 últimos

Os humores vêm de avatars/moods.json, gerado a partir da reference-library (as 40 canônicas
v6 recortadas em 512x512 centradas no rosto) + os 3 recortes legados do lote v5. Para
acrescentar foto nova: recorte em avatars/crop/ e acrescente a entrada no moods.json.

Idempotente: guarda o último humor aplicado e não chama a API se nada mudou
(use --force para aplicar mesmo assim). Humor sem arquivo correspondente é ignorado.

Cron: 0 7 * * *  (crontab -u unando)
"""

import argparse
import base64
import json
import os
import random
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/home/unando/.openclaw/workspace")

AVATAR_DIR = "/home/unando/.openclaw/workspaces/pepper/avatars/crop"
STATE_FILE = "/home/unando/.openclaw/workspaces/pepper/avatars/.state.json"
HISTORY_FILE = "/home/unando/.openclaw/workspaces/pepper/avatars/history.jsonl"
ENV_FILE = "/home/unando/.openclaw/.env"
GUILD = "999758825332674630"
UA = "DiscordBot (https://fhgomes.com, 1.0)"
TZ_BR = timezone(timedelta(hours=-3))
BUSY = 5  # compromissos no dia a partir dos quais o dia conta como "cheio"

MOODS_FILE = "/home/unando/.openclaw/workspaces/pepper/avatars/moods.json"

# Fallback se o manifesto sumir: as três de sempre.
MOODS_LEGADO = {
    "confiante": "confiante.png",
    "foco": "foco.png",
    "briefing": "briefing.png",
}


def load_manifest():
    """humor -> ficha. Vem de moods.json, gerado a partir da reference-library."""
    try:
        with open(MOODS_FILE, encoding="utf-8") as f:
            return json.load(f).get("humores", {})
    except Exception:
        return {m: {"arquivo": a, "reference_id": None, "papeis": ["geral"]}
                for m, a in MOODS_LEGADO.items()}


MANIFEST = load_manifest()
# mantido com o nome antigo porque o pepper_api.py importa PA.MOODS
MOODS = {m: v["arquivo"] for m, v in MANIFEST.items()}
REF_PARA_HUMOR = {v["reference_id"]: m for m, v in MANIFEST.items() if v.get("reference_id")}
RECENTES = 8  # quantos humores recentes o sorteio evita repetir


def read_env(name):
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"')
    return ""


def available():
    return {m: f for m, f in MOODS.items() if os.path.exists(os.path.join(AVATAR_DIR, f))}


def events_today():
    try:
        import google_api as G
        now = datetime.now(TZ_BR)
        ini = now.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = ini + timedelta(days=1)
        r = G.get_all_calendar_events(
            time_min=ini.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            time_max=fim.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            max_results=50)
        return len(r.get("items", []))
    except Exception as e:
        print(f"[aviso] não consegui ler a agenda ({e}); sigo sem ela", file=sys.stderr)
        return -1


def papeis(mood):
    return MANIFEST.get(mood, {}).get("papeis", ["geral"])


def com_papel(av, papel):
    return [m for m in av if papel in papeis(m)]


def recentes(n=RECENTES):
    """Últimos humores aplicados, do mais novo para o mais velho."""
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            linhas = [json.loads(l) for l in f if l.strip()]
    except Exception:
        return []
    return [e.get("mood") for e in reversed(linhas) if e.get("mood")][:n]


def sortear(av, atual):
    """Sorteia evitando o atual e o que saiu há pouco — com 43 fotos, repetir é burrice."""
    evitar = set(recentes()) | ({atual} if atual else set())
    pool = [m for m in av if m not in evitar] or [m for m in av if m != atual] or list(av)
    return random.choice(pool)


def pick(av, forced=None, atual=None):
    if forced:
        # aceita tanto o humor ("cafe-conversa") quanto o reference_id ("pepper_ref_043")
        alvo = REF_PARA_HUMOR.get(forced, forced)
        if alvo not in av:
            sys.exit(f"humor '{forced}' não disponível. Tem: {', '.join(sorted(av))}")
        return alvo, "forçado na linha de comando"
    n = events_today()
    if n >= BUSY:
        pool = com_papel(av, "foco")
        if pool:
            return sortear(pool, atual), f"agenda cheia ({n} compromissos hoje)"
    if datetime.now(TZ_BR).weekday() == 0:
        pool = com_papel(av, "briefing")
        if pool:
            return sortear(pool, atual), "segunda-feira — plano da semana"
    return sortear(av, atual), f"sorteio do dia ({n if n >= 0 else '?'} compromissos)"


def apply(mood, av, token):
    path = os.path.join(AVATAR_DIR, av[mood])
    data = "data:image/png;base64," + base64.b64encode(open(path, "rb").read()).decode()
    req = urllib.request.Request(
        f"https://discord.com/api/v10/guilds/{GUILD}/members/@me",
        data=json.dumps({"avatar": data}).encode(),
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json", "User-Agent": UA},
        method="PATCH")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.load(r).get("avatar")


def record(entry):
    """Uma linha por aplicacao efetiva, no workspace da Pepper — ela consegue ler."""
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[aviso] nao consegui gravar o historico ({e})", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mood", help=f"forçar um humor: {', '.join(sorted(MOODS))}")
    ap.add_argument("--force", action="store_true", help="reaplicar mesmo se o humor não mudou")
    ap.add_argument("--list", action="store_true", help="listar humores disponíveis e sair")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true", help="saida em JSON (para o pepper-api)")
    ap.add_argument("--origem", default="cron", help="quem pediu: cron, pepper, nando")
    ap.add_argument("--motivo", help="sobrescreve o texto do motivo no log e no historico")
    a = ap.parse_args()

    av = available()
    if a.list:
        for m, f in sorted(MOODS.items()):
            fic = MANIFEST.get(m, {})
            print(f"  {m:34} {'OK ' if m in av else '-- '} {','.join(fic.get('papeis', [])):28} "
                  f"{fic.get('reference_id') or '-':15} {f}")
        return
    if not av:
        sys.exit(f"nenhuma imagem em {AVATAR_DIR}")

    state = {}
    if os.path.exists(STATE_FILE):
        try:
            state = json.load(open(STATE_FILE))
        except Exception:
            pass

    mood, motivo = pick(av, a.mood, atual=state.get("mood"))
    if a.motivo:
        motivo = a.motivo
    stamp = datetime.now(TZ_BR).strftime("%Y-%m-%d %H:%M")
    if state.get("mood") == mood and not a.force and not a.dry_run:
        if a.json:
            print(json.dumps({"trocou": False, "mood": mood, "motivo": motivo,
                              "detalhe": "já estava nesse humor"}, ensure_ascii=False))
        else:
            print(f"{stamp} | já está em '{mood}' ({motivo}) — nada a fazer")
        return
    if a.dry_run:
        if a.json:
            print(json.dumps({"trocou": False, "dry_run": True, "mood": mood,
                              "arquivo": av[mood], "motivo": motivo}, ensure_ascii=False))
        else:
            print(f"{stamp} | [dry-run] aplicaria '{mood}' ({av[mood]}) — {motivo}")
        return

    token = read_env("DISCORD_TOKEN_PEPPER")
    if not token:
        sys.exit("DISCORD_TOKEN_PEPPER não encontrado no .env")
    try:
        code, h = apply(mood, av, token)
    except urllib.error.HTTPError as e:
        sys.exit(f"{stamp} | FALHA HTTP {e.code}: {e.read().decode()[:200]}")
    rid = MANIFEST.get(mood, {}).get("reference_id")
    json.dump({"mood": mood, "at": stamp, "hash": h, "motivo": motivo, "reference_id": rid},
              open(STATE_FILE, "w"))
    record({"at": stamp, "mood": mood, "arquivo": av[mood], "reference_id": rid,
            "motivo": motivo, "http": code, "por": a.origem})
    if a.json:
        print(json.dumps({"trocou": True, "mood": mood, "arquivo": av[mood],
                          "motivo": motivo, "at": stamp, "http": code}, ensure_ascii=False))
    else:
        print(f"{stamp} | avatar -> '{mood}' ({av[mood]}) | {motivo} | HTTP {code}")


if __name__ == "__main__":
    main()
