import streamlit as st
from src.data.storage_json import load, save
from datetime import datetime

DB_OS = "ordens_servico"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def page_operacao():
    st.header("Operação / Ordem de Serviço")

    os_db = load(DB_OS)
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
            st.write(f"**Título:** {o.get('titulo','')}")
            st.write(f"**PV:** {o.get('pv_doc','')}")
            st.write(f"**ORC:** {o.get('orc_doc','')}")
            st.write(f"**Criado em:** {o.get('created_at','')}")
            st.write(f"**Atualizado em:** {o.get('updated_at','')}")

            st.divider()
            st.markdown("### Status da OS")

            status_atual = o.get("status", "ABERTA")
            novo_status = st.selectbox(
                "Status",
                ["ABERTA", "EM_ANDAMENTO", "PAUSADA", "CONCLUIDA"],
                index=["ABERTA", "EM_ANDAMENTO", "PAUSADA", "CONCLUIDA"].index(status_atual)
                if status_atual in ["ABERTA", "EM_ANDAMENTO", "PAUSADA", "CONCLUIDA"] else 0,
                key=f"status_{o['id']}",
            )

            if st.button("Salvar status", key=f"save_status_{o['id']}"):
                os_db[o["id"]]["status"] = novo_status
                os_db[o["id"]]["updated_at"] = _now()
                save(DB_OS, os_db)
                st.success("Status atualizado!")
                st.rerun()

            st.divider()
            st.markdown("### Apontamento de horas (MVP)")

            colA, colB = st.columns(2)
            horas_txt = colA.text_input("Horas (ex.: 2h30, 1h, 0h45)", key=f"horas_txt_{o['id']}")
            desc = colB.text_input("Descrição", placeholder="Ex.: Ajustes CAD / Reunião / DFM", key=f"horas_desc_{o['id']}")

            if st.button("Lançar horas", key=f"add_horas_{o['id']}"):
                os_db[o["id"]].setdefault("horas", [])
                os_db[o["id"]]["horas"].append(
                    {
                        "quando": _now(),
                        "horas": horas_txt.strip(),
                        "descricao": desc.strip(),
                    }
                )
                os_db[o["id"]]["updated_at"] = _now()
                save(DB_OS, os_db)
                st.success("Horas lançadas!")
                st.rerun()

            horas = os_db.get(o["id"], {}).get("horas", [])
            if horas:
                st.write("**Lançamentos:**")
                st.dataframe(horas, use_container_width=True)
            else:
                st.caption("Nenhuma hora lançada ainda.")
