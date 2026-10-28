# 🏭 Mini-PCP

Planejamento e controle da produção para pequenas indústrias, feito em Python + Streamlit.

O app leva o fluxo clássico do PCP de uma planilha para um sistema simples:

**pedidos → ordens de produção → MRP de materiais → programação por máquina**

O app traz duas empresas **fictícias** de exemplo, escolhidas na barra lateral:

- **Panificadora Trigo Bom**: 5 produtos, 13 matérias-primas e embalagens, 3 linhas de produção.
- **Vasos Oeste Plásticos**: vasos injetados com reciclado próprio, masterbatch de cor, aditivo UV,
  3 injetoras e setup de troca de molde e de cor.

Os pedidos usam datas relativas a hoje, então a demonstração funciona em qualquer dia.

## Telas

| Tela | O que faz |
|---|---|
| **Painel** | Indicadores, carga de cada máquina em dias, alertas de compra e ordens que atrasam |
| **Pedidos** | Carteira de pedidos: cadastro, status (aberto/entregue/cancelado) e data de entrega |
| **Estoque** | Saldo, estoque mínimo, lead time e custo de cada item, com valor em estoque |
| **Ficha técnica** | Estrutura do produto (BOM), custo de material por unidade, roteiro, **plano B** (máquinas alternativas com prioridade) e máquinas com status Operando/Parada |
| **MRP** | Ordens de produção, necessidade de materiais, sugestão de compra e data limite (exporta CSV) |
| **Programação** | Sequenciamento por máquina pela menor data de entrega, Gantt, folga de cada ordem e **ordens remanejadas pelo plano B** |
| **Compras** | Consumo médio, cobertura em dias contra o lead time, ponto de pedido e lista por fornecedor (CSV) |

## Lógica de cálculo (`pcp.py`)

1. **Ordens de produção**: o estoque de produto acabado abate os pedidos abertos em ordem de entrega;
   o que falta vira ordem.
2. **MRP**: cada ordem é explodida pela ficha técnica. O material precisa estar na fábrica 1 dia
   antes da entrega. A sugestão de compra cobre a demanda e devolve o estoque ao mínimo.
   *Comprar até* = primeira data de falta − lead time do fornecedor.
3. **Programação**: as ordens de cada máquina são sequenciadas pela regra EDD (menor data de entrega),
   respeitando as horas de trabalho por dia. Ordens seguidas do mesmo produto não repetem o setup.
   Folga negativa = atraso.
4. **Plano B (máquina parada ou ordem atrasando)**: cada produto pode rodar em máquinas
   alternativas, em ordem de prioridade (2, 3...), cada uma com a sua produtividade.
   - Máquina marcada como **Parada** não recebe ordens: cada ordem dela vai para a alternativa
     que deixa o programa com menos atraso.
   - Depois, cada ordem que **atrasa** testa as alternativas. A troca só fica se o atraso total
     diminuir, para não salvar uma ordem atrasando as outras da máquina que a recebeu.
   - A tela mostra de onde a ordem saiu, para onde foi, a prioridade usada e o motivo.
5. **Compras**: consumo/dia = consumo dos últimos 90 dias ÷ 90; cobertura = estoque ÷ consumo/dia;
   ponto de pedido = consumo/dia × lead time + estoque mínimo. Cobertura menor que o lead time =
   *comprar já*. A sugestão cobre o lead time + N dias (ajustável) e respeita os pedidos firmes do MRP.

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

O banco SQLite (`pcp.db`) é criado sozinho com os dados de exemplo na primeira execução.
O botão **Restaurar dados de exemplo** na barra lateral volta a empresa escolhida ao estado inicial.

## Publicar no Streamlit Community Cloud

1. Suba esta pasta para um repositório no GitHub.
2. Em share.streamlit.io, crie um app apontando para `app.py`.

> No Streamlit Cloud o arquivo SQLite é temporário: os dados voltam ao exemplo quando o app reinicia.
> Para uso real com cliente, trocar por um banco hospedado (ex.: Supabase/PostgreSQL).

## Estrutura

```
app.py            # navegação e barra lateral
db.py             # SQLite + dados de exemplo
pcp.py            # regras de PCP (funções puras, testáveis)
ui.py             # utilidades de tela
views/            # uma página por arquivo
```

## Próximos passos (v2)

- Considerar estoque mínimo de produto acabado nas ordens
- Plano B dividindo uma ordem grande entre duas máquinas
- Priorizar pela cobertura do estoque (dias até faltar), além da data de entrega
- Calendário com fins de semana e feriados
- Programação para trás (data mais tarde de início) e simulação de hora extra
- Integração com o App Kaizen de Perdas (perdas reais reduzindo a produtividade)
- Login e banco hospedado para uso por cliente
