# Modo entrevista — criar um personagem novo do zero

Gatilhos: "cria um personagem novo", "quero definir um avatar", "/geracao-visual-consistente novo <nome>",
"me entrevista sobre o personagem", ou qualquer pedido de personagem que ainda não tem Character Bible.

Regras do modo:
- **Uma rodada por vez**, com AskUserQuestion (2 a 4 perguntas por rodada, opções + "Other").
  Nunca despejar as 6 rodadas de uma vez. Nunca inventar resposta: se o usuário não sabe, marcar
  `"a_definir"` e seguir.
- **Referências primeiro.** Antes da rodada 1, pedir imagens (caminho local, pasta, link do Drive,
  ou "não tenho"). Se vierem imagens: abrir cada uma (Read), descrever em 3 linhas o que se vê de
  identidade e de estilo, e usar isso pra pré-preencher as opções das rodadas. Referência é fonte de
  composição e de estilo; identidade só vira canônica depois que o usuário confirma na entrevista.
- **Separar sempre três coisas**: identidade (o que nunca muda), estilo de render (o acabamento), e
  variações permitidas (roupa, cena, maquiagem, humor).
- Ao final, gerar os arquivos da seção "Saídas" e perguntar se gera a character sheet agora.

## Rodada 0 — contexto

1. Nome do personagem e pra que serve (mascote de marca, avatar pessoal, personagem de conteúdo,
   assistente com rosto).
2. Onde vive: repo/pasta destino e pasta no Drive (ou "cria a estrutura padrão").
3. Referências: "me manda imagens ou links; ou diz 'não tenho'". Se for avatar do próprio usuário,
   pedir 2 a 3 fotos (frontal, 3/4, corpo inteiro) e avisar que só serão usadas como referência de
   identidade, nunca publicadas.

## Rodada 1 — identidade fixa (identity locks)

- Idade aparente e gênero. Espécie/tipo se não for humano.
- Cabelo: cor (com negações: "cobre vivo, NÃO auburn"), comprimento, penteado padrão, variantes
  permitidas.
- Olhos: cor e formato. Pele: tom e subtom. Sardas/marcas: sim ou não, onde.
- Rosto: formato, nariz, boca, sobrancelha, uma ou duas "assinaturas" (pinta, cicatriz, gap nos dentes).

## Rodada 2 — corpo e marcas

- Altura relativa e proporção (cabeças de altura), tipo de corpo, com limite explícito do que é
  exagero.
- Tatuagens, piercings, cicatrizes, marcas luminosas: **cada uma com lado e ponto exato** (pulso
  interno direito, antebraço esquerdo). Regra: lateralidade sempre descrita pelo ponto de vista do
  observador no prompt ("her RIGHT hand, on the VIEWER'S LEFT").
- Para cada marca, capture três coisas além do lugar, ou ela vai sair errada:
  - **Forma do traço**: "um arco, um movimento de caneta só, termina num ponto". Só dizer onde não
    basta; sem a forma o gerador ramifica, faz garfo, espelha no outro lado.
  - **Intensidade por comparação com algo real**: "igual a uma veia de verdade, só que com o matiz
    trocado", "como uma tatuagem cicatrizada de anos". Adjetivo abstrato ("sutil", "discreto") não
    converge, porque o gerador não tem régua.
  - **Emite luz ou não?** Se não emite, **nunca use a palavra "glow"** ao descrever: ela vira luz
    literal. Use "tint", "reads as", "the hue is wrong".
- Se o personagem usa roupa, pergunte se cabe um **sinal não-anatômico**: monograma bordado, pin,
  bordado na gola. Reaparece sem deriva, enquanto marca na pele costuma exigir várias calibrações.
- Acessórios de assinatura (óculos, brinco, colar, relógio) e quais são obrigatórios em toda imagem.

## Rodada 3 — estilo de render

- Mostrar 4 opções com descrição curta e pedir 1: (a) pintura digital 2D polida, semi-realista;
  (b) anime/editorial; (c) 3D estilizado tipo Pixar; (d) fotorrealista. Se houver referência de
  estilo, descrever o que ela é e sugerir.
- Paleta: 3 a 5 cores dominantes, temperatura (quente/fria), saturação (alta/média/baixa).
- Iluminação padrão (golden hour, luz de estúdio, difusa) e nível de detalhe do fundo (subordinado,
  médio, cenário rico).
- O que NÃO pode acontecer (ex.: nunca fotorrealista, nunca vetor chapado, nunca contorno preto).

## Rodada 4 — guarda-roupa e mundo

- Direção de estilo (smart-casual, executivo, esportivo, fantasia) e paleta de roupa.
- 3 a 6 looks aprovados, cada um em uma linha. **Varie por camada, não por cor**: paletó, sem paletó,
  malha, sobretudo. Look que muda de cor a cada cena destrói a leitura de identidade.
- Para cada look, anote o que fica **coberto**: um monograma no peito some sob uma malha, uma marca no
  pescoço some sob gola alta. Sem isso o prompt pede coisa impossível e o gerador inventa.
- Ambiente padrão (home office, cidade, estúdio, abstrato) e elementos recorrentes (planta, quadro,
  janela). Coisas proibidas no cenário (animal, logo, texto).

## Rodada 4b — personalidade e tradução visual

Não pule. Sem isso o gerador escorrega em pose de super-herói, gesto teatral e sorriso de propaganda,
e você vai brigar com isso em toda geração.

- Em uma frase: o que esse personagem é (executivo e seco, caloroso e brincalhão, técnico e paciente).
- **Como isso vira imagem.** Para cada traço, escreva o equivalente visual concreto:
  postura ("ombros para trás sem tensionar"), gesto ("medido e curto, nunca teatral"),
  sorriso ("sempre fechado e de canto" ou "aberto e fácil"), olhar ("direto e sustentado").
- O que ele **nunca** faria em imagem (gargalhar de boca aberta, posar de braços na cintura, encarar
  de cima). Isso vira linha no `negative_prompt`.

## Rodada 5 — expressão e personalidade visual

- 3 expressões padrão (ex.: sorriso confiante, sorriso de canto, foco).
- Maquiagem/acabamento de rosto: baseline e 2 a 4 variantes.
- Poses assinatura (2 a 4) e enquadramentos que a biblioteca vai ter (avatar circular, meio-corpo,
  corpo inteiro).

## Rodada 6 — confirmação

Mostrar um resumo em tabela (identidade | estilo | variações | proibições) e pedir "confirma, ou o
que muda?". Só depois gerar arquivos.

## Saídas (gerar todas)

Tudo dentro de `personas/<nome>/` (ver a árvore completa na seção 2 da SKILL.md):

```
identity/<nome>_character_bible_v1.json      # a partir de templates/character_bible_template.json
prompts/canonical/_bloco-identidade-canonica.txt   # inglês, locks + marcas com lateralidade E forma
prompts/canonical/_bloco-estilo.txt           # inglês, o parágrafo STYLE TO MATCH (curto!) + AVOID
prompts/canonical/sheet-<nome>.txt            # prompt da character sheet (frente + 3/4 + corpo, nome escrito)
reference-library/{canonicas,sheets,materiais}/   # pastas vazias, já na convenção
reference-library/<nome>_reference_library.json   # índice; image_file aponta a versão atual
docs/checklist-canonico.md                    # itens derivados das respostas
docs/convencao-arquivos.md                    # a convenção de nomes, escrita pro projeto
docs/historico-versoes-canonicas.md           # vazio, com a convenção
```

O Bible v1 tem que sair da entrevista já com:
- `personality` com a tradução visual de cada traço (rodada 4b), não só adjetivos;
- cada marca com **lugar, forma do traço e intensidade por comparação** (rodada 2);
- o guarda-roupa dizendo o que cada look **cobre**;
- `negative_prompt` alimentado pelo "o que ele nunca faria" das rodadas 3, 4 e 4b.

Depois: "Gero a character sheet agora no ChatGPT?" Se sim, seguir o ciclo da SKILL.md (chat novo,
referência de estilo anexada se houver, baixar, checklist, subir no Drive). A sheet aprovada vira a
Image 1 das gerações seguintes — lembrando que style-ref só funciona em composição diferente.

**Comite o Bible antes de gerar a primeira imagem.** É o ponto pra onde você vai querer voltar.
