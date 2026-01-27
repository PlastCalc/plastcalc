# data/checklist_ref_ids.py

# ==============================
# CHECKLIST – PROJETO DE PRODUTO
# ==============================

CHECKLIST_PRODUTO = [
    {"ref_id": "prod_01_linha_fechamento", "titulo": "Linha de fechamento do produto"},
    {"ref_id": "prod_02_espessura", "titulo": "Espessura do produto"},
    {"ref_id": "prod_03_marca_injecao", "titulo": "Marca do ponto de injeção aceitável"},
    {"ref_id": "prod_04_rechupe", "titulo": "Há risco de rechupe"},
    {"ref_id": "prod_05_angulo_saida", "titulo": "Ângulo de saída para desmoldagem"},
    {"ref_id": "prod_06_bico_quente", "titulo": "Necessidade de aplicação de bico quente"},
    {"ref_id": "prod_07_bordas", "titulo": "Bordas arredondadas na peça"},
    {"ref_id": "prod_08_tamanho", "titulo": "Tamanho do produto"},
    {"ref_id": "prod_09_encaixes", "titulo": "Encaixes do produto"},
    {"ref_id": "prod_10_montagem", "titulo": "Número de operações de montagem"},
    {"ref_id": "prod_11_mecanismo", "titulo": "Mecanismo do produto"},
    {"ref_id": "prod_12_quantidade", "titulo": "Quantidade de peças"},
    {"ref_id": "prod_13_distribuicao", "titulo": "Distribuição do produto no molde"},
]


# ===========================
# CHECKLIST – PROJETO DE MOLDE
# ===========================

CHECKLIST_MOLDE = {
    "cavidade_macho": [
        {"ref_id": "molde_cav_01_extracao", "titulo": "Sistema de extração adequado"},
        {"ref_id": "molde_cav_02_particao", "titulo": "Partição correta"},
        {"ref_id": "molde_cav_03_angulo", "titulo": "Ângulo de saída adequado"},
        {"ref_id": "molde_cav_04_polimento", "titulo": "Polimento especificado"},
        # 👉 depois você pode continuar a lista aqui
    ],
    "porta_molde": [
        {"ref_id": "molde_pm_01_dimensao", "titulo": "Dimensão do porta-molde"},
        {"ref_id": "molde_pm_02_colunas", "titulo": "Colunas e buchas"},
    ],
    "documentacao": [
        {"ref_id": "molde_doc_01_desenhos", "titulo": "Desenhos atualizados"},
        {"ref_id": "molde_doc_02_lista", "titulo": "Lista de componentes"},
    ]
}
