"""Página 1 — Visão geral: leitura simples e clara da desigualdade de renda."""

import plotly.graph_objects as go
import streamlit as st

import shared as S


@st.dialog(" ", width="large")
def _zoom(titulo, sub, draw):
    """Lightbox: mostra o conteúdo do painel ampliado, com animação suave (CSS)."""
    st.markdown(f"<div class='zoom-title'>{titulo}</div>", unsafe_allow_html=True)
    if sub:
        st.markdown(f"<div class='zoom-sub'>{sub}</div>", unsafe_allow_html=True)
    draw()


def _titulo(titulo, sub, key, draw):
    """Título de painel clicável: clique → abre o zoom (lightbox). draw() = conteúdo ampliado."""
    if st.button(f"{titulo}  ⤢", key=f"z_{key}", type="tertiary",
                 help="Clique para ampliar"):
        _zoom(titulo, sub, draw)
    if sub:
        st.markdown(f'<div class="panel-sub">{sub}</div>', unsafe_allow_html=True)


def _grande(fig, altura=620):
    """Devolve uma cópia da figura redimensionada para o zoom."""
    f = go.Figure(fig)
    f.update_layout(height=altura)
    return f


def render():
    ctx = S.get_filtros()
    d, ano, dff = ctx["dimensao"], ctx["ano"], ctx["dff"]
    grupos, grupos_kpi = ctx["grupos"], ctx["grupos_kpi"]
    g_a, g_b = ctx["g_a"], ctx["g_b"]

    sel = [u for u in S.destaque_atual() if u in set(dff["uf"])]
    # Estados selecionados no mapa viram o recorte de toda a página (média dos selecionados).
    dff_sel = dff[dff["uf"].isin(sel)] if sel else dff
    sel_label = ", ".join(S.UF2SIGLA.get(u, u) for u in sel)

    c1, c2 = st.columns([3, 1])
    titulo = f"### Panorama da renda · **{d}** · {ano}"
    if sel:
        titulo += f" · recorte: **{sel_label}**"
    c1.markdown(titulo)
    n_ufs = len(dff_sel[dff_sel.dimensao == d].uf.unique())
    recorte = f"{n_ufs} UF(s) selecionada(s)" if sel else f"{n_ufs} UFs"
    c2.markdown(
        f"<div style='text-align:right;color:#8A93A6;font-size:.85rem;padding-top:.6rem'>"
        f"{len(ctx['regioes'])} região(ões) · {recorte}</div>",
        unsafe_allow_html=True)
    st.write("")

    # ── KPIs (grid dinâmico, preenche a largura) ──────────────────────────────
    cards = []
    for i, g in enumerate(grupos_kpi):
        cor = S.ACCENTS[i % len(S.ACCENTS)]
        serie = S.serie_nacional(dff_sel, d, g)
        valor = serie.get(ano, float("nan"))
        anteriores = [a for a in S.ANOS if a < ano and serie.get(a) == serie.get(a)]
        prev = serie.get(max(anteriores)) if anteriores else float("nan")
        delta = (valor - prev) / prev * 100 if (prev and prev == prev) else None
        if delta is None:
            dhtml = ""
        else:
            sinal, dcor = ("▲", "#1DD1A1") if delta >= 0 else ("▼", "#FF5C7A")
            dhtml = (f"<div class='kpi-delta' style='color:{dcor}'>"
                     f"{sinal} {abs(delta):.1f}% vs ano ant.</div>")
        cards.append(f"""
            <div class="kpi-card">
              <div class="kpi-icon" style="background:{cor}22;color:{cor}">{S.ICONES.get(g,'●')}</div>
              <div class="kpi-mid"><div class="kpi-label">{g}</div>
                <div class="kpi-value">{S.brl(valor)}</div>{dhtml}</div>
              <div class="kpi-spark">{S.sparkline(serie.tolist(), cor)}</div>
            </div>""")

    cor_r = S.ACCENTS[3]
    razao_serie = S.serie_nacional(dff_sel, d, g_a) / S.serie_nacional(dff_sel, d, g_b)
    razao_val = razao_serie.get(ano, float("nan"))
    share = (1 / razao_val * 100) if (razao_val and razao_val == razao_val) else float("nan")
    cards.append(f"""
        <div class="kpi-card">
          <div class="kpi-icon" style="background:{cor_r}22;color:{cor_r}">÷</div>
          <div class="kpi-mid"><div class="kpi-label">Razão {g_a[:3]}÷{g_b[:3]}</div>
            <div class="kpi-value">{razao_val:.2f}×</div>
            <div class="kpi-delta" style="color:#9AA3B2">{S.grupo_frase(g_b, inicio=True)} recebem {share:.0f}% do que {S.grupo_frase(g_a)}</div></div>
          <div class="kpi-spark">{S.sparkline(razao_serie.tolist(), cor_r)}</div>
        </div>""")
    st.markdown(f'<div class="kpi-grid" style="grid-template-columns:repeat({len(cards)},1fr)">'
                f'{"".join(cards)}</div>', unsafe_allow_html=True)
    st.write("")

    # ── Evolução (nacional, por grupo) + Análise regional ─────────────────────
    col_evo, col_reg = st.columns([1.35, 1])
    with col_evo, st.container(border=True):
        sub_evo = (f'Média de {sel_label}, por grupo' if sel
                   else 'Média entre as UFs filtradas, por grupo')
        sub_evo = f'{sub_evo} · {min(S.ANOS)}–{max(S.ANOS)}'
        fig = go.Figure()
        for i, g in enumerate(grupos_kpi):
            cor = S.ACCENTS[i % len(S.ACCENTS)]
            s = S.serie_nacional(dff_sel, d, g)
            fig.add_trace(go.Scatter(
                x=S.ANOS, y=s.values, name=g, mode="lines+markers",
                line=dict(color=cor, width=3, shape="spline"),
                marker=dict(size=6, color=cor),
                fill="tozeroy", fillcolor=S.rgba(cor, 0.10),
                hovertemplate=f"<b>{g}</b><br>%{{x}}: %{{y:,.0f}}<extra></extra>"))
        fig.add_vline(x=ano, line_width=1, line_dash="dot",
                      line_color="rgba(255,255,255,0.35)")
        fig = S.fig_base(fig, 330)
        fig.update_yaxes(tickprefix="R$ ", separatethousands=True)
        _titulo("Evolução do rendimento médio", sub_evo, "evo",
                lambda: st.plotly_chart(_grande(fig), width="stretch",
                                        config={"displayModeBar": False}))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with col_reg, st.container(border=True):
        ano_df = dff[(dff["dimensao"] == d) & (dff["ano"] == ano)]  # todos os estados (seletor)
        piv = ano_df.pivot_table(index=["uf", "sigla", "regiao", "uf_id_str"],
                                 columns="grupo", values="rendimento").reset_index()
        # estatísticas sobre o recorte selecionado (ou nacional, se nada selecionado)
        ano_sel = dff_sel[(dff_sel["dimensao"] == d) & (dff_sel["ano"] == ano)]
        ps = ano_sel.pivot_table(index="uf", columns="grupo", values="rendimento")
        razao_nac = ps[g_a].mean() / ps[g_b].mean() if g_b in ps else float("nan")
        share_nac = (1 / razao_nac * 100) if razao_nac == razao_nac else float("nan")
        rend_nac = ps["Total"].mean() if "Total" in ps else ps[g_a].mean()
        stat1 = (f"<div class='big-stat'><div class='big-num' style='color:{S.ACCENTS[0]}'>"
                 f"{razao_nac:.2f}×</div><div class='big-cap'>Razão {S.grupo_frase(g_a)} ÷ "
                 f"{S.grupo_frase(g_b)}</div></div>")
        stat2 = (f"<div class='big-stat'><div class='big-num' style='color:{S.ACCENTS[1]}'>"
                 f"{share_nac:.0f}%</div><div class='big-cap'>é quanto {S.grupo_frase(g_b)} "
                 f"recebem do que {S.grupo_frase(g_a)} ganham</div></div>")
        stat3 = (f"<div class='big-stat' style='text-align:center;margin:.2rem 0 .3rem'>"
                 f"<div class='center-num'>{S.brl(rend_nac)}</div>"
                 f"<div class='big-cap' style='text-align:center'>rendimento médio (Total)</div></div>")
        reg_tot = ano_sel[ano_sel["grupo"] == "Total"].groupby("regiao")["rendimento"].mean()
        itens = "".join(
            f"<div class='reg-item'><div class='reg-val' style='color:{S.CORES_REGIAO[r]}'>"
            f"{S.brl(reg_tot[r])}</div><div class='reg-name'>{r}</div></div>"
            for r in S.ORDEM_REGIAO if r in ctx["regioes"] and r in reg_tot.index)
        reg_html = f"<div class='reg-row'>{itens}</div>"
        piv = piv.dropna(subset=[g_a, g_b])
        piv["razao"] = piv[g_a] / piv[g_b]
        mapa = go.Figure(go.Choropleth(
            geojson=S.GJ, locations=piv["uf_id_str"], featureidkey="properties.codigo_ibg",
            z=piv["razao"], text=piv["uf"], colorscale="Inferno",
            marker_line_color="#15181F", marker_line_width=0.6,
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)),
            colorbar=dict(title="razão", thickness=10, len=0.85, tickfont=dict(size=9)),
            hovertemplate="<b>%{text}</b><br>razão " + f"{g_a}÷{g_b}: " + "%{z:.2f}×<extra></extra>"))
        if sel:
            psel = piv[piv["uf"].isin(sel)]
            mapa.add_trace(go.Choropleth(
                geojson=S.GJ, locations=psel["uf_id_str"],
                featureidkey="properties.codigo_ibg", z=[1] * len(psel),
                showscale=False, colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                marker_line_color="#FFFFFF", marker_line_width=2.4, hoverinfo="skip"))
        # Pontos clicáveis (Scattergeo) — seleção de Choropleth não chega ao Streamlit.
        cent = [S.UF_CENTROIDES.get(u) for u in piv["uf"]]
        pm = piv[[c is not None for c in cent]].copy()
        cent = [c for c in cent if c is not None]
        sel_set = set(sel)
        mapa.add_trace(go.Scattergeo(
            lon=[c[0] for c in cent], lat=[c[1] for c in cent], mode="markers",
            customdata=list(zip(pm["uf"], pm["razao"])),
            marker=dict(
                size=[15 if u in sel_set else 9 for u in pm["uf"]],
                color=["#00E5FF" if u in sel_set else "rgba(255,255,255,0.85)" for u in pm["uf"]],
                line=dict(width=1, color="#15181F")),
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)),
            hovertemplate="<b>%{customdata[0]}</b><br>razão "
                          + f"{g_a}÷{g_b}: " + "%{customdata[1]:.2f}×<extra>clique p/ destacar</extra>"))
        mapa.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
        mapa.update_layout(height=240, margin=dict(l=0, r=0, t=0, b=0),
                           clickmode="event+select",
                           paper_bgcolor="rgba(0,0,0,0)", geo=dict(bgcolor="rgba(0,0,0,0)"))

        def _draw_reg():
            st.plotly_chart(_grande(mapa, 540), width="stretch",
                            config={"displayModeBar": False})
            z1, z2, z3 = st.columns(3)
            z1.markdown(stat1, unsafe_allow_html=True)
            z2.markdown(stat2, unsafe_allow_html=True)
            z3.markdown(stat3, unsafe_allow_html=True)
            st.markdown(reg_html, unsafe_allow_html=True)
        _titulo("Análise regional", None, "reg", _draw_reg)

        k1, k2 = st.columns(2)
        k1.markdown(stat1, unsafe_allow_html=True)
        k2.markdown(stat2, unsafe_allow_html=True)
        st.markdown(stat3, unsafe_allow_html=True)
        st.caption("💡 Clique no ponto de um estado para realçá-lo em todos os gráficos e na "
                   "aba Explorar (clique de novo para remover).")
        nonce = st.session_state.get("_ov_map_nonce", 0)
        ev = st.plotly_chart(mapa, width="stretch", on_select="rerun",
                             key=f"ov_mapa_{nonce}", config={"displayModeBar": False})
        if S.consumir_selecao_do_mapa(ev):
            st.session_state["_ov_map_nonce"] = nonce + 1  # widget novo zera a seleção
            st.rerun()
        if sel:
            chips = " · ".join(S.UF2SIGLA.get(u, u) for u in sel)
            cc1, cc2 = st.columns([3, 1])
            cc1.markdown(f"<div class='big-cap'>Destacando: <b>{chips}</b></div>",
                         unsafe_allow_html=True)
            if cc2.button("Limpar", key="ov_limpar", use_container_width=True):
                S.limpar_destaque()
                st.rerun()
        st.markdown(reg_html, unsafe_allow_html=True)

    # ── Barras por região (uma por grupo) ─────────────────────────────────────
    st.write("")
    cols = st.columns(len(grupos_kpi))
    for i, (g, col) in enumerate(zip(grupos_kpi, cols)):
        cor = S.ACCENTS[i % len(S.ACCENTS)]
        with col, st.container(border=True):
            sub = (dff_sel[(dff_sel.dimensao == d) & (dff_sel.ano == ano) & (dff_sel.grupo == g)]
                   .groupby("regiao")["rendimento"].mean())
            ordem = [r for r in S.ORDEM_REGIAO if r in sub.index]
            vals = [sub[r] for r in ordem]
            fig = go.Figure(go.Bar(
                x=ordem, y=vals, marker=dict(color=cor),
                text=[S.brl(v) for v in vals], textposition="outside",
                textfont=dict(size=10, color="#C7CDDA"),
                hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>"))
            fig = S.fig_base(fig, 240, legend=False)
            fig.update_yaxes(visible=False, range=[0, max(vals) * 1.25 if vals else 1])
            fig.update_xaxes(tickfont=dict(size=10))
            _titulo(g, "Rendimento médio por região", f"bar_{g}",
                    lambda f=fig: st.plotly_chart(_grande(f, 560), width="stretch",
                                                  config={"displayModeBar": False}))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.caption("Fonte: PNAD Contínua Anual — Tabelas 7444 (sexo) e 7441 (cor/raça) do "
               "SIDRA/IBGE · rendimento médio mensal real · média simples entre UFs.")
