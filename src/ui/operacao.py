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


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# -----------------------------
# Estrutura base (OS -> checklists)
# -----------------------------
def _ensure_checklists_struct(os_db: dict, os_id: str):
    os_db[os_id].setdefault("checklists", {})

    os_db[os_id]["checklists"].setdefault(
        "produto",
        {
            "status": "NAO_CRIADO",  # NAO_CRIADO / CRIADO
            "itens": [],
            "riscos": "",
            "pendencias": "",
            "decisoes": "",
            "aprovacao": "",
        },
    )

    os_db[os_id]["checklists"].setdefault(
        "molde",
        {
            "status": "NAO_CRIADO",  # NAO_CRIADO / CRIADO
            "secoes": {},
            "riscos": "",
            "pendencias": "",
            "decisoes": "",
            "aprovacao": "",
        },
    )


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
    prod = os_db[os_id]["checklists"]["produto"]
    if prod.get("itens"):
        return
    prod["itens"] = [{"nome": nome, "ok": False, "obs": ""} for nome in CHECKLIST_PRODUTO_ITENS]


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

    story.append(Paragraph("Ata Técnica — Projeto de Produto (Checklist Produto)", styles["Title"]))
    story.append(Spacer(1, 8))

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
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(t_meta)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Itens do Checklist", styles["Heading2"]))
    story.append(Spacer(1, 6))

    data = [["OK", "Item", "Observação"]]
    for it in checklist.get("itens", []) or []:
        ok = "✔" if it.get("ok") else ""
        data.append([ok, it.get("nome", ""), it.get("obs", "")])

    t = Table(data, colWidths=[10 * mm, 70 * mm, 105 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 10))

    def add_block(label: str, text: str):
        story.append(Paragraph(label, styles["Heading3"]))
        story.append(Paragraph((text or "-").replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 8))

    add_block("Riscos", checklist.get("riscos", ""))
    add_block("Pendências", checklist.get("pendencias", ""))
    add_block("Decisões", checklist.get("decisoes", ""))

    doc.build(story)
    return buf.getvalue()


# -----------------------------
# Checklist Molde (seções)
# -----------------------------
SECAO_CAVIDADE_MACHO = [
    "Material adequado para o termoplástico",
    "Contração utilizada",
    "Canal de injeção adequado",
    "Injeção capilar",
    "Injeção submarina",
    "Processo de fabricação disponível na empresa",
    "Avaliação de preenchimento do produto",
    "Quantidade e distribuição de extratores adequada",
    "Risco de colisão entre partes móveis",
    "Curso de extração suficiente",
    "Curso de partes móveis suficiente (anel, gaveta)",
    "Sistema de extração com mecanismo de retorno",
    "Válvula de ar",
    "Saída de gases",
    "Retenção do produto no lado da extração",
    "Refrigeração adequada",
    "Macho e cavidade empostiçados na placa",
    "Travamento adequado de partes móveis",
    "Necessidade de tratamento térmico",
    "Centralizadores adequados à peça",
    "Necessidade de usinar montado",
    "Necessidade de empostiçar partes do inserto",
    "Furo para coordenada de eletrodo",
    "Bico quente (Manifold)",
    "Concordância entre os insertos",
    "Alívio no fechamento",
    "Tipo de extração do galho",
    "Extratores travados",
    "Suporte pilar adequado",
    "Anel de centragem 90,0 mm",
    "Fixação auxiliar entre CPE e PE adequada",
]

SECAO_PORTA_MOLDE = [
    "Porta-molde padronizado",
    "Placas especiais (aços)",
    "Colunas, buchas e guias adequadas",
    "Coluna deslocada identificada",
    "Porta-molde com aba",
    "Tamanho do porta-molde compatível ao produto",
    "Porta-molde com rosca para sacar Manifold",
    "Porta-molde colunado",
]

SECAO_DOCUMENTACAO = [
    "Lista de material correta",
    "Desenhos adequados",
]


def _init_checklist_molde(os_db: dict, os_id: str):
    molde = os_db[os_id]["checklists"]["molde"]
    if molde.get("secoes"):
        return

    def make_items(lista):
        return [{"nome": n, "ok": False, "obs": ""} for n in lista]

    molde["secoes"] = {
        "Cavidade / Macho": make_items(SECAO_CAVIDADE_MACHO),
        "Porta-molde": make_items(SECAO_PORTA_MOLDE),
        "Documentação": make_items(SECAO_DOCUMENTACAO),
    }


def _build_checklist_molde_pdf(os_item: dict, checklist: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Checklist Molde",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Ata Técnica — Projeto de Molde (Checklist Molde)", styles["Title"]))
    story.append(Spacer(1, 8))

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
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(t_meta)
    story.append(Spacer(1, 10))

    for secao, itens in checklist.get("secoes", {}).items():
        story.append(Paragraph(secao, styles["Heading2"]))
        data = [["OK", "Item", "Observação"]]
        for it in itens:
            ok = "✔" if it.get("ok") else ""
            data.append([ok, it.get("nome", ""), it.get("obs", "")])

        t = Table(data, colWidths=[10 * mm, 70 * mm, 105 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 8))

    def add_block(label, txt):
        story.append(Paragraph(label, styles["Heading3"]))
        story.append(Paragraph((txt or "-").replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 6))

    add_block("Riscos", checklist.get("riscos", ""))
    add_block("Pendências", checklist.get("pendencias", ""))
    add_block("Decisões", checklist.get("decisoes", ""))

    doc.build(story)
    return buf.getvalue()


# -----------------------------
# UI – Operação
# -----------------------------
def page_operacao():
    st.header("Operação / Ordem de Serviço")

    os_db = load(DB_OS)
    items = list(os_db.values())
    items.sort(key=lambda x: x.get("doc", ""), reverse=True)

    if not items:
        st.info("Nenhuma OS encontrada ainda.")
        return

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
            st.markdown("## Checklists")

            prod = os_db[os_id]["checklists"]["produto"]
            molde = os_db[os_id]["checklists"]["molde"]

            c1, c2 = st.columns(2)

            # --- criar produto
            with c1:
                st.subheader("Projeto de Produto")
                st.write(f"Status: **{prod.get('status','')}**")
                if prod.get("status") != "CRIADO":
                    if st.button("🧩 Criar Checklist Produto", key=f"mk_prod_{os_id}"):
                        prod["status"] = "CRIADO"
                        _init_checklist_produto_items(os_db, os_id)
                        os_db[os_id]["updated_at"] = _now()
                        save(DB_OS, os_db)
                        st.success("Checklist Produto criado!")
                        st.rerun()

            # --- criar molde
            with c2:
                st.subheader("Projeto de Molde")
                st.write(f"Status: **{molde.get('status','')}**")
                if molde.get("status") != "CRIADO":
                    if st.button("🧩 Criar Checklist Molde", key=f"mk_molde_{os_id}"):
                        molde["status"] = "CRIADO"
                        _init_checklist_molde(os_db, os_id)
                        os_db[os_id]["updated_at"] = _now()
                        save(DB_OS, os_db)
                        st.success("Checklist Molde criado!")
                        st.rerun()

            st.divider()
            st.markdown("## Checklist Produto (itens + PDF)")

            if prod.get("status") != "CRIADO":
                st.info("Checklist Produto ainda não foi criado.")
            else:
                _init_checklist_produto_items(os_db, os_id)

                for i, item in enumerate(prod["itens"]):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        item["ok"] = st.checkbox(
                            item["nome"], value=item.get("ok", False), key=f"prod_ok_{os_id}_{i}"
                        )
                    with col2:
                        item["obs"] = st.text_input(
                            "Observação", value=item.get("obs", ""), key=f"prod_obs_{os_id}_{i}"
                        )

                prod["riscos"] = st.text_area("Riscos", value=prod.get("riscos", ""), key=f"prod_r_{os_id}")
                prod["pendencias"] = st.text_area("Pendências", value=prod.get("pendencias", ""), key=f"prod_p_{os_id}")
                prod["decisoes"] = st.text_area("Decisões", value=prod.get("decisoes", ""), key=f"prod_d_{os_id}")

                aprov_opts = ["", "APROVADO", "APROVADO COM RESSALVAS", "REPROVADO"]
                aprov_val = prod.get("aprovacao", "")
                if aprov_val not in aprov_opts:
                    aprov_val = ""
                prod["aprovacao"] = st.selectbox(
                    "Aprovação", aprov_opts, index=aprov_opts.index(aprov_val), key=f"prod_a_{os_id}"
                )

                colS1, colS2 = st.columns(2)
                if colS1.button("💾 Salvar Checklist Produto", key=f"save_prod_{os_id}"):
                    os_db[os_id]["updated_at"] = _now()
                    save(DB_OS, os_db)
                    st.success("Checklist Produto salvo!")
                    st.rerun()

                pdf_bytes = _build_checklist_produto_pdf(o, prod)
                colS2.download_button(
                    "📄 Baixar PDF Checklist Produto",
                    data=pdf_bytes,
                    file_name=f"Checklist_Produto_{o.get('doc','OS')}.pdf",
                    mime="application/pdf",
                    key=f"dl_prod_{os_id}",
                )

            st.divider()
            st.markdown("## Checklist Molde (itens + PDF)")

            if molde.get("status") != "CRIADO":
                st.info("Checklist Molde ainda não foi criado.")
            else:
                _init_checklist_molde(os_db, os_id)

                for secao, itens in molde["secoes"].items():
                    st.markdown(f"### {secao}")
                    for i, it in enumerate(itens):
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            it["ok"] = st.checkbox(
                                it["nome"], value=it.get("ok", False), key=f"{os_id}_{secao}_{i}_ok"
                            )
                        with col2:
                            it["obs"] = st.text_input(
                                "Observação", value=it.get("obs", ""), key=f"{os_id}_{secao}_{i}_obs"
                            )

                molde["riscos"] = st.text_area("Riscos (Molde)", value=molde.get("riscos", ""), key=f"mol_r_{os_id}")
                molde["pendencias"] = st.text_area(
                    "Pendências (Molde)", value=molde.get("pendencias", ""), key=f"mol_p_{os_id}"
                )
                molde["decisoes"] = st.text_area(
                    "Decisões (Molde)", value=molde.get("decisoes", ""), key=f"mol_d_{os_id}"
                )

                aprov_opts = ["", "APROVADO", "APROVADO COM RESSALVAS", "REPROVADO"]
                aprov_val = molde.get("aprovacao", "")
                if aprov_val not in aprov_opts:
                    aprov_val = ""
                molde["aprovacao"] = st.selectbox(
                    "Aprovação (Molde)", aprov_opts, index=aprov_opts.index(aprov_val), key=f"mol_a_{os_id}"
                )

                colM1, colM2 = st.columns(2)
                if colM1.button("💾 Salvar Checklist Molde", key=f"save_molde_{os_id}"):
                    os_db[os_id]["updated_at"] = _now()
                    save(DB_OS, os_db)
                    st.success("Checklist Molde salvo!")
                    st.rerun()

                pdf_bytes = _build_checklist_molde_pdf(o, molde)
                colM2.download_button(
                    "📄 Baixar PDF Checklist Molde",
                    data=pdf_bytes,
                    file_name=f"Checklist_Molde_{o.get('doc','OS')}.pdf",
                    mime="application/pdf",
                    key=f"dl_molde_{os_id}",
                )

            st.divider()
            st.markdown("### Status da OS")

            status_opts = ["ABERTA", "EM_ANDAMENTO", "PAUSADA", "CONCLUIDA"]
            status_atual = o.get("status", "ABERTA")
            if status_atual not in status_opts:
                status_atual = "ABERTA"

            novo_status = st.selectbox(
                "Status", status_opts, index=status_opts.index(status_atual), key=f"status_{os_id}"
            )

            if st.button("Salvar status", key=f"save_status_{os_id}"):
                os_db[os_id]["status"] = novo_status
                os_db[os_id]["updated_at"] = _now()
                save(DB_OS, os_db)
                st.success("Status atualizado!")
                st.rerun()