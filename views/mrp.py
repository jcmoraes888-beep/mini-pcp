"""MRP: ordens de produção e necessidade de materiais."""
import streamlit as st

import ui

ui.configurar()
dados, res = ui.contexto()
ordens, mrp = res["ordens"], res["mrp"]

st.title("🧮 MRP · necessidade de materiais")
st.caption("Estoque de produto acabado abate os pedidos por data de entrega → o que falta vira "
           "ordem de produção → as ordens são explodidas pela ficha técnica e comparadas "
           "com o estoque de cada material.")

st.subheader("Ordens de produção")
if ordens.empty:
    st.success("O estoque de produto acabado cobre todos os pedidos abertos.")
else:
    st.dataframe(
        ordens[["pedido_id", "cliente", "codigo", "produto", "quantidade", "data_entrega"]],
        hide_index=True,
        column_config={
            "pedido_id": "Pedido", "cliente": "Cliente", "codigo": "Código", "produto": "Produto",
            "quantidade": st.column_config.NumberColumn(f"Produzir ({ui.un()})", format="localized"),
            "data_entrega": st.column_config.DateColumn("Entrega", format=ui.FMT_DATA),
        },
    )

st.subheader("Materiais")
so_compras = st.toggle("Mostrar só o que precisa comprar", value=True)
vista = mrp[mrp["sugestao_compra"] > 0] if so_compras else mrp

cfg = {
    "status": "Situação", "codigo": "Código", "material": "Material", "unidade": "Un.",
    "estoque": st.column_config.NumberColumn("Estoque", format="localized"),
    "minimo": st.column_config.NumberColumn("Mínimo", format="localized"),
    "demanda": st.column_config.NumberColumn("Demanda", format="localized"),
    "saldo_projetado": st.column_config.NumberColumn("Saldo projetado", format="localized"),
    "primeira_falta": st.column_config.DateColumn("Falta em", format=ui.FMT_DATA),
    "lead_time": st.column_config.NumberColumn("Lead time (d)"),
    "sugestao_compra": st.column_config.NumberColumn("Sugestão de compra", format="localized"),
    "comprar_ate": st.column_config.DateColumn("Comprar até", format=ui.FMT_DATA),
    "custo_compra": st.column_config.NumberColumn("Custo estimado", format="R$ %.2f"),
}
st.dataframe(vista[list(cfg)], hide_index=True, column_config=cfg)

total = mrp["custo_compra"].sum()
c1, c2 = st.columns([1, 3])
c1.metric("Custo estimado das compras", f"R$ {ui.num(total, 2)}")
compras = mrp[mrp["sugestao_compra"] > 0][
    ["codigo", "material", "unidade", "sugestao_compra", "comprar_ate", "custo_compra"]]
c2.download_button(
    "⬇️ Baixar sugestão de compra (CSV)",
    compras.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
    file_name="sugestao_compra.csv", mime="text/csv", disabled=compras.empty,
)

with st.expander("Como a sugestão é calculada"):
    st.markdown(
        "- **Demanda**: soma de (quantidade da ordem × quantidade na ficha técnica).\n"
        "- **Falta em**: primeiro dia em que a demanda acumulada passa do estoque. "
        "O material precisa estar na fábrica 1 dia antes da entrega do pedido.\n"
        "- **Sugestão de compra**: o que cobre a demanda e devolve o estoque ao mínimo.\n"
        "- **Comprar até**: data da falta − lead time do fornecedor. "
        "Se já passou, a situação fica *urgente*."
    )
