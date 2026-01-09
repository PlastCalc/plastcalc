import io
import streamlit as st
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union


# ---------------------------
# Helpers
# ---------------------------
def format_pt(value: float, decimals: int = 2) -> str:
    """Formata número no padrão pt-BR (1.234,56)."""
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def load_stl_to_mesh(uploaded_file) -> trimesh.Trimesh:
    """
    Lê STL enviado no Streamlit e retorna um Trimesh.
    Usa io.BytesIO (mais robusto no Streamlit Cloud).
    Suporta casos em que trimesh retorna Scene.
    """
    data = uploaded_file.read()
    stream = io.BytesIO(data)

    mesh = trimesh.load(stream, file_type="stl")

    if isinstance(mesh, trimesh.Scene):
        if len(mesh.geometry) == 0:
            raise ValueError("STL carregou como Scene vazia.")
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError("Arquivo STL não gerou uma malha válida (Trimesh).")

    if mesh.faces is None or len(mesh.faces) == 0:
        raise ValueError("Malha sem faces (triângulos).")

    return mesh


def projected_area_xy_mm2(mesh: trimesh.Trimesh) -> float:
    """
    Calcula a área projetada (silhueta) do STL no plano XY.
    Assumimos Z como direção de injeção.
    Método: projeta triângulos em XY e faz união (union) com Shapely.

    Retorna mm².
    """
    if mesh is None or mesh.is_empty:
        return 0.0

    tris = mesh.triangles  # (n, 3, 3)
    if tris is None or len(tris) == 0:
        return 0.0

    tris_xy = tris[:, :, :2]  # (n, 3, 2)

    polys = []
    for tri in tris_xy:
        # Triângulo degenerado?
        if np.linalg.matrix_rank(tri - tri[0]) < 2:
            continue

        p = Polygon(tri)
        if p.is_valid and p.area > 0:
            polys.append(p)

    if not polys:
        return 0.0

    union = unary_union(polys)
    return float(union.area)


# ---------------------------
# Page
# ---------------------------
st.set_page_config(page_title="Força de Fechamento | PlastCalc", page_icon="🧮", layout="wide")

st.title("🔒 Força de Fechamento do Molde")
st.caption("Cálculo por área projetada (XY) e pressão na cavidade (MPa). **Z = direção de injeção**.")

with st.expander("📌 Fórmulas usadas", expanded=False):
    st.markdown(
        """
- **1 MPa = 1 N/mm²**
- **Força (N) = Pressão (MPa) × Área (mm²)**
- **Força (kN) = Força (N) ÷ 1000**
- **Força (tf) = Força (kN) ÷ 9,80665**
- **Força recomendada = Força × Fator de segurança**
        """
    )

st.divider()

# ---------------------------
# STL upload + projected area
# ---------------------------
st.subheader("📁 Área projetada a partir de STL (recomendado)")
st.warning(
    "Envie o STL **já orientado**: o eixo **Z** deve estar **na direção de injeção**. "
    "A área projetada será calculada no plano **XY**."
)

confirm = st.checkbox("Confirmo que o STL está orientado com Z na direção de injeção.", value=True)

uploaded = st.file_uploader("Enviar STL", type=["stl"], accept_multiple_files=False)

unit = st.selectbox(
    "Unidade do STL",
    ["mm", "cm", "m"],
    index=0,
    help="Se o STL estiver em cm ou m, o app converte para mm antes de calcular."
)
scale_to_mm = {"mm": 1.0, "cm": 10.0, "m": 1000.0}[unit]

area_from_stl = None
mesh_info = {}

if uploaded is not None:
    if not confirm:
        st.error("Marque a confirmação de orientação do STL (Z na direção de injeção) para prosseguir.")
    else:
        try:
            mesh = load_stl_to_mesh(uploaded)

            # Converte unidades para mm
            mesh.apply_scale(scale_to_mm)

            # Informações do STL
            bounds = mesh.bounds  # [[minx,miny,minz],[maxx,maxy,maxz]]
            size = bounds[1] - bounds[0]
            mesh_info = {
                "Triângulos": int(len(mesh.faces)),
                "Dimensões (mm) X": float(size[0]),
                "Dimensões (mm) Y": float(size[1]),
                "Dimensões (mm) Z": float(size[2]),
                "Watertight (fechado)": bool(mesh.is_watertight),
            }

            with st.spinner("Calculando área projetada (pode levar alguns segundos em STLs grandes)..."):
                area_from_stl = projected_area_xy_mm2(mesh)

            st.success(f"Área projetada (XY): **{format_pt(area_from_stl, 2)} mm²**")

            with st.expander("ℹ️ Informações do STL", expanded=False):
                st.write(mesh_info)

        except Exception as e:
            st.error(f"Falha ao ler/calcular o STL: {e}")

st.divider()

# ---------------------------
# Inputs for force calculation
# ---------------------------
st.subheader("🧮 Cálculo da força")

# Integração com página 02 (Pressão por L/t)
pressao_default = float(st.session_state.get("pressao_mpa", 7.47))
pressao_veio_da_tabela = "pressao_mpa" in st.session_state

if pressao_veio_da_tabela:
    st.info(
        f"Pressão carregada automaticamente da página **Pressão na Cavidade (L/t)**: "
        f"**{format_pt(pressao_default, 2)} MPa**"
    )
    col_clear, _ = st.columns([1, 3])
    with col_clear:
        if st.button("Limpar pressão automática"):
            st.session_state.pop("pressao_mpa", None)
            st.rerun()

c1, c2, c3 = st.columns(3)

with c1:
    default_area = float(area_from_stl) if area_from_stl is not None else 11816.0
    area_mm2 = st.number_input(
        "Área projetada (mm²)",
        min_value=0.0,
        value=default_area,
        step=1.0,
        help="Se você enviou STL, este valor vem da área projetada no plano XY."
    )

with c2:
    pressao_mpa = st.number_input(
        "Pressão efetiva na cavidade (MPa)",
        min_value=0.0,
        value=pressao_default,
        step=0.01,
        help="Dica: 1 bar = 0,1 MPa. Use a página de pressão por L/t para estimar."
    )

with c3:
    fs = st.number_input(
        "Fator de segurança",
        min_value=1.00,
        max_value=2.00,
        value=1.20,
        step=0.05
    )

st.divider()

# ---------------------------
# Calculations
# ---------------------------
forca_n = pressao_mpa * area_mm2
forca_kn = forca_n / 1000.0
forca_tf = forca_kn / 9.80665

forca_kn_rec = forca_kn * fs
forca_tf_rec = forca_tf * fs

m1, m2, m3 = st.columns(3)
m1.metric("Força calculada (kN)", format_pt(forca_kn, 2))
m2.metric("Força calculada (tf)", format_pt(forca_tf, 2))
m3.metric("Força recomendada (tf)", format_pt(forca_tf_rec, 2))

st.markdown("### Detalhamento")
st.write(
    {
        "Área projetada (mm²)": area_mm2,
        "Pressão cavidade (MPa)": pressao_mpa,
        "Fator de segurança": fs,
        "Força (N)": forca_n,
        "Força (kN)": forca_kn,
        "Força (tf)": forca_tf,
        "Força recomendada (kN)": forca_kn_rec,
        "Força recomendada (tf)": forca_tf_rec,
    }
)

st.info(
    "💡 **Importante:** a força de fechamento costuma considerar **área projetada total** "
    "(produto + canais/galhos se aplicável). Se quiser, adicionamos um campo opcional para "
    "**área adicional do sistema de canais** e somamos automaticamente."
)
