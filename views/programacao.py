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
           "Ordens seguidas do mesmo produto não repetem o setup. Com o **plano B**, ordens de "
           "máquina parada ou que atrasariam vão para a máquina alternativa (Ficha técnica).")

c1, c2, c3 = st.columns([1, 1, 1.2])
dia = c1.date_input("Começar a programar em", value=date.today(), format="DD/MM/YYYY")
hora = c2.number_input("Início do turno (hora)", min_value=0, max_value=23, value=6)
usar_b = c3.toggle("Usar plano B (remanejar ordens)", value=True)

paradas = dados["maquinas"][dados["maquinas"]["status"] == "Parada"]
for m in paradas.itertuples():
    st.error(f"⛔ **{m.nome}** parada" + (f" · {m.motivo}" if m.motivo else ""))

inicio = datetime.combine(dia, time(int(hora)))
if usar_b:
    prog, trocas = pcp.plano_b(res["ordens"], dados["roteiro"], dados["maquinas"],
                               dados["alternativas"], inicio, int(hora))
else:
    prog = pcp.programar(res["ordens"], dados["roteiro"], dados["maquinas"], inicio, int(hora))
    trocas = prog.iloc[0:0]

if prog.empty:
    st.success("Nenhuma ordem de produção para programar.")
    st.stop()

com_horario = prog.dropna(subset=["inicio"])
atrasos = prog["situacao"].str.startswith("🔴").sum()
sem_maquina = prog["situacao"].str.startswith("⛔").sum()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Ordens programadas", len(com_horario))
k2.metric("Ordens que atrasam", int(atrasos))
k3.metric("Remanejadas (plano B)", len(trocas),
          f"{int(sem_maquina)} paradas sem alternativa" if sem_maquina else None,
          delta_color="inverse")
k4.metric("Término da última ordem",
          com_horario["fim"].max().strftime("%d/%m %H:%M") if not com_horario.empty else "-")

if not com_horario.empty:
    # Cores fixas por produto (paleta categórica validada para daltonismo no tema escuro,
    # sem vermelho: vermelho fica reservado para atraso)
    PALETA = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300",
              "#9085e9", "#8a8577"]
    codigos = sorted(dados["produtos"].query("tipo == 'PA'")["codigo"])
    cores = {c: PALETA[i % len(PALETA)] for i, c in enumerate(codigos)}

    g = com_horario.assign(
        rotulo=com_horario["codigo"] + " · " + com_horario["cliente"],
        texto=com_horario["codigo"] + "<br>" + com_horario["quantidade"].map(ui.num),
    )
    fig = px.timeline(g, x_start="inicio", x_end="fim", y="maquina", color="codigo",
                      text="texto", hover_name="rotulo", color_discrete_map=cores,
                      category_orders={"codigo": codigos,
                                       "maquina": sorted(g["maquina"].unique())},
                      hover_data={"quantidade": ":,.0f", "data_entrega": True,
                                  "situacao": True, "maquina": False, "codigo": False,
                                  "texto": False},
                      labels={"maquina": "", "codigo": "Produto"})
    fig.update_yaxes(tickfont=dict(size=14))
    fig.update_xaxes(tickformat="%d/%m\n%H:%M", tickfont=dict(size=12),
                     gridcolor="rgba(128,128,128,0.18)")
    fig.update_traces(width=0.7, offset=-0.35, marker_line_color="#111318", marker_line_width=2,
                      textangle=0, textposition="inside", insidetextanchor="middle",
                      textfont=dict(size=13))
    TEXTO_ESCURO = {"#199e70", "#c98500"}  # cores claras pedem texto escuro
    for trace in fig.data:
        cor = cores.get(trace.name, "")
        trace.textfont.color = "#111111" if cor in TEXTO_ESCURO else "white"
    agora = datetime.now()
    fig.add_vline(x=agora, line_dash="dot", line_color="gray")
    fig.add_annotation(x=agora, y=1.02, yref="paper", text="agora", showarrow=False,
                       font=dict(size=12, color="gray"))
    fig.update_layout(barmode="overlay", height=160 + 110 * g["maquina"].nunique(),
                      margin=dict(l=0, r=0, t=30, b=0), uniformtext_minsize=10,
                      uniformtext_mode="hide",
                      legend=dict(title_text="", orientation="h", y=-0.15, x=0,
                                  font=dict(size=13)))
    st.plotly_chart(fig)
    st.caption("Cada bloco = uma ordem (código e quantidade). Blocos curtos escondem o texto: "
               "passe o mouse para ver cliente, entrega e situação.")

if len(trocas):
    st.subheader("🔁 Plano B: ordens remanejadas")
    st.dataframe(
        trocas, hide_index=True,
        column_config={
            "pedido_id": None, "codigo": "Código", "produto": "Produto", "cliente": "Cliente",
            "quantidade": st.column_config.NumberColumn("Qtd.", format="localized"),
            "de": "Máquina principal", "para": "Vai para",
            "prioridade": st.column_config.NumberColumn("Prioridade", format="%d"),
            "motivo": "Por quê",
        },
    )
    st.caption("A troca só fica quando diminui o atraso total: não adianta salvar uma ordem "
               "atrasando as outras da máquina alternativa.")

st.dataframe(
    prog, hide_index=True,
    column_config={
        "pedido_id": None, "maquina_original": "Máquina principal",
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
