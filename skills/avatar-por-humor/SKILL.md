---
name: avatar-por-humor
description: >-
  Transforma a biblioteca de referências de um personagem (as imagens canônicas no Drive + a
  reference-library JSON) em um rodízio de avatar por humor para um agente de chat (Discord hoje):
  baixa o lote, acha o rosto de cada imagem, recorta em quadrado com zoom que varia pelo
  enquadramento, gera um manifesto humor → ficha → papéis (foco, briefing, perfil, cozy, moleca,
  evento, bronca) e liga tudo num script de troca que sorteia por papel, evita repetir e aceita
  `reference_id`. Use quando o usuário pedir "põe as 40 fotos no rodízio", "ela fica sempre nas
  mesmas 3", "recorta as canônicas pra avatar", "cria humores a partir da library", "o cron de
  avatar só tem X opções", ou quando chegar um lote novo de canônicas e for preciso reprocessar.
  Também quando um recorte saiu errado ("ficou o sovaco, não a cara", "muito zoom"). Nascida na
  Pepper (repo fhgomes/personas), o mesmo desenho serve pro Jarvis ou qualquer personagem com
  Character Bible + library.
---

# Avatar por humor

> **Fonte desta skill:** `fhgomes/personas`, em `.claude/skills/avatar-por-humor/`. Edite aqui.
> Os scripts em `scripts/` são a implementação de referência (cópia do que roda no servidor da
> Pepper em `~/.openclaw/workspace/pepper_avatar*.py`). Quem manda é o que está rodando; ao mudar
> lá, traga pra cá com `scripts/sync-skill.sh`.

## O problema que ela resolve

O personagem tem 40 imagens canônicas no Drive e uma `reference_library.json` com ficha de cada
uma — mas o avatar dele no chat gira entre 3 recortes feitos à mão. O agente "não sabe" das outras
37, o cron sorteia cara ou coroa e o usuário vê sempre a mesma cara. Caso real documentado em
`docs/avatar-do-dia.md` (diagnóstico de 13/09/2026) e resolvido em 18/09/2026.

## O desenho (o que fica onde)

```
avatars/
  src/<lote>/            PNGs originais baixados do Drive (não versionar: ~2 MB cada)
  faces_<lote>.json      caixa do rosto por imagem, em % da largura/altura + "fonte"
  crop/<slug>.png        512x512, um por humor — é o que vai pro Discord
  moods.json             manifesto: humor -> arquivo, reference_id, ficha, papéis, enquadramento
  .state.json            último aplicado (humor + reference_id)
  history.jsonl          uma linha por troca, com reference_id
reference-library/
  <persona>_reference_library.json   a fonte das tags/coleções que viram papéis
```

Três scripts, três responsabilidades:

| Script | Faz | Quando roda |
|---|---|---|
| `avatar_build.py` | Drive → src → faces → crop → moods.json | a cada lote novo, ou pra refazer um recorte |
| `avatar_rotate.py` | escolhe o humor do dia e aplica no Discord (`PATCH /guilds/{id}/members/@me`) | cron das 7h; e sob demanda pelo agente |
| superfície do agente (`pepper-api avatar ...`) | lista, filtra, força por humor ou `reference_id` | quando alguém pede em conversa |

O **slug** do humor vem do nome do arquivo canônico: `pepper_ref_043-avatar-cafe-conversa_v6.png`
→ `cafe-conversa`. Isso pressupõe a convenção `<ref_id>-<enquadramento>-<descricao>_v<N>.png`
(ver `geracao-visual-consistente`). Com outra convenção, ajuste `slug_de()`.

## Passo a passo

### 1. Índice do Drive antes de tudo

A library precisa ter `drive_id`/`drive_url` por entrada e um índice enxuto arquivo → link. Sem
isso o agente não consegue citar a foto que usou. Liste a pasta pela API (o helper
`google_api.py` já tem token), case pelo `reference_id` no nome, e escreva de volta. Entradas sem
arquivo no lote ficam **sem link, explícitas** — nunca substituídas em silêncio.

### 2. Baixar e achar o rosto

```
python3 -m venv /tmp/cvenv && /tmp/cvenv/bin/pip install "opencv-python-headless<5"
./avatar_build.py --lote v6 --folder <drive_folder_id> --cv-python /tmp/cvenv/bin/python
```

OpenCV **4.x** (a 5.0 removeu `CascadeClassifier`). O host não tem cv2; usa venv descartável. O
detector é Haar frontal em 3 variantes sobre o **topo da imagem ampliado 3x**, e cada candidato só
vale se o cascade de **olhos com óculos** achar pelo menos um olho dentro da caixa. Sem essa
validação ele pega quadro na parede, almofada, planta e — literalmente — sovaco em pose de braço
levantado. Mesmo com ela, erra uns 10–20%.

### 3. CONFERIR olhando — a etapa que não se pula

```
./avatar_build.py --contato /tmp/contato.png
```

Gera a folha com todos os recortes **dentro do círculo**, do jeito que o Discord mostra. Leia a
imagem. Rosto fora do círculo é o único erro que o usuário vê, e ele vê na hora.

Errou? Corrija em `faces_<lote>.json` e marque `"fonte": "conferido a mao"` — o re-run preserva o
que foi conferido e só re-detecta o resto:

```json
"pepper_ref_021-corpo-inteiro-dia-quente-prendendo-cabelo_v6.png": {
  "centro_x_pct": 48.6, "centro_y_pct": 11.3, "altura_rosto_pct": 9.2, "fonte": "conferido a mao"
}
```

Pra achar as coordenadas certas, **não chute olhando thumbnail** — errei 5 de 8 assim. Rode o
detector com validação de olhos só naquela imagem e leia os candidatos, ou gere a imagem com grade
de % e leia numa resolução decente.

### 4. Zoom: não é tudo close

Bolinha de perfil não obriga close no rosto. Variação de distância é o que faz o rodízio parecer
vivo. Padrão por enquadramento (`ZOOM` no build):

| Enquadramento | Lado do quadrado | Rosto a … do topo |
|---|---|---|
| `avatar` (imagem já quadrada, composta como avatar) | imagem inteira | — |
| `meio-corpo` | 4.5 × altura do rosto | 36 % |
| `corpo-inteiro` | 4.0 × altura do rosto | 38 % |

Override por imagem no `faces_<lote>.json`: `"lado_em_rostos": 3.0`, `"rosto_y": 0.42`, ou
`"recorte": "inteiro"`. O primeiro passe usou 3.0/42 % pra tudo e ficou "zoom demais, sempre o mesmo
formatinho" — feedback literal do usuário.

### 5. Papéis: o que o sorteio consulta

O manifesto deriva **papéis** das `category_tags` + `collections` da library (tabela `PAPEIS` no
build). O rotate não conhece slugs; conhece papéis:

- dia com 5+ compromissos → sorteia entre os `foco` (óculos + tablet/whiteboard/caderno/mesa)
- segunda-feira → entre os `briefing` (whiteboard)
- resto → sorteio geral **evitando os 8 últimos** do `history.jsonl`

Outros papéis (`perfil`, `cozy`, `moleca`, `evento`, `bronca`) existem pro agente escolher em
conversa ("põe uma de café" → `avatar list "cafe"`). Humor sem sinal nenhum cai em `geral`.

Recortes antigos (feitos à mão antes do lote) são preservados no manifesto como **legado**, com
`reference_id: null` — não apague o que o usuário já viu no ar.

### 6. Ligar no agente

Se o agente **não tem tool de filesystem** (caso da Pepper: `group:fs` negado, uma única porta
`pepper-api`), arquivo no repo não serve pra nada — a library e o índice viram **subcomandos**
(`ref list|search|get|catalog`, `avatar list|papeis|status|<humor|reference_id>`). Depois
atualize o `AGENTS.md` do agente: os comandos, a regra de citar `reference_id`, e apague o
"só 3 das 40 estão prontas" que ficou pra trás. Teste **uma troca real** (HTTP 200) antes de
avisar o usuário.

### 7. Lote novo

```
./avatar_build.py --lote v7 --folder <id_da_pasta_v7> --cv-python /tmp/cvenv/bin/python
./avatar_build.py --contato /tmp/contato.png     # olhar
```

Humores do lote anterior cujo arquivo ainda existe continuam no manifesto. Se a library renumerou
referências (aconteceu do v5 pro v6: 039/040/041 viraram 029/030), os slugs velhos sobrevivem
como legado sem `reference_id`.

## Armadilhas

- `cv2 5.x` não tem `CascadeClassifier`; pin `<5`.
- Cena em golden hour inteira laranja: segmentar por cor de cabelo ruivo pega o fundo todo. Não
  tente.
- Não confie no rosto que o Haar achou só porque achou; a validação por olhos derruba a maioria dos
  falsos, e a folha de contato derruba o resto.
- Slug com mais de 32 chars: a regex de humor da superfície do agente (`MOOD_RE`) precisa aceitar
  (hoje 48).
- `history.jsonl` sem `reference_id` nas linhas antigas: o `list` mostra `null`, não é bug.
- O cron das 7h e a troca sob demanda são independentes: se o agente trocar à tarde, o cron troca
  de novo no dia seguinte. Está avisado na persona.
