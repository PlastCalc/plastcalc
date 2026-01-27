import streamlit as st

from src.ui.sidebar import render_sidebar
from src.ui.dashboard import page_dashboard
from src.ui.clientes import page_clientes
from src.ui.orcamentos import page_orcamentos
from src.ui.vendas import page_vendas
from src.ui.operacao import page_operacao
from src.ui.compras import page_compras
from src.ui.biblioteca import page_biblioteca
from src.ui.cadastros import page_cadastros

st.set_page_config(
    page_title="PlastCalc",
    layout="wide"
)

page = render_sidebar()

if page == "Dashboard":
    page_dashboard()

elif page == "Clientes":
    page_clientes()

elif page == "Orçamentos":
    page_orcamentos()

elif page == "Vendas":
    page_vendas()

elif page == "Operação":
    page_operacao()

elif page == "Compras":
    page_compras()

elif page == "Biblioteca Técnica":
    page_biblioteca()

elif page == "Cadastros":
    page_cadastros()
