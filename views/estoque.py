"""Cadastro de itens e posição de estoque."""
import streamlit as st

import db
import ui

ui.configurar()
dados, _ = ui.contexto()
produtos = dados["produtos"].copy()

st.title("📦 Estoque e cadastro de itens")

tipos = st.segmented_control("Tipo de item", list(db.TIPOS), selection_mode="multi",
                             default=list(db.TIPOS), format_func=db.TIPOS.get)
vista = produtos[produtos["tipo"].isin(tipos or [])].copy()
vista["situacao"] = vista.apply(
    lambda r: "🔴 Abaixo do mínimo" if r.estoque_atual < r.estoque_minimo else "🟢 OK", axis=1)
vista["valor_estoque"] = vista["estoque_atual"] * vista["custo_unit"]

st.caption("Edite saldo, mínimo, lead time e custo direto na tabela e clique em salvar.")
editado = st.data_editor(
    vista[["id", "codigo", "nome", "tipo", "unidade", "estoque_atual", "estoque_minimo",
           "situacao", "lead_time_dias", "custo_unit", "valor_estoque", "fornecedor",
           "consumo_90d"]],
    hide_index=True, key="editor_estoque",
    disabled=["id", "codigo", "tipo", "situacao", "valor_estoque"],
    column_config={
        "id": None, "codigo": "Código", "nome": "Descrição", "unidade": "Un.",
        "tipo": st.column_config.TextColumn("Tipo", width="small"),
        "estoque_atual": st.column_config.NumberColumn("Saldo", min_value=0, format="localized"),
        "estoque_minimo": st.column_config.NumberColumn("Mínimo", min_value=0, format="localized"),
        "situacao": "Situação",
        "lead_time_dias": st.column_config.NumberColumn("Lead time (dias)", min_value=0, step=1),
        "custo_unit": st.column_config.NumberColumn("Custo unit. (R$)", min_value=0,
                                                    format="R$ %.2f"),
        "valor_estoque": st.column_config.NumberColumn("Valor em estoque", format="R$ %.2f"),
        "fornecedor": "Fornecedor",
        "consumo_90d": st.column_config.NumberColumn("Consumo 90 dias", min_value=0,
                                                     format="localized"),
    },
)

if st.button("💾 Salvar alterações", type="primary"):
    db.executar_varios(
        "UPDATE produtos SET nome = ?, unidade = ?, estoque_atual = ?, estoque_minimo = ?, "
        "lead_time_dias = ?, custo_unit = ?, fornecedor = ?, consumo_90d = ? WHERE id = ?",
        [(r.nome, r.unidade, float(r.estoque_atual), float(r.estoque_minimo),
          int(r.lead_time_dias), float(r.custo_unit), str(r.fornecedor or ""),
          float(r.consumo_90d or 0), int(r.id)) for r in editado.itertuples()],
    )
    st.toast("Estoque atualizado.")
    st.rerun()

mat = produtos[produtos["tipo"] != "PA"]
st.metric("Valor total em matéria-prima e embalagem",
          f"R$ {ui.num((mat['estoque_atual'] * mat['custo_unit']).sum(), 2)}")

with st.expander("➕ Novo item"):
    with st.form("novo_item", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([1.5, 4, 2, 1])
        codigo = c1.text_input("Código")
        nome = c2.text_input("Descrição")
        tipo = c3.selectbox("Tipo", list(db.TIPOS), format_func=db.TIPOS.get)
        unidade = c4.text_input("Unidade", value="kg")
        c5, c6, c7, c8 = st.columns(4)
        saldo = c5.number_input("Saldo", min_value=0.0)
        minimo = c6.number_input("Mínimo", min_value=0.0)
        lead = c7.number_input("Lead time (dias)", min_value=0, step=1)
        custo = c8.number_input("Custo unit. (R$)", min_value=0.0, format="%.2f")
        if st.form_submit_button("Salvar item", type="primary"):
            if not codigo.strip() or not nome.strip():
                st.error("Informe código e descrição.")
            elif codigo.strip().upper() in set(produtos["codigo"]):
                st.error("Já existe um item com esse código.")
            else:
                db.executar(
                    "INSERT INTO produtos (codigo, nome, tipo, unidade, estoque_atual, "
                    "estoque_minimo, lead_time_dias, custo_unit) VALUES (?,?,?,?,?,?,?,?)",
                    (codigo.strip().upper(), nome.strip(), tipo, unidade.strip(),
                     saldo, minimo, int(lead), custo))
                st.toast("Item cadastrado.")
                st.rerun()
