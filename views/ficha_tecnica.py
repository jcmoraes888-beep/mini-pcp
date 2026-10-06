"""Ficha técnica (BOM), roteiro de produção e cadastro de máquinas."""
import pandas as pd
import streamlit as st

import db
import ui

ui.configurar()
dados, _ = ui.contexto()
produtos, bom, roteiro, maquinas = (dados["produtos"], dados["bom"],
                                    dados["roteiro"], dados["maquinas"])
acabados = produtos[produtos["tipo"] == "PA"]
materiais = produtos[produtos["tipo"] != "PA"]
nome_por_id = dict(zip(produtos["id"], produtos["nome"]))
id_por_nome = {v: k for k, v in nome_por_id.items()}

st.title("📋 Ficha técnica e roteiro")

if acabados.empty:
    st.info("Cadastre um produto acabado (tipo PA) em Estoque.")
    st.stop()

pa = st.selectbox("Produto acabado", acabados["id"], format_func=nome_por_id.get)

aba_bom, aba_rot, aba_maq = st.tabs(["Ficha técnica (BOM)", "Roteiro", "Máquinas"])

with aba_bom:
    atual = bom[bom["produto_id"] == pa].merge(
        materiais[["id", "nome", "unidade", "custo_unit"]],
        left_on="componente_id", right_on="id")
    tabela = pd.DataFrame({"componente": atual["nome"], "qtd_por_un": atual["qtd_por_un"]})

    st.caption("Quantidade de cada material para **1 unidade** do produto. "
               "Use a última linha para adicionar; selecione a linha e tecle Delete para remover.")
    editado = st.data_editor(
        tabela, hide_index=True, num_rows="dynamic", key=f"bom_{pa}",
        column_config={
            "componente": st.column_config.SelectboxColumn(
                "Componente", options=sorted(materiais["nome"]), required=True),
            "qtd_por_un": st.column_config.NumberColumn(
                "Qtd. por unidade", min_value=0.0, format="%.4f", required=True),
        },
    )

    custo = editado.dropna().merge(materiais[["nome", "unidade", "custo_unit"]],
                                   left_on="componente", right_on="nome")
    custo["custo"] = custo["qtd_por_un"] * custo["custo_unit"]
    st.metric("Custo de material por unidade", f"R$ {ui.num(custo['custo'].sum(), 4)}")

    if st.button("💾 Salvar ficha técnica", type="primary"):
        linhas = editado.dropna()
        if linhas["componente"].duplicated().any():
            st.error("Há componentes repetidos. Some as quantidades em uma linha só.")
        else:
            with db.conectar() as con:
                con.execute("DELETE FROM bom WHERE produto_id = ?", (int(pa),))
                con.executemany(
                    "INSERT INTO bom (produto_id, componente_id, qtd_por_un) VALUES (?,?,?)",
                    [(int(pa), int(id_por_nome[r.componente]), float(r.qtd_por_un))
                     for r in linhas.itertuples()])
            st.toast("Ficha técnica salva.")
            st.rerun()

with aba_rot:
    if maquinas.empty:
        st.info("Cadastre uma máquina na aba Máquinas.")
    else:
        rot = roteiro[roteiro["produto_id"] == pa]
        rot = rot.iloc[0] if not rot.empty else None
        ids_maq = list(maquinas["id"])
        with st.form(f"roteiro_{pa}"):
            c1, c2, c3 = st.columns([3, 1.5, 1.5])
            maq = c1.selectbox("Máquina / linha", ids_maq,
                               index=ids_maq.index(rot["maquina_id"]) if rot is not None else 0,
                               format_func=dict(zip(maquinas["id"], maquinas["nome"])).get)
            taxa = c2.number_input("Produtividade (un/h)", min_value=1.0,
                                   value=float(rot["un_por_hora"]) if rot is not None else 100.0)
            setup = c3.number_input("Setup (min)", min_value=0.0,
                                    value=float(rot["setup_min"]) if rot is not None else 30.0)
            if st.form_submit_button("Salvar roteiro", type="primary"):
                db.executar("INSERT OR REPLACE INTO roteiro (produto_id, maquina_id, un_por_hora, "
                            "setup_min) VALUES (?,?,?,?)", (int(pa), int(maq), taxa, setup))
                st.toast("Roteiro salvo.")
                st.rerun()
        if rot is None:
            st.warning("Este produto ainda não tem roteiro: as ordens dele não entram na programação.")

with aba_maq:
    st.caption("Horas de trabalho por dia de cada máquina (ex.: 2 turnos = 16 h).")
    ed_maq = st.data_editor(
        maquinas, hide_index=True, num_rows="dynamic", key="maquinas",
        column_config={
            "id": None, "nome": st.column_config.TextColumn("Máquina / linha", required=True),
            "horas_dia": st.column_config.NumberColumn("Horas por dia", min_value=1,
                                                       max_value=23.5, required=True),
        },
    )
    if st.button("💾 Salvar máquinas", type="primary"):
        ed_maq = ed_maq.dropna(subset=["nome", "horas_dia"])
        removidas = set(maquinas["id"]) - set(ed_maq["id"].dropna())
        usadas = removidas & set(roteiro["maquina_id"])
        if usadas:
            st.error("Não dá para excluir máquina usada em roteiro. Troque o roteiro antes.")
        else:
            with db.conectar() as con:
                for mid in removidas:
                    con.execute("DELETE FROM maquinas WHERE id = ?", (int(mid),))
                for r in ed_maq.itertuples():
                    if pd.isna(r.id):
                        con.execute("INSERT INTO maquinas (nome, horas_dia) VALUES (?,?)",
                                    (r.nome, float(r.horas_dia)))
                    else:
                        con.execute("UPDATE maquinas SET nome = ?, horas_dia = ? WHERE id = ?",
                                    (r.nome, float(r.horas_dia), int(r.id)))
            st.toast("Máquinas salvas.")
            st.rerun()
