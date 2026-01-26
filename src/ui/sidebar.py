import streamlit as st

def render_sidebar() -> str:
    with st.sidebar:
        st.title("PlastCalc")

        page = st.radio(
            "Menu",
            [
                "Dashboard",
                "Clientes",
                "Orçamentos",
                "Vendas",
                "Operação",
                "Compras",
                "Biblioteca Técnica",
                "Cadastros",
            ],
        )
    return page