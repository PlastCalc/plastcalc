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


# -----------------------------
# Regras de sugestão (mantidas)
# -----------------------------
def _servicos_texto_from_orc(orc: dict) -> str:
    itens = (orc or {}).get("itens", {})
    servicos = itens.get("servicos", []) or []
    parts = []
    for r in servicos:
        if isinstance(r, dict):
            parts.append(str(r.get("descricao", "") or ""))
    return " | ".join([p for p in parts if p.strip()])


def _get_orc_for_os(os_item: dict, pv_db: dict, orc_db: dict) -> dict:
    orc_id = os_item.get("orc_id", "") or ""
    if orc_id and orc_id in orc_db:
        return orc_db[orc_id]

    pv_id = os_item.get("pv_id", "") or ""
    pv = pv_db.get(pv_id, {}) if pv_id else {}
    orc_id2 = pv.get("orc_id", "") or ""
    if orc_id2 and orc_id2 in orc_db:
        return orc_db[orc_id2]

    return {}


def _suggest_from_servicos_text(serv_text: str) -> dict:
    t = _norm(serv_text)
    produto = ("projeto de produto" in t) or ("dfm" in t)
    molde = ("projeto de molde" in t) or ("fabricação de molde" in t) or ("ajustes de molde" in t)
    return {"produto": produto, "molde": molde}


def _ensure_checklists_struct(os_db: dict, os_id: str):
    os_db[os_id].setdefault("checklists", {})
    os_db[os_id]["checklists"].setdefault(
        "produto",
        {
            "status": "NAO_CRIADO",
            "itens": [],
            "riscos": "",
            "pendencias": "",
            "decisoes": "",
            "aprovacao": "",
        },
    )
    os_db[os_id]["checklists"].setdefault("molde", {"status": "NAO_CRIADO", "itens": []})


# -----------------------------
# Checklist Produto (13 itens)
# -----------------------------
CHECKLIST_PRODUTO_ITENS = [
    "Linha de fechamento do produto",
    "Espessura do produto",
    "Marca do ponto de injeção aceitável",
    "Há risco de rechupe",
    "Ângulo de saída para desmoldagem",
    "Necessidade de aplicação de bico quente",
    "Bordas arredondadas na peça",
    "Tamanho do produto",
    "Encaixes do produto",
    "Número de operações de montagem do produto",
    "Mecanismo do produto",
    "Quantidade de peças",
    "Distribuição do produto no molde",
]


def _init_checklist_produto_items(os_db: dict, os_id: str):
    itens = os_db[os_id]["checklists"]["produto"].get("itens", [])
    if itens:
        return
    os_db[os_id]["checklists"]["produto"]["itens"] = [
        {"nome": nome, "ok": False, "obs": ""} for nome in CHECKLIST_PRODUTO_ITENS
    ]


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

            _ensure_checklists_struct(os_db, os_id)

            st.write(f"**Título:** {o.get('titulo','')}")
            st.write(f"**PV:** {o.get('pv_doc','')}")
            st.write(f"**ORC:** {o.get('orc_doc','')}")
            st.write(f"**Criado em:** {o.get('created_at','')}")
            st.write(f"**Atualizado em:** {o.get('updated_at','')}")

            st.divider()
            st.markdown("## Checklist Produto")

            prod = os_db[os_id]["checklists"]["produto"]
            st.write(f"**Status:** {prod.get('status','')}")

            if prod.get("status") == "CRIADO":
                _init_checklist_produto_items(os_db, os_id)

                for i, item in enumerate(prod["itens"]):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        item["ok"] = st.checkbox(
                            item["nome"],
                            value=item.get("ok", False),
                            key=f"prod_ok_{os_id}_{i}",
                        )
                    with col2:
                        item["obs"] = st.text_input(
                            "Observação",
                            value=item.get("obs", ""),
                            key=f"prod_obs_{os_id}_{i}",
                        )

                st.markdown("### Riscos")
                prod["riscos"] = st.text_area(
                    "Riscos",
                    value=prod.get("riscos", ""),
                    key=f"prod_riscos_{os_id}",
                )

                st.markdown("### Pendências")
                prod["pendencias"] = st.text_area(
                    "Pendências",
                    value=prod.get("pendencias", ""),
                    key=f"prod_pend_{os_id}",
                )

                st.markdown("### Decisões")
                prod["decisoes"] = st.text_area(
                    "Decisões",
                    value=prod.get("decisoes", ""),
                    key=f"prod_dec_{os_id}",
                )

                st.markdown("### Aprovação")
                prod["aprovacao"] = st.selectbox(
                    "Aprovação",
                    ["", "APROVADO", "APROVADO COM RESSALVAS", "REPROVADO"],
                    index=["", "APROVADO", "APROVADO COM RESSALVAS", "REPROVADO"].index(
                        prod.get("aprovacao", "") if prod.get("aprovacao", "") in ["", "APROVADO", "APROVADO COM RESSALVAS", "REPROVADO"] else ""
                    ),
                    key=f"prod_aprov_{os_id}",
                )

                if st.button("💾 Salvar Checklist Produto", key=f"save_prod_{os_id}"):
                    os_db[os_id]["updated_at"] = _now()
                    save(DB_OS, os_db)
                    st.success("Checklist Produto salvo!")
                    st.rerun()
            else:
                st.info("Checklist Produto ainda não foi criado. Use o botão de criação.")

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
