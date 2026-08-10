# Color grading no ffmpeg (para corte de entrevista)

Escrito do zero pra este pipeline. Ideias de color science são conhecimento de
domínio (livre); os números aqui foram **medidos nesta máquina** em 2026-08-09,
não copiados. Filtros conferidos nos DOIS builds: WSL 4.4.2 e Windows 7.1.

Escopo: footage real de palestra/entrevista (celular, iPhone HLG, câmera de
evento). Não cobre grade criativo de ficção — nosso objetivo é **parecer
natural e consistente**, não "cinematográfico".

## Quando NÃO gradear

Comece por aqui, porque é a resposta certa na maioria dos cortes:

- **Footage já bem exposto** → não mexa. Grade ruim é pior que nenhum.
- **Um corte só, sem intercalar fontes** → ninguém tem referência pra comparar.
- **Se o problema é exposição/branco errado**, isso é *correção*, não grade —
  conserte e pare. Grade é a camada estética que vem depois.

O caso que realmente pede grade aqui: **juntar trechos de câmeras/momentos
diferentes no mesmo corte** (cold open de um take, corpo de outro). Aí a
inconsistência salta aos olhos e a correção vale o trabalho.

## Ordem da chain (importa)

Cada filtro opera no resultado do anterior, então a ordem muda o resultado:

```
1. tonemap/zscale     — só se for HLG/HDR (ver receita de iPhone abaixo)
2. colortemperature   — corrige o branco primeiro
3. colorbalance       — desloca cor por faixa (sombra/meio/alta)
4. curves             — molda contraste
5. eq                 — ajuste final de contraste/saturação
6. lut3d              — LUT criativo por ÚLTIMO, sobre imagem já corrigida
```

Regra prática: **corrigir antes de estilizar**. LUT em cima de branco errado
multiplica o erro em vez de esconder.

## Os filtros que usamos

| Filtro | Pra quê | Parâmetros |
|---|---|---|
| `eq` | contraste, saturação, brilho, gama | `contrast=1.0:saturation=1.0:brightness=0.0:gamma=1.0` |
| `colorbalance` | cor por faixa tonal | `rs/gs/bs` sombras · `rm/gm/bm` médios · `rh/gh/bh` altas (−1..1) |
| `curves` | curva de tom | `all='0/0 0.5/0.5 1/1'` ou `red=`/`green=`/`blue=` |
| `colortemperature` | balanço de branco | `temperature=6500` neutro · **menor = mais quente** |
| `lut3d` | aplica .cube | `lut3d='arquivo.cube'` |
| `normalize` | estica histograma | `blackpt=black:whitept=white` |

⚠️ `colortemperature` é contraintuitivo: o parâmetro é a temperatura da LUZ da
cena, então **baixar o número esquenta a imagem**. `temperature=5000` deixa mais
quente que `6500`, não mais frio.

Todos existem no 4.4.2 do WSL e no 7.1 do Windows (verificado 2026-08-09).

## Receitas (medidas, não chutadas)

Valores de referência medidos em `testsrc2` — a coluna U é o canal
azul-diferença, que é onde temperatura aparece objetivamente (U menor = menos
azul = mais quente). Neutro medido: **Y=124.7 U=127.4 V=125.2**.

### Quente / acolhedor — `Y=125.5 U=123.5` (−3.9 U, esquentou)

```
colorbalance=rs=0.06:gs=0.02:bs=-0.04:rh=0.05:gh=0.01:bh=-0.03,eq=contrast=1.05:saturation=1.08
```

Para depoimento, história pessoal, conteúdo de conexão.

### Frio / técnico — `Y=123.5 U=128.6` (+1.1 U, esfriou)

```
colorbalance=rs=-0.03:bs=0.06:rh=-0.02:bh=0.04,eq=contrast=1.06:saturation=0.95
```

Para conteúdo técnico, principalmente se tem screenshot de IDE dark no corte.

### Punch (alto contraste) — `Y=123.0`, sombras fechadas

```
curves=all='0/0 0.15/0.08 0.5/0.52 0.85/0.92 1/1',eq=contrast=1.15:saturation=1.2
```

Chama atenção no feed. ⚠️ **Mede mais agressivo do que parece** — ver a seção
de pele antes de usar em close.

### Sóbrio / sério — `Y=121.2`, contraste lavado

```
curves=all='0/0.04 0.25/0.22 0.5/0.47 0.75/0.73 1/0.94',eq=contrast=1.03:saturation=0.75
```

Levanta o preto (0/0.04) e segura o branco (1/0.94): o "faded" documental.

## Pele: o teste que decide

Pele é onde o olho detecta grade errado na hora. A referência clássica é a
"linha de skin tone" do vetorscópio (~123°, entre vermelho e amarelo).

**Medi três tons de pele antes e depois de cada grade** (ângulo do vetor de
croma; o que importa é o DESVIO, não o valor absoluto):

| Tom | Neutro | Quente | Punch | `saturation=1.3` |
|---|---|---|---|---|
| Médio (#C68642) | 139.8° | 141.6° (+1.8) | **143.3° (+3.5)** | 141.1° (+1.3) |
| Claro (#F1C27D) | 144.9° | 146.0° (+1.1) | **154.8° (+9.9)** | 146.0° (+1.1) |
| Escuro (#8D5524) | 137.0° | 139.3° (+2.3) | **133.1° (−3.9)** | 138.8° (+1.8) |

O que isso mostra, e que vale mais que qualquer regra decorada:

1. **O grade quente é seguro** — desloca ≤2,3° em todos os tons. Pode usar.
2. **O punch é o perigoso, e de forma desigual**: quase 10° em pele clara e
   puxa pele escura pro lado OPOSTO (−3,9°). Ou seja, ele não "satura mais",
   ele **distorce o matiz de forma diferente conforme o tom** — dois
   participantes com peles diferentes ficam desalinhados entre si.
3. **A curva é a vilã, não a saturação**: `saturation=1.3` sozinho desloca só
   ~1,5°, menos que o punch inteiro. A regra comum "não passe de 1.2 de
   saturação" mira no alvo errado — quem torce a pele é a curva de contraste.

**Regra prática daqui**: em close de pessoa, prefira o grade quente ou nada.
Se for usar punch, **suavize a curva antes de mexer na saturação** — trocar
`0.15/0.08 ... 0.85/0.92` por `0.15/0.11 ... 0.85/0.90` corta boa parte do
desvio (medido):

| Tom | Punch original | Punch suave |
|---|---|---|
| Médio | +3.5° | +2.9° |
| Claro | +9.9° | **+6.2°** |
| Escuro | −3.9° | **−1.3°** |

O ganho é justamente onde doía mais (pele clara e escura). Versão suave:

```
curves=all='0/0 0.15/0.11 0.5/0.52 0.85/0.90 1/1',eq=contrast=1.15:saturation=1.2
```

E sempre extraia frame e OLHE (regra 5) — número não substitui olho.

## HDR/HLG de iPhone → SDR

O caso mais comum de "cor errada" aqui não é grade, é **HLG entregue como se
fosse SDR** — sai lavado e acinzentado. Já está nos exemplos do TDC; a chain:

```
zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p
```

`hable` preserva melhor a alta-luz que `reinhard`. `desat=0` evita o
dessaturado que o tonemap costuma introduzir. Isso é **correção**, roda antes
de qualquer grade.

## LUT .cube

```bash
# LUT a 70% (mistura com o original) — validado nos dois builds 2026-08-09
ffmpeg -nostdin -y -i in.mp4 -filter_complex \
  "split[a][b];[b]lut3d='meu.cube'[g];[a][g]blend=all_mode=normal:all_opacity=0.7" \
  -c:a copy out.mp4
```

- LUT a 100% quase sempre exagera; **0,6-0,8 é a faixa útil**.
- Corrija (branco/exposição) ANTES; o LUT é a última camada.
- **Um LUT por vídeo.** Trocar entre cenas quebra a consistência, que é
  justamente o que o grade deveria resolver.
- Teste em frame com pele antes de rodar o vídeo inteiro.

## Legenda queimada continua legível?

Grade escuro reduz o contraste do texto contra o fundo. Nossa legenda usa
contorno preto, o que já protege bastante — mas depois de um grade tipo
"sóbrio" (que levanta o preto pra 0.04) vale conferir num frame com legenda
sobre a área mais clara do vídeo.

Referência: 4.5:1 é o mínimo de contraste pra texto (WCAG AA). Na prática, a
verificação honesta aqui é visual — extraia o frame e olhe.

## Fluxo recomendado

```bash
# 1) frame de referência ANTES de gradear o vídeo todo (economiza render)
ffmpeg -nostdin -y -ss 10 -i IN.mp4 -frames:v 1 /tmp/before.png

# 2) testa o grade no frame
ffmpeg -nostdin -y -i /tmp/before.png -vf "<CHAIN>" /tmp/after.png

# 3) OLHE os dois (Read). So depois roda o video inteiro.
# 4) grade junto com legenda e formato = 1 encode so
```

Ajuste em passos pequenos (±0,05) e reveja. Grade bom é o que ninguém percebe.
