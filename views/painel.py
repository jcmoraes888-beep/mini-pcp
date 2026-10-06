"""Painel geral."""
import plotly.express as px
import streamlit as st

import ui

ui.configurar()
dados, res = ui.contexto()
pedidos, ordens, mrp, prog = dados["pedidos"], res["ordens"], res["mrp"], res["programa"]

st.title("🏭 Mini-PCP")
st.caption("Planejamento e controle da produção para pequenas indústrias: "
           "pedidos → necessidade de produção → MRP de materiais → programação por máquina.")

abertos = pedidos[pedidos["status"] == "Aberto"]
atrasadas = prog[prog["situacao"] == "🔴 Atrasa"]
urgentes = mrp[mrp["status"] == "🔴 Falta - urgente"]
a_comprar = mrp[mrp["sugestao_compra"] > 0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Pedidos abertos", len(abertos), f"{ui.num(abertos['quantidade'].sum())} pct",
          delta_color="off")
c2.metric("Ordens de produção", len(ordens), f"{ui.num(ordens['quantidade'].sum())} pct a produzir",
          delta_color="off")
c3.metric("Ordens que atrasam", len(atrasadas),
          "verificar programação" if len(atrasadas) else "tudo no prazo",
          delta_color="inverse" if len(atrasadas) else "off")
c4.metric("Materiais a comprar", len(a_comprar), f"{len(urgentes)} urgentes",
          delta_color="inverse" if len(urgentes) else "off")

st.divider()
esq, dir_ = st.columns(2)

with esq:
    st.subheader("Carga por máquina")
    if prog.empty:
        st.info("Nenhuma ordem de produção em aberto.")
    else:
        carga = (prog.dropna(subset=["producao_h"])
                 .assign(horas=lambda d: d["setup_h"] + d["producao_h"])
                 .groupby("maquina", as_index=False)["horas"].sum())
        carga = carga.merge(dados["maquinas"].rename(columns={"nome": "maquina"}), on="maquina")
        carga["dias_de_carga"] = carga["horas"] / carga["horas_dia"]
        fig = px.bar(carga, x="dias_de_carga", y="maquina", orientation="h",
                     text=carga["dias_de_carga"].map(lambda v: f"{ui.num(v, 1)} dias"),
                     labels={"dias_de_carga": "Dias de produção na fila", "maquina": ""})
        fig.update_traces(marker_color="#2f6db5", textposition="outside", cliponaxis=False)
        fig.update_layout(height=280, margin=dict(l=0, r=40, t=10, b=0))
        st.plotly_chart(fig)

with dir_:
    st.subheader("Alertas de compra")
    if a_comprar.empty:
        st.success("Nenhum material precisa de compra agora.")
    else:
        st.dataframe(
            a_comprar[["status", "material", "sugestao_compra", "unidade", "comprar_ate"]],
            hide_index=True,
            column_config={
                "status": "Situação", "material": "Material", "unidade": "Un.",
                "sugestao_compra": st.column_config.NumberColumn("Comprar", format="localized"),
                "comprar_ate": st.column_config.DateColumn("Comprar até", format=ui.FMT_DATA),
            },
        )

if not atrasadas.empty:
    st.subheader("Ordens que não fecham no prazo")
    st.dataframe(
        atrasadas.assign(atraso_h=-atrasadas["folga_h"])[
            ["maquina", "produto", "cliente", "quantidade", "data_entrega", "fim", "atraso_h"]],
        hide_index=True,
        column_config={
            "maquina": "Máquina", "produto": "Produto", "cliente": "Cliente",
            "quantidade": st.column_config.NumberColumn("Qtd.", format="localized"),
            "data_entrega": st.column_config.DateColumn("Entrega", format=ui.FMT_DATA),
            "fim": st.column_config.DatetimeColumn("Termina em", format=ui.FMT_DATAHORA),
            "atraso_h": st.column_config.NumberColumn("Atraso (h)", format="%.1f"),
        },
    )
    st.caption("Sugestão: antecipar a produção, fazer hora extra ou renegociar a data com o cliente.")

st.divider()
st.markdown("**Como usar:** cadastre pedidos em *Pedidos*, ajuste saldos em *Estoque*, "
            "revise receitas e máquinas em *Ficha técnica* e acompanhe *MRP* e *Programação*.")
