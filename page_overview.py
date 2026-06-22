"""Página 1 — Visão geral: leitura simples e clara da desigualdade de renda."""

import plotly.graph_objects as go
import streamlit as st

import shared as S


def render():
    ctx = S.get_filtros()
    d, ano, dff = ctx["dimensao"], ctx["ano"], ctx["dff"]
    grupos, grupos_kpi = ctx["grupos"], ctx["grupos_kpi"]
    g_a, g_b = ctx["g_a"], ctx["g_b"]

    c1, c2 = st.columns([3, 1])
    c1.markdown(f"### Panorama da renda · **{d}** · {ano}")
    c2.markdown(
        f"<div style='text-align:right;color:#8A93A6;font-size:.85rem;padding-top:.6rem'>"
        f"{len(ctx['regioes'])} região(ões) · "
        f"{len(dff[dff.dimensao == d].uf.unique())} UFs</div>",
        unsafe_allow_html=True)
    st.write("")

    # ── KPIs (grid dinâmico, preenche a largura) ──────────────────────────────
    cards = []
    for i, g in enumerate(grupos_kpi):
        cor = S.ACCENTS[i % len(S.ACCENTS)]
        serie = S.serie_nacional(dff, d, g)
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
    razao_serie = S.serie_nacional(dff, d, g_a) / S.serie_nacional(dff, d, g_b)
    razao_val = razao_serie.get(ano, float("nan"))
    share = (1 / razao_val * 100) if (razao_val and razao_val == razao_val) else float("nan")
    cards.append(f"""
        <div class="kpi-card">
          <div class="kpi-icon" style="background:{cor_r}22;color:{cor_r}">÷</div>
          <div class="kpi-mid"><div class="kpi-label">Razão {g_a[:3]}÷{g_b[:3]}</div>
            <div class="kpi-value">{razao_val:.2f}×</div>
            <div class="kpi-delta" style="color:#9AA3B2">{g_b} recebem {share:.0f}%</div></div>
          <div class="kpi-spark">{S.sparkline(razao_serie.tolist(), cor_r)}</div>
        </div>""")
    st.markdown(f'<div class="kpi-grid" style="grid-template-columns:repeat({len(cards)},1fr)">'
                f'{"".join(cards)}</div>', unsafe_allow_html=True)
    st.write("")

    # ── Evolução (nacional, por grupo) + Análise regional ─────────────────────
    col_evo, col_reg = st.columns([1.35, 1])
    with col_evo, st.container(border=True):
        st.markdown('<div class="panel-title">Evolução do rendimento médio</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="panel-sub">Média entre as UFs filtradas, por grupo · '
                    f'{min(S.ANOS)}–{max(S.ANOS)}</div>', unsafe_allow_html=True)
        fig = go.Figure()
        for i, g in enumerate(grupos_kpi):
            cor = S.ACCENTS[i % len(S.ACCENTS)]
            s = S.serie_nacional(dff, d, g)
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
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with col_reg, st.container(border=True):
        st.markdown('<div class="panel-title">Análise regional</div>', unsafe_allow_html=True)
        ano_df = dff[(dff["dimensao"] == d) & (dff["ano"] == ano)]
        piv = ano_df.pivot_table(index=["uf", "sigla", "regiao", "uf_id_str"],
                                 columns="grupo", values="rendimento").reset_index()
        razao_nac = piv[g_a].mean() / piv[g_b].mean() if g_b in piv else float("nan")
        share_nac = (1 / razao_nac * 100) if razao_nac == razao_nac else float("nan")
        rend_nac = piv["Total"].mean() if "Total" in piv else piv[g_a].mean()
        k1, k2 = st.columns(2)
        k1.markdown(f"<div class='big-stat'><div class='big-num' style='color:{S.ACCENTS[0]}'>"
                    f"{razao_nac:.2f}×</div><div class='big-cap'>Razão {g_a}÷{g_b}</div></div>",
                    unsafe_allow_html=True)
        k2.markdown(f"<div class='big-stat'><div class='big-num' style='color:{S.ACCENTS[1]}'>"
                    f"{share_nac:.0f}%</div><div class='big-cap'>{g_b} recebem do que {g_a}</div></div>",
                    unsafe_allow_html=True)
        st.markdown(f"<div class='big-stat' style='text-align:center;margin:.2rem 0 .3rem'>"
                    f"<div class='center-num'>{S.brl(rend_nac)}</div>"
                    f"<div class='big-cap' style='text-align:center'>rendimento médio (Total)</div></div>",
                    unsafe_allow_html=True)
        piv = piv.dropna(subset=[g_a, g_b])
        piv["razao"] = piv[g_a] / piv[g_b]
        mapa = go.Figure(go.Choropleth(
            geojson=S.GJ, locations=piv["uf_id_str"], featureidkey="properties.codigo_ibg",
            z=piv["razao"], text=piv["uf"], colorscale="Inferno",
            marker_line_color="#15181F", marker_line_width=0.6,
            colorbar=dict(title="razão", thickness=10, len=0.85, tickfont=dict(size=9)),
            hovertemplate="<b>%{text}</b><br>razão " + f"{g_a}÷{g_b}: " + "%{z:.2f}×<extra></extra>"))
        mapa.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
        mapa.update_layout(height=240, margin=dict(l=0, r=0, t=0, b=0),
                           paper_bgcolor="rgba(0,0,0,0)", geo=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(mapa, width="stretch", config={"displayModeBar": False})
        reg_tot = ano_df[ano_df["grupo"] == "Total"].groupby("regiao")["rendimento"].mean()
        itens = "".join(
            f"<div class='reg-item'><div class='reg-val' style='color:{S.CORES_REGIAO[r]}'>"
            f"{S.brl(reg_tot[r])}</div><div class='reg-name'>{r}</div></div>"
            for r in S.ORDEM_REGIAO if r in ctx["regioes"] and r in reg_tot.index)
        st.markdown(f"<div class='reg-row'>{itens}</div>", unsafe_allow_html=True)

    # ── Barras por região (uma por grupo) ─────────────────────────────────────
    st.write("")
    cols = st.columns(len(grupos_kpi))
    for i, (g, col) in enumerate(zip(grupos_kpi, cols)):
        cor = S.ACCENTS[i % len(S.ACCENTS)]
        with col, st.container(border=True):
            st.markdown(f'<div class="panel-title">{g}</div>', unsafe_allow_html=True)
            st.markdown('<div class="panel-sub">Rendimento médio por região</div>',
                        unsafe_allow_html=True)
            sub = (dff[(dff.dimensao == d) & (dff.ano == ano) & (dff.grupo == g)]
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
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.caption("Fonte: PNAD Contínua Anual — Tabelas 7444 (sexo) e 7441 (cor/raça) do "
               "SIDRA/IBGE · rendimento médio mensal real · média simples entre UFs.")
