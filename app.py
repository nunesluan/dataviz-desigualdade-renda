"""
Dashboard: Desigualdade de Renda no Brasil por Sexo e Cor/Raça
Fonte: PNAD Contínua Anual — SIDRA/IBGE

Executar:
    pip install -r requirements.txt
    python app.py
"""

import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
from pathlib import Path
from functools import lru_cache

# ─── Constantes ───────────────────────────────────────────────────────────────

SIDRA_BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"
ANOS = list(range(2012, 2025))
CACHE = Path("dados_cache.parquet")

UF_REGIAO = {
    "Rondônia": "Norte", "Acre": "Norte", "Amazonas": "Norte",
    "Roraima": "Norte", "Pará": "Norte", "Amapá": "Norte", "Tocantins": "Norte",
    "Maranhão": "Nordeste", "Piauí": "Nordeste", "Ceará": "Nordeste",
    "Rio Grande do Norte": "Nordeste", "Paraíba": "Nordeste",
    "Pernambuco": "Nordeste", "Alagoas": "Nordeste", "Sergipe": "Nordeste",
    "Bahia": "Nordeste", "Minas Gerais": "Sudeste", "Espírito Santo": "Sudeste",
    "Rio de Janeiro": "Sudeste", "São Paulo": "Sudeste",
    "Paraná": "Sul", "Santa Catarina": "Sul", "Rio Grande do Sul": "Sul",
    "Mato Grosso do Sul": "Centro-Oeste", "Mato Grosso": "Centro-Oeste",
    "Goiás": "Centro-Oeste", "Distrito Federal": "Centro-Oeste",
}

UF_SIGLA = {
    "Rondônia": "RO", "Acre": "AC", "Amazonas": "AM", "Roraima": "RR",
    "Pará": "PA", "Amapá": "AP", "Tocantins": "TO", "Maranhão": "MA",
    "Piauí": "PI", "Ceará": "CE", "Rio Grande do Norte": "RN",
    "Paraíba": "PB", "Pernambuco": "PE", "Alagoas": "AL", "Sergipe": "SE",
    "Bahia": "BA", "Minas Gerais": "MG", "Espírito Santo": "ES",
    "Rio de Janeiro": "RJ", "São Paulo": "SP", "Paraná": "PR",
    "Santa Catarina": "SC", "Rio Grande do Sul": "RS",
    "Mato Grosso do Sul": "MS", "Mato Grosso": "MT",
    "Goiás": "GO", "Distrito Federal": "DF",
}

CORES_REGIAO = {
    "Norte": "#1f77b4", "Nordeste": "#ff7f0e",
    "Sudeste": "#2ca02c", "Sul": "#d62728", "Centro-Oeste": "#9467bd",
}

CORES_GRUPO = {
    "Homens": "#4C78A8", "Mulheres": "#E45756", "Total": "#72B7B2",
    "Branca": "#F58518", "Preta": "#54A24B", "Parda": "#EECA3B",
}


# ─── Extração de dados ────────────────────────────────────────────────────────

def _fetch_tabela(tabela_id: int, classificacao: str) -> pd.DataFrame:
    """Busca dados de uma tabela SIDRA para todas as UFs e anos."""
    anos_str = "|".join(str(a) for a in ANOS)
    url = (
        f"{SIDRA_BASE}/{tabela_id}/periodos/{anos_str}"
        f"/variaveis/10774?localidades=N3[all]&classificacao={classificacao}"
    )
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    rows = []
    for bloco in resp.json():
        for resultado in bloco["resultados"]:
            grupo = ""
            dimensao = ""
            for clf in resultado.get("classificacoes", []):
                dimensao = clf["nome"]
                grupo = next(iter(clf["categoria"].values()), "")
            for serie in resultado["series"]:
                loc = serie["localidade"]
                for ano, valor in serie["serie"].items():
                    if valor not in ("-", "...", ""):
                        try:
                            rows.append({
                                "uf_id": int(loc["id"]),
                                "uf": loc["nome"],
                                "ano": int(ano),
                                "rendimento": float(valor),
                                "grupo": grupo,
                                "dimensao": dimensao,
                            })
                        except (ValueError, TypeError):
                            pass
    return pd.DataFrame(rows)


def carregar_dados() -> pd.DataFrame:
    """Carrega dados do cache ou extrai da API SIDRA."""
    if CACHE.exists():
        return pd.read_parquet(CACHE)

    print("Extraindo dados da API SIDRA... (pode levar ~30s)")
    df_sexo = _fetch_tabela(7444, "2[4,5,6794]")        # Homens, Mulheres, Total
    df_raca = _fetch_tabela(7441, "86[2776,2777,2779,95251]")  # Branca, Preta, Parda, Total

    df_sexo["dimensao"] = "Sexo"
    df_raca["dimensao"] = "Cor/Raça"

    df = pd.concat([df_sexo, df_raca], ignore_index=True)
    df["regiao"] = df["uf"].map(UF_REGIAO)
    df["sigla"] = df["uf"].map(UF_SIGLA)
    df["uf_id_str"] = df["uf_id"].astype(str)
    df.to_parquet(CACHE)
    print(f"Dados extraídos: {len(df):,} registros salvos em cache.")
    return df


@lru_cache(maxsize=1)
def get_geojson_estados():
    """Retorna o GeoJSON de estados brasileiros (codeforamerica/click_that_hood)."""
    url = (
        "https://raw.githubusercontent.com/codeforamerica/"
        "click_that_hood/master/public/data/brazil-states.geojson"
    )
    return requests.get(url, timeout=30).json()


# ─── Dados globais ────────────────────────────────────────────────────────────

DF = carregar_dados()
ANOS_DISP = sorted(DF["ano"].unique().tolist())
UFS_DISP = sorted(DF["uf"].unique().tolist())


# ─── Layout ───────────────────────────────────────────────────────────────────

_DARKLY = "https://cdn.jsdelivr.net/npm/bootswatch@5/dist/darkly/bootstrap.min.css"
app = Dash(__name__, external_stylesheets=[_DARKLY], suppress_callback_exceptions=True)
app.title = "Desigualdade de Renda no Brasil [DARK]"

HEADER = dbc.Row(
    dbc.Col([
        html.H2("Desigualdade de Renda no Brasil", className="mt-4 mb-1 fw-bold"),
        html.P(
            "Rendimento médio mensal real (R$) por sexo e cor/raça — "
            "PNAD Contínua Anual | SIDRA/IBGE | 2012–2024",
            className="text-muted",
        ),
        html.Hr(),
    ])
)

TABS = dbc.Tabs(
    [
        dbc.Tab(label="📈 Série Temporal",       tab_id="serie"),
        dbc.Tab(label="🗺️ Mapa de Disparidade",  tab_id="mapa"),
        dbc.Tab(label="↔️ Gap por UF",           tab_id="gap"),
        dbc.Tab(label="📉 Slope Chart",          tab_id="slope"),
    ],
    id="tabs",
    active_tab="serie",
)

app.layout = dbc.Container(
    [
        HEADER,
        html.Div(id="uf-indicador", className="mb-2", style={"minHeight": "38px"}),
        TABS,
        html.Div(id="conteudo-tab", className="mt-3"),
        dcc.Store(id="uf-selecionada", data=None),
    ],
    fluid=True,
)


# ─── Renderização de abas ─────────────────────────────────────────────────────

def _radio_dimensao(id_prefix):
    return dcc.RadioItems(
        id=f"{id_prefix}-dimensao",
        options=[
            {"label": "  Sexo", "value": "Sexo"},
            {"label": "  Cor/Raça", "value": "Cor/Raça"},
        ],
        value="Sexo",
        inline=True,
        inputStyle={"marginRight": "4px", "marginLeft": "12px"},
        className="mb-2",
    )


def _slider_ano(id_prefix, value=None):
    v = value if value is not None else max(ANOS_DISP)
    return dcc.Slider(
        id=f"{id_prefix}-ano",
        min=min(ANOS_DISP), max=max(ANOS_DISP), step=1,
        value=v,
        marks={a: str(a) for a in ANOS_DISP if a % 2 == 0},
        tooltip={"placement": "bottom", "always_visible": False},
    )


@app.callback(Output("conteudo-tab", "children"), Input("tabs", "active_tab"))
def render_tab(tab):
    if tab == "serie":
        return dbc.Row([
            dbc.Col([
                html.Label("Dimensão", className="fw-semibold"),
                _radio_dimensao("serie"),
                html.Label("Estados (selecione até 5)", className="fw-semibold mt-3"),
                dcc.Dropdown(
                    id="serie-ufs",
                    options=[{"label": u, "value": u} for u in UFS_DISP],
                    value=["São Paulo", "Bahia", "Maranhão"],
                    multi=True,
                ),
                html.Label("Grupos", className="fw-semibold mt-3"),
                dcc.Checklist(id="serie-grupos", inputStyle={"marginRight": "6px"}),
                html.Hr(),
                html.Small(
                    "Passe o mouse sobre as linhas para ver valores. "
                    "Clique na legenda para mostrar/ocultar grupos.",
                    className="text-muted",
                ),
            ], width=3),
            dbc.Col(dcc.Graph(id="serie-fig", style={"height": "560px"}), width=9),
        ])

    elif tab == "mapa":
        return dbc.Row([
            dbc.Col([
                html.Label("Métrica exibida", className="fw-semibold"),
                dcc.RadioItems(
                    id="mapa-dimensao",
                    options=[
                        {"label": "  Razão Homens ÷ Mulheres", "value": "Sexo"},
                        {"label": "  Razão Branca ÷ Preta",    "value": "Cor/Raça"},
                    ],
                    value="Sexo",
                    inline=False,
                    inputStyle={"marginRight": "4px", "marginLeft": "12px"},
                    className="mb-3",
                ),
                html.Label("Ano", className="fw-semibold"),
                _slider_ano("mapa"),
                html.Div(id="mapa-stats", className="mt-4"),
            ], width=3),
            dbc.Col(dcc.Graph(id="mapa-fig", style={"height": "580px"}), width=9),
        ])

    elif tab == "gap":
        return dbc.Row([
            dbc.Col([
                html.Label("Dimensão", className="fw-semibold"),
                _radio_dimensao("gap"),
                html.Label("Grupo A (diamante)", className="fw-semibold mt-2"),
                dcc.Dropdown(id="gap-grupo-a", clearable=False),
                html.Label("Grupo B (círculo)", className="fw-semibold mt-2"),
                dcc.Dropdown(id="gap-grupo-b", clearable=False),
                html.Label("Ano", className="fw-semibold mt-3"),
                _slider_ano("gap"),
                html.Hr(),
                html.Small(
                    "UFs ordenadas pelo gap absoluto (A − B). "
                    "Cores indicam a região geográfica.",
                    className="text-muted",
                ),
            ], width=3),
            dbc.Col(dcc.Graph(id="gap-fig", style={"height": "720px"}), width=9),
        ])

    elif tab == "slope":
        return dbc.Row([
            dbc.Col([
                html.Label("Dimensão", className="fw-semibold"),
                _radio_dimensao("slope"),
                html.Label("Grupo", className="fw-semibold mt-2"),
                dcc.Dropdown(id="slope-grupo", clearable=False),
                html.Label("Ano inicial", className="fw-semibold mt-2"),
                dcc.Dropdown(
                    id="slope-ano-a",
                    options=[{"label": a, "value": a} for a in ANOS_DISP],
                    value=2015, clearable=False,
                ),
                html.Label("Ano final", className="fw-semibold mt-2"),
                dcc.Dropdown(
                    id="slope-ano-b",
                    options=[{"label": a, "value": a} for a in ANOS_DISP],
                    value=max(ANOS_DISP), clearable=False,
                ),
                html.Label("Regiões", className="fw-semibold mt-3"),
                dcc.Checklist(
                    id="slope-regioes",
                    options=[{"label": f"  {r}", "value": r} for r in CORES_REGIAO],
                    value=list(CORES_REGIAO.keys()),
                    inputStyle={"marginRight": "6px"},
                ),
                html.Hr(),
                html.Small(
                    "Espessura da linha proporcional à variação percentual. "
                    "Cores indicam a região.",
                    className="text-muted",
                ),
            ], width=3),
            dbc.Col(dcc.Graph(id="slope-fig", style={"height": "720px"}), width=9),
        ])


# ─── Callbacks: Seleção cross-tab ────────────────────────────────────────────

@app.callback(
    Output("uf-selecionada", "data"),
    Input("mapa-fig", "clickData"),
    prevent_initial_call=True,
)
def selecionar_uf(click_data):
    if not click_data:
        return None
    return click_data["points"][0].get("hovertext")


@app.callback(
    Output("uf-indicador", "children"),
    Input("uf-selecionada", "data"),
)
def mostrar_indicador(uf):
    if not uf:
        return html.Small(
            "💡 Clique em um estado no mapa para destacá-lo nas demais visualizações.",
            className="text-muted fst-italic",
        )
    sigla = UF_SIGLA.get(uf, "")
    return dbc.Alert(
        [
            html.Strong(f"📍 {uf} ({sigla}) selecionado — "),
            "destacado nas outras abas. Clique em outro estado para mudar.",
        ],
        color="info",
        className="py-1 px-3 mb-0",
        style={"fontSize": "0.875rem"},
    )


# ─── Callbacks: Série Temporal ────────────────────────────────────────────────

@app.callback(
    Output("serie-grupos", "options"),
    Output("serie-grupos", "value"),
    Input("serie-dimensao", "value"),
)
def serie_update_grupos(dimensao):
    grupos = sorted(
        g for g in DF[DF["dimensao"] == dimensao]["grupo"].unique() if g != "Total"
    )
    opts = [{"label": g, "value": g} for g in grupos]
    return opts, grupos


@app.callback(
    Output("serie-fig", "figure"),
    Input("serie-dimensao", "value"),
    Input("serie-ufs", "value"),
    Input("serie-grupos", "value"),
    Input("uf-selecionada", "data"),
)
def serie_update_fig(dimensao, ufs, grupos, uf_sel):
    if not ufs or not grupos:
        return go.Figure()

    # Auto-inclui a UF selecionada caso não esteja na lista
    ufs_efetivos = list(ufs[:5])
    if uf_sel and uf_sel not in ufs_efetivos:
        ufs_efetivos = [uf_sel] + ufs_efetivos[:4]

    df = DF[
        (DF["dimensao"] == dimensao) &
        (DF["uf"].isin(ufs_efetivos)) &
        (DF["grupo"].isin(grupos))
    ].sort_values("ano")

    fig = go.Figure()
    for (uf, grupo), sub in df.groupby(["uf", "grupo"]):
        cor = CORES_GRUPO.get(grupo, "#888")
        destaque = bool(uf_sel and uf == uf_sel)
        idx = ufs_efetivos.index(uf) if uf in ufs_efetivos else 0
        estilo = "solid" if (destaque or idx % 2 == 0) else "dash"
        fig.add_trace(go.Scatter(
            x=sub["ano"], y=sub["rendimento"],
            mode="lines+markers",
            name=f"{'★ ' if destaque else ''}{sub['sigla'].iloc[0]} — {grupo}",
            line=dict(color=cor, width=3 if destaque else 1.5, dash=estilo),
            marker=dict(
                size=8 if destaque else 5,
                line=dict(width=1.5, color="black") if destaque else dict(width=0),
            ),
            opacity=1.0 if (destaque or not uf_sel) else 0.4,
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "Ano: %{x}<br>"
                "R$ %{y:,.0f}<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=f"Rendimento médio mensal real por {dimensao}",
        xaxis_title="Ano",
        yaxis_title="R$ (preços médios do ano)",
        hovermode="x unified",
        template="plotly_dark",
        legend=dict(orientation="v", x=1.01),
    )
    return fig


# ─── Callbacks: Mapa de Disparidade ──────────────────────────────────────────

@app.callback(
    Output("mapa-fig", "figure"),
    Output("mapa-stats", "children"),
    Input("mapa-dimensao", "value"),
    Input("mapa-ano", "value"),
)
def mapa_update(dimensao, ano):
    if dimensao == "Sexo":
        g_a, g_b = "Homens", "Mulheres"
    else:
        g_a, g_b = "Branca", "Preta"

    df = DF[
        (DF["dimensao"] == dimensao) &
        (DF["ano"] == ano) &
        (DF["grupo"].isin([g_a, g_b]))
    ]

    pivot = (
        df.pivot_table(index=["uf", "uf_id_str", "sigla"], columns="grupo", values="rendimento")
        .reset_index()
    )

    if g_a not in pivot.columns or g_b not in pivot.columns:
        return go.Figure(), ""

    pivot = pivot.dropna(subset=[g_a, g_b])
    pivot["razao"] = pivot[g_a] / pivot[g_b]

    try:
        geojson = get_geojson_estados()
    except Exception:
        return go.Figure(layout=dict(title="Erro ao carregar GeoJSON")), ""

    fig = px.choropleth(
        pivot,
        geojson=geojson,
        locations="uf_id_str",
        featureidkey="properties.codigo_ibg",
        color="razao",
        color_continuous_scale="RdYlGn_r",
        range_color=[1.0, min(pivot["razao"].max(), 2.0)],
        hover_name="uf",
        hover_data={
            "uf_id_str": False,
            g_a: ":,.0f",
            g_b: ":,.0f",
            "razao": ":.2f",
        },
        labels={
            "razao": f"Razão {g_a}/{g_b}",
            g_a: f"R$ {g_a}",
            g_b: f"R$ {g_b}",
        },
    )
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(
        title=f"Razão de renda {g_a} ÷ {g_b} por UF — {ano}",
        margin=dict(l=0, r=0, t=40, b=0),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(
            title=f"{g_a}/{g_b}",
            tickformat=".2f",
            len=0.6,
        ),
    )

    med = pivot["razao"].mean()
    max_row = pivot.loc[pivot["razao"].idxmax()]
    min_row = pivot.loc[pivot["razao"].idxmin()]
    stats = html.Div([
        html.P(f"Razão média nacional: {med:.2f}×", className="fw-bold mb-1"),
        html.P(f"Maior gap: {max_row['sigla']} ({max_row['razao']:.2f}×)", className="mb-1 small"),
        html.P(f"Menor gap: {min_row['sigla']} ({min_row['razao']:.2f}×)", className="mb-1 small"),
        html.P(
            f"Significa que {g_a} ganham em média {med:.2f}× mais que {g_b}.",
            className="text-muted small fst-italic",
        ),
    ])
    return fig, stats


# ─── Callbacks: Gap Chart ─────────────────────────────────────────────────────

@app.callback(
    Output("gap-grupo-a", "options"),
    Output("gap-grupo-a", "value"),
    Output("gap-grupo-b", "options"),
    Output("gap-grupo-b", "value"),
    Input("gap-dimensao", "value"),
)
def gap_update_grupos(dimensao):
    grupos = sorted(
        g for g in DF[DF["dimensao"] == dimensao]["grupo"].unique() if g != "Total"
    )
    opts = [{"label": g, "value": g} for g in grupos]
    return opts, grupos[0], opts, grupos[1] if len(grupos) > 1 else grupos[0]


@app.callback(
    Output("gap-fig", "figure"),
    Input("gap-dimensao", "value"),
    Input("gap-grupo-a", "value"),
    Input("gap-grupo-b", "value"),
    Input("gap-ano", "value"),
    Input("uf-selecionada", "data"),
)
def gap_update_fig(dimensao, g_a, g_b, ano, uf_sel):
    if not g_a or not g_b or g_a == g_b:
        return go.Figure()

    df = DF[
        (DF["dimensao"] == dimensao) &
        (DF["ano"] == ano) &
        (DF["grupo"].isin([g_a, g_b]))
    ]
    pivot = (
        df.pivot_table(index=["uf", "sigla", "regiao"], columns="grupo", values="rendimento")
        .reset_index()
    )
    if g_a not in pivot.columns or g_b not in pivot.columns:
        return go.Figure()

    pivot = pivot.dropna(subset=[g_a, g_b])
    pivot["gap"] = pivot[g_a] - pivot[g_b]
    pivot = pivot.sort_values("gap")

    fig = go.Figure()

    # Linhas conectando os dois grupos
    for _, row in pivot.iterrows():
        cor = CORES_REGIAO.get(row["regiao"], "#aaa")
        destaque = bool(uf_sel and row["uf"] == uf_sel)
        fig.add_trace(go.Scatter(
            x=[row[g_b], row[g_a]],
            y=[row["sigla"], row["sigla"]],
            mode="lines",
            line=dict(color=cor, width=4 if destaque else 2),
            opacity=1.0 if (destaque or not uf_sel) else 0.25,
            showlegend=False,
            hoverinfo="skip",
        ))

    # Pontos para cada grupo
    for grupo, simbolo in [(g_b, "circle"), (g_a, "diamond")]:
        for _, row in pivot.iterrows():
            cor = CORES_REGIAO.get(row["regiao"], "#aaa")
            destaque = bool(uf_sel and row["uf"] == uf_sel)
            fig.add_trace(go.Scatter(
                x=[row[grupo]],
                y=[row["sigla"]],
                mode="markers",
                marker=dict(
                    size=14 if destaque else 10,
                    color=cor,
                    symbol=simbolo,
                    line=dict(color="black", width=2) if destaque else dict(width=0),
                ),
                opacity=1.0 if (destaque or not uf_sel) else 0.25,
                showlegend=False,
                hovertemplate=(
                    f"<b>{row['uf']}</b><br>"
                    f"{grupo}: R$ {row[grupo]:,.0f}<br>"
                    f"Gap (A−B): R$ {row['gap']:,.0f}<extra></extra>"
                ),
            ))

    # Entradas de legenda: regiões
    for regiao, cor in CORES_REGIAO.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers+lines",
            marker=dict(size=8, color=cor),
            line=dict(color=cor, width=2),
            name=regiao, legendgroup=regiao,
        ))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
        marker=dict(size=10, symbol="diamond", color="#555"), name=f"{g_a} (diamante)"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
        marker=dict(size=10, symbol="circle", color="#555"), name=f"{g_b} (círculo)"))

    fig.update_layout(
        title=f"Gap de renda: {g_a} vs {g_b} por UF — {ano}",
        xaxis_title="Rendimento médio mensal real (R$)",
        yaxis_title="",
        template="plotly_dark",
        legend_title="Região",
        hovermode="closest",
    )
    return fig


# ─── Callbacks: Slope Chart ───────────────────────────────────────────────────

@app.callback(
    Output("slope-grupo", "options"),
    Output("slope-grupo", "value"),
    Input("slope-dimensao", "value"),
)
def slope_update_grupos(dimensao):
    grupos = sorted(
        g for g in DF[DF["dimensao"] == dimensao]["grupo"].unique() if g != "Total"
    )
    opts = [{"label": g, "value": g} for g in grupos]
    return opts, grupos[0] if grupos else None


@app.callback(
    Output("slope-fig", "figure"),
    Input("slope-dimensao", "value"),
    Input("slope-grupo", "value"),
    Input("slope-ano-a", "value"),
    Input("slope-ano-b", "value"),
    Input("slope-regioes", "value"),
    Input("uf-selecionada", "data"),
)
def slope_update_fig(dimensao, grupo, ano_a, ano_b, regioes, uf_sel):
    if not grupo or ano_a == ano_b or not regioes:
        return go.Figure()

    df = DF[
        (DF["dimensao"] == dimensao) &
        (DF["grupo"] == grupo) &
        (DF["ano"].isin([ano_a, ano_b])) &
        (DF["regiao"].isin(regioes))
    ]
    pivot = (
        df.pivot_table(index=["uf", "sigla", "regiao"], columns="ano", values="rendimento")
        .reset_index()
    )
    if ano_a not in pivot.columns or ano_b not in pivot.columns:
        return go.Figure()

    pivot = pivot.dropna(subset=[ano_a, ano_b])
    pivot["var_pct"] = (pivot[ano_b] - pivot[ano_a]) / pivot[ano_a] * 100

    fig = go.Figure()

    # Desenha UFs não-selecionadas primeiro (ficam abaixo)
    for _, row in pivot.iterrows():
        destaque = bool(uf_sel and row["uf"] == uf_sel)
        if destaque:
            continue  # deixa para o segundo passo
        cor = CORES_REGIAO.get(row["regiao"], "#aaa")
        largura = 1.0 + abs(row["var_pct"]) / 40.0
        fig.add_trace(go.Scatter(
            x=[ano_a, ano_b],
            y=[row[ano_a], row[ano_b]],
            mode="lines+markers+text",
            line=dict(color=cor, width=largura),
            marker=dict(size=7, color=cor),
            text=[row["sigla"], row["sigla"]],
            textposition=["middle left", "middle right"],
            textfont=dict(size=9, color=cor),
            legendgroup=row["regiao"],
            showlegend=False,
            opacity=0.35 if uf_sel else 1.0,
            hovertemplate=(
                f"<b>{row['uf']}</b> — {grupo}<br>"
                f"{ano_a}: R$ {row[ano_a]:,.0f}<br>"
                f"{ano_b}: R$ {row[ano_b]:,.0f}<br>"
                f"Variação: {row['var_pct']:+.1f}%<extra></extra>"
            ),
        ))

    # Desenha a UF selecionada por último (fica no topo)
    if uf_sel:
        sel_rows = pivot[pivot["uf"] == uf_sel]
        for _, row in sel_rows.iterrows():
            cor = CORES_REGIAO.get(row["regiao"], "#333")
            largura = 3.0 + abs(row["var_pct"]) / 40.0
            fig.add_trace(go.Scatter(
                x=[ano_a, ano_b],
                y=[row[ano_a], row[ano_b]],
                mode="lines+markers+text",
                line=dict(color=cor, width=largura),
                marker=dict(
                    size=11, color=cor,
                    line=dict(color="black", width=2),
                ),
                text=[f"★{row['sigla']}", f"★{row['sigla']}"],
                textposition=["middle left", "middle right"],
                textfont=dict(size=11, color="black"),
                legendgroup=row["regiao"],
                showlegend=False,
                hovertemplate=(
                    f"<b>{row['uf']}</b> — {grupo}<br>"
                    f"{ano_a}: R$ {row[ano_a]:,.0f}<br>"
                    f"{ano_b}: R$ {row[ano_b]:,.0f}<br>"
                    f"Variação: {row['var_pct']:+.1f}%<extra></extra>"
                ),
            ))

    for regiao, cor in CORES_REGIAO.items():
        if regiao in regioes:
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode="lines+markers",
                line=dict(color=cor, width=2),
                marker=dict(size=7, color=cor),
                name=regiao,
                legendgroup=regiao,
            ))

    fig.update_layout(
        title=f"Evolução do rendimento — {grupo} | {ano_a} → {ano_b}",
        xaxis=dict(
            tickvals=[ano_a, ano_b],
            ticktext=[str(ano_a), str(ano_b)],
            range=[ano_a - 1.5, ano_b + 1.5],
        ),
        yaxis_title="Rendimento médio mensal real (R$)",
        template="plotly_dark",
        legend_title="Região",
        hovermode="closest",
    )
    return fig


# ─── Inicialização ────────────────────────────────────────────────────────────

server = app.server  # exposto para gunicorn

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, port=port, host="0.0.0.0")
