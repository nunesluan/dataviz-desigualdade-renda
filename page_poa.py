"""Página 3 — Porto Alegre: desigualdade intraurbana (Censo 2010 por setor).

Visão coordenada inspirada no paradigma do **The Urban Toolkit** (Moreira et al.,
IEEE TVCG 2024, arXiv:2308.07769) — o paper estudado: uma camada **espacial**
(mapa dos setores censitários) ligada a camadas **temáticas** (renda × raça) por
*brushing & linking*. Selecione setores no gráfico de dispersão para vê-los
realçados no mapa.

⚠️ Fonte distinta das demais páginas: **Censo Demográfico 2010 / IBGE**, agregados
por setor censitário de Porto Alegre (renda total dos domicílios e composição por
cor/raça). É a 2ª fonte do trabalho, usada para descer ao recorte intraurbano que
a PNAD por UF não alcança.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import shared as S

BASE = Path(__file__).parent / "poa_data"
GEOJSON = BASE / "poa_setores.geojson"
CSV = BASE / "poa_setores.csv"

ESC_RENDA = [[0.0, "#3B0F70"], [0.35, "#8C2981"], [0.6, "#DE4968"],
             [0.82, "#FE9F6D"], [1.0, "#FCFDBF"]]  # magma — escuro=pobre, claro=rico
ESC_NEGRA = [[0.0, "#FCFDBF"], [0.5, "#FE9F6D"], [1.0, "#3B0F70"]]


@st.cache_data(show_spinner="Carregando setores de Porto Alegre (Censo 2010)…")
def _carregar():
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    df = pd.read_csv(CSV, dtype={"cod": str})
    df = df[df["renda_pc"].notna() & (df["pop"] > 0)].copy()
    return gj, df


def _gini(v):
    v = np.sort(np.asarray(v, dtype=float))
    n = len(v)
    if n == 0 or v.sum() == 0:
        return float("nan")
    idx = np.arange(1, n + 1)
    return float((2 * (idx * v).sum()) / (n * v.sum()) - (n + 1) / n)


def _cods_selecionados(ev):
    """Lê os códigos de setor selecionados no scatter (brushing)."""
    try:
        pts = ev["selection"]["points"]
    except (TypeError, KeyError):
        return []
    cods = []
    for p in pts:
        cd = p.get("customdata")
        if isinstance(cd, (list, tuple)) and cd:
            cods.append(str(cd[0]))
        elif isinstance(cd, str):
            cods.append(cd)
    return cods


def _mapa(gj, df, metrica, sel):
    if metrica == "Renda per capita":
        z, escala, titulo, fmt = df["renda_pc"], ESC_RENDA, "R$/mês", ":,.0f"
        rev = False
    else:
        z, escala, titulo, fmt = df["pct_negra"], ESC_NEGRA, "% negra", ":.1f"
        rev = False

    fig = go.Figure(go.Choropleth(
        geojson=gj, locations=df["cod"], featureidkey="properties.cod",
        z=z, customdata=np.stack([df["bairro"], df["renda_pc"], df["pct_negra"]], axis=-1),
        colorscale=escala, reversescale=rev,
        marker_line_color="rgba(0,0,0,0.15)", marker_line_width=0.2,
        colorbar=dict(title=titulo, thickness=10, len=0.85, tickfont=dict(size=9)),
        hovertemplate=("<b>%{customdata[0]}</b><br>renda pc: R$ %{customdata[1]:,.0f}"
                       "<br>pop. negra: %{customdata[2]:.1f}%<extra></extra>"),
    ))
    # camada de destaque: setores selecionados no scatter
    if sel:
        d2 = df[df["cod"].isin(sel)]
        if not d2.empty:
            fig.add_trace(go.Choropleth(
                geojson=gj, locations=d2["cod"], featureidkey="properties.cod",
                z=[1] * len(d2), showscale=False,
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                marker_line_color="#00E5FF", marker_line_width=1.4,
                hoverinfo="skip"))
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=460, margin=dict(l=0, r=0, t=0, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", geo=dict(bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _scatter(df, sel):
    cor_sel = df["cod"].isin(sel) if sel else pd.Series(False, index=df.index)
    base = df[~cor_sel] if sel else df
    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=base["renda_pc"], y=base["pct_negra"], mode="markers",
        marker=dict(size=6, color=base["renda_pc"], colorscale=ESC_RENDA,
                    opacity=0.55, line=dict(width=0)),
        customdata=np.stack([base["cod"], base["bairro"]], axis=-1),
        hovertemplate=("<b>%{customdata[1]}</b><br>renda pc: R$ %{x:,.0f}"
                       "<br>pop. negra: %{y:.1f}%<extra></extra>"),
        name="setores"))
    if sel:
        d2 = df[cor_sel]
        fig.add_trace(go.Scattergl(
            x=d2["renda_pc"], y=d2["pct_negra"], mode="markers",
            marker=dict(size=9, color="#00E5FF", line=dict(width=1, color="#fff")),
            customdata=np.stack([d2["cod"], d2["bairro"]], axis=-1),
            hovertemplate=("<b>%{customdata[1]}</b><br>renda pc: R$ %{x:,.0f}"
                           "<br>pop. negra: %{y:.1f}%<extra></extra>"),
            name="selecionados"))
    fig = S.fig_base(fig, 460, legend=False)
    fig.update_xaxes(title="Renda per capita do setor (R$/mês)", tickprefix="R$ ",
                     separatethousands=True, type="log")
    fig.update_yaxes(title="% população preta + parda")
    event = st.plotly_chart(fig, width="stretch", key="poa_brush",
                            on_select="rerun", selection_mode=("box", "lasso"),
                            config={"displayModeBar": True,
                                    "modeBarButtonsToRemove": ["zoom", "pan", "autoScale"]})
    return event


def _ranking_bairros(df):
    tmp = df.assign(rxp=df["renda_pc"] * df["pop"])
    g = (tmp.groupby("bairro")
         .agg(rxp=("rxp", "sum"), pop=("pop", "sum")).reset_index())
    g["renda_pc"] = g["rxp"] / g["pop"]
    g = g[(g["pop"] >= 500) & (g["bairro"] != "—")].sort_values("renda_pc")
    piores = g.head(8)
    melhores = g.tail(8)
    sel = pd.concat([piores, melhores])
    cores = ["#DE4968"] * len(piores) + ["#FCA50A"] * len(melhores)
    fig = go.Figure(go.Bar(
        x=sel["renda_pc"], y=sel["bairro"], orientation="h",
        marker=dict(color=cores), text=[S.brl(v) for v in sel["renda_pc"]],
        textposition="outside", textfont=dict(size=9, color="#C7CDDA"),
        hovertemplate="<b>%{y}</b><br>renda pc média: R$ %{x:,.0f}<extra></extra>"))
    fig = S.fig_base(fig, 460, legend=False)
    fig.update_xaxes(tickprefix="R$ ", separatethousands=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render():
    if not GEOJSON.exists() or not CSV.exists():
        st.error("Dados de Porto Alegre não encontrados. Rode: "
                 "`uv run --with pyshp python poa_data/build_poa.py`")
        return

    gj, df = _carregar()

    st.markdown("### 🏙️ Porto Alegre · desigualdade intraurbana (Censo 2010)")
    st.caption(
        "Inspirado no **The Urban Toolkit** (Moreira et al., IEEE TVCG 2024) — o paper "
        "estudado: camada **espacial** (setores censitários) ligada a camadas **temáticas** "
        "(renda × cor/raça) por *brushing & linking*. **Selecione setores no gráfico de "
        "dispersão** (ferramenta de caixa/laço) para realçá-los no mapa. Fonte: **Censo "
        "2010 / IBGE** por setor — recorte intraurbano que a PNAD por UF não alcança."
    )

    ev = st.session_state.get("poa_brush")
    sel = _cods_selecionados(ev)

    # KPIs ----------------------------------------------------------------------
    r = df["renda_pc"]
    p10, p90 = np.percentile(r, 10), np.percentile(r, 90)
    corr = df["renda_pc"].corr(df["pct_negra"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Renda per capita mediana", S.brl(r.median()))
    c2.metric("Razão 10% + ricos ÷ 10% + pobres", f"{p90 / p10:.1f}×",
              help="Entre setores: renda média do decil superior sobre o inferior.")
    c3.metric("Gini da renda entre setores", f"{_gini(r):.3f}",
              help="0 = igualdade total entre setores; 1 = concentração máxima.")
    c4.metric("Correlação renda × % negra", f"{corr:+.2f}",
              help="Negativa: quanto mais pobre o setor, maior a proporção de "
                   "população preta + parda — desigualdade racial no território.")

    if sel:
        d2 = df[df["cod"].isin(sel)]
        st.markdown(
            f"<div class='insight'>🔦 <b>Seleção:</b> {len(d2)} setores · renda pc média "
            f"<b>{S.brl(np.average(d2['renda_pc'], weights=d2['pop']))}</b> · "
            f"população negra média <b>{np.average(d2['pct_negra'], weights=d2['pop']):.1f}%</b> "
            f"(cidade: {np.average(df['pct_negra'], weights=df['pop']):.1f}%). "
            f"Realçados em ciano no mapa.</div>", unsafe_allow_html=True)

    # Visões coordenadas --------------------------------------------------------
    a, b = st.columns([1, 1])
    with a, st.container(border=True):
        st.markdown('<div class="panel-title">🗺️ Camada espacial — setores de POA</div>',
                    unsafe_allow_html=True)
        metrica = st.radio("Colorir por", ["Renda per capita", "% população negra"],
                           horizontal=True, key="poa_metrica", label_visibility="collapsed")
        st.markdown('<div class="panel-sub">Contorno ciano = setores selecionados ao lado.</div>',
                    unsafe_allow_html=True)
        _mapa(gj, df, metrica, sel)
    with b, st.container(border=True):
        st.markdown('<div class="panel-title">🎯 Renda × raça (fonte do brushing)</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="panel-sub">Cada ponto = um setor. Use caixa/laço para '
                    'selecionar e ver onde ficam no mapa.</div>', unsafe_allow_html=True)
        _scatter(df, sel)

    a, b = st.columns([1, 1])
    with a, st.container(border=True):
        st.markdown('<div class="panel-title">🏘️ Bairros — extremos de renda</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="panel-sub">8 menores (vermelho) e 8 maiores (amarelo) — '
                    'renda pc média ponderada pela população (bairros ≥ 500 hab.)</div>',
                    unsafe_allow_html=True)
        _ranking_bairros(df)
    with b, st.container(border=True):
        st.markdown('<div class="panel-title">📊 Distribuição da renda entre setores</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="panel-sub">Quantos setores em cada faixa de renda per '
                    'capita</div>', unsafe_allow_html=True)
        fig = go.Figure(go.Histogram(
            x=df["renda_pc"], nbinsx=40, marker=dict(color="#DE4968"),
            hovertemplate="R$ %{x:,.0f}<br>%{y} setores<extra></extra>"))
        fig.add_vline(x=r.median(), line_dash="dot", line_color="#FCA50A",
                      annotation_text=f"mediana {S.brl(r.median())}",
                      annotation_font_color="#FCA50A")
        fig = S.fig_base(fig, 460, legend=False)
        fig.update_xaxes(title="Renda per capita (R$/mês)", tickprefix="R$ ",
                         separatethousands=True)
        fig.update_yaxes(title="nº de setores")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.caption("Fonte: Censo Demográfico 2010 — IBGE, agregados por setor censitário de "
               "Porto Alegre (DomicilioRenda + Pessoa/cor-raça). Visão coordenada inspirada "
               "no The Urban Toolkit (arXiv:2308.07769).")
