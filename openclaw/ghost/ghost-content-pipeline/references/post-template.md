# Template de Post Otimizado para SEO

## Estrutura HTML

```html
<!--
  Meta fields (set via API, não no HTML):
  - meta_title: max 60 chars, inclui keyword principal
  - meta_description: max 155 chars, CTA ou benefício claro
  - og_title, og_description: podem ser diferentes do meta
  - twitter_title, twitter_description: idem
  - custom_excerpt: 1-2 frases, resumo do post
  - feature_image: URL da imagem principal (1200x630px ideal)
-->

<!-- ANSWER CAPSULE — Featured Snippet bait -->
<blockquote>
  <p><strong>Em resumo:</strong> [Resposta direta à pergunta principal em 2-3 frases.
  Isso aumenta chances de aparecer como featured snippet no Google.]</p>
</blockquote>

<!-- INTRODUÇÃO — Hook + contexto -->
<p>[1-2 parágrafos. Começar com gancho que gera curiosidade. 
Mencionar a keyword principal naturalmente. 
Estabelecer autoridade/credibilidade.]</p>

<!-- SEÇÃO PRINCIPAL — H2s como perguntas -->
<h2>O que é [tópico]?</h2>
<p>[Explicação clara. Usar linguagem acessível. 
Incluir dados/estatísticas se disponíveis.]</p>

<h2>Como [ação principal] funciona?</h2>
<p>[Passo a passo ou explicação detalhada.]</p>

<!-- IMAGEM CONTEXTUAL -->
<figure>
  <img src="[url-da-imagem]" alt="[descrição detalhada para acessibilidade]" />
  <figcaption>[Legenda descritiva]</figcaption>
</figure>

<h2>Por que [benefício] é importante?</h2>
<p>[Conectar com dor/necessidade do leitor.]</p>

<!-- TABELA COMPARATIVA (quando aplicável) -->
<h2>[Tópico A] vs [Tópico B]: Comparação</h2>
<table>
  <thead>
    <tr>
      <th>Aspecto</th>
      <th>[Tópico A]</th>
      <th>[Tópico B]</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>[Critério 1]</td>
      <td>[Valor]</td>
      <td>[Valor]</td>
    </tr>
    <!-- mais linhas -->
  </tbody>
</table>

<!-- SEÇÃO PRÁTICA — How-to ou dicas -->
<h2>Como [fazer a coisa]? Guia passo a passo</h2>
<ol>
  <li><strong>[Passo 1]:</strong> [Descrição]</li>
  <li><strong>[Passo 2]:</strong> [Descrição]</li>
  <li><strong>[Passo 3]:</strong> [Descrição]</li>
</ol>

<!-- FAQ — Baseado em PAA real do Google -->
<h2>Perguntas Frequentes</h2>

<h3>[Pergunta real do Google PAA 1]?</h3>
<p>[Resposta direta, 2-4 frases.]</p>

<h3>[Pergunta real do Google PAA 2]?</h3>
<p>[Resposta direta, 2-4 frases.]</p>

<h3>[Pergunta real do Google PAA 3]?</h3>
<p>[Resposta direta, 2-4 frases.]</p>

<!-- Repetir para 5-10 FAQs -->

<!-- INTERNAL LINKS -->
<h2>Leia também</h2>
<ul>
  <li><a href="/post-relacionado-1/">Título do post relacionado 1</a></li>
  <li><a href="/post-relacionado-2/">Título do post relacionado 2</a></li>
  <li><a href="/post-relacionado-3/">Título do post relacionado 3</a></li>
</ul>

<!-- CONCLUSÃO -->
<h2>Conclusão</h2>
<p>[Resumo dos pontos principais. CTA claro — o que o leitor deve fazer agora?]</p>
```

## Regras de Qualidade

### Título (H1)
- Max 60 caracteres
- Inclui keyword principal
- Formato preferido: "Como [fazer X]: Guia Completo [ano]" ou "O que é [X]? Tudo que você precisa saber"

### Corpo
- Mínimo 1500 palavras para posts pillar
- Mínimo 800 palavras para posts regulares
- H2s escritos como perguntas reais do usuário
- Parágrafos curtos (3-4 frases max)
- Usar listas quando apropriado
- Pelo menos 1 tabela comparativa se o tópico permitir

### Imagens
- Feature image: 1200x630px (OG padrão)
- Formato: WebP preferível, < 200KB
- Alt text descritivo em todas as imagens
- Pelo menos 2 imagens por post de 1500+ palavras

### SEO
- Keyword principal no título, primeiro parágrafo, e 1-2 H2s
- Meta description com CTA (max 155 chars)
- Custom excerpt diferente da meta description
- URLs curtas e descritivas (slug)

### Internal Linking
- Mínimo 2 internal links por post
- Links em contexto relevante, não só no final
- Anchor text descritivo (não "clique aqui")

### E-E-A-T Signals
- Autor nomeado
- Voz em primeira pessoa quando apropriado
- Dados/fontes citados quando disponíveis
- Data de publicação e última atualização visíveis
