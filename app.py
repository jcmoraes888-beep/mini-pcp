"""Mini-PCP · ponto de entrada (rode com: streamlit run app.py)."""
import streamlit as st

import db

st.set_page_config(page_title="Mini-PCP", page_icon="🏭", layout="wide")
db.iniciar()

paginas = st.navigation({
    "Visão geral": [st.Page("views/painel.py", title="Painel", icon="🏭", default=True)],
    "Cadastros": [
        st.Page("views/pedidos.py", title="Pedidos", icon="🧾"),
        st.Page("views/estoque.py", title="Estoque", icon="📦"),
        st.Page("views/ficha_tecnica.py", title="Ficha técnica", icon="📋"),
    ],
    "Planejamento": [
        st.Page("views/mrp.py", title="MRP", icon="🧮"),
        st.Page("views/programacao.py", title="Programação", icon="📅"),
    ],
})

with st.sidebar:
    st.caption("Panificadora Trigo Bom · empresa fictícia para demonstração")
    if st.button("↺ Restaurar dados de exemplo", width="stretch"):
        db.carregar_exemplo()
        st.toast("Dados de exemplo restaurados.")
        st.rerun()

paginas.run()
