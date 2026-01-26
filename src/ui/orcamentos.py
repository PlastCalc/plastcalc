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

def page_orcamentos():
    st.header("Orçamentos")

    # Carrega bases
    clientes_db = load(DB_CLIENTES)   # {id: {...}}
    orc_db = load(DB_ORC)             # {id: {...}}

    # Mapa id->nome para select
    clientes_lista = list(clientes_db.values())
    clientes_lista.sort(key=lambda c: c.get("nome","").lower())

    tab1, tab2 = st.tabs(["📋 Lista", "➕ Novo orçamento"])

    # -------------------------
    # NOVO ORÇAMENTO
    # -------------------------
    with tab2:
        st.subheader("Criar orçamento")

        if not clientes_lista:
            st.warning("Cadastre pelo menos 1 cliente antes de criar orçamento.")
            return

        clientes_opcoes = {f"{c['nome']} ({c.get('cidade','')})".strip(): c["id"] for c in clientes_lista}
        cliente_label = st.selectbox("Cliente*", list(clientes_opcoes.keys()))
        cliente_id = clientes_opcoes[cliente_label]

        colA, colB = st.columns(2)
        titulo = colA.text_input("Título do orçamento*", placeholder="Ex.: Projeto de molde + DFM")
        validade_dias = colB.number_input("Validade (dias)", min_value=1, max_value=120, value=15)

        st.markdown("### Itens do orçamento")
        st.caption("Preencha os itens abaixo. Depois clique em **Salvar orçamento**.")

        st.markdown("#### 1) Serviços")
        servicos = st.data_editor(
            st.session_state.get("orc_servicos", []),
            key="orc_servicos",
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "descricao": st.column_config.TextColumn("Descrição"),
                "qtd": st.column_config.NumberColumn("Qtd", min_value=0.0, step=1.0),
                "valor_unit": st.column_config.NumberColumn("Valor unit (R$)", min_value=0.0, step=10.0),
            },
        )

        st.markdown("#### 2) Materiais / Insumos")
        materiais = st.data_editor(
            st.session_state.get("orc_materiais", []),
            key="orc_materiais",
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "descricao": st.column_config.TextColumn("Descrição"),
                "qtd": st.column_config.NumberColumn("Qtd", min_value=0.0, step=1.0),
                "valor_unit": st.column_config.NumberColumn("Valor unit (R$)", min_value=0.0, step=10.0),
            },
        )

        st.markdown("#### 3) Terceiros / Outros")
        terceiros = st.data_editor(
            st.session_state.get("orc_terceiros", []),
            key="orc_terceiros",
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "descricao": st.column_config.TextColumn("Descrição"),
                "qtd": st.column_config.NumberColumn("Qtd", min_value=0.0, step=1.0),
                "valor_unit": st.column_config.NumberColumn("Valor unit (R$)", min_value=0.0, step=10.0),
            },
        )

        def total_bloco(itens):
            total = 0.0
            for row in itens or []:
                try:
                    qtd = float(row.get("qtd") or 0)
                    vu = float(row.get("valor_unit") or 0)
                    total += qtd * vu
                except Exception:
                    pass
            return total

        total_serv = total_bloco(servicos)
        total_mat = total_bloco(materiais)
        total_ter = total_bloco(terceiros)
        total_geral = total_serv + total_mat + total_ter

        st.markdown("### Resumo")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Serviços", _money(total_serv))
        c2.metric("Materiais", _money(total_mat))
        c3.metric("Terceiros", _money(total_ter))
        c4.metric("TOTAL", _money(total_geral))

        obs = st.text_area("Observações do orçamento", placeholder="Prazos, condições, escopo, etc.")

        if st.button("Salvar orçamento", type="primary"):
            if not titulo.strip():
                st.error("Título é obrigatório.")
            elif total_geral <= 0:
                st.error("Inclua pelo menos 1 item com valor.")
            else:
                doc = next_doc("ORC")
                oid = str(uuid4())[:8]
                orc_db[oid] = {
                    "id": oid,
                    "doc": doc,
                    "cliente_id": cliente_id,
                    "titulo": titulo.strip(),
                    "validade_dias": int(validade_dias),
                    "itens": {
                        "servicos": servicos or [],
                        "materiais": materiais or [],
                        "terceiros": terceiros or [],
                    },
                    "totais": {
                        "servicos": total_serv,
                        "materiais": total_mat,
                        "terceiros": total_ter,
                        "geral": total_geral,
                    },
                    "observacoes": obs.strip(),
                    "status": "RASCUNHO",
                    "created_at": _now(),
                    "updated_at": _now(),
                }
                save(DB_ORC, orc_db)

                # limpa editores
                st.session_state["orc_servicos"] = []
                st.session_state["orc_materiais"] = []
                st.session_state["orc_terceiros"] = []

                st.success(f"Orçamento salvo: {doc}")
                st.rerun()

    # -------------------------
    # LISTA / DETALHE
    # -------------------------
    with tab1:
        st.subheader("Lista de orçamentos")

        q = st.text_input("Buscar", placeholder="ORC-2026-0001, cliente, título...")

        items = list(orc_db.values())

        # Enriquecer com nome do cliente
        for o in items:
            c = clientes_db.get(o.get("cliente_id", ""), {})
            o["_cliente_nome"] = c.get("nome", "(cliente não encontrado)")

        if q.strip():
            q2 = q.strip().lower()
            items = [
                o for o in items
                if q2 in (
                    (o.get("doc","") + " " + o.get("_cliente_nome","") + " " + o.get("titulo","")).lower()
                )
            ]

        items.sort(key=lambda x: x.get("doc",""), reverse=True)

        st.caption(f"Total: {len(items)}")

        if not items:
            st.info("Nenhum orçamento encontrado.")
            return

        for o in items:
            total = float(o.get("totais", {}).get("geral", 0.0) or 0.0)
            with st.expander(f"{o.get('doc','')} • {o.get('_cliente_nome','')} • {_money(total)}"):
                st.write(f"**Título:** {o.get('titulo','')}")
                st.write(f"**Status:** {o.get('status','')}")
                st.write(f"**Criado em:** {o.get('created_at','')}")
                st.write(f"**Observações:** {o.get('observacoes','') or '-'}")

                st.divider()
                st.markdown("### Itens")

                col1, col2, col3 = st.columns(3)
                col1.write("**Serviços**")
                col1.dataframe(o.get("itens", {}).get("servicos", []), use_container_width=True)

                col2.write("**Materiais**")
                col2.dataframe(o.get("itens", {}).get("materiais", []), use_container_width=True)

                col3.write("**Terceiros**")
                col3.dataframe(o.get("itens", {}).get("terceiros", []), use_container_width=True)

                st.divider()
                st.markdown("### Ações (MVP)")

                colA, colB = st.columns(2)
                if colA.button("Marcar como ENVIADO", key=f"enviar_{o['id']}"):
                    orc_db[o["id"]]["status"] = "ENVIADO"
                    orc_db[o["id"]]["updated_at"] = _now()
                    save(DB_ORC, orc_db)
                    st.success("Atualizado!")
                    st.rerun()

                if colB.button("Excluir orçamento", key=f"excluir_{o['id']}"):
                    del orc_db[o["id"]]
                    save(DB_ORC, orc_db)
                    st.success("Excluído!")
                    st.rerun()