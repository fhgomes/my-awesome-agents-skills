---
name: video-editing
description: >-
  Cortar, juntar, converter formato (9:16 Reels/Shorts/TikTok) e queimar
  legendas em vídeo com ffmpeg (WSL) e faster-whisper GPU. Use SEMPRE que o
  usuário pedir "corta o vídeo", "faz um corte", "junta os trechos", "versão
  pra Reels/Shorts/TikTok", "9:16", "fundo desfocado", "queima a legenda",
  "burn subtitles", "legenda estilo CapCut / palavra por palavra", "cold open",
  extrair trecho/frame de vídeo, concat de clipes, ou qualquer edição de vídeo
  por linha de comando. Também cobre: specs de entrega por plataforma (bitrate,
  duração máx, safe zone, -14 LUFS), escolher QUAL trecho vira corte (rubrica
  de hook/coerência/emoção), reenquadre 9:16 seguindo quem fala (face-pan) e
  detecção da GPU/NVENC desta máquina (scripts/gpu_probe.py — NUNCA hardcode
  params de placa). Inclui scripts prontos (word_captions.py, face_pan.py,
  gpu_probe.py) — não reescreva do zero. Para transcrição de palestras/frases
  (SRT longo, TXT), use a skill media-transcription.
---

# Edição de vídeo (ffmpeg WSL + legendas word-level GPU)

## Fatos desta máquina (validados 2026-08-06)

⚠️ **NUNCA hardcode params de GPU.** Rode `scripts/gpu_probe.py` — a skill roda
em mais de uma máquina (Fernando: GTX 1650 **SUPER**; esposa: **RTX 5060**) e
cada uma pede preset/codec diferente. Ver `references/platform-specs.md`.

```bash
python "C:/Users/ferna/.claude/skills/video-editing/scripts/gpu_probe.py"
ARGS=$(python .../gpu_probe.py --encode-args --quality high)   # pra script
```

- **ffmpeg no WSL Ubuntu (4.4.2, CPU-only)** para filtros/concat/extract:
  `wsl.exe -d Ubuntu -- bash -c ...`.
- **ffmpeg no WINDOWS com NVENC (instalado 2026-08-09, ordem do Fernando)**:
  `C:\Users\ferna\Tools\ffmpeg71\ffmpeg-n7.1-latest-win64-gpl-7.1\bin\ffmpeg.exe`
  (BtbN n7.1). **USE ESTE para encodes/burns longos** — h264_nvenc na 1650 Super
  a ~8-15x o x264 medium; params validados:
  `-c:v h264_nvenc -preset p5 -rc vbr -cq 22 -b:v 0` (+ `-bf 3`: a 1650 Super
  **suporta B-frames em H.264 E HEVC** — confirmado por encode real 2026-08-09,
  44 B-frames num teste HEVC; a tabela "TU116 não tem B-frame HEVC" está errada).
  libass acha fontes do sistema sozinho (SEM fontsdir; paths relativos: `cd` na
  pasta antes).
  ⚠️ O winget (Gyan.FFmpeg = ffmpeg 8) EXIGE driver NVIDIA ≥610 e o driver
  atual é 595.97 → "nvenc API 13.1 required" — por isso o build 7.1 pinado.
  ⚠️ NVENC NÃO existe dentro do WSL2 (GPU-PV só expõe CUDA compute).
- Python com faster-whisper + CUDA fica no **Windows** (GTX 1650 4 GB) — ver
  skill media-transcription. Transcrição roda no Windows, queima roda no WSL.
- Paths no WSL: `C:\Users\ferna\Downloads` → `/mnt/c/Users/ferna/Downloads`.
- Outputs finais em Downloads ao lado do original; intermediários em `/tmp`
  do WSL (ext4 é mais rápido que /mnt/c) — limpe no fim.

## Regras de ouro (aprendidas na dor)

0. **ORQUESTRAÇÃO (2026-08-09, custou 2 rodadas de workflow): subagente NUNCA
   deixa encode em `run_in_background` e retorna "aguardando"** — o processo
   morre junto com o agente/workflow (seg7 de 794s morreu 2x assim). Padrões
   que funcionam: (a) encodes longos rodam como background do LOOP PRINCIPAL
   (sobrevivem entre turnos e notificam); (b) subagente só roda foreground
   (timeout ≤10 min — quebrar encode longo em metades + concat); (c) detach
   REAL dentro do WSL: `nohup bash /tmp/x.sh > /tmp/x.log 2>&1 &` + waiter
   foreground. Subagentes ficam com análise/legendas/QA (trabalho de arquivo).
   GPU: transcrições SEMPRE sequenciais (4 GB, um whisper por vez); o ffmpeg
   do WSL é CPU-only (sem NVENC) — máx 2-3 encodes paralelos (dividem cores).
   Mute de nome: janela com folga ≥0,15s de cada lado e RE-CHECAR volumedetect
   (fronteira de frame AAC vaza: janela exata deu −37 dB; alargada, −91 dB).

1. **SEMPRE `ffmpeg -nostdin`**. Sem isso, ffmpeg lê o stdin, entra em modo
   interativo e já gerou 305 MB de log de debug numa sessão (o resto do script
   vira "teclas" para o ffmpeg).
2. **Scripts via ARQUIVO, nunca pipe**: `tr -d '\r' < /mnt/c/.../x.sh >
   /tmp/x.sh && bash /tmp/x.sh`. Pipe `| bash` alimenta o stdin do ffmpeg
   (ver regra 1); o `tr -d '\r'` mata CRLF do Windows. Com AGENTES PARALELOS,
   use nome de /tmp ÚNICO por agente (`/tmp/cunha-x.sh`, `/tmp/marco-x.sh`) —
   em 2026-08-08 dois agentes compartilhando `/tmp/x.sh` se atropelaram e um
   corte morreu no meio ("glevel: command not found").
3. **Quoting inline não sobrevive** à cadeia GitBash → wsl.exe → bash
   (`$VAR` expande vazio, aspas somem). Qualquer comando com variável ou
   filter_complex vai para script-arquivo.
4. **Vídeo de celular: ffprobe "cru" mente sobre orientação.** VID_*.mp4
   1920x1080 pode ser VERTICAL (rotação em display matrix). O re-encode aplica
   a rotação sozinho (autorotate). Antes de planejar filtro 9:16, extraia um
   frame e OLHE (Read no .jpg). Se o vídeo já é 9:16 nativo, a receita de fundo
   desfocado é no-op — pule.
5. **QA visual sempre**: após cada render, extraia 2-3 frames em pontos
   conhecidos e confira (enquadramento, legenda certa, formato).

## Receita: corte com emenda (cold open + take)

Re-encode com params idênticos → concat sem re-encode:

```bash
set -e
IN=/mnt/c/Users/ferna/Downloads/ORIGINAL.mp4
OUT=/mnt/c/Users/ferna/Downloads
mkdir -p /tmp/work && cd /tmp/work

# -ss/-to DEPOIS do -i = frame-accurate no timeline original
ffmpeg -nostdin -y -i "$IN" -ss 00:03:28.0 -to 00:03:31.5 \
  -c:v libx264 -preset slow -crf 18 -r 30 \
  -c:a aac -b:a 192k -ar 48000 -ac 2 p1.mp4 -loglevel error
ffmpeg -nostdin -y -i "$IN" -ss 00:00:24.0 -to 00:01:38.0 \
  -c:v libx264 -preset slow -crf 18 -r 30 \
  -c:a aac -b:a 192k -ar 48000 -ac 2 p2.mp4 -loglevel error

printf "file 'p1.mp4'\nfile 'p2.mp4'\n" > concat.txt
ffmpeg -nostdin -y -f concat -safe 0 -i concat.txt -c copy "$OUT/FINAL.mp4" -loglevel error
```

Verifique a duração final com ffprobe (soma dos trechos ±0,1s).

## Receita: 9:16 com fundo desfocado (só p/ source horizontal!)

```bash
ffmpeg -nostdin -y -i in.mp4 -filter_complex \
"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30[bg];[0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" \
-c:v libx264 -crf 20 -preset slow -c:a copy out-reels.mp4
```

## Receita: 1:1 p/ LinkedIn a partir de 9:16 (blur lateral + legenda, 1 encode)

LinkedIn corta prévia de 9:16 no desktop; 1:1 rende melhor. Reaproveite o
.ass do 9:16 via sed (preserva correções de QA — NÃO re-transcreva):

```bash
sed 's/PlayResY: 1920/PlayResY: 1080/; s/,88,/,64,/; s/,60,60,400,1/,60,60,90,1/' \
  CORTE-words.ass > LINKEDIN-words.ass
```

Formato + legenda numa filter chain só (uma geração de encode a menos):

```bash
cp LINKEDIN-words.ass /tmp/li.ass
ffmpeg -nostdin -y -loglevel error -i CORTE.mp4 -filter_complex \
"[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,gblur=sigma=30[bg];[0:v]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=/tmp/li.ass:fontsdir=/mnt/c/Windows/Fonts" \
-c:v libx264 -crf 18 -preset slow -c:a copy LINKEDIN-SUB.mp4
```

## Receita: 9:16 seguindo quem fala (face-pan) — alternativa ao fundo desfocado

Para entrevista/podcast 16:9 com DUAS pessoas e câmera estática: em vez de
encolher o vídeo no meio do quadro (fundo desfocado), enquadra em tela cheia
quem está falando, com hard cut. `scripts/face_pan.py` (portado do clipify,
MIT) — sem OpenCV, sem ML: mede o brilho (`signalstats.YAVG`) de duas ROIs de
boca/queixo e deduz quem fala pela variação.

```bash
# 1) extrai frame e VOCÊ olha pra achar as ROIs (regra 4/5: sempre olhe)
python .../scripts/face_pan.py probe --video IN.mp4 --at 5

# 2) confira as caixas desenhadas (itere no MÁXIMO 2x — é tolerante)
python .../scripts/face_pan.py probe --video IN.mp4 --at 5 \
  --left 100,300,500,400 --right 1300,300,500,400

# 3) gera a filter chain
VF=$(python .../scripts/face_pan.py build --video IN.mp4 \
      --left 100,300,500,400 --right 1300,300,500,400)

# 4) queima junto com a legenda (1 encode só)
ffmpeg -nostdin -y -i IN.mp4 -vf "$VF,ass=/tmp/subs.ass:fontsdir=/mnt/c/Windows/Fonts" \
  -c:v libx264 -crf 18 -preset slow -c:a copy OUT.mp4
```

Validado 2026-08-09 em vídeo sintético: troca detectada a 3,033s contra
ground truth de 3,000s (1 frame de erro, da janela de suavização).

- ROI = **boca + queixo**, evitando mãos e microfone (mão gesticulando engana).
- `--margin 1.15` é a histerese: só troca quando o outro passa 15% do atual —
  sem isso o corte pisca no silêncio. Suba se ficar instável.
- `--min-dur 1.0` descarta troca curta demais pra ler na tela.
- **Só funciona com câmera estática dentro do corte.** Se a câmera se mexe ou
  tem corte de plano, o método cai — use o fundo desfocado.
- Uma pessoa só: não precisa disso, `crop` centralizado resolve.

## Receita: legendas word-level estilo CapCut (automatizado)

SRT de transcrição normal (blocos de frase, 10-15s) fica FEIO queimado em
Reels. O caminho: regenerar word-level e queimar.

1. **Transcreva o VÍDEO JÁ CORTADO** (nunca o original — os timestamps nascem
   certos no timeline final, sem re-sincronizar):

```bash
python "C:/Users/ferna/.claude/skills/video-editing/scripts/word_captions.py" \
  "C:/Users/ferna/Downloads/CORTE.mp4" --out-dir "C:/Users/ferna/Downloads" \
  --base CORTE --language en --prompt "nomes próprios e jargão esperado"
```

   Gera `CORTE-words.ass` (pronto p/ queimar, 1080x1920, Arial Black 88,
   UPPERCASE, MarginV 400 = acima da UI do Reels) e `CORTE-words.srt` (mesmos
   blocos, p/ conferência ou CapCut). Flags: `--max-words 3 --max-dur 1.2
   --res --font --font-size --margin-v --no-upper`. GPU: 77s de vídeo ≈ 13s.
   Cheque `nvidia-smi` antes (GPU ocupada = arrastar; ver media-transcription).

2. **QA no .srt** (Read completo — é curto): erros típicos são siglas
   ("SSD" por "SDD") e hífens do tokenizador ("CO -WORKER"). Corrija com sed
   **nos dois arquivos** (.srt E .ass). Repetições de fala real ("that that")
   deixe — é como a pessoa falou.

3. **Queime no WSL** (fontsdir dá acesso às fontes do Windows — Arial Black
   renderiza; sem isso o libass cai em DejaVu):

```bash
cp "$OUT/CORTE-words.ass" /tmp/subs.ass
ffmpeg -nostdin -y -loglevel error -i "$OUT/CORTE.mp4" \
  -vf "ass=/tmp/subs.ass:fontsdir=/mnt/c/Windows/Fonts" \
  -c:v libx264 -crf 18 -preset slow -c:a copy "$OUT/CORTE-SUB.mp4"
```

4. QA visual: frames em 2-3 timestamps com texto conhecido do .srt.

5. **Re-estruturar um corte que já tem legendas corrigidas** (trocar/remover
   segmento, encurtar intro): NÃO re-transcreva — edite os blocos existentes
   por script (remover faixa de tempo, shiftar o resto pelo delta exato das
   durações medidas). Re-transcrever reintroduz alucinações de emenda (toda
   fronteira de corte gera lixo: "PUZZLES", "PUZZLE HOUSE, YOU GOT IT") e
   perde as correções manuais. Whisper também ENGOLE o cold open curto quando
   emendado (fundiu com a fala seguinte) — sempre confira os primeiros blocos
   contra o que foi falado.

6. **Fluxo superior (validado 2026-08-08, 5 cortes): transcrever o ORIGINAL
   1x e DERIVAR as legendas de cada corte** com
   `scripts/word_captions_map.py` (variante com `--words-json` e
   `--segments "a-b,c-d"` em segundos do timeline original → remapeia as
   palavras pro timeline concatenado, na ordem dos segmentos). Vantagens:
   os MESMOS word timestamps planejam os pontos de corte com fronteira exata
   de palavra; zero alucinação de emenda; cold open nunca é engolido; N cortes
   do mesmo vídeo = 1 transcrição. ARMADILHA: confira palavra ESTICADA na
   fronteira (um "Cunha," de 1s quase foi cortado no meio — cheque o start
   real da primeira palavra no JSON, não o bloco do SRT). Roda em CPU int8
   (~0,23x tempo real) — usar quando a GPU estiver com jogo aberto
   (nvidia-smi mostrando League/jogo = NÃO suba modelo CUDA).

## Receita: transição hook→conteúdo (pesquisado 2026-08: Gemini+ChatGPT+Perplexity convergiram)

O padrão 2025-2026 de retention editing para cold open → take (mesma cena)
NÃO é transição chamativa — é **snap punch-in permanente + whoosh grave sutil**:

- **Visual**: no frame do corte, o take entra ampliado (efeito "câmera B") e
  PERMANECE ampliado. Reels 9:16: ~10%; LinkedIn 1:1: ~6% + subir o
  enquadramento ~20px (muda a linha dos olhos). Corte seco, sem animação.
- **Som**: whoosh LOW-END (grave/abafado, nunca agudo). Começa ~80ms antes do
  corte, pico exatamente no corte, cauda ~180ms. Volume ~18dB abaixo dos
  PICOS da voz (medir com volumedetect; voz de celular: mean ~-11, max ~0dBFS
  → whoosh a -12dB do arquivo gerado; LinkedIn -15dB).
- **EVITAR (datado, "template CapCut/Hormozi 2021"unânime nas 3 fontes)**:
  white flash forte, glitch/RGB, whip pan artificial, zoom >15%, riser,
  bass drop, VHS, film burn, whoosh agudo "espada ninja".

Asset pronto: `assets/whoosh-lowend-260ms.wav` (pico interno em ~80ms →
adelay = (t_corte - 0.08)*1000). Gerador: `scripts/make_whoosh.sh`.

Filter chain (preserva timeline → .ass continua válido; punch via trim/concat):

```
[0:v]trim=0:3.5,setpts=PTS-STARTPTS[v1];
[0:v]trim=3.5,setpts=PTS-STARTPTS[vz];
[vz]crop=w=980:h=1744:x=50:y=68,scale=1080:1920,setsar=1[v2];   # 10%: 1080/1.1→980 par, y central-20
[v1][v2]concat=n=2:v=1:a=0[vc];
[vc]ass=/tmp/subs.ass:fontsdir=/mnt/c/Windows/Fonts[vout];
[1:a]adelay=3420|3420,volume=-12dB[wh];
[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]
```

Validar áudio sem ouvir: `showspectrumpic` do trecho do corte (whoosh = mancha
low-end + coluna de transiente no corte); punch: frames pré/pós corte.

**Calibração de gosto (lição 2026-08)**: a versão "invisível" da pesquisa
(punch estático 10% + whoosh -19dB) foi rejeitada pelo dono — "tá muito seco,
não tem NADA". Quando o usuário pedir transição PERCEPTÍVEL/suave, ir direto
no combo validado: zoom animado 100→112% nos últimos 0,3s do hook (zoompan,
easing pow 2) + white flash rampa 0,15s+0,15s + whoosh -6dB (Reels) / zoom
10% e whoosh -9dB (LinkedIn). O "caricato" a evitar é o som AGUDO e efeitos
de 1s+ — flash suave curto e whoosh grave audível são o padrão growth. Chain
completa em render-v3-*.sh desta sessão; zoom+flash ANTES do ass e, no 1:1,
ANTES do layout (flash cobre o quadro todo).

Refinamentos do workflow de pesquisa (2026-08, 4 agentes, receitas EXECUTADAS
no 4.4.2):

- **Variante punch-OUT** (hook a ~112-115% → take a 100%): mesma eficácia, e o
  take LONGO fica em resolução nativa (upscale só nos 3,5s do hook) — melhor
  nitidez; hook mais "íntimo/tenso". Considerar como default em vídeos longos.
- Regra do pico: o PICO do SFX cai no frame do corte (tolerância +1-2 frames);
  arquivo começa 80-300ms antes. Volume: 6-19dB abaixo dos PICOS da fala
  (mais presente p/ hype, mais baixo p/ entrevista profissional).
- Dosagem: máx 2-3 punch-ins/min; 1 transição "bold" nos primeiros 5s e só.
- Opções avançadas: J-cut (áudio do take entra ~300ms antes do corte de vídeo,
  costura fina); riser 0,8-1,5s sob o fim do hook com pico no corte (nunca
  competindo com a fala).
- Zoom ANIMADO no ffmpeg 4.4: crop com expressões de t NÃO anima — usar
  `zoompan=d=1`. Punch estático por trecho: trim+crop fixo+scale+concat (ok).
  **No 4.4.2 do WSL o zoompan NÃO tem `in_time`/`it`** (validado 2026-08-08:
  `ffmpeg -h filter=zoompan | grep -c in_time` → 0). Easing por FRAME com `on`:
  trecho de 0,3s a 30fps = 9 frames → `z='min(1.12,1+0.12*pow(on/8,2))'`
  + `x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1`.
- White flash: **NUNCA aplique o par fade out/in no timeline GLOBAL pós-concat**
  (armadilha 2026-08-08, deu vídeo 100% branco): `fade=t=out` SEGURA a cor até o
  fim do vídeo depois de st+d, e `fade=t=in` pinta de branco TUDO antes do st.
  O certo é POR SEGMENTO, antes do concat: no fim do segmento do hook
  `...,fade=t=out:st=HOOKLEN-0.15:d=0.15:c=white[vb]` e no início do corpo
  `...,fade=t=in:st=0:d=0.15:c=white[vc]` (st=0 não tem "antes" pra pintar).
  Bônus: o fade-in mascara cauda de palavra cortada no início do corpo.
  Nunca o preset de 15 frames do CapCut.
- Whoosh "airy" alternativo (sweep): anoisesrc + `asendcmd` varrendo lowpass
  300→4600→900Hz em 400ms (mais swoosh, menos thud que o asset da skill).

ATENÇÃO: NÃO deixe assets em `/tmp` do WSL entre comandos — a distro desliga
por inatividade e limpa `/tmp` no boot. Use o scratchpad (`/mnt/c/...`).

## Entrega: specs de plataforma (Reels / TikTok / Shorts / LinkedIn)

Ver **`references/platform-specs.md`** — bitrate, duração máx, tamanho de
arquivo, safe zones e o comando de QA que desenha as guias num frame.

Os 3 fatos que mais mordem:

1. **-14 LUFS em todas.** Se entregar mais alto, a plataforma abaixa e sobra a
   distorção: `-af loudnorm=I=-14:TP=-1:LRA=11`.
2. **Safe zone da base.** `MarginV 400` (default do `word_captions.py`) passa em
   TikTok/IG/Shorts. Para o MESMO arquivo nas três, subir p/ 450.
3. **Bitrate do Reels é baixo** (4.5M) comparado a Shorts (12M) — mandar 12M
   pro IG só engorda o arquivo, ele reencoda igual.

## Dicas de edição p/ Reels (decisões que já tomamos)

- Intro de credenciais (15-25s) NÃO entra no corte — vira caption queimada no
  primeiro frame ("Quarkus contributor" etc.).
- Cold open: 2-4s da frase mais forte, depois o take completo.
- Falsos inícios e "Okay." finais ficam fora.
- Título/caption estática por cima é melhor no CapCut/editor; o que dá para
  automatizar aqui é a legenda word-level (receita acima).
