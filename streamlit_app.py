"""
Dashboard (Streamlit): Desigualdade de Renda no Brasil por Sexo e Cor/Raça
Fonte: PNAD Contínua Anual — SIDRA/IBGE (2012–2024)

Multipage:
    • Visão geral — leitura simples e clara
    • Explorar    — visualizações aprofundadas

Executar:
    uv run streamlit run streamlit_app.py
"""

import streamlit as st

import shared as S

st.set_page_config(
    page_title="Desigualdade de Renda no Brasil",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

S.inject_css()

import page_overview
import page_explorar
import page_poa

nav = st.navigation([
    st.Page(page_overview.render, title="Visão geral", icon="📊",
            url_path="visao-geral", default=True),
    st.Page(page_explorar.render, title="Explorar", icon="🔎", url_path="explorar"),
    st.Page(page_poa.render, title="Porto Alegre", icon="🏙️", url_path="porto-alegre"),
])

with st.sidebar:
    st.markdown("## 📊 Desigualdade de Renda")
    st.caption("Rendimento médio mensal real (R$) · PNAD Contínua · SIDRA/IBGE · 2012–2024")
    st.divider()

S.sidebar_filtros()

nav.run()
