import streamlit as st
import json
import os
import re

# =========================
# CONFIGURAÇÃO BÁSICA
# =========================
st.set_page_config(page_title="PlastCalc", layout="wide")
DATA_DIR = "data"
BIB_FILE = os.path.join(DATA_DIR, "biblioteca.json")


# =========================
# UTILIDADES DE ARQUIVO
# =========================
def garantir_pasta():
    os.makedirs(DATA_DIR, exist_ok=True)


def carregar_json(caminho, padrao):
    if not os.path.exists(caminho):
        return padrao
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


# =========================
# BIBLIOTECA – CRIA SE NÃO EXISTIR
# =========================
def criar_biblioteca_se_nao_existir():
    garantir_pasta()

    if os.path.exists(BIB_FILE):
        return

    biblioteca_inicial = [
        {
            "id": "rechupe",
            "titulo": "Risco de Rechupe",
            "tags": ["defeito", "injeção", "produto", "molde"],
            "resumo": "Afundamento superficial causado por retração mal compensada.",
            "conteudo": """
### O que é
Rechupe é um afundamento na superfície da peça, comum em regiões espessas.

### Causas
- Espessura elevada
- Recalque insuficiente
- Gate pequeno ou distante

### Soluções
**Produto**
- Uniformizar espessura
- Aliviar nervuras e bosses

**Molde**
- Melhorar refrigeração
- Ajustar ponto de injeção

**Processo**
- Aumentar pressão e tempo de recalque
"""
        }
    ]

    salvar_json(BIB_FILE, biblioteca_inicial)


# =========================
# BIBLIOTECA – FUNÇÕES
# =========================
def carregar_biblioteca():
    criar_biblioteca_se_nao_existir()
    return carregar_json(BIB_FILE, [])


def filtrar_artigos(artigos, texto, tags):
    texto = texto.lower()
    resultado = []

    for art in artigos:
        base = (
            art["titulo"] +
            art["resumo"] +
            art["conteudo"] +
            " ".join(art["tags"])
        ).lower()

        if texto and texto not in base:
            continue

        if tags and not set(tags).issubset(set(art["tags"])):
            continue

        resultado.append(art)

    return resultado


# =========================
# INTERFACE – TABS
# =========================
st.title("PlastCalc")

tab_produto, tab_molde, tab_horas, tab_os, tab_biblioteca = st.tabs(
    ["Produto", "Molde", "Horas", "OS", "Biblioteca Técnica"]
)

with tab_produto:
    st.subheader("Produto")
    st.info("Aqui entra sua tab Produto.")

with tab_molde:
    st.subheader("Molde")
    st.info("Aqui entra sua tab Molde.")

with tab_horas:
    st.subheader("Horas")
    st.info("Aqui entra sua tab Horas.")

with tab_os:
    st.subheader("OS")
    st.info("Aqui entra sua tab OS (ORC → PV → OS).")

with tab_biblioteca:
    st.subheader("Biblioteca Técnica")

    artigos = carregar_biblioteca()
    todas_tags = sorted({t for a in artigos for t in a["tags"]})

    busca = st.text_input("Buscar")
    tags_sel = st.multiselect("Filtrar por tags", todas_tags)

    artigos_filtrados = filtrar_artigos(artigos, busca, tags_sel)

    st.divider()

    for art in artigos_filtrados:
        with st.expander(art["titulo"]):
            st.caption("Tags: " + ", ".join(art["tags"]))
            st.write(art["resumo"])
            st.markdown(art["conteudo"])