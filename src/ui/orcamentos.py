import streamlit as st
from datetime import datetime
from uuid import uuid4

from src.data.storage_json import load, save
from src.models.sequencias import next_doc

DB_ORC = "orcamentos"
DB_CLIENTES = "clientes"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _money(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _ensure_list_of_dicts(value):
    """Garante que o data_editor receba sempre list[dict]."""
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        vals = list(value.values())
        return [v for v in vals if isinstance(v, dict)]
    return []


def _total_bloco(itens):
    total = 0.0
    for row in itens or []:
        try:
            qtd = float(row.get("qtd") or 0)
            vu = float(row.get("valor_unit") or 0)
            total += qtd * vu
        except Exception:
            pass
    return total


def page_orcamentos():
    st.header("Orçamentos")

    # defaults (evita estado quebrado)
    st.session_state.setdefault("orc_servicos", [])
    st.session_state.setdefault("orc_materiais", [])
    st.session_state.setdefault("orc_terceiros", [])

    # Carrega bases
    clientes_db = load(DB_CLIENTES)   # {id: {...}}
    orc_db = load(DB_ORC)             # {id: {...}}

    # Lista de clientes (ordenada)
    clientes_lista = list(clientes_db.values())
    clientes_lista.sort(key=lambda c: c.get("nome", "").lower())

    tab1, tab2 = st.tabs(["📋 Lista", "➕ Novo orçamento"])

    # -------------------------
    # NOVO ORÇAMENTO
    # -------------------------
    with tab2:
        st.subheader("Criar orçamento")

        if not clientes_lista:
            st.warning("Cadastre pelo menos 1 cliente antes de criar orçamento.")
            st.info("Vá no menu lateral → **Clientes**. Depois volte aqui.")
            st.stop()

        # Select cliente
        clientes_opcoes = {
            f"{c.get('nome','')} ({c.get('cidade','')})".strip(): c["id"]
            for c in clientes_lista
        }
        cliente_label = st.selectbox("Cliente*", list(clientes_opcoes.keys()))
        cliente_id = clientes_opcoes[cliente_label]

        colA, colB = st.columns(2)
        titulo = colA.text_input("Título do orçamento*", placeholder="Ex.: Projeto de molde + DFM")
        validade_dias = colB.number_input("Validade (dias)", min_value=1, max_value=120, value=15)

        st.markdown("### Itens do orçamento")
        st.caption("Preencha os itens abaixo. Depois clique em **Salvar**.")

        # --- Serviços
        st.markdown("#### 1) Serviços")
        servicos_in = _ensure_list_of_dicts(st.session_state.get("orc_servicos"))
        st.session_state["orc_servicos"] = servicos_in

        servicos = st.data_editor(
            servicos_in,
            key="orc_servicos",
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "descricao": st.column_config.TextColumn("Descrição"),
                "qtd": st.column_config.NumberColumn("Qtd", min_value=0.0, step=1.0),
                "valor_unit": st.column_config.NumberColumn("Valor unit (R$)", min_value=0.0, step=10.0),
            },
        )

        # --- Materiais
        st.markdown("#### 2) Materiais / Insumos")
        materiais_in = _ensure_list_of_dicts(st.session_state.get("orc_materiais"))
        st.session_state["orc_materiais"] = materiais_in

        materiais = st.data_editor(
            materiais_in,
            key="orc_materiais",
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "descricao": st.column_config.TextColumn("Descrição"),
