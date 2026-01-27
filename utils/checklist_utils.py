# utils/checklist_utils.py

def criar_checklist_com_ref(base_itens):
    """
    Recebe uma lista de itens com ref_id e titulo
    e cria a estrutura padrão usada na OS.
    """
    checklist = []

    for item in base_itens:
        checklist.append({
            "ref_id": item["ref_id"],
            "titulo": item["titulo"],
            "checked": False,
            "observacao": ""
        })

    return checklist
