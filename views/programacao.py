"""Programação da produção por máquina (Gantt)."""
from datetime import date, datetime, time

import plotly.express as px
import streamlit as st

import pcp
import ui

ui.configurar()
dados, res = ui.contexto()

st.title("📅 Programação da produção")
st.caption("Sequência por máquina pela **menor data de entrega** (regra EDD). "
           "Ordens seguidas do mesmo produto não repetem o setup.")

c1, c2 = st.columns(2)
dia = c1.date_input("Começar a programar em", value=date.today(), format="DD/MM/YYYY")
hora = c2.number_input("Início do turno (hora)", min_value=0, max_value=23, value=6)

prog = pcp.programar(res["ordens"], dados["roteiro"], dados["maquinas"],
                     datetime.combine(dia, time(int(hora))), int(hora))

if prog.empty:
    st.success("Nenhuma ordem de produção para programar.")
    st.stop()

com_horario = prog.dropna(subset=["inicio"])
atrasos = (prog["situacao"] == "🔴 Atrasa").sum()
k1, k2, k3 = st.columns(3)
k1.metric("Ordens programadas", len(com_horario))
k2.metric("Ordens que atrasam", int(atrasos))
k3.metric("Término da última ordem",
          com_horario["fim"].max().strftime("%d/%m %H:%M") if not com_horario.empty else "-")

if not com_horario.empty:
    g = com_horario.assign(rotulo=com_horario["codigo"] + " · " + com_horario["cliente"])
    fig = px.timeline(g, x_start="inicio", x_end="fim", y="maquina", color="codigo",
                      text="codigo", hover_name="rotulo",
                      hover_data={"quantidade": ":,.0f", "data_entrega": True,
                                  "situacao": True, "maquina": False, "codigo": False},
                      labels={"maquina": "", "codigo": "Produto"})
    fig.update_yaxes(autorange="reversed")
    fig.update_traces(marker_line_color="white", marker_line_width=1, textangle=0,
                      insidetextanchor="middle")
    fig.add_vline(x=datetime.now(), line_dash="dot", line_color="gray")
    fig.update_layout(height=120 + 70 * g["maquina"].nunique(),
                      margin=dict(l=0, r=0, t=10, b=0), legend_title_text="")
    st.plotly_chart(fig)

st.dataframe(
    prog, hide_index=True,
    column_config={
        "maquina": "Máquina", "codigo": "Código", "produto": "Produto", "cliente": "Cliente",
        "quantidade": st.column_config.NumberColumn("Qtd.", format="localized"),
        "data_entrega": st.column_config.DateColumn("Entrega", format=ui.FMT_DATA),
        "setup_h": st.column_config.NumberColumn("Setup (h)", format="%.2f"),
        "producao_h": st.column_config.NumberColumn("Produção (h)", format="%.2f"),
        "inicio": st.column_config.DatetimeColumn("Início", format=ui.FMT_DATAHORA),
        "fim": st.column_config.DatetimeColumn("Fim", format=ui.FMT_DATAHORA),
        "folga_h": st.column_config.NumberColumn("Folga (h)", format="%.1f"),
        "situacao": "Situação",
    },
)
st.caption("Folga = horas entre o fim da produção e o início do turno no dia da entrega. "
           "Negativa significa atraso.")
