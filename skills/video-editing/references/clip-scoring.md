# Escolher QUAL trecho vira corte (rubrica de scoring)

Adaptado de `claude-shorts` (MIT) + sinais do `clipify` (MIT). Serve pra quando
o pedido é "acha os melhores momentos desse vídeo" em vez de "corta de X a Y".

Use com o JSON word-level que a skill já gera (`word_captions_map.py
--words-json`) — os mesmos timestamps que planejam o corte com fronteira exata
de palavra (regra 6 da SKILL.md).

## As 5 dimensões (0-100 cada)

```
score = hook*0.30 + coerencia*0.25 + emocao*0.20 + valor*0.15 + payoff*0.10
```

### 1. Hook — os 3 primeiros segundos (peso 0.30)

| Arquétipo | Exemplo | Faixa |
|---|---|---|
| Contrarian | "Tudo que te falaram sobre X está errado" | 80-100 |
| Curiosity gap | "Tem uma coisa que ninguém te conta sobre..." | 75-95 |
| Promessa de valor | "O framework exato que usei pra..." | 70-90 |
| Pattern interrupt | "Peraí, deixa eu te mostrar uma coisa" | 70-90 |
| Preview do payoff | "No fim disso você vai saber..." | 65-85 |
| Começo em movimento | [entra no meio da frase, com energia] | 60-80 |
| Genérico | "Então hoje eu quero falar sobre..." | 10-40 |

Bônus (+5-10 cada): número específico ("3 passos", "R$50 mil"), nome
reconhecível (pessoa/empresa/ferramenta), experiência própria ("eu testei").

### 2. Coerência standalone (peso 0.25)

Tem que fazer sentido pra quem NÃO viu o resto.

| Critério | Score |
|---|---|
| Arco completo (setup → desenvolvimento → resolução) | 85-100 |
| Ideia completa com lacuna que dá pra inferir | 65-84 |
| Referencia conteúdo anterior ("como eu disse") | 40-64 |
| Precisa do contexto anterior pra entender | 10-39 |
| Fragmento — começa ou termina no meio | 0-9 |

**Red flags (score baixo automático)**: "como eu falei antes", "voltando
àquele ponto", pronome sem referente ("ele disse que..."), corte no meio da
frase no fim.

### 3. Intensidade emocional (peso 0.20)

| Sinal | Faixa |
|---|---|
| Desabafo/opinião forte com convicção | 80-100 |
| Revelação surpreendente / virada | 75-95 |
| Humor genuíno / risada | 70-90 |
| Vulnerabilidade / história de fracasso honesta | 70-90 |
| Explicação entusiasmada de algo fascinante | 60-80 |
| Observação calma mas perspicaz | 40-60 |
| Recitação monótona de fatos | 10-30 |

### 4. Densidade de valor (peso 0.15)

| Tipo | Faixa |
|---|---|
| Passo a passo / método exato | 80-100 |
| Framework / modelo mental com exemplo | 75-95 |
| Dado específico / achado de pesquisa | 70-90 |
| Insight contra-intuitivo explicado | 65-85 |
| Conselho geral com algum específico | 40-60 |
| Platitude ("trabalhe mais", "seja consistente") | 10-30 |

Penalize se >30% do tempo for filler, repetição ou tangente.

### 5. Payoff — como termina (peso 0.10)

| Final | Faixa |
|---|---|
| Punchline / revelação satisfatória | 85-100 |
| CTA claro com próximo passo | 75-90 |
| Pensamento completo, parada natural | 65-80 |
| Dissolve no próximo assunto (dá pra cortar limpo) | 40-60 |
| Corta no meio / sem resolução | 10-30 |

## Regras de seleção

1. Mirar **8-12 candidatos** num vídeo de 30-60 min
2. **Duração**: 15-55s (pico de engajamento em 25-40s)
3. **Corte mínimo: 60.** Abaixo disso, pula
4. **Diversidade**: não escolher 5 trechos do mesmo subtema
5. **Espaçamento**: preferir trechos a ≥2 min de distância no original
6. **Fronteira**: alinhar início/fim em fronteira de frase, nunca no meio da
   palavra — usar o `--words-json` pra pegar o start real (armadilha da regra 6:
   palavra esticada na fronteira)

## Sinais mecânicos (baratos, rodam antes do LLM ler)

Do `clipify` — servem pra pré-filtrar e reduzir o que o modelo precisa ler:

- **Picos de áudio**: `ffmpeg -af volumedetect` ou alternância rápida de
  segmentos curtos do Whisper (bate-papo/reação)
- **Risada**: "haha", "kkk", palavrão, "não acredito", "caraca"
- **Pausa awkward**: gap longo entre segmentos do Whisper
- **Reversão**: pergunta no setup → resposta inesperada
- **One-liner citável**: frase declarativa curta que se sustenta sozinha

## Texto de hook (overlay dos primeiros ~3,5s)

- **Linha 1**: 4-8 palavras, a afirmação que segura o scroll
- **Linha 2**: 3-6 palavras, contexto
- ⚠️ **NÃO** repetir as primeiras palavras faladas — o overlay complementa o
  áudio, não duplica. Combina com o punch-in da receita de transição.
