# Exemplo real — radar de 12 meses, 5 regiões (set/2026)

Pedido: "mapeamento de eventos que dá pra ir ou submeter, de hoje até daqui 12 meses — Java principalmente, mas também GDG,
MVP Conf, Oracle, Codecon; não só Brasil: EUA, LatAm, Europa e JUGs remotos; com probabilidade de aceite".

## Como foi feito

1. **Base existente primeiro**: um tracker próprio já tinha 66 eventos com chance de aceite calculada. Foi lido como
   `--extra` e virou a base dos ids (nada reescrito).
2. **Fontes locais por HTTP**: planilha Google comunitária de São Paulo (4 abas, ago–nov), eventos.cafebugado.com.br (todos os
   eventos vêm no HTML da página 1), Luma SP (precisou do navegador: SPA).
3. **5 subagentes em paralelo** (Brasil, EUA/Canadá, Europa, LatAm, online/JUGs) com o `fanout-brief-template.md` e
   o schema JSON idêntico ao do script. Cada um devolveu 58–111 entradas + um `.md` com o que não conseguiu verificar.
   Todos esgotaram a cota de WebSearch na metade e terminaram com WebFetch nas fontes oficiais.
4. **Merge** por `id` + aliases (TDC Porto Alegre ≡ TDCx Porto Alegre; vJUG apareceu em 3 agentes) → 426 eventos:
   BR 99 · EU 115 · NA 84 · LATAM 67 · ONLINE 51 · OTHER 10.
5. **Verificação manual dos "agir agora"** no Sessionize: um CFP registrado como "fechado em 22/09" estava **aberto até
   30/09** (prazo estendido). Outros dois confirmados (JCON Europe 23/10, Code Remix 30/09 com hotel + verba de viagem).
6. **Painel** (`panel.html`) com "agir agora" (CFP aberto ou prazo ≤ 60 dias), linha do tempo por mês e tabela filtrável;
   nota-resumo com tabela de prazos, estratégia de escada (JUG online → regional → média → grande) e lista do que ficou
   estimado.

## O que o resumo final trouxe (forma, não os dados)

- Tabela "fecham até 15/11" com 25 linhas: prazo, evento, região, chance, o que o speaker recebe, talk sugerida, link.
- 6 pontos de estratégia (semana mais cara do ano, escada de credibilidade, eventos que pagam viagem, onde estrear a talk
  nova, programas que mudam o aceite, o que é só estimativa).
- "Só ir" nos próximos 90 dias na cidade da pessoa, com o motivo de networking de cada um.
- Lista explícita de não verificados (calendário do ano seguinte inteiro, JUGs regionais sem prova de atividade, páginas
  JS que não abriram).

## Lições que viraram regra na skill

- Prazo anotado em tracker envelhece: verificar na fonte antes de dizer "fechou".
- Tags de agregador superestimam IA; nome do evento pesa mais.
- JUGs locais e eventos de vendor nunca aparecem em agregador: só pesquisa dirigida por região.
- Dois eventos com o mesmo nome em anos diferentes não são duplicata; o mesmo evento com nomes diferentes é.
