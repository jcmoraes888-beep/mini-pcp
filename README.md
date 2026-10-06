# 🏭 Mini-PCP

Planejamento e controle da produção para pequenas indústrias, feito em Python + Streamlit.

O app leva o fluxo clássico do PCP de uma planilha para um sistema simples:

**pedidos → ordens de produção → MRP de materiais → programação por máquina**

Os dados de exemplo são de uma panificadora **fictícia** (Panificadora Trigo Bom): 5 produtos,
13 matérias-primas e embalagens, 3 linhas de produção e 12 pedidos com datas relativas a hoje.

## Telas

| Tela | O que faz |
|---|---|
| **Painel** | Indicadores, carga de cada máquina em dias, alertas de compra e ordens que atrasam |
| **Pedidos** | Carteira de pedidos: cadastro, status (aberto/entregue/cancelado) e data de entrega |
| **Estoque** | Saldo, estoque mínimo, lead time e custo de cada item, com valor em estoque |
| **Ficha técnica** | Estrutura do produto (BOM), custo de material por unidade, roteiro e máquinas |
| **MRP** | Ordens de produção, necessidade de materiais, sugestão de compra e data limite (exporta CSV) |
| **Programação** | Sequenciamento por máquina pela menor data de entrega, Gantt e folga de cada ordem |

## Lógica de cálculo (`pcp.py`)

1. **Ordens de produção**: o estoque de produto acabado abate os pedidos abertos em ordem de entrega;
   o que falta vira ordem.
2. **MRP**: cada ordem é explodida pela ficha técnica. O material precisa estar na fábrica 1 dia
   antes da entrega. A sugestão de compra cobre a demanda e devolve o estoque ao mínimo.
   *Comprar até* = primeira data de falta − lead time do fornecedor.
3. **Programação**: as ordens de cada máquina são sequenciadas pela regra EDD (menor data de entrega),
   respeitando as horas de trabalho por dia. Ordens seguidas do mesmo produto não repetem o setup.
   Folga negativa = atraso.

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

O banco SQLite (`pcp.db`) é criado sozinho com os dados de exemplo na primeira execução.
O botão **Restaurar dados de exemplo** na barra lateral volta tudo ao estado inicial.

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
- Calendário com fins de semana e feriados
- Programação para trás (data mais tarde de início) e simulação de hora extra
- Integração com o App Kaizen de Perdas (perdas reais reduzindo a produtividade)
- Login e banco hospedado para uso por cliente
