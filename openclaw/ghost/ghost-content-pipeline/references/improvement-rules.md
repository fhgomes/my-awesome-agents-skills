# Regras de Melhoria de Conteúdo (Content Improver)

## Princípio Central

Melhorar posts existentes SEM quebrar o que já funciona. 
Nunca mudar a URL/slug. Nunca remover conteúdo que ranqueie bem.
Sempre ADICIONAR valor — nunca subtrair.

## Checklist de Análise (antes de melhorar)

1. **Word count** — Se < 800 palavras, expandir significativamente
2. **Estrutura de H2s** — Existem H2s? São perguntas reais?
3. **FAQ section** — Existe? Usa dados PAA reais?
4. **Feature image** — Existe? Está otimizada (WebP, < 200KB)?
5. **Meta description** — Existe? É atraente? Tem CTA?
6. **Custom excerpt** — Existe? É diferente da meta description?
7. **Internal links** — Quantos? Mínimo 2.
8. **Tabelas** — Tem comparações que beneficiariam de tabela?
9. **Alt text** — Todas imagens têm alt descritivo?
10. **Answer capsule** — Tem resposta rápida no topo?

## Regras de Melhoria

### DO (Fazer)
- Adicionar answer capsule se não existir
- Converter H2s genéricos em perguntas reais
- Adicionar FAQ com 5-10 perguntas do Google PAA (dados reais, via Serper)
- Adicionar tabela comparativa quando o tópico permitir
- Adicionar internal links para posts relacionados
- Expandir parágrafos curtos com mais contexto
- Adicionar dados/estatísticas quando disponíveis
- Melhorar meta description com CTA
- Gerar novas imagens se as atuais forem de baixa qualidade
- Adicionar structured data markup se apropriado

### DON'T (Não fazer)
- Nunca mudar o slug/URL
- Nunca remover conteúdo que possa estar ranqueando
- Nunca mudar o tom/voz drasticamente
- Nunca inventar FAQs — usar dados reais do Google
- Nunca adicionar keywords de forma forçada (keyword stuffing)
- Nunca remover internal links existentes
- Nunca mudar o autor
- Nunca resetar a data de publicação original
- Nunca usar imagens genéricas de stock sem contexto

## Ordem de Prioridade

1. **Alta prioridade**: Meta description vazia, sem FAQ, sem answer capsule
2. **Média prioridade**: Poucos internal links, sem tabelas, < 1000 palavras
3. **Baixa prioridade**: Melhorar H2s, adicionar mais imagens, expandir seções

## Critérios de Seleção (qual post melhorar primeiro)

Para cron job de content improver, selecionar posts por:

```
ORDER BY updated_at ASC  → Post mais antigo sem update
```

Isso garante que todos os posts recebem atenção ao longo do tempo.

Alternativas:
- Posts com mais tráfego mas sem FAQ → maior impacto
- Posts com meta_description vazia → quick win
- Posts com < 800 palavras → maior potencial de melhoria

## Validação Pós-Melhoria

Após melhorar o post, verificar:

1. HTML é válido (não quebrou nada)
2. Links internos apontam para posts que existem
3. Imagens carregam corretamente
4. Meta description tem < 155 chars
5. Título tem < 60 chars
6. Post renderiza corretamente no Ghost
