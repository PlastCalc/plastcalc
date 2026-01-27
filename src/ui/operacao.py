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


# -----------------------------
# Estrutura base
# -----------------------------
def _ensure_checklists_struct(os_db: dict, os_id: str):
    os_db[os_id].setdefault("checklists", {})
    os_db[os_id]["checklists"].setdefault(
        "produto",
        {"status": "NAO_CRIADO", "itens": [], "riscos": "", "pendencias": "", "decisoes": "", "aprovacao": ""},
    )
    os_db[os_id]["checklists"].setdefault(
        "molde",
        {
            "status": "NAO_CRIADO",
            "secoes": {},
            "riscos": "",
            "pendencias": "",
            "decisoes": "",
            "aprovacao": "",
        },
    )


# -----------------------------
# Checklist Molde – Itens
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


# -----------------------------
# PDF – Checklist Molde
# -----------------------------
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
        st.info("Nenhuma OS encontrada.")
        return

    for o in items:
        with st.expander(f"{o.get('doc')} • {o.get('cliente_nome')} • {o.get('status')}"):
            os_id = o.get("id")
            _ensure_checklists_struct(os_db, os_id)

            st.write(f"**Título:** {o.get('titulo')}")
            st.write(f"**Criado em:** {o.get('created_at')}")

            st.divider()
            st.markdown("## Checklist Molde")

            molde = os_db[os_id]["checklists"]["molde"]
            st.write(f"**Status:** {molde.get('status')}")

            if molde.get("status") != "CRIADO":
                if st.button("🧩 Criar Checklist Molde", key=f"mk_molde_{os_id}"):
                    molde["status"] = "CRIADO"
                    _init_checklist_molde(os_db, os_id)
                    os_db[os_id]["updated_at"] = _now()
                    save(DB_OS, os_db)
                    st.success("Checklist Molde criado!")
                    st.rerun()
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

                molde["riscos"] = st.text_area("Riscos", value=molde.get("riscos", ""), key=f"riscos_m_{os_id}")
                molde["pendencias"] = st.text_area(
                    "Pendências", value=molde.get("pendencias", ""), key=f"pend_m_{os_id}"
                )
                molde["decisoes"] = st.text_area(
                    "Decisões", value=molde.get("decisoes", ""), key=f"dec_m_{os_id}"
                )

                aprov_opts = ["", "APROVADO", "APROVADO COM RESSALVAS", "REPROVADO"]
                aprov_val = molde.get("aprovacao", "")
                if aprov_val not in aprov_opts:
                    aprov_val = ""
                molde["aprovacao"] = st.selectbox(
                    "Aprovação", aprov_opts, index=aprov_opts.index(aprov_val), key=f"aprov_m_{os_id}"
                )

                colS1, colS2 = st.columns(2)
                if colS1.button("💾 Salvar Checklist Molde", key=f"save_molde_{os_id}"):
                    os_db[os_id]["updated_at"] = _now()
                    save(DB_OS, os_db)
                    st.success("Checklist Molde salvo!")
                    st.rerun()

                pdf_bytes = _build_checklist_molde_pdf(o, molde)
                colS2.download_button(
                    "📄 Baixar PDF Checklist Molde",
                    data=pdf_bytes,
                    file_name=f"Checklist_Molde_{o.get('doc')}.pdf",
                    mime="application/pdf",
                )
