---
name: media-transcription
description: >-
  Transcrever áudio e vídeo em texto/legendas — local (faster-whisper large-v3
  na GPU) ou remoto (youtubetotranscript.com para vídeos do YouTube). Use SEMPRE
  que o usuário pedir "transcreve", "transcrição", "extrai o texto do
  vídeo/áudio", "gera legenda", "SRT", mencionar Whisper, ou quiser o texto de
  uma palestra, mentoria, reunião gravada ou vídeo do YouTube. Use também
  quando comparar qualidade de transcrições ou quando um transcript anterior
  tiver loops/alucinações ("gato gato gato") — o remédio é o modelo large-v3.
  Inclui script pronto (scripts/transcribe_gpu.py) — não reescreva do zero.
---

# Transcrição de mídia (local GPU + remoto)

## Decisão rápida

| Situação | Caminho |
|---|---|
| Vídeo já está no YouTube e só precisa do texto | **Remoto**: youtubetotranscript.com (sem download, sem GPU) |
| Arquivo local (.mp4/.wav/.mp3), qualidade importa | **Local**: `scripts/transcribe_gpu.py` (large-v3 GPU) |
| Vídeo privado no Google Photos/Drive | Baixar antes (skill `browser-file-download`), depois local |

## Local — faster-whisper large-v3 na GPU

Script pronto e validado (2026-07): `scripts/transcribe_gpu.py` desta skill.

```bash
python scripts/transcribe_gpu.py --out-dir "C:\saida" --base "nome-do-evento" ^
  --prompt "Palestra sobre X; nomes: Fulano, Sicrano; termos: Deep Work, RAG" ^
  video1.mp4 video2.mp4
```

Fatos desta máquina (GTX 1650 4 GB, Python embed 3.13 em `D:\Programas\`):
- Pacotes já instalados: `faster-whisper nvidia-cublas-cu12 nvidia-cudnn-cu12`.
- `float16` NÃO cabe (precisa ~4,5 GB) — o script usa `int8_float16` (~1,9 GB)
  com fallback `int8`. Roda a **~4,3x tempo real** (50 min ≈ 12 min).
- O script já resolve o problema clássico do Windows: `cublas64_12.dll not
  found` na hora do encode — exige PATH + pré-carga ctypes das DLLs pip da
  NVIDIA antes do import (`os.add_dll_directory` sozinho não funciona).
- **GPU ocupada = transcrição arrastando**: com Chrome baixando/reproduzindo
  vídeo a velocidade caiu de 4,3x para 0,1x. Cheque `nvidia-smi` antes; se a
  VRAM estiver quase cheia, avise o usuário e/ou espere downloads terminarem.
  Sequencie: primeiro baixar/fechar abas de vídeo (Google Photos deixa o vídeo
  em LOOP tocando!), só então transcrever. Se já degradou, fechar abas NÃO
  recupera o processo vivo (alocações ficam presas na memória compartilhada
  WDDM) — mate e relance; partes já gravadas não se perdem.
- Se a GPU falhar de vez: **pergunte antes de cair para CPU** (large-v3 em CPU
  leva ~2h+ por hora de áudio; o usuário pode preferir esperar/fechar apps).

Qualidade (o que realmente move o ponteiro):
- Modelo: small alucina em fala ao vivo (loops "gato gato gato", "tablet de
  tablet..."); large-v3 elimina os loops. Modelo > hardware para qualidade;
  GPU só compra velocidade.
- `--prompt` (initial_prompt): passe título do evento, nomes próprios e jargão
  esperado — é a alavanca barata para acertar nomes. **Efeito colateral**: em
  trechos de silêncio/ruído (início de gravação, pausas) o Whisper pode ECOAR o
  prompt verbatim como se fosse fala. Sempre grep o resultado por frases do
  prompt e remova esses segmentos (renumere o SRT e regere o TXT).
- Sempre `vad_filter=True`, `beam_size=5`, `language` explícito.
- Aceita `.mp4` direto (PyAV decodifica) — não extraia WAV antes.
- Mesmo no large-v3, nomes próprios erram (ex.: "executadores" por
  "recrutadores") — recomende revisão ou faça um passe de correção via LLM.
- QA rápido: escanear o SRT por janelas de 30s com bigramas repetidos
  (degeneração) — se aparecer, o áudio tem trecho ruim ou o modelo derrapou.

Primeira execução baixa o modelo (~3 GB, cache Hugging Face) — precisa de
internet e ~80 s extras.

## Remoto — YouTube

- **youtubetotranscript.com** (já usado com sucesso em sessão anterior): colar
  a URL do YouTube, copiar o transcript. Para texto rápido sem timestamps
  precisos. Não requer download nem GPU.
- Alternativas: painel "Mostrar transcrição" do próprio YouTube;
  `yt-dlp --write-auto-sub --skip-download <url>` quando precisar do .vtt.
- Limite: transcript automático do YouTube tem qualidade de auto-caption
  (pior que large-v3). Para palestra do próprio usuário que valha capricho,
  baixar o vídeo e rodar local.

## Pós-processamento padrão (sempre rode os 3)

1. **Grep de eco do prompt**: busque frases do initial_prompt no SRT; remova
   segmentos idênticos, renumere, regere TXT (echo aparece em silêncio/ruído).
2. **Scan de degeneração**: janelas de 30s com bigrama repetido ≥8x = loop de
   alucinação (só deve aparecer em modelo small; no large-v3 investigue o áudio).
3. **Leitura de amostra**: início + 1 trecho do meio; anote termos suspeitos
   (nomes próprios errados) na nota do vault como pendência de revisão.

## Gravações particionadas (vários vídeos da mesma sessão)

- Ordene pelos timestamps do nome (`VID_YYYYMMDD_HHMMSS`); transcreva cada
  parte separada (SRT por parte serve de legenda para o vídeo correspondente).
- Gere um transcript unificado com **timeline global**: offset de cada parte =
  (HHMMSS da parte − HHMMSS da parte 1); marque os intervalos sem gravação
  entre partes. Fica um arquivo único navegável, "o transcript da sessão".
- Se o processo morrer no meio (OOM/thrash/kill): partes já gravadas em disco
  não se perdem — relance só as partes restantes com um script de resume
  (mesma numeração) e monte o unificado juntando o que já existia.

## Rodando em background (tarefas de 10+ min)

- Lance com run_in_background + Monitor (tail -f do log filtrando
  `\[done|\[fim\]|Error|Traceback`) + um "deadman" (`sleep N` em background)
  para reavaliar mesmo se o log ficar mudo — travamento silencioso não notifica.
- Throughput saudável nesta máquina: ~4-5x tempo real. Se cair para <1x,
  cheque `nvidia-smi`: outro app comendo VRAM. Fechar o app NÃO recupera o
  processo já degradado (alocações presas em memória compartilhada) — mate e
  use o resume.

## Depois de transcrever

Transcrições de palestras do usuário vão para o vault Obsidian em
`15_Portfolio/talks/` (txt + srt + nota .md com frontmatter e entrada no
inventário `palestras-2026-inventario-e-dados.md`) — ver skill `archivist`.
O vault sincroniza com o servidor (OpenClaw) via git — o usuário faz
commit/push manualmente; avise quando os arquivos estiverem prontos.
