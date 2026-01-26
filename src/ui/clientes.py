import streamlit as st
from datetime import datetime
from uuid import uuid4

from src.data.storage_json import load, save

DB_NAME = "clientes"

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def page_clientes():
    st.header("Clientes")

    db = load(DB_NAME)  # dict: {id: {campos...}}

    tab1, tab2 = st.tabs(["📋 Lista", "➕ Novo cliente"])

    with tab2:
        st.subheader("Cadastrar cliente")

        with st.form("form_novo_cliente", clear_on_submit=True):
            nome = st.text_input("Nome / Razão social*", placeholder="Ex.: Brinquedos ABC Ltda")
            documento = st.text_input("CPF/CNPJ", placeholder="Opcional")
            telefone = st.text_input("Telefone/WhatsApp", placeholder="Opcional")
            email = st.text_input("E-mail", placeholder="Opcional")
            cidade = st.text_input("Cidade", placeholder="Opcional")
            observacoes = st.text_area("Observações", placeholder="Opcional")

            submitted = st.form_submit_button("Salvar")

        if submitted:
            if not nome.strip():
                st.error("Informe o nome / razão social.")
            else:
                cid = str(uuid4())[:8]
                db[cid] = {
                    "id": cid,
                    "nome": nome.strip(),
                    "documento": documento.strip(),
                    "telefone": telefone.strip(),
                    "email": email.strip(),
                    "cidade": cidade.strip(),
                    "observacoes": observacoes.strip(),
                    "created_at": _now(),
                    "updated_at": _now(),
                }
                save(DB_NAME, db)
                st.success("Cliente cadastrado!")

    with tab1:
        st.subheader("Lista de clientes")

        q = st.text_input("Buscar", placeholder="Digite nome, cidade, email, etc.")

        items = list(db.values())
        if q.strip():
            q2 = q.strip().lower()
            items = [
                c for c in items
                if q2 in (c.get("nome","").lower()
                          + " " + c.get("cidade","").lower()
                          + " " + c.get("email","").lower()
                          + " " + c.get("telefone","").lower()
                          + " " + c.get("documento","").lower())
            ]

        items.sort(key=lambda x: x.get("nome", "").lower())

        st.caption(f"Total: {len(items)}")

        if not items:
            st.info("Nenhum cliente encontrado.")
            return

        for c in items:
            with st.expander(f"{c.get('nome','(sem nome)')}  •  {c.get('cidade','')}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**CPF/CNPJ:** {c.get('documento','')}")
                    st.write(f"**Telefone:** {c.get('telefone','')}")
                    st.write(f"**E-mail:** {c.get('email','')}")
                    st.write(f"**Criado em:** {c.get('created_at','')}")
                with col2:
                    st.write(f"**Cidade:** {c.get('cidade','')}")
                    st.write(f"**Atualizado em:** {c.get('updated_at','')}")
                    st.write("**Observações:**")
                    st.write(c.get("observacoes","") or "-")

                st.divider()
                st.markdown("### Editar / Excluir")

                with st.form(f"form_edit_{c['id']}"):
                    nome2 = st.text_input("Nome / Razão social*", value=c.get("nome",""))
                    documento2 = st.text_input("CPF/CNPJ", value=c.get("documento",""))
                    telefone2 = st.text_input("Telefone/WhatsApp", value=c.get("telefone",""))
                    email2 = st.text_input("E-mail", value=c.get("email",""))
                    cidade2 = st.text_input("Cidade", value=c.get("cidade",""))
                    observacoes2 = st.text_area("Observações", value=c.get("observacoes",""))

                    colA, colB = st.columns(2)
                    salvar = colA.form_submit_button("Salvar alterações")
                    excluir = colB.form_submit_button("Excluir cliente")

                if salvar:
                    if not nome2.strip():
                        st.error("Nome é obrigatório.")
                    else:
                        db[c["id"]].update({
                            "nome": nome2.strip(),
                            "documento": documento2.strip(),
                            "telefone": telefone2.strip(),
                            "email": email2.strip(),
                            "cidade": cidade2.strip(),
                            "observacoes": observacoes2.strip(),
                            "updated_at": _now(),
                        })
                        save(DB_NAME, db)
                        st.success("Alterações salvas! Recarregando…")
                        st.rerun()

                if excluir:
                    del db[c["id"]]
                    save(DB_NAME, db)
                    st.success("Cliente excluído! Recarregando…")
                    st.rerun()