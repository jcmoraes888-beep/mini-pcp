"""Compras: cobertura em dias, ponto de pedido e sugestão por fornecedor."""
import plotly.graph_objects as go
import streamlit as st

import pcp
import ui

ui.configurar()
dados, res = ui.contexto()

st.title("🛒 Compras · cobertura e ponto de pedido")
st.caption("O controle que evita compra urgente: consumo médio dos últimos 90 dias, "
           "prazo real de cada fornecedor e os pedidos firmes do MRP, item a item.")

dias_cobrir = st.slider("Cada compra deve cobrir quantos dias além do lead time?",
                        min_value=7, max_value=90, value=30, step=1)
compras = pcp.calcular_compras(dados["produtos"], res["mrp"], dias_cobrir)

comprar_ja = compras[compras["situacao"] == "🔴 Comprar já"]
pedir = compras[compras["situacao"] == "🟠 Pedir agora"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Comprar já", len(comprar_ja), "cobertura menor que o lead time",
          delta_color="inverse" if len(comprar_ja) else "off")
c2.metric("Pedir agora", len(pedir), "chegou no ponto de pedido", delta_color="off")
c3.metric("Valor sugerido", f"R$ {ui.num(compras['valor_compra'].sum(), 2)}")
com_consumo = compras.dropna(subset=["cobertura_dias"])
c4.metric("Cobertura mediana", f"{ui.num(com_consumo['cobertura_dias'].median(), 0)} dias"
          if not com_consumo.empty else "-")

st.divider()
st.subheader("Cobertura de cada item contra o prazo do fornecedor")
st.caption("Barra = quantos dias o estoque dura no consumo médio. "
           "Traço = lead time do fornecedor. Barra que não alcança o traço já virou urgência.")
graf = com_consumo.sort_values("cobertura_dias", ascending=False)
limite = (min(120.0, 1.1 * float(max(graf["cobertura_dias"].max(), graf["lead_time_dias"].max() + 5)))
          if not graf.empty else 90.0)
fig = go.Figure()
fig.add_bar(
    y=graf["nome"], x=graf["cobertura_dias"].clip(upper=limite), orientation="h",
    marker=dict(color="#3987e5", cornerradius=4), name="Cobertura (dias)",
    customdata=graf[["cobertura_dias", "lead_time_dias", "situacao"]].values,
    hovertemplate="<b>%{y}</b><br>Cobertura: %{customdata[0]:.0f} dias"
                  "<br>Lead time: %{customdata[1]} dias<br>%{customdata[2]}<extra></extra>",
)
fig.add_scatter(
    y=graf["nome"], x=graf["lead_time_dias"], mode="markers", name="Lead time (dias)",
    marker=dict(symbol="line-ns", size=22, line=dict(width=3, color="#f0f1f3")),
    hovertemplate="<b>%{y}</b><br>Lead time: %{x} dias<extra></extra>",
)
fig.update_layout(height=max(260, 34 * len(graf) + 60), margin=dict(l=0, r=20, t=10, b=0),
                  xaxis_title="dias", legend=dict(orientation="h", y=1.08, x=0),
                  bargap=0.35)
fig.update_xaxes(range=[0, limite], gridcolor="rgba(128,128,128,0.15)")
st.plotly_chart(fig)

st.subheader("Lista de compras")
fornecedores = sorted(f for f in compras["fornecedor"].unique() if f)
escolha = st.multiselect("Fornecedor", fornecedores, placeholder="Todos os fornecedores")
so_sugestao = st.toggle("Mostrar só itens com sugestão de compra", value=True)
vista = compras[compras["fornecedor"].isin(escolha)] if escolha else compras
if so_sugestao:
    vista = vista[vista["sugestao"] > 0]

cfg = {
    "situacao": "Situação", "fornecedor": "Fornecedor", "codigo": "Código",
    "nome": "Item", "unidade": "Un.",
    "estoque_atual": st.column_config.NumberColumn("Estoque", format="localized"),
    "consumo_dia": st.column_config.NumberColumn("Consumo/dia", format="%.1f"),
    "cobertura_dias": st.column_config.NumberColumn("Cobertura (dias)", format="%.0f"),
    "lead_time_dias": st.column_config.NumberColumn("Lead time (dias)"),
    "ponto_pedido": st.column_config.NumberColumn("Ponto de pedido", format="localized"),
    "sugestao": st.column_config.NumberColumn("Comprar", format="localized"),
    "valor_compra": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
}
st.dataframe(vista[list(cfg)], hide_index=True, column_config=cfg)

por_fornecedor = (compras[compras["sugestao"] > 0]
                  .groupby("fornecedor", as_index=False)
                  .agg(itens=("codigo", "count"), valor=("valor_compra", "sum"))
                  .sort_values("valor", ascending=False))
esq, dir_ = st.columns([2, 1])
with esq:
    st.markdown("**Resumo por fornecedor** (um pedido de compra para cada)")
    st.dataframe(por_fornecedor, hide_index=True, column_config={
        "fornecedor": "Fornecedor", "itens": "Itens",
        "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")})
with dir_:
    st.download_button(
        "⬇️ Baixar lista de compras (CSV)",
        vista.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="lista_compras.csv", mime="text/csv", disabled=vista.empty, width="stretch",
    )

with st.expander("Como o cálculo funciona"):
    st.markdown(
        "- **Consumo/dia** = consumo dos últimos 90 dias ÷ 90.\n"
        "- **Cobertura** = estoque ÷ consumo/dia. Se for menor que o lead time, "
        "o material acaba antes de a compra chegar: **comprar já**.\n"
        "- **Ponto de pedido** = consumo/dia × lead time + estoque mínimo (segurança). "
        "Chegou nele: **pedir agora**.\n"
        "- **Comprar** = o que cobre o lead time + os dias escolhidos acima, mais o mínimo. "
        "Se os pedidos firmes do MRP pedirem mais, vale o maior.\n"
        "- Antes de uma alta de vendas (ex.: a primavera na jardinagem), o consumo passado "
        "subestima a demanda: aí a previsão de vendas, explodida no MRP, manda."
    )
