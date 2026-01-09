import streamlit as st

st.set_page_config(page_title="Pressão na Cavidade | PlastCalc", page_icon="🧮", layout="wide")
st.title("📈 Pressão na Cavidade (por L/t e espessura)")
st.caption("Estimativa baseada em tabelas: relação trajeto/espessura (L/t) × espessura da parede. Saída em bar e MPa.")

with st.expander("📌 Como funciona", expanded=False):
    st.markdown(
        """
1. Você informa **Comprimento de fluxo (L)** e **Espessura (t)**  
2. O app calcula **R = L/t** (ex.: 100:1)  
3. Busca na tabela a **pressão base (bar)** para aquela espessura e razão  
4. Aplica o **fator do material**  
5. Converte para **MPa** (1 bar = 0,1 MPa)  
        """
    )

# ---------------------------
# Tabela (bar)
# Linhas: R = L/t (sem 50:1 conforme solicitado)
# Colunas: espessura (mm)
# ---------------------------
THK = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5, 4.0, 4.5, 5.0]
RATIOS = [75, 100, 150, 200, 250]

# Valores conforme a tabela da sua imagem (sem linha 50:1)
P = {
    75:  [400, 375, 325, 300, 270, 240, 220, 200, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180],
    100: [480, 450, 400, 370, 340, 300, 290, 280, 250, 230, 210, 190, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180],
    150: [720, 670, 580, 530, 480, 440, 425, 400, 375, 360, 340, 320, 260, 220, 210, 180, 180, 180, 180, 180, 180, 180],
    200: [900, 850, 750, 720, 700, 630, 580, 520, 500, 450, 430, 410, 360, 320, 290, 260, 240, 220, 180, 180, 180, 180],
    250: [1050, 1000, 900, 850, 800, 700, 660, 620, 560, 530, 500, 480, 420, 360, 330, 300, 275, 250, 225, 200, 180, 180],
}

def lerp(x, x0, x1, y0, y1):
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * ((x - x0) / (x1 - x0))

def clamp(v, vmin, vmax):
    return max(vmin, min(vmax, v))

def interp_pressao_bar(ratio: float, thk: float) -> float:
    # limita ao domínio
    ratio = clamp(ratio, min(RATIOS), max(RATIOS))
    thk = clamp(thk, min(THK), max(THK))

    # vizinhos em ratio
    r0 = max([r for r in RATIOS if r <= ratio])
    r1 = min([r for r in RATIOS if r >= ratio])

    # vizinhos em espessura
    t0 = max([t for t in THK if t <= thk])
    t1 = min([t for t in THK if t >= thk])

    i0 = THK.index(t0)
    i1 = THK.index(t1)

    # “quinas”
    p_r0_t0 = P[r0][i0]
    p_r0_t1 = P[r0][i1]
    p_r1_t0 = P[r1][i0]
    p_r1_t1 = P[r1][i1]

    # interpola na espessura para cada linha
    p_r0 = lerp(thk, t0, t1, p_r0_t0, p_r0_t1)
    p_r1 = lerp(thk, t0, t1, p_r1_t0, p_r1_t1)

    # interpola no ratio
    p = lerp(ratio, r0, r1, p_r0, p_r1)
    return float(p)

def fmt_pt(x, dec=2):
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# ---------------------------
# UI
# ---------------------------
c1, c2, c3 = st.columns(3)
with c1:
    L = st.number_input("Comprimento de fluxo L (mm)", min_value=1.0, value=150.0, step=1.0)
with c2:
    t = st.number_input("Espessura da parede t (mm)", min_value=0.2, value=1.5, step=0.05)
with c3:
    material = st.selectbox(
        "Material (fator de fluxo)",
        [
            "PP/PE/PS (1,0)",
            "PA (1,2)", "PA (1,3)", "PA (1,4)",
            "ABS/SAN (1,3)", "ABS/SAN (1,4)",
            "POM (1,5)",
            "PMMA/PPO (1,5)",  # você confirmou a faixa correta; mantive 1,5 como padrão
            "PC/PVC (1,7)", "PC/PVC (2,0)",
        ],
        index=0
    )

fatores = {
    "PP/PE/PS (1,0)": 1.0,
    "PA (1,2)": 1.2,
    "PA (1,3)": 1.3,
    "PA (1,4)": 1.4,
    "ABS/SAN (1,3)": 1.3,
    "ABS/SAN (1,4)": 1.4,
    "POM (1,5)": 1.5,
    "PMMA/PPO (1,5)": 1.5,
    "PC/PVC (1,7)": 1.7,
    "PC/PVC (2,0)": 2.0,
}
f = fatores[material]

ratio = L / t
p_base_bar = interp_pressao_bar(ratio, t)
p_final_bar = p_base_bar * f
p_final_mpa = p_final_bar * 0.1

st.divider()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Relação L/t", f"{fmt_pt(ratio, 1)}:1")
m2.metric("Pressão base (bar)", fmt_pt(p_base_bar, 0))
m3.metric("Fator do material", fmt_pt(f, 2))
m4.metric("Pressão final (MPa)", fmt_pt(p_final_mpa, 2))

st.markdown("### Resultado")
st.write(
    {
        "L (mm)": L,
        "t (mm)": t,
        "L/t": ratio,
        "Pressão base (bar)": p_base_bar,
        "Fator material": f,
        "Pressão final (bar)": p_final_bar,
        "Pressão final (MPa)": p_final_mpa,
    }
)

st.divider()

# ---------------------------
# Integração com página 01 (session_state)
# ---------------------------
st.subheader("➡️ Enviar para Força de Fechamento")

st.write("Clique para usar esta pressão final (MPa) automaticamente na página **Força de Fechamento**.")

if st.button("Usar esta pressão na Força de Fechamento (MPa)"):
    st.session_state["pressao_mpa"] = float(p_final_mpa)
    st.success("Pronto! Abra a página **Força de Fechamento** e a pressão já estará preenchida.")
