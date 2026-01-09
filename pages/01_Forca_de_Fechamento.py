import io
import streamlit as st
import numpy as np
import trimesh


# ---------------------------
# Helpers
# ---------------------------
def format_pt(value: float, decimals: int = 2) -> str:
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def load_stl_to_mesh(uploaded_file) -> trimesh.Trimesh:
    data = uploaded_file.read()
    stream = io.BytesIO(data)
    mesh = trimesh.load(stream, file_type="stl")

    if isinstance(mesh, trimesh.Scene):
        if len(mesh.geometry) == 0:
            raise ValueError("STL vazio.")
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError("Arquivo não é uma malha válida.")

    return mesh


def projected_area_xy_mm2(mesh: trimesh.Trimesh, resolution: int = 400) -> float:
    """
    Área projetada no plano XY usando rasterização + ray casting (sem Shapely).
    Z é assumido como direção de injeção.
    """
    bounds = mesh.bounds
    min_x, min_y = bounds[0][0], bounds[0][1]
    max_x, max_y = bounds[1][0], bounds[1][1]

    xs = np.linspace(min_x, max_x, resolution)
    ys = np.linspace(min_y, max_y, resolution)
    dx = (max_x - min_x) / (resolution - 1)
    dy = (max_y - min_y) / (resolution - 1)
    pixel_area = dx * dy

    xx, yy = np.meshgrid(xs, ys)
    origins = np.column_stack([
        xx.ravel(),
        yy.ravel(),
        np.full(xx.size, bounds[1][2] + 1.0)  # acima da peça
    ])

    directions = np.tile([0, 0, -1], (origins.shape[0], 1))

    locations, index_ray, _ = mesh.ray.intersects_location(
        ray_origins=origins,
        ray_directions=directions,
        multiple_hits=False
    )

    hit_mask = np.zeros(origins.shape[0], dtype=bool)
    hit_mask[index_ray] = True

    area = hit_mask.sum() * pixel_area
    return float(area)


# ---------------------------
# Page
# ---------------------------
st.set_page_config(page_title="Força de Fechamento | PlastCalc", page_icon="🧮", layout="wide")

st.title("🔒 Força de Fechamento do Molde")
st.caption("Área projetada (XY) + pressão na cavidade. Z = direção de injeção.")

with st.expander("📌 Fórmulas usadas", expanded=False):
    st.markdown("""
- **1 MPa = 1 N/mm²**
- **Força (N) = Pressão (MPa) × Área (mm²)**
- **Força (kN) = N ÷ 1000**
- **Força (tf) = kN ÷ 9,80665**
""")

st.divider()

# ---------------------------
# STL Upload
# ---------------------------
st.subheader("📁 Área projetada via STL (recomendado)")
st.warning("Envie o STL orientado com **Z na direção de injeção**.")

confirm = st.checkbox("Confirmo a orientação correta do STL (Z = injeção)", value=True)
uploaded = st.file_uploader("Enviar STL", type=["stl"])

unit = st.selectbox("Unidade do STL", ["mm", "cm", "m"], index=0)
scale = {"mm": 1.0, "cm": 10.0, "m": 1000.0}[unit]

area_from_stl = None

if uploaded and confirm:
    try:
        mesh = load_stl_to_mesh(uploaded)
        mesh.apply_scale(scale)

        with st.spinner("Calculando área projetada..."):
            area_from_stl = projected_area_xy_mm2(mesh, resolution=400)

        st.success(f"Área projetada (XY): **{format_pt(area_from_stl, 2)} mm²**")

    except Exception as e:
        st.error(f"Erro no STL: {e}")

st.divider()

# ---------------------------
# Inputs
# ---------------------------
pressao_default = float(st.session_state.get("pressao_mpa", 7.47))

c1, c2, c3 = st.columns(3)

with c1:
    area_mm2 = st.number_input(
        "Área projetada (mm²)",
        min_value=0.0,
        value=float(area_from_stl) if area_from_stl else 11816.0,
        step=1.0
    )

with c2:
    pressao_mpa = st.number_input(
        "Pressão na cavidade (MPa)",
        min_value=0.0,
        value=pressao_default,
        step=0.01
    )

with c3:
    fs = st.number_input("Fator de segurança", 1.0, 2.0, 1.20, 0.05)

st.divider()

# ---------------------------
# Calculations
# ---------------------------
forca_n = pressao_mpa * area_mm2
forca_kn = forca_n / 1000.0
forca_tf = forca_kn / 9.80665
forca_tf_rec = forca_tf * fs

m1, m2, m3 = st.columns(3)
m1.metric("Força (kN)", format_pt(forca_kn))
m2.metric("Força (tf)", format_pt(forca_tf))
m3.metric("Força recomendada (tf)", format_pt(forca_tf_rec))

st.info(
    "💡 Método robusto (sem Shapely/GEOS). "
    "Precisão adequada para engenharia de injeção e compatível com Streamlit Cloud."
)
