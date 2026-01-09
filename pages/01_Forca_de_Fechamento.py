import streamlit as st

st.set_page_config(page_title="Força de Fechamento | PlastCalc", page_icon="🧮", layout="wide")

st.title("🔒 Força de Fechamento do Molde")
st.caption("Estimativa baseada em área projetada e pressão efetiva na cavidade (com fator de segurança).")

with st.expander("📌 Como o cálculo funciona (fórmulas)", expanded=False):
    st.markdown(
        """
- **1 MPa = 1 N/mm²**
- **Força (kN) = Pressão (MPa) × Área (mm²) ÷ 1000**
- **Força (tf) = Força (kN) ÷ 9,80665**
- **Força recomendada = Força × Fator de segurança**
        """
    )

col1, col2, col3 = st.columns(3)

with col1:
    area_mm2 = st.number_input("Área projetada (mm²)", min_value=0.0, value=11816.0, step=1.0)

with col2:
    pressao_mpa = st.number_input("Pressão efetiva (MPa)", min_value=0.0, value=7.47, step=0.01)

with col3:
    fs = st.number_input("Fator de segurança", min_value=1.00, max_value=2.00, value=1.20, step=0.05)

st.divider()

# Cálculos
forca_n = pressao_mpa * area_mm2               # N (pois MPa = N/mm²)
forca_kn = forca_n / 1000.0                    # kN
forca_tf = forca_kn / 9.80665                  # toneladas-força (tf)

forca_kn_rec = forca_kn * fs
forca_tf_rec = forca_tf * fs

c1, c2, c3 = st.columns(3)
c1.metric("Força calculada (kN)", f"{forca_kn:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c2.metric("Força calculada (tf)", f"{forca_tf:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c3.metric("Força recomendada (tf)", f"{forca_tf_rec:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("### Detalhamento")
st.write(
    {
        "Área projetada (mm²)": area_mm2,
        "Pressão efetiva (MPa)": pressao_mpa,
        "Fator de segurança": fs,
        "Força (N)": forca_n,
        "Força (kN)": forca_kn,
        "Força (tf)": forca_tf,
        "Força recomendada (kN)": forca_kn_rec,
        "Força recomendada (tf)": forca_tf_rec,
    }
)

st.info(
    "Dica: se você tiver a **pressão de injeção da máquina**, a pressão efetiva na cavidade pode ser bem menor "
    "dependendo de perdas (canal, bico, hot runner, viscosidade, espessura, etc.)."
)
