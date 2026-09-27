---
name: geracao-visual-consistente
description: >-
  Procedimento pra gerar personagens, avatares e artefatos visuais CONSISTENTES com IA generativa
  (ChatGPT / GPT Image 2 hoje; Nano Banana, Midjourney, Flux como alternativas), com Character
  Bible, referências canônicas, checklist e comparação lado a lado. Use SEMPRE que o usuário pedir
  pra criar ou manter um personagem/avatar/mascote com identidade visual estável ("gera a Pepper",
  "cria um avatar meu", "mantém o estilo", "referência canônica", "character sheet", "ficou
  fotorrealista demais", "saiu diferente da referência", "consistência de personagem", "style
  reference", "gera no ChatGPT e sobe no Drive"), ou quando uma geração desviou em estilo, cor,
  cabelo, maquiagem ou tatuagem. Inclui a operação do ChatGPT pelo navegador (destravar render,
  baixar, subir no Drive), a convenção de pastas e de versão no nome do arquivo, o que fazer quando o
  usuário aprova uma variante (promoção de canon) e as lições de calibração de sinais sutis (forma do
  traço, intensidade por comparação, nunca "glow" pra algo que não emite luz). A lição central:
  descrever estilo em texto longo faz o ChatGPT recusar como "edição", então estilo vai por IMAGEM de
  referência, e só funciona se a composição pedida for diferente da imagem anexada.
  Nascida no projeto Pepper, amadurecida no Jarvis (repo fhgomes/personas).
---

# Geração visual consistente

> **Fonte desta skill:** `fhgomes/personas`, em `.claude/skills/geracao-visual-consistente/`.
> Edite lá. A cópia em `fhgomes/my-awesome-agents-skills` é publicação, sincronizada por
> `scripts/sync-skill.sh`. Editar a cópia faz as duas divergirem.

Casos reais e documentação detalhada: mesmo repo, `docs/` na raiz (método compartilhado) e
`personas/<nome>/docs/` (por personagem). Ver "Onde está o resto" no fim.
Esta skill é a versão portátil, pra qualquer personagem, em qualquer repo.

## 0. Dois modos

- **Personagem novo** (não existe Character Bible ainda): entrar no **modo entrevista** descrito em
  `entrevista.md` (mesma pasta desta skill). São 6 rodadas curtas de perguntas com AskUserQuestion,
  referências lidas antes da rodada 1, e no fim os arquivos gerados a partir de
  `templates/character_bible_template.json`. Só depois disso gerar imagem.
- **Personagem existente** (já tem Bible + bloco canônico + referência aprovada): ir direto pro
  ciclo da seção 5 usando a receita da seção 3.

Como o usuário dispara: "cria um personagem novo chamado X", "quero definir o avatar da minha
marca", "me entrevista pra definir o estilo do personagem", ou `/geracao-visual-consistente novo X`.
Com referências: "aqui estão as referências: <caminhos ou links>". Sem referências: "não tenho
referência, vamos definir do zero".

## 1. Modelo mental (o que a pesquisa de set/2026 e os testes provaram)

1. **Imagem carrega identidade e estilo; texto carrega cena.** GPT Image 2 é um modelo baseado em
   LLM que "pattern-matcha" a descrição. Quanto mais texto de identidade, mais deriva. Character
   sheet (frente + 3/4, nome escrito) + prompt curto de cena é o padrão de mercado em 2026.
2. **Vocabulário fotográfico vota em foto.** "golden hour", "window light", "depth-blurred",
   "believable anatomy and fabric materials", "natural freckles", "AVOID porcelain skin" empurram pra
   fotorrealismo mesmo com "illustration, NOT a photograph" no prompt. Negação funciona como
   instrução, mas é um voto contra trinta.
3. **Bloco longo de estilo em texto faz o ChatGPT recusar** ("the image tool classified this as an
   edit"). Testado 4 vezes em chats novos, com controle e bissecção. Instruções imperativas sobre
   partes da imagem ("paint the skin", "build the hair", "keep the eyes crisp") viram "retoque".
   **Solução: anexar uma imagem aprovada como referência de estilo** e abrir o prompt com
   "Image 1 is attached ONLY as a rendering-style reference ... Create a brand new illustration from
   the written description below". Com imagem, o roteador vai pra edição de propósito.
4. **JSON não melhora o modelo**, melhora a gente (um lugar só pra editar). O cookbook da OpenAI é
   neutro sobre formato.
5. **Chat novo pra toda prova real.** Chat usado está contaminado e dá falso positivo.
6. **Corrija o prompt, não converse.** Se faltou um elemento (tatuagem, óculos), a causa está no
   prompt ou na pose que esconde a parte do corpo. Ajuste e rode em chat novo.
7. **Imagem de estilo só funciona com composição DIFERENTE.** Anexar uma sheet e pedir a mesma sheet
   faz o modelo tratar como edição e devolver a própria imagem com os mesmos defeitos, mesmo com o
   cabeçalho "ONLY as a rendering-style reference". Style-ref serve pra levar acabamento de uma cena
   pra outra, nunca pra refazer a mesma cena. (Jarvis, 2026-09-10: sheet v2-styleref.)
8. **Lateralidade correta não garante FORMA.** Dizer "só na têmpora esquerda dele" acertou o lado, mas
   a linha continuou saindo em garfo até o prompt descrever o desenho: "um arco, um movimento de
   caneta só, termina num ponto, nunca Y nem V, sem segundo segmento". Descreva o traço, não só onde.
9. **Pra um sinal sutil, ancore em algo real e troque UM atributo.** Intensidade em abstrato ("sutil",
   "baixo contraste", "claramente visível") não converge, porque o gerador não tem régua. "Igual a uma
   veia de verdade, só que com o matiz trocado" entrega a régua pronta. Três rodadas na veia do Jarvis
   até chegar nisso.
10. **Nunca use "glow" pra algo que não deve emitir luz.** A palavra vira luz literal, principalmente
    onde a superfície está bem iluminada e de frente. Use "tint", "reads as", "the hue is wrong".
11. **Prompt com instruções contraditórias faz o modelo inventar uma terceira coisa.** Pedir "difuso
    sob a pele" e "baixíssimo contraste" ao mesmo tempo produziu um risco escuro desenhado por cima,
    que é o oposto dos dois. Antes de culpar o gerador, releia o prompt procurando contradição.
12. **Cor de íris incomum sem virar olho de robô:** exija a estrutura humana da íris (fibras radiais,
    anel limbal mais escuro, pupila preta, catchlight) e proíba explicitamente íris chapada e
    autoiluminada. Descrever só a cor faz o modelo pintar um disco uniforme, que lê como lente.
13. **O Character Bible precisa de um bloco de PERSONALIDADE com tradução visual.** Sem ele o gerador
    escorrega em pose de super-herói, gesto teatral e sorriso de propaganda. Não basta "executivo e
    seco": escreva o que isso vira na imagem ("gesto medido e curto", "sorriso sempre fechado e de
    canto", "ombros para trás sem tensionar").
14. **Um sinal de identidade não-anatômico é mais estável que um traço no corpo.** Um monograma
    bordado na roupa reapareceu em todas as gerações sem deriva, enquanto marcas na pele exigiram
    três calibrações. Se o personagem usa roupa, considere um monograma antes de inventar cicatriz.
15. **A imagem de estilo vence o texto também nos detalhes de maquiagem, cor de boca e delineado.**
    Ao recalibrar a Pepper (2026-09-11), decote, pose e olhar mudaram nas seis referências, mas a boca
    não: o brilho médio do batom ficou igual (ref 039: 0.486 → 0.477; ref 003: 0.626 → 0.615), porque a
    imagem de estilo anexada era a versão anterior, de boca escura. Pedir "batom mais claro" por texto
    enquanto se anexa uma referência de batom escuro é instrução contraditória (ver item 11). **Para
    mudar um atributo que a style ref carrega, a style ref precisa mudar junto** — gere uma variante
    aprovada com o atributo novo e passe a usá-la como referência de estilo.
16. **Antes de gerar, releia também o bloco de ESTILO, não só o de identidade.** Na mesma rodada, o
    `_bloco-estilo-pintura-2d.txt` ainda pedia "dark winged upper eyeliner" e "richer dusty berry-rose
    lips" — exatamente o registro que o Character Bible novo tinha acabado de proibir. O bloco de estilo
    é um segundo lugar onde a aparência é definida, e ele silenciosamente sobrescreve o canon novo.
17. **Quando o feedback é sobre "vibe" e não sobre um item, procure a causa no Character Bible.**
    "Ela está sempre sexy demais" não se resolve trocando a roupa de uma imagem: o v7 da Pepper tinha
    `default_energy` com a palavra "sexy", busto travado como "full and prominent", nenhuma regra de
    decote e a boca escura liberada como look de escritório. Gerar imagem nova sem mexer nisso repete o
    resultado. Promova o Bible primeiro (seção 6), depois gere.
18. **Ao corrigir uma leitura indesejada, escreva o limite da correção no próprio canon.** O Fernando
    pediu para reduzir a maquiagem "mas não deixar apagada". Sem um `balance_warning` explícito no Bible
    e um "BALANCE WARNING" no bloco de prompt, a próxima sessão só lê a lista de proibições e entrega uma
    versão sem graça do personagem. Toda regra de redução precisa dizer onde ela para.
19. **Style ref SEM ROSTO: recorte a referência de estilo abaixo do queixo quando um atributo de rosto
    precisa mudar.** Teste A/B na Pepper (2026-09-11, refs 001 e 039, mesmo prompt, chats novos): com a
    referência inteira anexada, batom vinho e sorrisinho de canto voltaram nas duas apesar do texto pedir
    boca rosa e sorriso simétrico; com a mesma imagem recortada do queixo pra baixo (torso, mãos, roupa,
    fundo), boca e sorriso obedeceram ao texto **e o acabamento de pintura se manteve** — pele, cabelo,
    tecido e paleta bastam pra carregar o estilo. Acrescente ao cabeçalho: "Image 1 is a deliberately
    cropped detail of a finished painting: the face is intentionally outside the crop... Build her face,
    expression and makeup entirely from the text." Corolário: quando o rosto está na style ref, ele é
    lido como identidade e sobrescreve expressão, batom e delineado descritos em texto.
    **Custo:** sem o rosto na referência, a identidade facial passa a depender só do texto e afrouxa um
    pouco (rosto mais redondo, olhos menos estilizados em 2 de 6). Mitigação: anexar uma SEGUNDA imagem, um
    sheet de rosto já no registro novo, como referência de identidade — sheet + style, item 1.

## 2. Estrutura mínima por personagem

Um repositório de personas abriga **uma pasta por personagem**, com o método compartilhado na raiz:

```
docs/                                  # método que vale pra QUALQUER persona (pipeline, procedimento,
                                       # geradores, aprendizados). Não misture com o específico.
personas/<nome>/
  identity/<nome>_character_bible_vN.json        # manda em tudo; imagem não é fonte de identidade
  prompts/canonical/_bloco-identidade-canonica.txt   # injetado em todo prompt (marcas com lateralidade
                                                     # pelo ponto de vista do observador)
  prompts/canonical/_bloco-estilo.txt             # parágrafo STYLE TO MATCH curto + AVOID
  prompts/canonical/ref_NNN-<descricao>.txt       # um prompt por referência
  prompts/canonical/variantes-arquivadas/         # prompts de linhas descartadas
  reference-library/
    canonicas/                         # as aprovadas
      historico/                       # versões anteriores, nunca apagadas
    sheets/                            # character sheets
      historico/
    materiais/                         # comparações, recortes de detalhe, contact sheets
    variantes/<linha>/                 # linhas descartadas, com PREFIXO próprio no nome
    <nome>_reference_library.json      # índice: aponta qual arquivo é a versão atual
  docs/checklist-canonico.md           # ~30 itens
  docs/historico-versoes-canonicas.md  # linhagem: versão -> prompt -> resultado -> por quê
  docs/convencao-arquivos.md           # a convenção abaixo, escrita pro projeto
  docs/assets-drive.md                 # links do Drive, por referência e por versão
```

### Convenção de nome (vale no repo e no Drive)

```
<tipo>_<id>_v<N>[_<descricao>].png
```

- `ref_001_v3.png`, `sheet_marcele_v5_olho-azul.png`, `comp_marcele_v4-v5.jpg`
- `v<N>` é a versão que gerou **aquela imagem**, não a do Character Bible.
- **Nenhum arquivo canônico sem versão no nome.** Sem isso não dá pra saber qual prompt o gerou.
- O ponteiro de "qual é a atual" vive no campo `image_file` da reference library, **não no nome**.
  Assim nada precisa ser renomeado quando chega versão nova, e nada é sobrescrito.
- Variantes descartadas levam prefixo próprio (`sintetica_ref_001_v1.png`). Sem isso elas colidem com
  as canônicas: duas pastas com `ref_001.png` é armadilha pra qualquer script que liste por nome.

**Nunca apague versão anterior**: move pra `historico/` no mesmo momento em que promove a nova.

### Ao promover uma imagem, faça os seis

1. Passou no checklist. 2. Nome carrega a versão. 3. Anterior foi pro `historico/`.
4. `reference_library.json` aponta pro arquivo novo. 5. `historico-versoes-canonicas.md` ganhou a linha
com o que mudou e por quê. 6. Subiu pro Drive e o link entrou em `assets-drive.md`.

## 3. Receita do prompt que funciona (ChatGPT, set/2026)

```
Image 1 is attached ONLY as a rendering-style reference: match its visual medium, finish, color
treatment and level of stylization. Do not copy its composition, pose, hands, or scene layout; do
not reuse it as a base image. Create a brand new illustration from the written description below.

STYLE TO MATCH FROM IMAGE 1: <um parágrafo: meio, pele, cabelo, maquiagem, paleta, fundo>

Create a <formato> character portrait.

COMPOSITION / CHARACTER / POSE / EXPRESSION / HAIR / GLASSES / WARDROBE / MAKEUP / BACKGROUND
TATTOOS (lateralidade exata, "her RIGHT hand, on the VIEWER'S LEFT")
IDENTITY LOCKS (cabelo, olhos, pele, rosto, idade, corpo, acessórios; cor por negação:
  "vivid copper, NOT dark auburn, NOT burgundy")
AVOID: <lista curta, sem "porcelain skin", sem repetir photograph/DSLR/pores>
```

Não use: bloco RENDERING STYLE longo em texto, "depth-blurred", "practical lights", "canonical",
"approved variation", verbos de pós-produção (grade, treatment, finish, sharpness, color cast).
Sempre inclua um bloco HAIR (sem ele o cabelo sai solto).

## 4. Operação no ChatGPT pelo navegador (claude-in-chrome)

- Aba **Chat**, não Work (o campo da Work não aceita a inserção).
- Inserir texto: `#prompt-textarea` focado + `document.execCommand("insertText", false, texto)`.
- Anexar: `find` "file upload input" e `file_upload` com caminho local.
- Enviar: clique no DOM, `[...document.querySelectorAll('button')].find(b=>/send prompt/i.test(b.getAttribute('aria-label')||'')).click()`.
  Prova de envio: URL vira `/c/<id>`, campo zera, botão Stop aparece.
- Esperar 1 a 3 min. Polling com `await new Promise(r=>setTimeout(r,25000))` (nunca mais de 30 s por
  chamada, o CDP dá timeout em 45 s).
- **Quadro preto = imagem pronta sem renderizar.** Clique no quadro (ou no card do painel Outputs).
  Se não resolver: F5 na URL do chat. Aba degradada (screenshot "0 width" ou timeout): aba nova e
  `tabs_context_mcp({createIfEmpty:true})`.
- "Something went wrong / Retry" em 95%: F5 primeiro; a imagem costuma já existir.
- Baixar: `fetch(img.src)` → blob → `<a download>`; pegar a imagem de MAIOR posição vertical
  (ordem do DOM não é ordem da conversa). Mover de `~/Downloads`.
- **Selecione a imagem gerada pelo `alt`, não pela posição.** O resultado vem com
  `alt="Generated image: <título>"`; o anexo vem com `alt="<nome do arquivo>"`. Filtre por
  `/Generated image/.test(img.alt)` — elimina o risco de baixar a anexada, e funciona mesmo quando o
  texto "Worked for" não renderiza (aconteceu em 3 de 4 chats numa rodada; o polling por "Worked for"
  teria travado). Achado do subagente Opus, 2026-09-11.
- **`naturalWidth === 0` não quer dizer que a imagem não existe.** Ela pode estar no DOM com `src`
  válido e sem decodificar. Filtre por `getBoundingClientRect().width > 200` em vez de `naturalWidth`,
  e o `fetch(img.src)` baixa normalmente mesmo com o quadro preto na tela. Isso evita esperar render
  à toa. Valide o blob com `if (bl.size < 50000) throw` pra não salvar placeholder.
- **Lote grande (10+ imagens): use a pasta sincronizada do Drive for Desktop, não a API nem a UI.**
  Subir por API custa contexto: o `base64Content` passa pelo modelo, e 41 PNGs de ~2 MB viram ~117 MB
  de base64 (~29M tokens) — mais que o orçamento de qualquer sessão. Um subagente que tentou abortou
  na conta, corretamente, antes de deixar a pasta pela metade. Se o Drive for Desktop estiver montado,
  `cp` para a pasta sincronizada resolve: zero contexto, zero OAuth, e o cliente sobe sozinho. Confira
  com `md5sum` origem contra destino, e depois a contagem pela API. Ache o ponto de montagem com
  `Get-PSDrive` (a unidade com Description "Google Drive") e resolva o atalho `My Drive.lnk` com
  `WScript.Shell.CreateShortcut`, porque o alvo real costuma estar em outra unidade.
  **Cuidado com conta:** se houver mais de uma conta Google, a pasta sincronizada local pode ser de
  uma e a pasta-alvo de outra. Procure o arquivo por nome com `search_files` e compare o `owner`.
  (Pepper, 2026-09-11: 41 arquivos, 84 MB.)
- Subir no Drive em resolução cheia (poucos arquivos, pela UI): abrir a pasta, clicar "Novo", disparar
  pointerdown/mousedown/pointerup/mouseup/click no `[role=menuitem]` "Upload de arquivo", tornar o
  `input[type=file]` visível, `find` + `file_upload`. Mover/renomear existentes: MCP do Drive
  (`update_file` com `parentId`/`title`) — bem mais confiável que arrastar na UI.
- **O menu "Novo" do Drive alterna a cada clique** e fecha se o clique anterior o abriu. Se
  `[role=menuitem]` vier vazio, clique uma vez no vazio da pasta, depois no "Novo". O atalho
  `alt+c` seguido de `u` também abre o seletor, mas falha se o foco estiver fora da lista.
- O `input[type=file]` é **consumido a cada upload**: pra um segundo lote, reabra o menu. Uploads de
  até 4 arquivos por vez (~7 MB) passaram sem problema.
- Ler coordenadas sempre do DOM (`getBoundingClientRect`); nunca reaproveitar de outra sessão.
- **Dê respiro ao rate limit.** 3 abas é o teto, mas ritmo também conta: em lote longo (30+ imagens) o
  ChatGPT passa a reclamar de "Too many requests" mesmo dentro do teto. O que funciona: escalonar o
  início (20 s entre abrir um job e o próximo), 15 s entre terminar um job e começar outro na mesma aba,
  e 60 s de pausa entre lotes. Ao ver "Too many requests" / "Please wait" / "You've reached": espere 90 s
  (em esperas de 30 s, porque o CDP estoura em 45 s), recarregue e só então reenvie; se voltar, 180 s.
  Nunca reenvie na hora — esperar é mais rápido que quebrar o lote e ficar com referência sem par.
  (Fernando, 2026-09-11, no lote de 34 da Pepper.)
- Paralelismo: **3 abas é o teto seguro**. Acima disso o ChatGPT devolve "Too many requests" e o lote
  quebra no meio, sobrando referência sem par. **Não feche abas no meio do lote**: fechar uma derruba
  o grupo de abas da automação e as outras ficam órfãs. Se o grupo se perder,
  `tabs_context_mcp({createIfEmpty:true})` recria.
- Uma geração pode falhar de verdade ("Something went wrong while generating your image"), diferente
  do quadro preto. Confira com screenshot antes de insistir no F5.
- Validado em 6 de 6 referências da Pepper (2026-09-09/10): a receita de imagem de estilo bate o
  acabamento aprovado em todas, com tatuagens e penteado certos.

## 5. Ciclo de uma referência

1. Ficha da biblioteca → prompt (`ref_NNN-*.txt`) com bloco canônico e HAIR.
2. Chat novo, imagem de estilo anexada, prompt inserido, enviado.
3. Baixar, montar lado a lado (antiga | versão anterior | nova) com PIL, medir colorfulness
   (Hasler & Süsstrunk) e detalhe fino (FIND_EDGES) se a dúvida for estilo/cor.
4. Rodar o checklist. Elemento faltando → corrigir prompt → chat novo.
5. Aprovada: subir no Drive, mover a anterior pra `historico/_vK`, registrar em
   `historico-versoes-canonicas.md` e na tabela de aprendizados.

## 6. Quando o usuário aprova uma variante (promoção de canon)

**Erro caro cometido em 2026-09-10, no Jarvis:** o usuário aprovou uma variante ("aprovado"), e eu
segui gerando oito referências a partir do Character Bible **antigo**. Oito imagens jogadas fora.

Um "aprovado" sobre uma imagem que diverge do Bible **não é** aprovação daquela imagem só: é uma
mudança de canon. Antes de gerar qualquer coisa depois de um aprovado, pare e faça:

1. **Pergunte-se: essa imagem bate com o `identity_lock` atual?** Se diverge em qualquer trava
   (etnia, pele, cabelo, olhos, material), o canon mudou. Não existe "aprovada mas não canônica"
   quando o usuário vai pedir mais imagens dela.
2. **Promova antes de gerar.** Escreva o Bible novo (`_vN+1`), com `supersedes` apontando pro
   anterior e `source` dizendo qual imagem virou canon e por quê.
3. **Arquive o anterior**, não apague: `identity/variantes-arquivadas/`, prompts em
   `prompts/canonical/variantes-arquivadas/`, imagens em `reference-library/variantes/<linha>/` com
   prefixo próprio.
4. **Reescreva o bloco de identidade canônica** a partir do Bible novo. É ele que entra nos prompts;
   se ficar velho, toda geração sai errada e parece problema do gerador.
5. **Só então** gere. E comite antes de gerar: a promoção de canon é o ponto que você vai querer
   poder voltar.

Sinal de alerta na conversa: se o usuário disser "aprovado" e a sua próxima ação for gerar imagem sem
ter tocado no Bible, você provavelmente está prestes a gerar do canon errado.

## 7. Onde está o resto (repo `fhgomes/personas`, ex-`pepper`)

Método compartilhado, na raiz do repo:

- `docs/rascunho-consistencia-visual.md` — pesquisa por provider, tabela imagem × texto × JSON,
  falhas conhecidas, aprendizados datados.
- `docs/procedimento-chatgpt.md` — operação detalhada e histórico dos travamentos.
- `docs/metodo-fidelidade.md`, `docs/pipeline-geracao.md`, `docs/geradores.md`.

Por persona, em `personas/<nome>/`:

- `docs/checklist-canonico.md`, `docs/historico-versoes-canonicas.md`, `docs/convencao-arquivos.md`,
  `docs/assets-drive.md`.
- Pepper: `personas/pepper/docs/diagnostico-estilo-cor.md` — diagnóstico de desvio com medição, e
  `prompts/canonical/ref_003-avatar-queixo-na-mao-v3-styleref.txt`, o prompt vencedor de exemplo.
- Jarvis: `personas/jarvis/docs/historico-versoes-canonicas.md` — as três rodadas de calibração da
  veia e a tabela do que cada texto produziu. É o melhor exemplo de como calibrar um sinal sutil.
