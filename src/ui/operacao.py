import streamlit as st
from datetime import datetime
from io import BytesIO

from src.data.storage_json import load, save

# PDF (ReportLab)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

DB_OS = "ordens_servico"
DB_PV = "vendas_pv"
DB_ORC = "orcamentos"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _norm(s: str) -> str:
    return (s or "").strip().lower()


# -----------------------------
# Sugestões (mantidas)
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


# -----------------------------
# PDF generator
# -----------------------------
def _build_checklist_produto_pdf(os_item: dict, checklist: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Checklist Produto",
    )

    styles = getSampleStyleSheet()
    story = []

    title = "Ata Técnica — Projeto de Produto (Checklist Produto)"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 8))

    # Cabeçalho
    meta = [
        ["OS", os_item.get("doc", "")],
        ["Cliente", os_item.get("cliente_nome", "")],
        ["Título", os_item.get("titulo", "")],
        ["Status OS", os_item.get("status", "")],
        ["Aprovação", checklist.get("aprovacao", "") or "-"],
        ["Gerado em", _now()],
    ]
    t_meta = Table(meta, colWidths=[35 * mm, 150 * mm])
    t_meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(t_meta)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Itens do Checklist", styles["Heading2"]))
    story.append(Spacer(1, 6))

    # Itens
    data = [["OK", "Item", "Observação"]]
    for it in checklist.get("itens", []) or []:
        ok = "✔" if it.get("ok") else ""
        nome = str(it.get("nome", "") or "")
        obs = str(it.get("obs", "") or "")
        data.append([ok, nome, obs])

    t = Table(data, colWidths=[10 * mm, 70 * mm, 105 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 10))

    # Blocos finais
    def add_block(label: str, text: str):
        story.append(Paragraph(label, styles["Heading3"]))
        story.append(Paragraph((text or "-").replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 8))

    add_block("Riscos", checklist.get("riscos", ""))
    add_block("Pendências", checklist.get("pendencias", ""))
    add_block("Decisões", checklist.get("decisoes", ""))

    doc.build(story)
    return buf.getvalue()


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

            # Serviços (para sugestão)
            orc = _get_orc_for_os(o, pv_db, orc_db)
            serv_text = _servicos_texto_from_orc(orc) if orc else ""
            sugest = _suggest_from_servicos_text(serv_text)

            st.divider()
            st.markdown("## Checklists (Produto / Molde)")
            st.caption(f"Serviços (lidos do orçamento): {serv_text or '-'}")

            prod_status = os_db[os_id]["checklists"]["produto"].get("status", "NAO_CRIADO")
            molde_status = os_db[os_id]["checklists"]["molde"].get("status", "NAO_CRIADO")

            colA, colB, colC = st.columns(3)

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

            if colB.button("🧩 Criar Checklist Produto", key=f"cria_prod_{os_id}"):
                if prod_status == "CRIADO":
                    st.info("Checklist Produto já está criado.")
                else:
                    os_db[os_id]["checklists"]["produto"]["status"] = "CRIADO"
                    _init_checklist_produto_items(os_db, os_id)
                    os_db[os_id]["updated_at"] = _now()
                    save(DB_OS, os_db)
                    st.success("Checklist Produto criado!")
                    st.rerun()

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
            st.markdown("## Checklist Produto (itens)")

            prod = os_db[os_id]["checklists"]["produto"]

            if prod.get("status") != "CRIADO":
                st.info("Checklist Produto ainda não foi criado. Clique em **Criar Checklist Produto**.")
            else:
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
                prod["riscos"] = st.text_area("Riscos", value=prod.get("riscos", ""), key=f"prod_riscos_{os_id}")

                st.markdown("### Pendências")
                prod["pendencias"] = st.text_area(
                    "Pendências", value=prod.get("pendencias", ""), key=f"prod_pend_{os_id}"
                )

                st.markdown("### Decisões")
                prod["decisoes"] = st.text_area(
                    "Decisões", value=prod.get("decisoes", ""), key=f"prod_dec_{os_id}"
                )

                st.markdown("### Aprovação")
                aprov_opts = ["", "APROVADO", "APROVADO COM RESSALVAS", "REPROVADO"]
                aprov_val = prod.get("aprovacao", "")
                if aprov_val not in aprov_opts:
                    aprov_val = ""
                prod["aprovacao"] = st.selectbox(
                    "Aprovação",
                    aprov_opts,
                    index=aprov_opts.index(aprov_val),
                    key=f"prod_aprov_{os_id}",
                )

                colS1, colS2 = st.columns(2)

                if colS1.button("💾 Salvar Checklist Produto", key=f"save_prod_{os_id}"):
                    os_db[os_id]["updated_at"] = _now()
                    save(DB_OS, os_db)
                    st.success("Checklist Produto salvo!")
                    st.rerun()

                # PDF export
                pdf_bytes = _build_checklist_produto_pdf(o, prod)
                filename = f"Checklist_Produto_{o.get('doc','OS')}.pdf"

                colS2.download_button(
                    "📄 Baixar PDF do Checklist Produto",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    key=f"dl_pdf_prod_{os_id}",
                )

            st.divider()
            st.markdown("### Status da OS")

            status_atual = o.get("status", "ABERTA")
            status_opts = ["ABERTA", "EM_ANDAMENTO", "PAUSADA", "CONCLUIDA"]
            if status_atual not in status_opts:
                status_atual = "ABERTA"

            novo_status = st.selectbox(
                "Status",
                status_opts,
                index=status_opts.index(status_atual),
                key=f"status_{os_id}",
            )

            if st.button("Salvar status", key=f"save_status_{os_id}"):
                os_db[os_id]["status"] = novo_status
                os_db[os_id]["updated_at"] = _now()
                save(DB_OS, os_db)
                st.success("Status atualizado!")
                st.rerun()
