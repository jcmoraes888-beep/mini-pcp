"""Carteira de pedidos."""
from datetime import date, timedelta

import streamlit as st

import db
import ui

ui.configurar()
dados, _ = ui.contexto()
produtos, pedidos = dados["produtos"], dados["pedidos"]
acabados = produtos[produtos["tipo"] == "PA"]

st.title("🧾 Carteira de pedidos")

with st.expander("➕ Novo pedido", expanded=pedidos.empty):
    with st.form("novo_pedido", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([3, 3, 1.5, 1.5])
        cliente = c1.text_input("Cliente")
        produto_id = c2.selectbox("Produto", acabados["id"],
                                  format_func=dict(zip(acabados["id"], acabados["nome"])).get)
        qtd = c3.number_input(f"Quantidade ({ui.un()})", min_value=1, step=100, value=1000)
        entrega = c4.date_input("Entrega", value=date.today() + timedelta(days=3),
                                format="DD/MM/YYYY")
        if st.form_submit_button("Salvar pedido", type="primary"):
            if not cliente.strip():
                st.error("Informe o cliente.")
            else:
                db.executar("INSERT INTO pedidos (cliente, produto_id, quantidade, data_entrega) "
                            "VALUES (?,?,?,?)",
                            (cliente.strip(), int(produto_id), qtd, entrega.isoformat()))
                st.toast("Pedido salvo.")
                st.rerun()

filtro = st.segmented_control("Mostrar", ["Aberto", "Entregue", "Cancelado"],
                              selection_mode="multi", default=["Aberto"])
vista = pedidos[pedidos["status"].isin(filtro or [])]

st.caption("Altere o **status** ou a **data de entrega** direto na tabela e clique em salvar.")
editado = st.data_editor(
    vista[["id", "cliente", "produto", "quantidade", "data_entrega", "status"]],
    hide_index=True, key="editor_pedidos",
    disabled=["id", "cliente", "produto"],
    column_config={
        "id": st.column_config.NumberColumn("Nº", width="small"),
        "cliente": "Cliente", "produto": "Produto",
        "quantidade": st.column_config.NumberColumn(f"Qtd. ({ui.un()})", min_value=1, format="localized"),
        "data_entrega": st.column_config.DateColumn("Entrega", format=ui.FMT_DATA),
        "status": st.column_config.SelectboxColumn("Status", options=db.STATUS_PEDIDO,
                                                   required=True),
    },
)

if st.button("💾 Salvar alterações", type="primary"):
    db.executar_varios(
        "UPDATE pedidos SET quantidade = ?, data_entrega = ?, status = ? WHERE id = ?",
        [(float(r.quantidade), r.data_entrega.isoformat(), r.status, int(r.id))
         for r in editado.itertuples()],
    )
    st.toast("Pedidos atualizados.")
    st.rerun()

st.divider()
resumo = (pedidos[pedidos["status"] == "Aberto"]
          .groupby("produto", as_index=False)["quantidade"].sum()
          .sort_values("quantidade", ascending=False))
st.subheader("Demanda aberta por produto")
st.dataframe(resumo, hide_index=True,
             column_config={"produto": "Produto",
                            "quantidade": st.column_config.NumberColumn(f"Qtd. ({ui.un()})",
                                                                        format="localized")})
