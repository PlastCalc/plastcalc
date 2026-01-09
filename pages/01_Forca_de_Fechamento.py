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
        raise ValueError("Arquivo não gerou uma malha Trimesh válida.")

    if mesh.faces is None or len(mesh.faces) == 0:
        raise ValueError("Malha sem faces (triângulos).")

    return mesh


def points_in_triangle(px, py, ax, ay, bx, by, cx, cy):
    """
    Teste ponto-no-triângulo 2D (barycentric) vetorizado.
    Retorna máscara booleana com o mesmo shape de px/py.
    """
    v0x, v0y = cx - ax, cy - ay
    v1x, v1y = bx - ax, by - ay
    v2x, v2y = px - ax, py - ay

    den = v0x * v1y - v1x * v0y
    if den == 0:
        return np.zeros_like(px, dtype=bool)

    inv_den = 1.0 / den
    u = (v2x * v1y - v1x * v2y) * inv_den
    v = (v0x * v2y - v2x * v0y) * inv_den

    return (u >= 0) & (v >= 0) & (u + v <= 1)


def projected_area_xy_mm2(mesh: trimesh.Trimesh, resolution: int = 350) -> float:
    """
    Área projetada no plano XY SEM rtree e SEM shapely.
    Método: rasterização de triângulos projetados em um grid (ocupação 2D).
    """
    bounds = mesh.bounds
    min_x, min_y = bounds[0][0], bounds[0][1]
    max_x, max_y = bounds[1][0], bounds[1][1]

    if max_x <= min_x or max_y <= min_y:
        return 0.0

    xs = np.linspace(min_x, max_x, resolution)
    ys = np.linspace(min_y, max_y, resolution)
    dx = (max_x - min_x) / (resolution - 1)
    dy = (max_y - min_y) / (resolution - 1)
    pixel_area = dx * dy

    occ = np.zeros((resolution, resolution), dtype=bool)  # [iy, ix]

    tris = mesh.triangles[:, :, :2]  # (n,3,2)
    # Para acelerar buscas de faixa (índices)
    # xs e ys já são ordenados, então usamos searchsorted.
    for tri in tris:
        (ax, ay), (bx, by), (cx, cy) = tri

        tminx = min(ax, bx, cx)
        tmaxx = max(ax, bx, cx)
        tminy = min(ay, by, cy)
        tmaxy = max(ay, by, cy)

        # recorte rápido: tri fora do bounds
        if tmaxx < min_x or tminx > max_x or tmaxy < min_y or tminy > max_y:
            continue

        ix0 = int(np.searchsorted(xs, tminx, side="left"))
        ix1 = int(np.searchsorted(xs, tmaxx, side="right"))
        iy0 = int(np.searchsorted(ys, tminy, side="left"))
        iy1 = int(np.searchsorted(ys, tmaxy, side="right"))

        ix0 = max(0, min(ix0, resolution - 1))
        ix1 = max(0, min(ix1, resolution))
        iy0 = max(0, min(iy0, resolution - 1))
        iy1 = max(0, min(iy1, resolution))

        if ix1 <= ix0 or iy1 <= iy0:
            continue

        sub_x = xs[ix0:ix1]
        sub_y = ys[iy0:iy1]
        xx, yy = np.meshgrid(sub_x, sub_y)

        inside = points_in_triangle(xx, yy, ax, ay, bx, by, cx, cy)
        occ[iy0:iy1, ix0:ix1] |= inside

    return float(occ.sum() * pixel_area)


# ---------------------------
# Page
# ---------------------------
st.set_page_config(page_title="Força de Fechamento | PlastCalc", page_icon="🧮", layout="wide")

st.title("🔒 Força de Fechamento do Molde")
st.caption("Área projetada (XY) + pressão na cavidade. **Z = direção de injeção**.")

with st.expander("📌 Fórmulas usadas", expanded=False):
    st.markdown("""
- **1 MPa = 1 N/mm²**
- **Força (N) = Pressão (MPa) × Área (mm²)**
- **Força (kN) = N ÷ 1000**
- **Força (tf) = kN ÷ 9,80665**
- **Força recomendada = Força × Fator de segurança**
""")

st.divider()

st.subheader("📁 Área projetada via STL (recomendado)")
st.warning("Envie o STL orientado com **Z na direção de injeção** (a projeção é no plano **XY**).")

confirm = st.checkbox("Confirmo a orientação correta do STL (Z = injeção)", value=True)
uploaded = st.file_uploader("Enviar STL", type=["stl"])

unit = st.selectbox("Unidade do STL", ["mm", "cm", "m"], index=0)
scale = {"mm": 1.0, "cm": 10.0, "m": 1000.0}[unit]

quality = st.selectbox("Qualidade do cálculo (velocidade x precisão)", ["Rápido", "Normal", "Preciso"], index=1)
res_map = {"Rápido": 220, "Normal": 350, "Preciso": 500}
resolution = res_map[quality]

area_from_stl = None

if uploaded and confirm:
    try:
        mesh = load_stl_to_mesh(uploaded)
        mesh.apply_scale(scale)

        bounds = mesh.bounds
        size = bounds[1] - bounds[0]

        with st.spinner("Calculando área projetada (sem rtree)..."):
            area_from_stl = projected_area_xy_mm2(mesh, resolution=resolution)

        st.success(f"Área projetada (XY): **{format_pt(area_from_stl, 2)} mm²**")

        with st.expander("ℹ️ Informações do STL", expanded=False):
            st.write({
                "Triângulos": int(len(mesh.faces)),
                "Dimensões (mm) X": float(size[0]),
                "Dimensões (mm) Y": float(size[1]),
                "Dimensões (mm) Z": float(size[2]),
                "Watertight (fechado)": bool(mesh.is_watertight),
                "Resolução usada": resolution,
            })

    except Exception as e:
        st.error(f"Erro no STL: {e}")

elif uploaded and not confirm:
    st.error("Marque a confirmação de orientação do STL para prosseguir.")

st.divider()

st.subheader("🧮 Cálculo da força")

pressao_default = float(st.session_state.get("pressao_mpa", 7.47))
if "pressao_mpa" in st.session_state:
    st.info(f"Pressão recebida da página **Pressão na Cavidade (L/t)**: **{format_pt(pressao_default, 2)} MPa**")
    if st.button("Limpar pressão automática"):
        st.session_state.pop("pressao_mpa", None)
        st.rerun()

c1, c2, c3 = st.columns(3)

with c1:
    area_mm2 = st.number_input(
        "Área projetada (mm²)",
        min_value=0.0,
        value=float(area_from_stl) if area_from_stl else 11816.0,
        step=1.0,
    )

with c2:
    pressao_mpa = st.number_input(
        "Pressão na cavidade (MPa)",
        min_value=0.0,
        value=pressao_default,
        step=0.01,
    )

with c3:
    fs = st.number_input("Fator de segurança", min_value=1.0, max_value=2.0, value=1.20, step=0.05)

st.divider()

forca_n = pressao_mpa * area_mm2
forca_kn = forca_n / 1000.0
forca_tf = forca_kn / 9.80665
forca_tf_rec = forca_tf * fs

m1, m2, m3 = st.columns(3)
m1.metric("Força (kN)", format_pt(forca_kn, 2))
m2.metric("Força (tf)", format_pt(forca_tf, 2))
m3.metric("Força recomendada (tf)", format_pt(forca_tf_rec, 2))

st.info("✅ Este cálculo de área projetada não depende de `rtree` e funciona no Streamlit Cloud.")
