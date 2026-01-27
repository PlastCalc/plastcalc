import streamlit as st
from datetime import datetime

from src.data.storage_json import load, save

DB_OS = "ordens_servico"
DB_PV = "vendas_pv"
DB_ORC = "orcamentos"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _servicos_texto_from_orc(orc: dict) -> str:
    itens = (orc or {}).get("itens", {})
    servicos = itens.get("servicos", []) or []
    parts = []
    for r in servicos:
        if isinstance(r, dict):
            parts.append(str(r.get("descricao", "") or ""))
    return " | ".join([p for p in parts if p.strip()])


def _get_orc_for_os(os_item: dict, pv_db: dict, orc_db: dict) -> dict:
    # 1) tenta via orc_id da própria OS
    orc_id = os_item.get("orc_id", "") or ""
    if orc_id and orc_id in orc_db:
        return orc_db[orc_id]

    # 2) tenta via pv_id
    pv_id = os_item.get("pv_id", "") or ""
    pv = pv_db.get(pv_id, {}) if pv_id else {}
    orc_id2 = pv.get("orc_id", "") or ""
    if orc_id2 and orc_id2 in orc_db:
        return orc_db[orc_id2]

    return {}


def _suggest_from_servicos_text(serv_text: str) -> dict:
    """
    Regras:
    - Produto: "projeto de produto" ou "dfm"
    - Molde: "projeto de molde" ou "fabricação de molde" ou "ajustes de molde"
    """
    t = _norm(serv_text)

    produto = ("projeto de produto" in t) or ("dfm" in t)
    molde = ("projeto de molde" in t) or ("fabricação de molde" in t) or ("ajustes de molde" in t)

    return {"produto": produto, "molde": molde}


def _ensure_checklists_struct(os_db: dict, os_id: str):
    os_db[os_id].setdefault("checklists", {})
    os_db[os_id]["checklists"].setdefault("produto", {"status": "NAO_CRIADO", "itens": []})
    os_db[os_id]["checklists"].setdefault("molde", {"status": "NAO_CRIADO", "itens": []})


def page_operacao():
    st.header("Operação / Ordem de Serviço")

    os_db = load(DB_OS)
    pv_db = load(DB_PV)
    orc_db = load(DB_ORC)

    items = list(os_db.values())
    items.sort(key=lambda x: x.get("doc", ""), reverse=True)

    if not items:
        st.info("Nenhuma OS encontrada ainda. Gere uma OS a partir de Orçamentos.")
        return

    q = st.text_input("Buscar OS", placeholder="OS-2026-0001, cliente, título...")
    if q.strip():
        q2 = q.strip().lower()
        items = [
            o for o in items
            if q2 in ((o.get("doc","") + " " + o.get("cliente_nome","") + " " + o.get("titulo","")).lower())
        ]

    st.caption(f"Total: {len(items)}")

    for o in items:
        with st.expander(f"{o.get('doc','')} • {o.get('cliente_nome','')} • {o.get('status','')}"):
            os_id = o.get("id", "")
            if not os_id:
                continue

            st.write(f"**Título:** {o.get('titulo','')}")
            st.write(f"**PV:** {o.get('pv_doc','')}")
            st.write(f"**ORC:** {o.get('orc_doc','')}")
            st.write(f"**Criado em:** {o.get('created_at','')}")
            st.write(f"**Atualizado em:** {o.get('updated_at','')}")

            # garantir estrutura
            _ensure_checklists_struct(os_db, os_id)

            st.divider()
            st.markdown("## Checklists (Produto / Molde)")

            # Puxa ORC e serviços
            orc = _get_orc_for_os(o, pv_db, orc_db)
            serv_text = _servicos_texto_from_orc(orc) if orc else ""
            st.caption(f"Serviços (lidos do orçamento): {serv_text or '-'}")

            sugest = _suggest_from_servicos_text(serv_text)

            prod_status = os_db[os_id]["checklists"]["produto"].get("status", "NAO_CRIADO")
            molde_status = os_db[os_id]["checklists"]["molde"].get("status", "NAO_CRIADO")

            colA, colB, colC = st.columns(3)

            # Aplicar sugestões
            if colA.button("✨ Aplicar sugestões", key=f"sug_{os_id}"):
                changed = False

                if sugest["produto"] and prod_status == "NAO_CRIADO":
                    os_db[os_id]["checklists"]["produto"]["status"] = "SUGERIDO"
                    changed = True

                if sugest["molde"] and molde_status == "NAO_CRIADO":
                    os_db[os_id]["checklists"]["molde"]["status"] = "SUGERIDO"
                    changed = True

                if changed:
                    os_db[os_id]["updated_at"] = _now()
                    save(DB_OS, os_db)
                    st.success("Sugestões aplicadas na OS.")
                    st.rerun()
                else:
                    st.info("Nada para sugerir (ou já foi criado/sugerido).")

            # Criar checklist Produto
            if colB.button("🧩 Criar Checklist Produto", key=f"cria_prod_{os_id}"):
                if prod_status == "CRIADO":
                    st.info("Checklist Produto já está criado.")
                else:
                    os_db[os_id]["checklists"]["produto"]["status"] = "CRIADO"
                    # (itens entram na opção 3, por enquanto fica vazio)
                    os_db[os_id]["updated_at"] = _now()
                    save(DB_OS, os_db)
                    st.success("Checklist Produto criado!")
                    st.rerun()

            # Criar checklist Molde
            if colC.button("🧩 Criar Checklist Molde", key=f"cria_molde_{os_id}"):
                if molde_status == "CRIADO":
                    st.info("Checklist Molde já está criado.")
                else:
                    os_db[os_id]["checklists"]["molde"]["status"] = "CRIADO"
                    os_db[os_id]["updated_at"] = _now()
                    save(DB_OS, os_db)
                    st.success("Checklist Molde criado!")
                    st.rerun()

            st.write(f"**Status Produto:** {os_db[os_id]['checklists']['produto'].get('status','')}")
            st.write(f"**Status Molde:** {os_db[os_id]['checklists']['molde'].get('status','')}")

            st.divider()
            st.markdown("### Status da OS")

            status_atual = o.get("status", "ABERTA")
            novo_status = st.selectbox(
                "Status",
                ["ABERTA", "EM_ANDAMENTO", "PAUSADA", "CONCLUIDA"],
                index=["ABERTA", "EM_ANDAMENTO", "PAUSADA", "CONCLUIDA"].index(status_atual)
                if status_atual in ["ABERTA", "EM_ANDAMENTO", "PAUSADA", "CONCLUIDA"] else 0,
                key=f"status_{os_id}",
            )

            if st.button("Salvar status", key=f"save_status_{os_id}"):
                os_db[os_id]["status"] = novo_status
                os_db[os_id]["updated_at"] = _now()
                save(DB_OS, os_db)
                st.success("Status atualizado!")
                st.rerun()

            st.divider()
            st.markdown("### Apontamento de horas (MVP)")

            col1, col2 = st.columns(2)
            horas_txt = col1.text_input("Horas (ex.: 2h30, 1h, 0h45)", key=f"horas_txt_{os_id}")
            desc = col2.text_input(
                "Descrição",
                placeholder="Ex.: Ajustes CAD / Reunião / DFM",
                key=f"horas_desc_{os_id}",
            )

            if st.button("Lançar horas", key=f"add_horas_{os_id}"):
                os_db[os_id].setdefault("horas", [])
                os_db[os_id]["horas"].append(
                    {"quando": _now(), "horas": horas_txt.strip(), "descricao": desc.strip()}
                )
                os_db[os_id]["updated_at"] = _now()
                save(DB_OS, os_db)
                st.success("Horas lançadas!")
                st.rerun()

            horas = os_db.get(os_id, {}).get("horas", [])
            if horas:
                st.write("**Lançamentos:**")
                st.dataframe(horas, use_container_width=True)
            else:
                st.caption("Nenhuma hora lançada ainda.")
