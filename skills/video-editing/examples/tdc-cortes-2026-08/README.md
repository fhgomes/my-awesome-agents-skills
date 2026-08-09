# Exemplos reais — cortes de entrevista TDC (sessão 2026-08)

Scripts **reais** de uma sessão de produção de cortes de entrevista para
Reels/LinkedIn (formato cold open + pergunta + resposta). Não são templates
polidos — são o pipeline como ele rodou, publicado como referência de uso da
skill [video-editing](../../SKILL.md).

> **Aviso**: os paths são da máquina de origem (`/mnt/c/Users/...`, scratchpad
> de sessão, WSL Ubuntu). São **exemplos, não plug-and-play** — adapte inputs,
> outputs e timestamps ao seu caso.

## Pipeline (na ordem em que roda)

1. **Probe + frames de inspeção** — `probe.sh`, `probe2.sh`, `extract2.sh`:
   ffprobe em JSON, extração de frame para OLHAR a orientação/qualidade real,
   e WAV 16 kHz mono para transcrição.
2. **Transcrição word-level 1x no ORIGINAL** — `word_captions_cpu.py`
   (variante CPU int8 do `scripts/word_captions.py` da skill, para quando a
   GPU está ocupada). Gera `-words.json` com timestamps por palavra; a flag
   `--segments "a-b,c-d"` **deriva as legendas de cada corte remapeando o
   timeline** — sem re-transcrever a emenda (zero alucinação de fronteira,
   cold open nunca é engolido, N cortes = 1 transcrição). Os mesmos timestamps
   planejam os pontos de corte com fronteira exata de palavra.
3. **Corte por segmentos frame-accurate + concat** — `cut.sh`, `cunha-cut.sh`,
   `marco-cut.sh`: re-encode de cada segmento com params idênticos
   (`-ss/-to` depois do `-i`) e concat sem re-encode.
4. **Transição hook→conteúdo** — `render-reels.sh`, `render-linkedin.sh`,
   `cunha-render.sh`: zoom animado 100→112% (zoompan com easing por frame) +
   white flash **por segmento** (fade out/in antes do concat — nunca no
   timeline global) + whoosh low-end alinhado ao frame do corte
   (`assets/whoosh-lowend-260ms.wav` da skill).
5. **Burn de legendas .ass** — na mesma filter chain do render
   (`ass=...:fontsdir=/mnt/c/Windows/Fonts`); versão LinkedIn 1:1 reaproveita
   o .ass do 9:16 via sed.
6. **QA por frames** — `qa.sh`, `qa-cunha.sh`, `qa-marco.sh`: frames em
   timestamps conhecidos (hook, flash, corpo, fim) + showspectrumpic para
   validar o whoosh sem ouvir.

## Particularidades das fontes

- **iPhone 4K HLG (HDR)**: `tonemap-test.sh` compara operadores e o pipeline
  usa **tonemap hable** (zscale linear → tonemap → bt709) para SDR sem cores
  lavadas — ver `cut.sh`.
- **Fonte low-res / horizontal**: canvas 9:16 com **blur-pad** (fundo
  desfocado gblur + overlay centrado) — ver `marco-cut.sh`.

## Arquivos

| Arquivo | Papel |
|---|---|
| `probe.sh`, `probe2.sh`, `extract2.sh` | probe JSON, frames de inspeção, WAV 16k |
| `tonemap-test.sh` | teste hable vs mobius (HDR→SDR) |
| `word_captions_cpu.py` | transcrição word-level CPU + `--segments` (deriva legendas do corte) |
| `cut.sh`, `cunha-cut.sh`, `marco-cut.sh` | cortes frame-accurate + concat (3 vídeos diferentes) |
| `render-reels.sh`, `render-linkedin.sh`, `cunha-render.sh` | transição zoom+flash+whoosh + burn .ass (9:16 e 1:1) |
| `qa.sh`, `qa-cunha.sh`, `qa-marco.sh` | QA visual por frames + espectrograma |
