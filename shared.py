"""
Módulo compartilhado: dados, constantes, helpers e CSS do dashboard.
Fonte: PNAD Contínua Anual — SIDRA/IBGE (2012–2024).
"""

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).parent
CACHE = BASE / "dados_cache.parquet"
GEOJSON = BASE / "brasil_estados.geojson"

# ─── Paleta e metadados ─────────────────────────────────────────────────────────

ACCENTS = ["#FF2E63", "#1DD1A1", "#FF9F1C", "#2E86DE"]  # rosa, verde, laranja, azul

GRUPOS_DIM = {
    "Sexo": ["Homens", "Mulheres", "Total"],
    "Cor/Raça": ["Branca", "Preta", "Parda", "Total"],
}
ICONES = {"Homens": "♂", "Mulheres": "♀", "Total": "Σ",
          "Branca": "●", "Preta": "●", "Parda": "●"}

# par usado na razão de desigualdade de cada dimensão (maior ÷ menor)
PAR_RAZAO = {"Sexo": ("Homens", "Mulheres"), "Cor/Raça": ("Branca", "Preta")}

CORES_REGIAO = {"Norte": "#2E86DE", "Nordeste": "#FF9F1C", "Sudeste": "#1DD1A1",
                "Sul": "#FF2E63", "Centro-Oeste": "#A55EEA"}
ORDEM_REGIAO = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]

# escala verde→âmbar→vermelho→roxo para razões de desigualdade
GAP_SCALE = [[0.00, "#38B000"], [0.32, "#FFB703"], [0.62, "#E63946"], [1.00, "#7B2D8B"]]


# ─── Carregamento de dados ──────────────────────────────────────────────────────

@st.cache_data(show_spinner="Baixando dados do SIDRA/IBGE…")
def load_data() -> pd.DataFrame:
    if not CACHE.exists():
        import app  # efeito colateral: extrai da API SIDRA e grava o cache
        app.carregar_dados()
    df = pd.read_parquet(CACHE)
    df["ano"] = df["ano"].astype(int)
    return df


@st.cache_data(show_spinner=False)
def load_geojson() -> dict:
    if not GEOJSON.exists():
        import app
        gj = app.get_geojson_estados()
        GEOJSON.write_text(json.dumps(gj, ensure_ascii=False))
        return gj
    return json.loads(GEOJSON.read_text())


DF = load_data()
GJ = load_geojson()
ANOS = sorted(DF["ano"].unique().tolist())
UFS = sorted(DF["uf"].unique().tolist())
ID2UF = dict(zip(DF["uf_id_str"], DF["uf"]))
UF2SIGLA = dict(zip(DF["uf"], DF["sigla"]))


# ─── Helpers de formatação e figura ─────────────────────────────────────────────

def rgba(hex_cor, alpha):
    h = hex_cor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def brl(v, casas=0):
    if v != v:
        return "—"
    return "R$ " + f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fig_base(fig, height, legend=True):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=height, margin=dict(l=10, r=10, t=10, b=10),
        font=dict(color="#C7CDDA", size=12),
        legend=(dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                     yanchor="bottom", y=1.02, x=0) if legend else {}),
        hoverlabel=dict(bgcolor="#1E222B", bordercolor="#3A4150"),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    return fig


def sparkline(valores, cor, w=110, h=36):
    vals = [(i, v) for i, v in enumerate(valores) if v == v]
    if len(vals) < 2:
        return ""
    ys = [v for _, v in vals]
    mn, mx = min(ys), max(ys)
    rng = (mx - mn) or 1
    n = len(valores)
    pts = [((i / (n - 1)) * (w - 6) + 3, (h - 4) - (v - mn) / rng * (h - 10))
           for i, v in vals]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pts[0][0]:.1f},{h} " + line + f" {pts[-1][0]:.1f},{h}"
    lx, ly = pts[-1]
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<polygon points="{area}" fill="{cor}" opacity="0.16"/>'
        f'<polyline points="{line}" fill="none" stroke="{cor}" stroke-width="2.2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3" fill="{cor}"/></svg>'
    )


# ─── Transformações de dados ─────────────────────────────────────────────────────

def serie_nacional(df, dimensao, grupo):
    """Razão das médias: média do rendimento do grupo entre as UFs, por ano."""
    sub = df[(df["dimensao"] == dimensao) & (df["grupo"] == grupo)]
    return sub.groupby("ano")["rendimento"].mean().reindex(ANOS)


def gap_por_uf(df, dimensao, ano=None):
    """Razão de cada UF = grupo A ÷ grupo B no próprio estado."""
    g_a, g_b = PAR_RAZAO[dimensao]
    sub = df[(df["dimensao"] == dimensao) & (df["grupo"].isin([g_a, g_b]))]
    if ano is not None:
        sub = sub[sub["ano"] == ano]
    piv = sub.pivot_table(index=["uf", "sigla", "regiao", "ano"],
                          columns="grupo", values="rendimento").reset_index()
    if g_a not in piv or g_b not in piv:
        return pd.DataFrame()
    piv = piv.dropna(subset=[g_a, g_b])
    piv["gap"] = piv[g_a] / piv[g_b]
    return piv


def build_gapminder(df):
    gx = (df[(df["dimensao"] == "Sexo") & (df["grupo"].isin(["Homens", "Mulheres"]))]
          .pivot_table(index=["uf", "sigla", "regiao", "ano"], columns="grupo",
                       values="rendimento").reset_index())
    gx["gap_genero"] = gx["Homens"] / gx["Mulheres"]
    gr = (df[(df["dimensao"] == "Cor/Raça") & (df["grupo"].isin(["Branca", "Preta"]))]
          .pivot_table(index=["uf", "ano"], columns="grupo",
                       values="rendimento").reset_index())
    gr["gap_raca"] = gr["Branca"] / gr["Preta"]
    tot = (df[(df["dimensao"] == "Sexo") & (df["grupo"] == "Total")]
           [["uf", "ano", "rendimento"]].rename(columns={"rendimento": "renda_total"}))
    m = (gx.merge(gr[["uf", "ano", "gap_raca", "Branca", "Preta"]], on=["uf", "ano"])
           .merge(tot, on=["uf", "ano"], how="left"))
    m = m.dropna(subset=["gap_genero", "gap_raca", "renda_total"])
    m["ano_str"] = m["ano"].astype(str)
    return m


def razao_nacional(df, dimensao, ano):
    """Razão das médias nacionais (= dividir os dois cartões de KPI)."""
    g_a, g_b = PAR_RAZAO[dimensao]
    a = serie_nacional(df, dimensao, g_a).get(ano, float("nan"))
    b = serie_nacional(df, dimensao, g_b).get(ano, float("nan"))
    return (a / b) if (b and b == b) else float("nan")


R2_MIN = 0.30  # abaixo disso, consideramos que não há tendência linear clara


def explica_paridade(rp):
    """Frase dinâmica explicando por que os dois cenários de projeção divergem."""
    full, rec = rp["full"], rp["recente"]

    def rumo(s):
        return "queda" if s < -0.002 else "alta" if s > 0.002 else "estabilidade"

    partes = []
    if full["r2"] < R2_MIN:
        partes.append(f"Na **série inteira** não há tendência linear clara "
                      f"(R² {full['r2']:.2f}): a razão oscila sem direção definida.")
    else:
        partes.append(f"A **série inteira** mostra tendência de {rumo(full['slope'])} "
                      f"(R² {full['r2']:.2f}), puxada sobretudo pelo movimento dos "
                      f"primeiros anos.")
    if rec:
        if rec["r2"] < R2_MIN:
            partes.append(f"Já nos **últimos 5 anos** a razão fica praticamente estável e "
                          f"ruidosa (R² {rec['r2']:.2f}), **sem tendência estatística** — "
                          f"é por isso que os dois cenários divergem.")
        else:
            partes.append(f"Nos **últimos 5 anos** o ritmo é de {rumo(rec['slope'])} "
                          f"(R² {rec['r2']:.2f}).")
    return " ".join(partes)


def _ols_paridade(serie):
    """Ajusta uma reta à série da razão e projeta o cruzamento com 1,00.

    Retorna slope, intercepto, R² do ajuste e os anos/ano projetados de paridade
    (None quando a razão é estável/crescente — não converge).
    """
    import numpy as np
    if serie is None or len(serie) < 3:
        return None
    anos = serie.index.values.astype(float)
    vals = serie.values.astype(float)
    slope, intercept = np.polyfit(anos, vals, 1)
    pred = intercept + slope * anos
    ss_res = float(((vals - pred) ** 2).sum())
    ss_tot = float(((vals - vals.mean()) ** 2).sum())
    r2 = (1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    ano0, r0 = float(anos.max()), float(vals[-1])
    convergindo = slope < -1e-5 and r0 > 1.0
    anos_proj = (r0 - 1.0) / (-slope) if convergindo else None
    return {
        "slope": float(slope), "intercept": float(intercept), "r2": r2,
        "ano0": ano0, "r0": r0, "anos_proj": anos_proj,
        "ano_paridade": (ano0 + anos_proj) if anos_proj else None,
    }


def ritmo_paridade(df, dimensao):
    """Projeções de paridade (série completa + últimos 5 anos) com R² e gap absoluto."""
    g_a, g_b = PAR_RAZAO[dimensao]
    sa, sb = serie_nacional(df, dimensao, g_a), serie_nacional(df, dimensao, g_b)
    r = (sa / sb).dropna()
    if len(r) < 3:
        return None
    return {
        "serie": r,
        "full": _ols_paridade(r),
        "recente": _ols_paridade(r.tail(5)) if len(r) >= 5 else None,
        "gap_abs": (sa - sb),  # diferença em R$ por ano
        "g_a": g_a, "g_b": g_b,
    }


# ─── CSS e cabeçalho compartilhados ──────────────────────────────────────────────

CSS = """
<style>
.block-container { padding-top: 2.4rem; padding-bottom: 1rem; max-width: 1500px; }
h3 { margin-top: .2rem !important; }
#MainMenu, footer { visibility: hidden; }
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #1E222B; border: 1px solid #2A2F3A !important; border-radius: 16px; }
.panel-title { font-size: 1.05rem; font-weight: 700; color: #fff; margin: 0 0 .35rem 0; }
.panel-sub { font-size: .78rem; color: #8A93A6; margin: -.25rem 0 .5rem 0; }
.kpi-grid { display: grid; gap: 14px; }
.kpi-card { background: #1E222B; border: 1px solid #2A2F3A; border-radius: 16px;
    padding: 14px 18px; display: flex; align-items: center; gap: 16px; }
.kpi-icon { width: 50px; height: 50px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: 700; }
.kpi-mid { flex: 1; min-width: 0; }
.kpi-label { font-size: .72rem; color: #8A93A6; font-weight: 700;
    text-transform: uppercase; letter-spacing: .06em; }
.kpi-value { font-size: 1.55rem; font-weight: 800; color: #fff; line-height: 1.15; }
.kpi-delta { font-size: .74rem; font-weight: 700; margin-top: 1px; }
.kpi-spark { flex-shrink: 0; }
.big-stat { padding: 4px 0; }
.big-num { font-size: 2.3rem; font-weight: 800; line-height: 1; }
.big-cap { font-size: .78rem; color: #9AA3B2; font-weight: 600; margin-top: 4px; }
.center-num { font-size: 3rem; font-weight: 800; color: #fff; line-height: 1; }
.reg-row { display: flex; justify-content: space-between; gap: 8px; margin-top: 6px; }
.reg-item { text-align: center; flex: 1; }
.reg-val { font-size: 1.05rem; font-weight: 800; }
.reg-name { font-size: .66rem; color: #8A93A6; font-weight: 600; text-transform: uppercase; }
.insight { background: linear-gradient(90deg, rgba(255,46,99,.10), rgba(46,134,222,.06));
    border-left: 4px solid #FF2E63; border-radius: 10px; padding: 12px 16px;
    font-size: .95rem; color: #E6E9EF; margin-bottom: 4px; }
section[data-testid="stSidebar"] { background: #12151C; }
.stTabs [data-baseweb="tab"] { font-weight: 600; }
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


# ─── Filtros globais (sidebar) ───────────────────────────────────────────────────

def sidebar_filtros():
    with st.sidebar:
        st.markdown("### 🎛️ Filtros gerais")
        st.caption("Aplicam-se a todas as páginas.")
        dimensao = st.radio("**Dimensão**", list(GRUPOS_DIM.keys()), key="f_dim")
        ano = st.select_slider("**Ano**", options=ANOS, value=max(ANOS), key="f_ano")
        regioes = st.multiselect("**Regiões**", ORDEM_REGIAO, default=ORDEM_REGIAO,
                                 key="f_reg")
        if not regioes:
            regioes = ORDEM_REGIAO
        st.divider()
        g_a, g_b = PAR_RAZAO[dimensao]
        st.caption(f"📌 **Razão** = renda de **{g_a}** ÷ **{g_b}**. "
                   f"Acima de 1 indica vantagem de {g_a}.")


def get_filtros():
    """Lê os filtros globais do session_state e devolve um contexto pronto."""
    dimensao = st.session_state.get("f_dim", "Sexo")
    ano = st.session_state.get("f_ano", max(ANOS))
    regioes = st.session_state.get("f_reg") or ORDEM_REGIAO
    dff = DF[DF["regiao"].isin(regioes)]
    grupos = GRUPOS_DIM[dimensao]
    g_a, g_b = PAR_RAZAO[dimensao]
    return {
        "dimensao": dimensao, "ano": ano, "regioes": regioes, "dff": dff,
        "grupos": grupos, "grupos_kpi": [g for g in grupos if g != "Total"][:3],
        "g_a": g_a, "g_b": g_b,
    }
