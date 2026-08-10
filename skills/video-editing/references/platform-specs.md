# Specs de entrega por plataforma (Reels / TikTok / Shorts / LinkedIn)

Adaptado de `claude-shorts` (MIT, AgriciDaniel) + validacao local 2026-08-09.
Params de encode NAO estao hardcoded aqui: rode `scripts/gpu_probe.py` e use
o que ele devolver — a 1650 Super (Fernando) e a RTX 5060 (esposa) pedem
presets diferentes.

## Tabela de encode

Todos: **1080x1920, 9:16, H.264 High@4.2, yuv420p, `-movflags +faststart`**.

| | YouTube Shorts | TikTok | Instagram Reels |
|---|---|---|---|
| Duracao max | 60s (3min em 2025+) | 60s (10min c/ conta) | 90s (3min em 2025+) |
| Bitrate video | 12M alvo / 14M max | CRF 18, max 10M | 4.5M alvo / 5M max |
| Bufsize | 24M | 20M | 10M |
| Audio | AAC 192k / 48kHz | AAC 128k / 44.1kHz | AAC 128k / 44.1kHz |
| Tamanho max | 256 MB | 287 MB | 250 MB |

LinkedIn: preferir **1:1 (1080x1080)** — o feed desktop corta previa de 9:16
(ja e a decisao registrada na SKILL.md). Max 10min / 5 GB.

## Loudness: -14 LUFS em TODAS

Todas as plataformas normalizam pra ~-14 LUFS. Se voce entregar mais alto,
ELAS abaixam (e sobra so a distorcao). Normalize antes:

```
-af loudnorm=I=-14:TP=-1:LRA=11
```

- `I=-14` alvo integrado · `TP=-1` true peak (headroom anti-clip) · `LRA=11` faixa dinamica

Para entrega seria, `loudnorm` de **2 passadas** (a de 1 passada erra ~1 LU):
medir com `-af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null -`,
depois realimentar `measured_I/measured_TP/measured_LRA/measured_thresh`.

## Safe zones (onde a UI da plataforma cobre o video)

⚠️ **Nenhuma plataforma publica specs oficiais de pixel.** Os numeros abaixo
sao mediana de 10+ medicoes da comunidade a 1080x1920 e a margem de baixo
varia com o tamanho da legenda/descricao. Trate como ponto de partida e
CONFIRA com frame real antes de entregar campanha.

| Zona | TikTok | YT Shorts | IG Reels | Universal |
|---|---|---|---|---|
| Topo | 150px | 150px | 210px | 210px |
| Base | 320px | 350px | 340px | 450px |
| Esquerda | 60px | 60px | 40px | 60px |
| Direita | 120px | 150px | 100px | 150px |

**Legenda word-level**: `MarginV 400` (o default do `word_captions.py`) passa
em TikTok (320) e IG (340) e cobre YT Shorts (350). Para post cross-platform
sem retrabalho, **450px+** e o seguro. O valor 400 atual esta correto para o
uso de hoje — so suba se for postar o MESMO arquivo nas tres.

## Verificar safe zone sem adivinhar

Desenhe as guias num frame e OLHE (regra 5 da SKILL.md — QA visual sempre):

```bash
ffmpeg -nostdin -y -ss 3 -i IN.mp4 -frames:v 1 -vf \
"drawbox=x=0:y=0:w=1080:h=210:color=red@0.35:t=fill,\
drawbox=x=0:y=1470:w=1080:h=450:color=red@0.35:t=fill,\
drawbox=x=0:y=0:w=60:h=1920:color=orange@0.3:t=fill,\
drawbox=x=930:y=0:w=150:h=1920:color=orange@0.3:t=fill" /tmp/safezone.jpg
```

Nada essencial (rosto, legenda, logo) pode cair nas areas pintadas.

## Encode final: use o probe

```bash
# params certos pra ESTA maquina
ARGS=$(python "$SKILL/scripts/gpu_probe.py" --encode-args --quality high)

ffmpeg -nostdin -y -i IN.mp4 $ARGS \
  -af loudnorm=I=-14:TP=-1:LRA=11 \
  -c:a aac -b:a 128k -ar 44100 \
  -movflags +faststart OUT.mp4
```

Bitrate por plataforma (quando quiser bater a tabela em vez de CRF/CQ):
troque `-cq N -b:v 0` por `-b:v 4500k -maxrate 5000k -bufsize 10M` (Reels),
`-b:v 12M -maxrate 14M -bufsize 24M` (Shorts).

## Notas de hardware (medidas aqui, 2026-08-09)

- **GTX 1650 SUPER** (TU116, 4 GB, driver 595.97): h264_nvenc + hevc_nvenc,
  **B-frames OK nos dois** (confirmado por encode real: 44 B-frames num teste
  HEVC — a tabela "TU116 nao tem B-frame em HEVC" que circula por ai esta
  errada pra este chip). Sem AV1. Max ~3 encodes em paralelo. `-preset p5`.
  ⚠️ NVENC **nao existe dentro do WSL2** — encode NVENC roda no ffmpeg do
  Windows; o WSL fica com filtro/concat/libass em CPU.
- **RTX 5060** (Blackwell, maquina da esposa): NVENC 9a geracao, **AV1** e
  4:2:2, `-preset p6` com folga, mais sessoes simultaneas. Nao assuma —
  rode o probe la tambem; `--codec av1` so vale a pena se o destino aceitar
  (YouTube aceita AV1; TikTok/IG: manter H.264).
- Sem NVIDIA (ou codec ausente): o probe cai sozinho pra libx264/libx265/
  libsvtav1 em CPU.
