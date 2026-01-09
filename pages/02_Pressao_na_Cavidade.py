import streamlit as st

st.set_page_config(page_title="Pressão na Cavidade | PlastCalc", page_icon="🧮", layout="wide")
st.title("📈 Pressão na cavidade (por L/t e espessura)")

# ---- 1) Tabela (preencher com seus valores) ----
# Colunas (espessura em mm) — use exatamente as que aparecem na sua tabela
THICKNESS = [0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.75,2.0,2.25,2.5,2.75,3.0,3.5,4.0,4.5,5.0]

# Linhas (razão L/t)
RATIOS = [50, 75, 100, 150, 200, 250]

# PRESSURE_TABLE[ratio_index][thickness_index] em bar
# ⚠️ PREENCHA com os números da sua tabela
PRESSURE_TABLE = {
    50:  [None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None],
    75:  [400,375,325,300,270,240,220,200,180,180,180,180,180,180,180,180,180,180,180,180,180,180],
    100: [480,450,400,370,340,300,290,280,250,230,210,190,180,180,180,180,180,180,180,180,180,180],
    150: [720,670,580,530,480,440,425,400,375,360,340,320,260,220,210,180,180,180,180,180,180,180],
    200: [900,850,750,720,700,630,580,520,500,450,430,410,360,320,290,260,240,220,180,180,180,180],
    250: [1050,1000,900,850,800,700,660,620,560,530,500,480,420,360,330,300,275,250,225,200,180,180],
}

# ---- 2) Funções de interpolação ----
def lerp(x, x0, x1, y0, y1):
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * ((x - x0) / (x1 - x0))

def clamp(v, vmin, vmax):
    return max(vmin, min(vmax, v))

def interp_pressao_bar(ratio, thk):
    # limita ao domínio da tabela
    ratio = clamp(ratio, min(RATIOS), max(RATIOS))
    thk   = clamp(thk,   min(THICKNESS), max(THICKNESS))

    # acha vizinhos de ratio
    r0 = max([r for r in RATIOS if r <= ratio])
    r1 = min([r for r in RATIOS if r >= ratio])

    # acha vizinhos de espessura
    t0 = max([t for t in THICKNESS if t <= thk])
    t1 = min([t for t in THICKNESS if t >= thk])

    i_t0 = THICKNESS.index(t0)
    i_t1 = THICKNESS.index(t1)

    # pega pressões nas quatro “quinas”
    p_r0_t0 = PRESSURE_TABLE[r0][i_t0]
    p_r0_t1 = PRESSURE_TABLE[r0][i_t1]
    p_r1_t0 = PRESSURE_TABLE[r1][i_t0]
    p_r1_t1 = PRESSURE_TABLE[r1][i_t1]

    # se houver None (caso linha 50 incompleta), cai para o mais próximo válido
    for v in [p_r0_t0, p_r0_t1, p_r1_t0, p_r1_t1]:
        if v is None:
            # fallback simples: usa a linha imediatamente acima (ex.: 75) se existir
            # (você pode remover isso se preencher 100% da tabela)
            pass

    # interpola em espessura para cada linha
    p_r0 = lerp(thk, t0, t1, p_r0_t0, p_r0_t1)
    p_r1 = lerp(thk, t0, t1, p_r1_t0, p_r1_t1)

    # interpola em ratio
    p = lerp(ratio, r0, r1, p_r0, p_r1)
    return p

# ---- 3) UI ----
c1, c2, c3 = st.columns(3)
with c1:
    L = st.number_input("Comprimento de fluxo L (mm)", min_value=1.0, value=150.0, step=1.0)
with c2:
    t = st.number_input("Espessura t (mm)", min_value=0.2, value=1.5, step=0.1)
with c3:
    material = st.selectbox(
        "Material (fator de fluxo)",
        ["PP/PE/PS (1,0)", "PA (1,2)", "PA (1,3)", "PA (1,4)", "ABS/SAN (1,3)", "ABS/SAN (1,4)", "POM (1,5)", "PC/PVC (1,7)", "PC/PVC (2,0)"]
    )

fatores = {
    "PP/PE/PS (1,0)": 1.0,
    "PA (1,2)": 1.2,
    "PA (1,3)": 1.3,
    "PA (1,4)": 1.4,
    "ABS/SAN (1,3)": 1.3,
    "ABS/SAN (1,4)": 1.4,
    "POM (1,5)": 1.5,
    "PC/PVC (1,7)": 1.7,
    "PC/PVC (2,0)": 2.0,
}
f_mat = fatores[material]

ratio = L / t  # L/t

p_base_bar = interp_pressao_bar(ratio, t)
p_final_bar = p_base_bar * f_mat
p_final_mpa = p_final_bar * 0.1

st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("Relação L/t", f"{ratio:,.1f}:1".replace(",", "X").replace(".", ",").replace("X", "."))
m2.metric("Pressão (tabela) [bar]", f"{p_base_bar:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
m3.metric("Pressão final [MPa]", f"{p_final_mpa:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.info("Você pode usar esta pressão final (MPa) como entrada direta na página de Força de Fechamento.")
