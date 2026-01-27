import streamlit as st
from datetime import datetime
from uuid import uuid4

from src.data.storage_json import load, save
from src.models.sequencias import next_doc

DB_ORC = "orcamentos"
DB_PV = "vendas_pv"
DB_OS = "ordens_servico"
DB_CLIENTES = "clientes"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _money(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _ensure_list_of_dicts(value):
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


def _editor_items(name: str, title: str, version: int):
    st.markdown(title)

    data_key = f"{name}_data"
    editor_key = f"{name}_editor_{version}"

    st.session_state.setdefault(data_key, [])
    current = _ensure_list_of_dicts(st.session_state.get(data_key))

    edited = st.data_editor(
        current,
        key=editor_key,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "descricao": st.column_config.TextColumn("Descrição"),
            "qtd": st.column_config.NumberColumn("Qtd", min_value=0.0, step=1.0),
            "valor_unit": st.column_config.NumberColumn("Valor unit (R$)", min_value=0.0, step=10.0),
        },
    )

    st.session_state[data_key] = _ensure_list_of_dicts(edited)
    return st.session_state[data_key]


def _cliente_nome(clientes_db, cliente_id: str) -> str:
    c = clientes_db.get(cliente_id, {})
    return c.get("nome", "(cliente não encontrado)")


def page_orcamentos():
    st.header("Orçamentos")

    st.session_state.setdefault("orc_editor_v", 1)
    v = st.session_state["orc_editor_v"]

    clientes_db = load(DB_CLIENTES)
    orc_db = load(DB_ORC)
    pv_db = load(DB_PV)
    os_db = load(DB_OS)

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
        servicos = _editor_items("orc_servicos", "#### 1) Serviços", v)
        materiais = _editor_items("orc_materiais", "#### 2) Materiais / Insumos", v)
        terceiros = _editor_items("orc_terceiros", "#### 3) Terceiros / Outros", v)

        total_serv = _total_bloco(servicos)
        total_mat = _total_bloco(materiais)
        total_ter = _total_bloco(terceiros)
        total_geral = total_serv + total_mat + total_ter

        st.markdown("### Resumo")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Serviços", _money(total_serv))
        c2.metric("Materiais", _money(total_mat))
        c3.metric("Terceiros", _money(total_ter))
        c4.metric("TOTAL", _money(total_geral))

        obs = st.text_area("Observações do orçamento", placeholder="Prazos, condições, escopo, etc.")

        colS1, colS2 = st.columns(2)
        salvar_rascunho = colS1.button("Salvar rascunho", type="secondary")
        salvar_enviar = colS2.button("Salvar e marcar ENVIADO", type="primary")

        if salvar_rascunho or salvar_enviar:
            if not titulo.strip():
                st.error("Título é obrigatório.")
            else:
                doc = next_doc("ORC")
                oid = str(uuid4())[:8]
                status = "ENVIADO" if salvar_enviar else "RASCUNHO"

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
                    "status": status,
                    "pv_id": "",      # preenchido quando gerar PV
                    "os_id": "",      # preenchido quando gerar OS
                    "created_at": _now(),
                    "updated_at": _now(),
                }
                save(DB_ORC, orc_db)

                st.session_state["orc_servicos_data"] = []
                st.session_state["orc_materiais_data"] = []
                st.session_state["orc_terceiros_data"] = []
                st.session_state["orc_editor_v"] = st.session_state["orc_editor_v"] + 1

                st.success(f"Orçamento salvo: {doc} ({status})")
                st.rerun()

    # -------------------------
    # LISTA / DETALHE
    # -------------------------
    with tab1:
        st.subheader("Lista de orçamentos")
        q = st.text_input("Buscar", placeholder="ORC-2026-0001, cliente, título...")

        items = list(orc_db.values())

        for o in items:
            o["_cliente_nome"] = _cliente_nome(clientes_db, o.get("cliente_id", ""))

        if q.strip():
            q2 = q.strip().lower()
            items = [
                o for o in items
                if q2 in ((o.get("doc","") + " " + o.get("_cliente_nome","") + " " + o.get("titulo","")).lower())
            ]

        items.sort(key=lambda x: x.get("doc", ""), reverse=True)
        st.caption(f"Total: {len(items)}")

        if not items:
            st.info("Nenhum orçamento encontrado.")
            return

        for o in items:
            total = float(o.get("totais", {}).get("geral", 0.0) or 0.0)
            cliente_nome = o.get("_cliente_nome", "")
            with st.expander(f"{o.get('doc','')} • {cliente_nome} • {_money(total)}"):
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
                st.markdown("### Fluxo do MVP (PV e OS)")

                pv_id = o.get("pv_id") or ""
                os_id = o.get("os_id") or ""

                colA, colB, colC = st.columns(3)

                # 1) Gerar PV (snapshot)
                if not pv_id:
                    if colA.button("✅ Gerar PV (aprovar)", key=f"gerar_pv_{o['id']}"):
                        pv_doc = next_doc("PV")
                        pvid = str(uuid4())[:8]
                        pv_db[pvid] = {
                            "id": pvid,
                            "doc": pv_doc,
                            "orc_id": o["id"],
                            "orc_doc": o.get("doc",""),
                            "cliente_id": o.get("cliente_id",""),
                            "cliente_nome": cliente_nome,
                            "titulo": o.get("titulo",""),
                            "validade_dias": o.get("validade_dias", 0),
                            "itens": o.get("itens", {}),
                            "totais": o.get("totais", {}),
                            "observacoes": o.get("observacoes",""),
                            "status": "ABERTO",
                            "created_at": _now(),
                            "updated_at": _now(),
                        }
                        save(DB_PV, pv_db)

                        orc_db[o["id"]]["pv_id"] = pvid
                        orc_db[o["id"]]["status"] = "APROVADO"
                        orc_db[o["id"]]["updated_at"] = _now()
                        save(DB_ORC, orc_db)

                        st.success(f"PV gerado: {pv_doc}")
                        st.rerun()
                else:
                    pv = pv_db.get(pv_id, {})
                    colA.success(f"PV: {pv.get('doc','(não encontrado)')}")

                # 2) Gerar OS
                if pv_id and not os_id:
                    if colB.button("🧾 Gerar OS", key=f"gerar_os_{o['id']}"):
                        os_doc = next_doc("OS")
                        osid = str(uuid4())[:8]

                        # puxa PV pra garantir snapshot
                        pv = pv_db.get(pv_id, {})
                        os_db[osid] = {
                            "id": osid,
                            "doc": os_doc,
                            "pv_id": pv_id,
                            "pv_doc": pv.get("doc",""),
                            "orc_id": o["id"],
                            "orc_doc": o.get("doc",""),
                            "cliente_id": o.get("cliente_id",""),
                            "cliente_nome": cliente_nome,
                            "titulo": pv.get("titulo", o.get("titulo","")),
                            "status": "ABERTA",
                            "horas": [],
                            "compras": [],
                            "anexos": [],
                            "checklists": {
                                "produto": {"status": "NAO_CRIADO", "itens": []},
                                "molde": {"status": "NAO_CRIADO", "itens": []},
                            },
                            "created_at": _now(),
                            "updated_at": _now(),
                        }
                        save(DB_OS, os_db)

                        orc_db[o["id"]]["os_id"] = osid
                        orc_db[o["id"]]["updated_at"] = _now()
                        save(DB_ORC, orc_db)

                        st.success(f"OS gerada: {os_doc}")
                        st.rerun()
                elif os_id:
                    osx = os_db.get(os_id, {})
                    colB.success(f"OS: {osx.get('doc','(não encontrado)')}")

                # 3) Ações simples
                if colC.button("🗑️ Excluir orçamento", key=f"excluir_{o['id']}"):
                    del orc_db[o["id"]]
                    save(DB_ORC, orc_db)
                    st.success("Excluído!")
                    st.rerun()
