"""Página 2 — Explorar: visualizações aprofundadas, layout compacto (2 por linha)."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import shared as S


def _head(titulo, sub, key=None):
    """Cabeçalho do painel + checkbox opcional 'apenas UFs em destaque'."""
    apenas = False
    if key:
        c1, c2 = st.columns([3, 1])
        c1.markdown(f'<div class="panel-title">{titulo}</div>', unsafe_allow_html=True)
        apenas = c2.checkbox("Só destaque", key=key,
                             help="Mostrar apenas as UFs em destaque selecionadas acima.")
    else:
        st.markdown(f'<div class="panel-title">{titulo}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="panel-sub">{sub}</div>', unsafe_allow_html=True)
    return apenas


def _sec_paridade(dff, d, g_a, g_b, PLOT):
    _head("Ritmo rumo à paridade salarial",
          f"Tendência da razão {g_a}÷{g_b} e tempo projetado até a igualdade (1,00) — "
          "com aderência do ajuste e diferença absoluta como contraprova")
    rp = S.ritmo_paridade(dff, d)
    if rp is None:
        st.info("Sem dados suficientes.")
        return
    full, rec = rp["full"], rp["recente"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Δ razão por ano", f"{full['slope']:+.4f}",
              help="Inclinação da reta ajustada à razão. Negativo = caminhando para a igualdade.")
    m2.metric("Aderência (R²)", f"{full['r2']:.2f}",
              help="Quão bem uma reta descreve a série (1,00 = perfeito). "
                   "Valores baixos tornam a projeção pouco confiável.")
    if full["anos_proj"]:
        m3.metric("Paridade — série completa", f"{full['anos_proj']:.0f} anos",
                  help=f"≈ {full['ano_paridade']:.0f}, mantido o ritmo de 2012–2024.")
    else:
        m3.metric("Paridade — série completa", "não converge",
                  help="A razão está estável ou aumentando.")
    rec_r2 = f" (R² {rec['r2']:.2f})" if rec else ""
    if rec and rec["anos_proj"]:
        m4.metric("Paridade — ritmo recente (5 anos)", f"{rec['anos_proj']:.0f} anos",
                  help=f"≈ {rec['ano_paridade']:.0f}, mantido o ritmo dos últimos 5 anos.{rec_r2}")
    else:
        m4.metric("Paridade — ritmo recente (5 anos)", "não converge",
                  help=f"Razão estável ou subindo nos últimos 5 anos.{rec_r2}")

    cL, cR = st.columns(2)
    with cL:
        st.markdown('<div class="panel-sub">Razão observada + tendência da série e dos '
                    'últimos 5 anos, projetadas no tempo</div>', unsafe_allow_html=True)
        r = rp["serie"]
        horizonte = int(S.ANOS[-1] + 60)
        xs = list(range(int(S.ANOS[0]), horizonte + 1))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(r.index), y=list(r.values), name="razão observada",
            mode="lines+markers", line=dict(color=S.ACCENTS[0], width=3, shape="spline"),
            marker=dict(size=5), hovertemplate="%{x}: %{y:.3f}×<extra></extra>"))
        fig.add_trace(go.Scatter(x=xs, y=[full["intercept"] + full["slope"] * x for x in xs],
            name="tendência (série)", mode="lines",
            line=dict(color="#9AA3B2", width=1.6, dash="dash"), hoverinfo="skip"))
        if rec:
            xr = list(range(int(rec["ano0"] - 4), horizonte + 1))
            fig.add_trace(go.Scatter(x=xr, y=[rec["intercept"] + rec["slope"] * x for x in xr],
                name="tendência (5 anos)", mode="lines",
                line=dict(color="#FF9F1C", width=1.6, dash="dot"), hoverinfo="skip"))
        fig.add_hline(y=1.0, line_dash="dot", line_color="rgba(56,176,0,0.7)",
                      annotation_text="paridade (1,00)", annotation_font_color="#38B000")
        for p, c in [(full, "#9AA3B2"), (rec, "#FF9F1C")]:
            if p and p["ano_paridade"] and p["ano_paridade"] <= horizonte:
                fig.add_vline(x=p["ano_paridade"], line_dash="dot", line_width=1,
                              line_color=c)
        fig = S.fig_base(fig, 330)
        fig.update_yaxes(title="razão", tickformat=".2f")
        st.plotly_chart(fig, width="stretch", config=PLOT)
    with cR:
        st.markdown(f'<div class="panel-sub">Diferença absoluta em R$ ({g_a} − {g_b}) — '
                    'mesmo com a razão caindo, o fosso em reais pode crescer</div>',
                    unsafe_allow_html=True)
        ga = rp["gap_abs"].reindex(S.ANOS)
        cor = S.ACCENTS[2]
        delta_ini_fim = ga.dropna().iloc[-1] - ga.dropna().iloc[0]
        fig = go.Figure(go.Scatter(
            x=S.ANOS, y=ga.values, mode="lines+markers", name="gap R$",
            line=dict(color=cor, width=3, shape="spline"), marker=dict(size=5),
            fill="tozeroy", fillcolor=S.rgba(cor, 0.12),
            hovertemplate="%{x}: R$ %{y:,.0f}<extra></extra>"))
        fig = S.fig_base(fig, 330, legend=False)
        fig.update_yaxes(tickprefix="R$ ", separatethousands=True, rangemode="tozero")
        rumo = "aumentou" if delta_ini_fim > 0 else "diminuiu"
        fig.add_annotation(xref="paper", yref="paper", x=0.5, y=1.06, showarrow=False,
            text=f"De {S.ANOS[0]} a {S.ANOS[-1]} o gap absoluto {rumo} "
                 f"{S.brl(abs(delta_ini_fim))}", font=dict(size=11, color="#C7CDDA"))
        st.plotly_chart(fig, width="stretch", config=PLOT)

    st.markdown(f"<div class='insight'>🔍 <b>Por que os dois cenários divergem?</b> "
                f"{S.explica_paridade(rp)}</div>", unsafe_allow_html=True)

    with st.expander("ℹ️ Como esta projeção é calculada (e seus limites)"):
        st.markdown(
            "- **Razão nacional** = média do rendimento do grupo A entre as UFs ÷ média do grupo B, "
            "ano a ano.\n"
            "- A **reta** é ajustada por mínimos quadrados (OLS) sobre a série da razão; o **R²** "
            "mede o quanto uma linha reta de fato descreve os pontos.\n"
            "- **Anos até a paridade** = quando essa reta cruzaria 1,00, projetando a partir do "
            "último ano. Calculo dois ritmos — **toda a série (2012–2024)** e **últimos 5 anos** — "
            "para mostrar uma *faixa*, não um número único.\n"
            "- **Limites:** é uma **extrapolação linear** — pressupõe que o ritmo passado continue, "
            "ignorando políticas, choques e mudanças de composição. Serve para **dimensionar a "
            "lentidão**, não como previsão exata.\n"
            "- O gráfico do **gap absoluto em R$** é a contraprova: a razão pode cair enquanto a "
            "diferença em reais se mantém ou cresce.")


def render():
    ctx = S.get_filtros()
    d, ano, dff = ctx["dimensao"], ctx["ano"], ctx["dff"]
    grupos, g_a, g_b = ctx["grupos"], ctx["g_a"], ctx["g_b"]
    PLOT = {"displayModeBar": False}

    st.markdown(f"### 🔎 Explorar · {d} · {ano}")
    st.caption("Gráficos aprofundados. Filtros gerais na barra lateral; cada gráfico tem "
               "controles próprios e pode ser restrito às UFs em destaque.")

    ufs_pool = sorted(dff["uf"].unique())
    default_ufs = [u for u in ["São Paulo", "Bahia", "Maranhão", "Rio Grande do Sul",
                               "Distrito Federal"] if u in ufs_pool][:5]
    # Conjunto de destaque compartilhado com o clique no mapa (página Visão geral).
    st.session_state.setdefault(S.DESTAQUE_KEY, default_ufs)
    st.session_state[S.DESTAQUE_KEY] = [u for u in st.session_state[S.DESTAQUE_KEY]
                                        if u in ufs_pool]
    ufs_destaque = st.multiselect(
        "⭐ **UFs em destaque** — sincronizadas com o clique no mapa; usadas na comparação "
        "e disponíveis como filtro em cada gráfico",
        ufs_pool, key=S.DESTAQUE_KEY)
    dsel = set(ufs_destaque)
    st.divider()

    # ── Flagship: Ritmo rumo à paridade (largura total) ───────────────────────
    with st.container(border=True):
        _sec_paridade(dff, d, g_a, g_b, PLOT)

    # ── Comparação entre UFs | Renda × desigualdade ──────────────────────────
    a, b = st.columns(2)
    with a, st.container(border=True):
        ca, cb = st.columns([3, 1])
        ca.markdown('<div class="panel-title">Comparação entre UFs</div>', unsafe_allow_html=True)
        grp_cmp = cb.selectbox("Grupo", grupos, key="x_grp_cmp", label_visibility="collapsed")
        st.markdown('<div class="panel-sub">Evolução do rendimento das UFs em destaque</div>',
                    unsafe_allow_html=True)
        if not ufs_destaque:
            st.info("Selecione ao menos uma UF em destaque.")
        else:
            fig = go.Figure()
            for i, u in enumerate(ufs_destaque):
                cor = list(S.CORES_REGIAO.values())[i % 5]
                s = (dff[(dff.dimensao == d) & (dff.grupo == grp_cmp) & (dff.uf == u)]
                     .set_index("ano")["rendimento"].reindex(S.ANOS))
                fig.add_trace(go.Scatter(
                    x=S.ANOS, y=s.values, name=S.UF2SIGLA[u], mode="lines+markers",
                    line=dict(color=cor, width=2.6, shape="spline"), marker=dict(size=5, color=cor),
                    hovertemplate=f"<b>{u}</b><br>%{{x}}: %{{y:,.0f}}<extra></extra>"))
            fig.add_vline(x=ano, line_width=1, line_dash="dot", line_color="rgba(255,255,255,0.35)")
            fig = S.fig_base(fig, 320)
            fig.update_yaxes(tickprefix="R$ ", separatethousands=True)
            st.plotly_chart(fig, width="stretch", config=PLOT)

    with b, st.container(border=True):
        only = _head("Renda média × desigualdade",
                     f"Cada ponto = UF em {ano} · X = renda total · Y = razão {g_a}÷{g_b}",
                     key="x_sc_only")
        gp = S.gap_por_uf(dff, d, ano)
        tot = (dff[(dff.dimensao == d) & (dff.ano == ano) & (dff.grupo == "Total")]
               [["uf", "rendimento"]].rename(columns={"rendimento": "renda_total"}))
        sc = gp.merge(tot, on="uf", how="left").dropna(subset=["renda_total", "gap"])
        if only:
            sc = sc[sc["uf"].isin(dsel)]
        if sc.empty:
            st.info("Sem dados (verifique as UFs em destaque).")
        else:
            fig = px.scatter(sc, x="renda_total", y="gap", color="regiao", text="sigla",
                color_discrete_map=S.CORES_REGIAO, hover_name="uf",
                labels={"renda_total": "Renda total (R$)", "gap": f"Razão {g_a}÷{g_b}",
                        "regiao": "Região"})
            fig.update_traces(textposition="top center", textfont=dict(size=8, color="#C7CDDA"),
                marker=dict(size=11, line=dict(width=1, color="rgba(255,255,255,0.3)")))
            fig.add_hline(y=1.0, line_dash="dot", line_color="rgba(255,255,255,0.3)")
            if len(sc) >= 3:
                corr = sc["renda_total"].corr(sc["gap"])
                fig.add_annotation(xref="paper", yref="paper", x=0.99, y=0.98,
                    text=f"correlação: {corr:+.2f}", showarrow=False,
                    font=dict(size=11, color="#9AA3B2"))
            fig = S.fig_base(fig, 360)
            fig.update_xaxes(tickprefix="R$ ", separatethousands=True)
            st.plotly_chart(fig, width="stretch", config=PLOT)

    # ── Heatmap | Ranking ─────────────────────────────────────────────────────
    a, b = st.columns(2)
    with a, st.container(border=True):
        only = _head("Heatmap UF × Ano", f"Razão {g_a}÷{g_b} de cada estado", key="x_heat_only")
        gp = S.gap_por_uf(dff, d)
        if only:
            gp = gp[gp["uf"].isin(dsel)]
        if gp.empty:
            st.info("Sem dados (verifique as UFs em destaque).")
        else:
            pivot = gp.pivot_table(index="sigla", columns="ano", values="gap")
            pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]
            vmax = max(pivot.max().max(), 1.6)
            fig = px.imshow(pivot, color_continuous_scale=S.GAP_SCALE, zmin=1.0, zmax=vmax,
                            aspect="auto", text_auto=".2f", labels={"color": "razão", "x": "", "y": ""})
            fig.update_traces(textfont_size=8)
            fig = S.fig_base(fig, max(360, 22 * len(pivot) + 70), legend=False)
            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(side="top", dtick=1, tickfont=dict(size=9))
            st.plotly_chart(fig, width="stretch", config=PLOT)

    with b, st.container(border=True):
        only = _head("Ranking de UFs", f"Para o ano de {ano}", key="x_rank_only")
        r1, r2 = st.columns([3, 1])
        opts = [f"Renda — {g}" for g in grupos] + [f"Razão {g_a}÷{g_b} (gap)"]
        metrica = r1.selectbox("Métrica", opts, key="x_rank_metric", label_visibility="collapsed")
        top_n = r2.slider("Top", 5, 27, 15, key="x_rank_topn", label_visibility="collapsed")
        if metrica.startswith("Razão"):
            base = S.gap_por_uf(dff, d, ano).rename(columns={"gap": "valor"})
            eh_razao = True
        else:
            grp = metrica.split("— ")[1]
            base = (dff[(dff.dimensao == d) & (dff.ano == ano) & (dff.grupo == grp)]
                    [["uf", "sigla", "regiao", "rendimento"]].rename(columns={"rendimento": "valor"}))
            eh_razao = False
        if only and not base.empty:
            base = base[base["uf"].isin(dsel)]
        if base is None or base.empty:
            st.info("Sem dados (verifique as UFs em destaque).")
        else:
            base = base.sort_values("valor", ascending=False).head(top_n).iloc[::-1]
            cores = [("#fff" if u in dsel else S.CORES_REGIAO.get(rg, "#888"))
                     for u, rg in zip(base["uf"], base["regiao"])]
            txt = ([f"{v:.2f}×" for v in base["valor"]] if eh_razao
                   else [S.brl(v) for v in base["valor"]])
            fig = go.Figure(go.Bar(
                x=base["valor"], y=base["sigla"], orientation="h",
                marker=dict(color=cores, line=dict(color="#15181F", width=1)),
                text=txt, textposition="outside", textfont=dict(size=9, color="#C7CDDA"),
                customdata=base["uf"], hovertemplate="<b>%{customdata}</b><br>%{x:,.2f}<extra></extra>"))
            if eh_razao:
                fig.add_vline(x=1.0, line_dash="dot", line_color="rgba(255,255,255,0.4)")
            fig = S.fig_base(fig, max(360, 22 * len(base) + 70), legend=False)
            st.plotly_chart(fig, width="stretch", config=PLOT)

    # ── Bolhas raça×gênero | Slope de ranking ────────────────────────────────
    a, b = st.columns(2)
    with a, st.container(border=True):
        only = _head("Gap racial × gap de gênero",
                     "X = H÷M · Y = Branca÷Preta · tamanho = renda · ▶ anima os anos",
                     key="x_bub_only")
        gm = S.build_gapminder(dff)
        if only:
            gm = gm[gm["uf"].isin(dsel)]
        if gm.empty:
            st.info("Sem dados (verifique as UFs em destaque).")
        else:
            xr = [gm.gap_genero.min() * 0.95, gm.gap_genero.max() * 1.05]
            yr = [gm.gap_raca.min() * 0.95, gm.gap_raca.max() * 1.05]
            fig = px.scatter(gm, x="gap_genero", y="gap_raca", size="renda_total",
                color="regiao", animation_frame="ano_str", animation_group="uf", text="sigla",
                hover_name="uf", color_discrete_map=S.CORES_REGIAO, size_max=50,
                range_x=xr, range_y=yr,
                labels={"gap_genero": "Gap de gênero (H÷M)", "gap_raca": "Gap racial (B÷P)",
                        "regiao": "Região"})
            fig.update_traces(textposition="middle center", textfont=dict(size=7, color="white"),
                marker=dict(opacity=0.8, line=dict(width=1, color="rgba(255,255,255,0.4)")))
            fig.add_hline(y=1.0, line_dash="dot", line_color="rgba(255,255,255,0.2)")
            fig.add_vline(x=1.0, line_dash="dot", line_color="rgba(255,255,255,0.2)")
            fig = S.fig_base(fig, 400)
            st.plotly_chart(fig, width="stretch", config=PLOT)

    with b, st.container(border=True):
        only = _head("Slope de ranking", "Mudança na posição de desigualdade entre dois anos",
                     key="x_slope_only")
        s1, s2 = st.columns(2)
        ano_ini = s1.selectbox("Ano inicial", S.ANOS, index=0, key="x_slope_ini")
        ano_fim = s2.selectbox("Ano final", S.ANOS, index=len(S.ANOS) - 1, key="x_slope_fim")
        top_s = st.slider("Destacar top N", 5, 27, 12, key="x_slope_topn")
        gp = S.gap_por_uf(dff, d)
        if gp.empty or ano_ini == ano_fim:
            st.info("Escolha dois anos diferentes.")
        else:
            aa = gp[gp.ano == ano_ini][["uf", "sigla", "regiao", "gap"]].rename(columns={"gap": "g0"})
            bb = gp[gp.ano == ano_fim][["uf", "gap"]].rename(columns={"gap": "g1"})
            m = aa.merge(bb, on="uf").dropna()
            m["r0"] = m["g0"].rank(ascending=False).astype(int)
            m["r1"] = m["g1"].rank(ascending=False).astype(int)
            if only:
                m = m[m["uf"].isin(dsel)]
            if m.empty:
                st.info("Sem dados (verifique as UFs em destaque).")
            else:
                fig = go.Figure()
                for _, row in m.iterrows():
                    hot = row["r0"] <= top_s or row["r1"] <= top_s or row["uf"] in dsel
                    cor = "#fff" if row["uf"] in dsel else S.CORES_REGIAO.get(row["regiao"], "#888")
                    fig.add_trace(go.Scatter(
                        x=[0, 1], y=[row["r0"], row["r1"]], mode="lines+markers",
                        line=dict(color=cor, width=3 if hot else 0.8),
                        marker=dict(size=8 if hot else 3, color=cor),
                        opacity=1.0 if hot else 0.25, showlegend=False,
                        hovertemplate=(f"<b>{row['uf']}</b><br>{ano_ini}: rank {row['r0']} "
                                       f"({row['g0']:.2f}×)<br>{ano_fim}: rank {row['r1']} "
                                       f"({row['g1']:.2f}×)<extra></extra>")))
                    if hot:
                        fig.add_annotation(x=-0.04, y=row["r0"], text=row["sigla"], xanchor="right",
                                           showarrow=False, font=dict(size=9, color=cor))
                        fig.add_annotation(x=1.04, y=row["r1"], text=row["sigla"], xanchor="left",
                                           showarrow=False, font=dict(size=9, color=cor))
                fig = S.fig_base(fig, 400, legend=False)
                fig.update_xaxes(tickvals=[0, 1], ticktext=[str(ano_ini), str(ano_fim)],
                                 range=[-0.22, 1.22], showgrid=False)
                fig.update_yaxes(autorange="reversed", title="Ranking (1 = maior gap)")
                st.plotly_chart(fig, width="stretch", config=PLOT)

    st.caption("Fonte: PNAD Contínua Anual — SIDRA/IBGE · rendimento médio mensal real · "
               "razões calculadas por UF.")
