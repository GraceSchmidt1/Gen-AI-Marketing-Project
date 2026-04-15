import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import llm_client
from constants import (
    C, PLATFORM_COLORS, CARD_BG, CARD_BG_SOLID, BORDER,
    ICP_COLORS, PILLAR_COLORS,
)

SKILLS_DIR = Path(__file__).parent.parent / "skills"
_ANALYTICS_SKILL_PATH = SKILLS_DIR / "marketing-analytics" / "marketing-analytics-skill.skill"


@st.cache_data
def _load_analytics_skill() -> str:
    """Extract and return the SKILL.md content from the marketing-analytics .skill archive."""
    if not _ANALYTICS_SKILL_PATH.exists():
        return ""
    with zipfile.ZipFile(_ANALYTICS_SKILL_PATH, "r") as zf:
        md_entries = [n for n in zf.namelist() if n.endswith("SKILL.md")]
        if not md_entries:
            return ""
        return zf.read(md_entries[0]).decode("utf-8")


def render(df, sidebar_api_key, model_backend="claude"):
    st.markdown(
        f"""<div style="padding:0 0 20px 0">
          <h1 style="margin:0;font-size:26px;font-weight:800;">Forecast &amp; Strategy</h1>
          <p style="margin:4px 0 0 0;color:{C['muted']};font-size:14px">
          Trend projections and content recommendations based on your historical post performance.
          </p></div>""",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("No data loaded. Add your CSV files to the data/ folder.")
        return

    # ── SECTION 1: Platform Performance Forecast ──────────────────────────────
    st.markdown("### 📈 Platform Performance Forecast")
    st.markdown(
        f'<p style="color:{C["muted"]};font-size:13px;margin-top:-8px">'
        "Linear trend projection from weekly aggregated data. Dashed lines show the projected period.</p>",
        unsafe_allow_html=True,
    )

    fc_left, fc_right = st.columns([3, 1])
    with fc_right:
        forecast_metric = st.selectbox(
            "Metric", ["Impressions", "Engagement", "Clicks", "KeyActions"], key="fc_metric"
        )
        forecast_horizon = st.selectbox(
            "Forecast weeks", [2, 4, 6, 8], index=1, key="fc_horizon"
        )
        fc_platforms = st.multiselect(
            "Platforms", ["Facebook", "Instagram", "LinkedIn"],
            default=["Facebook", "Instagram", "LinkedIn"], key="fc_platforms",
        )

    # Build weekly aggregation per platform
    weekly_plat = (
        df.groupby(["WeekStart", "Platform"])[forecast_metric]
        .sum().reset_index().sort_values("WeekStart")
    )

    forecast_summaries = []
    fig_fc = go.Figure()

    with fc_left:
        for platform in fc_platforms:
            pdf = weekly_plat[weekly_plat["Platform"] == platform].copy()
            if len(pdf) < 2:
                continue
            color = PLATFORM_COLORS.get(platform, C["accent"])
            x_dates = pdf["WeekStart"].tolist()
            y_vals  = pdf[forecast_metric].tolist()

            # Fit linear trend on historical data
            x_num  = np.arange(len(y_vals), dtype=float)
            coeffs = np.polyfit(x_num, y_vals, 1)
            trend  = np.poly1d(coeffs)

            # Project forward
            future_dates = [
                pdf["WeekStart"].max() + pd.Timedelta(weeks=i + 1)
                for i in range(forecast_horizon)
            ]
            future_y = [max(0.0, trend(len(y_vals) + i)) for i in range(forecast_horizon)]

            # Historical trace
            fig_fc.add_trace(go.Scatter(
                x=x_dates, y=y_vals, mode="lines+markers", name=platform,
                line=dict(color=color, width=2), marker=dict(size=5),
            ))
            # Forecast trace (connects from last historical point)
            fig_fc.add_trace(go.Scatter(
                x=[x_dates[-1]] + future_dates,
                y=[y_vals[-1]]  + future_y,
                mode="lines+markers", name=f"{platform} (forecast)",
                line=dict(color=color, width=2, dash="dash"),
                marker=dict(size=6, symbol="diamond"),
            ))

            forecast_summaries.append({
                "platform":    platform,
                "color":       color,
                "slope":       coeffs[0],
                "next_week":   round(future_y[0]),
                "end_week":    round(future_y[-1]),
                "current_avg": round(sum(y_vals[-4:]) / min(4, len(y_vals))),
            })

        # Shade forecast region
        if not weekly_plat.empty and forecast_summaries:
            last_hist = weekly_plat["WeekStart"].max()
            fig_fc.add_vrect(
                x0=last_hist,
                x1=last_hist + pd.Timedelta(weeks=forecast_horizon),
                fillcolor="rgba(57,122,114,0.10)", line_width=0,
                annotation_text="Forecast", annotation_position="top left",
                annotation_font_color=C["muted"], annotation_font_size=11,
            )

        fig_fc.update_layout(
            template="plotly_dark",
            paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
            margin=dict(l=0, r=0, t=20, b=0), height=380,
            legend=dict(orientation="h", y=-0.14, x=0),
            xaxis_title=None, yaxis_title=forecast_metric,
            yaxis=dict(tickformat=","),
        )
        if forecast_summaries:
            st.plotly_chart(fig_fc, use_container_width=True)
        else:
            st.info("Need at least 2 weeks of data per platform to generate a forecast.")

    # Forecast summary cards
    if forecast_summaries:
        card_cols = st.columns(len(forecast_summaries))
        for card_col, s in zip(card_cols, forecast_summaries):
            direction  = "▲" if s["slope"] >= 0 else "▼"
            dir_color  = C["green"] if s["slope"] >= 0 else C["red"]
            card_col.markdown(
                f"""<div style="background:{CARD_BG_SOLID};border:1px solid {BORDER};
                    border-radius:12px;padding:14px 18px;margin-top:8px">
                  <div style="font-size:11px;color:{s['color']};text-transform:uppercase;
                       font-weight:700;letter-spacing:.6px">{s['platform']}</div>
                  <div style="font-size:22px;font-weight:800;margin:6px 0 2px 0">
                    {direction} <span style="color:{dir_color}">{abs(round(s['slope'], 1)):,.1f}/wk</span>
                  </div>
                  <div style="font-size:12px;color:{C['muted']}">
                    Next week est.: <strong style="color:{C['accent']}">{s['next_week']:,}</strong>
                  </div>
                  <div style="font-size:12px;color:{C['muted']}">
                    Wk {forecast_horizon} est.: <strong style="color:{C['accent']}">{s['end_week']:,}</strong>
                  </div>
                  <div style="font-size:11px;color:{C['muted']};margin-top:4px">
                    4-wk avg: {s['current_avg']:,}
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

    # ── SECTION 2: Segment × Pillar Optimizer ─────────────────────────────────
    st.markdown("---")
    st.markdown("### 🎯 Segment × Pillar Optimizer")

    has_seg = (
        "ICP_Segment" in df.columns and "Content_Pillar" in df.columns
        and df["ICP_Segment"].notna().any()
    )

    if not has_seg:
        st.info(
            "No ICP segment data found. Tag posts in `data/post_segments.csv` "
            "with ICP_Segment and Content_Pillar to unlock this section."
        )
    else:
        st.markdown(
            f'<p style="color:{C["muted"]};font-size:13px;margin-top:-8px">'
            "Average performance by ICP Segment and Content Pillar. "
            "The brightest cells show your highest-impact combinations.</p>",
            unsafe_allow_html=True,
        )

        seg_df = df.dropna(subset=["ICP_Segment", "Content_Pillar"]).copy()

        opt_c1, opt_c2, opt_c3 = st.columns([1, 1, 2])
        opt_metric = opt_c1.selectbox(
            "Metric", ["Engagement", "Impressions", "Clicks", "KeyActions"], key="opt_metric"
        )
        opt_agg = opt_c2.selectbox("Aggregate", ["Mean per post", "Total"], key="opt_agg")
        opt_plat_filter = opt_c3.multiselect(
            "Filter by platform", sorted(df["Platform"].unique().tolist()),
            default=sorted(df["Platform"].unique().tolist()), key="opt_plat",
        )

        if opt_plat_filter:
            seg_df = seg_df[seg_df["Platform"].isin(opt_plat_filter)]

        agg_fn = "mean" if opt_agg == "Mean per post" else "sum"
        pivot = (
            seg_df.groupby(["ICP_Segment", "Content_Pillar"])[opt_metric]
            .agg(agg_fn).unstack(fill_value=0)
        )

        if not pivot.empty:
            hm_col, rank_col = st.columns(2)

            with hm_col:
                fig_hm = px.imshow(
                    pivot,
                    color_continuous_scale=["#131c1b", "#397a72", "#76e5de", "#ddfab3"],
                    template="plotly_dark",
                    labels=dict(x="Content Pillar", y="ICP Segment", color=opt_metric),
                    text_auto=".0f", aspect="auto",
                )
                fig_hm.update_layout(
                    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                    margin=dict(l=0, r=0, t=30, b=0), height=320,
                    title=dict(
                        text=f"{opt_metric} by Segment × Pillar ({opt_agg})",
                        font=dict(size=13), x=0
                    ),
                    xaxis=dict(tickangle=-30, tickfont=dict(size=10)),
                    yaxis=dict(tickfont=dict(size=10)),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_hm, use_container_width=True)

            with rank_col:
                combo_df = (
                    seg_df.groupby(["ICP_Segment", "Content_Pillar"])
                    .agg(
                        Avg=(opt_metric, "mean"),
                        Total=(opt_metric, "sum"),
                        Posts=("Date", "count"),
                    )
                    .reset_index()
                    .sort_values("Avg", ascending=False)
                    .head(8).reset_index(drop=True)
                )
                combo_df.index += 1
                combo_df.columns = [
                    "ICP Segment", "Content Pillar",
                    f"Avg {opt_metric}", f"Total {opt_metric}", "Posts"
                ]
                st.markdown(f"**Top Combos — Avg {opt_metric} per Post**")
                st.dataframe(
                    combo_df.style.format({
                        f"Avg {opt_metric}": "{:,.1f}",
                        f"Total {opt_metric}": "{:,.0f}",
                    }),
                    use_container_width=True, height=290,
                )

        # Per-platform segment breakdown
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Average Performance by Segment per Platform")
        seg_by_plat = (
            seg_df.groupby(["Platform", "ICP_Segment"])[["Impressions", "Engagement", "Clicks"]]
            .mean().round(1).reset_index()
        )
        available_platforms = sorted(seg_by_plat["Platform"].unique().tolist())
        if available_platforms:
            plat_tabs = st.tabs(available_platforms)
            for pt, pname in zip(plat_tabs, available_platforms):
                with pt:
                    plat_data = (
                        seg_by_plat[seg_by_plat["Platform"] == pname]
                        .sort_values("Engagement", ascending=False)
                    )
                    melted = plat_data.melt(
                        id_vars=["ICP_Segment"],
                        value_vars=["Impressions", "Engagement", "Clicks"],
                    )
                    fig_ps = px.bar(
                        melted, x="ICP_Segment", y="value",
                        color="variable", barmode="group",
                        template="plotly_dark",
                        color_discrete_map={
                            "Impressions": C["accent"],
                            "Engagement":  C["green"],
                            "Clicks":      C["yellow"],
                        },
                        labels={"ICP_Segment": "", "value": "Avg per post", "variable": ""},
                    )
                    fig_ps.update_layout(
                        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                        margin=dict(l=0, r=0, t=10, b=0), height=280,
                        legend=dict(orientation="h", y=1.1, x=0),
                    )
                    st.plotly_chart(fig_ps, use_container_width=True)

    # ── SECTION 3: Content Format Performance ─────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Content Format Performance")
    st.markdown(
        f'<p style="color:{C["muted"]};font-size:13px;margin-top:-8px">'
        "Best-performing content formats by average engagement and reach, per platform. "
        "Only formats with 2+ posts shown.</p>",
        unsafe_allow_html=True,
    )

    fmt_data = (
        df.groupby(["Platform", "Format"])
        .agg(
            Avg_Impressions=("Impressions", "mean"),
            Avg_Engagement =("Engagement",  "mean"),
            Avg_Clicks     =("Clicks",       "mean"),
            Posts          =("Date",         "count"),
        )
        .reset_index()
    )
    fmt_data = fmt_data[fmt_data["Posts"] >= 2].copy()

    fmt_metric_sel = st.selectbox(
        "Metric",
        ["Avg_Engagement", "Avg_Impressions", "Avg_Clicks"],
        format_func=lambda x: x.replace("Avg_", "Avg "),
        key="fmt_metric_sel",
    )

    fmt_cols = st.columns(len(df["Platform"].unique()))
    for col_f, platform in zip(fmt_cols, sorted(df["Platform"].unique())):
        with col_f:
            pdf = (
                fmt_data[fmt_data["Platform"] == platform]
                .sort_values(fmt_metric_sel, ascending=True)
            )
            if pdf.empty:
                continue
            color = PLATFORM_COLORS.get(platform, C["accent"])
            fig_fmt = px.bar(
                pdf, x=fmt_metric_sel, y="Format", orientation="h",
                template="plotly_dark",
                color_discrete_sequence=[color],
                text=fmt_metric_sel,
                labels={fmt_metric_sel: fmt_metric_sel.replace("Avg_", "Avg "), "Format": ""},
            )
            fig_fmt.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_fmt.update_layout(
                paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                margin=dict(l=0, r=70, t=30, b=0),
                height=max(200, 60 + len(pdf) * 44),
                showlegend=False, xaxis_title=None,
                title=dict(text=platform, font=dict(size=13, color=color), x=0),
            )
            st.plotly_chart(fig_fmt, use_container_width=True)

    # ── SECTION 4: Strategic Recommendations ──────────────────────────────────
    st.markdown("---")
    st.markdown("### 💡 Strategic Recommendations")
    st.markdown(
        f'<p style="color:{C["muted"]};font-size:13px;margin-top:-8px">'
        "Data-driven priorities to focus your next content cycle.</p>",
        unsafe_allow_html=True,
    )

    top_eng_rec = top_imp_rec = seg_df_full = None
    if has_seg:
        seg_df_full = df.dropna(subset=["ICP_Segment", "Content_Pillar"]).copy()
        top_eng_rec = (
            seg_df_full.groupby(["ICP_Segment", "Content_Pillar"])["Engagement"]
            .mean().reset_index().sort_values("Engagement", ascending=False)
        )
        top_imp_rec = (
            seg_df_full.groupby(["ICP_Segment", "Content_Pillar"])["Impressions"]
            .mean().reset_index().sort_values("Impressions", ascending=False)
        )

        rec_c1, rec_c2 = st.columns(2)
        with rec_c1:
            st.markdown(
                f'<div style="background:{CARD_BG_SOLID};border:1px solid {BORDER};'
                f'border-radius:12px;padding:16px 20px">',
                unsafe_allow_html=True,
            )
            st.markdown("**🟢 Focus for Engagement**")
            for _, row in top_eng_rec.head(3).iterrows():
                ic = ICP_COLORS.get(row["ICP_Segment"], C["accent"])
                pc = PILLAR_COLORS.get(row["Content_Pillar"], C["muted"])
                st.markdown(
                    f'<div style="margin:8px 0;padding:10px;'
                    f'background:rgba(57,122,114,0.08);border-radius:8px">'
                    f'<span style="color:{ic};font-weight:700">{row["ICP_Segment"]}</span>'
                    f'<span style="color:{C["muted"]}"> × </span>'
                    f'<span style="color:{pc}">{row["Content_Pillar"]}</span><br>'
                    f'<span style="color:{C["green"]};font-size:13px">'
                    f'Avg engagement: <strong>{row["Engagement"]:.1f}</strong></span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)

        with rec_c2:
            st.markdown(
                f'<div style="background:{CARD_BG_SOLID};border:1px solid {BORDER};'
                f'border-radius:12px;padding:16px 20px">',
                unsafe_allow_html=True,
            )
            st.markdown("**📣 Focus for Reach (Impressions)**")
            for _, row in top_imp_rec.head(3).iterrows():
                ic = ICP_COLORS.get(row["ICP_Segment"], C["accent"])
                pc = PILLAR_COLORS.get(row["Content_Pillar"], C["muted"])
                st.markdown(
                    f'<div style="margin:8px 0;padding:10px;'
                    f'background:rgba(57,122,114,0.08);border-radius:8px">'
                    f'<span style="color:{ic};font-weight:700">{row["ICP_Segment"]}</span>'
                    f'<span style="color:{C["muted"]}"> × </span>'
                    f'<span style="color:{pc}">{row["Content_Pillar"]}</span><br>'
                    f'<span style="color:{C["accent"]};font-size:13px">'
                    f'Avg impressions: <strong>{row["Impressions"]:.1f}</strong></span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)

    # Best format per platform cards
    if not fmt_data.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        fmt_rec_cols = st.columns(len(df["Platform"].unique()))
        for col_r, platform in zip(fmt_rec_cols, sorted(df["Platform"].unique())):
            with col_r:
                plat_fmt = (
                    fmt_data[fmt_data["Platform"] == platform]
                    .sort_values("Avg_Engagement", ascending=False)
                    .reset_index(drop=True)
                )
                if plat_fmt.empty:
                    continue
                color = PLATFORM_COLORS.get(platform, C["accent"])
                second_line = (
                    f'<div style="font-size:12px;color:{C["muted"]};margin-top:4px">'
                    f'2nd: <strong>{plat_fmt.iloc[1]["Format"]}</strong></div>'
                    if len(plat_fmt) > 1 else ""
                )
                col_r.markdown(
                    f'<div style="background:{CARD_BG_SOLID};border:1px solid {BORDER};'
                    f'border-radius:12px;padding:16px 18px">'
                    f'<div style="font-size:11px;color:{color};text-transform:uppercase;'
                    f'font-weight:700;letter-spacing:.6px">{platform}</div>'
                    f'<div style="font-size:12px;color:{C["muted"]};margin-top:8px">'
                    f'Best format for engagement:</div>'
                    f'<div style="font-size:18px;font-weight:800;margin:4px 0">'
                    f'{plat_fmt.iloc[0]["Format"]}</div>'
                    f'<div style="font-size:12px;color:{C["green"]}">'
                    f'Avg {plat_fmt.iloc[0]["Avg_Engagement"]:.1f} engagement/post</div>'
                    f'{second_line}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── AI Strategic Analysis ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🤖 AI Strategic Analysis")
    resolved_key = sidebar_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    ai_ready = model_backend == "local" or bool(resolved_key)

    if not ai_ready:
        st.info("Add your Anthropic API key in the sidebar to generate AI-powered strategic recommendations.")
    else:
        if st.button("Generate AI Strategy Report", key="fc_ai_btn"):
            fc_lines = []
            for s in forecast_summaries:
                direction = "upward" if s["slope"] >= 0 else "downward"
                fc_lines.append(
                    f"- {s['platform']}: {direction} trend "
                    f"({s['slope']:+.1f}/wk), next-week est. {s['next_week']:,} {forecast_metric}"
                )

            seg_ctx = imp_ctx = "No segment/pillar data available."
            if has_seg and seg_df_full is not None and not seg_df_full.empty:
                seg_ctx = "\n".join(
                    f"- {r['ICP_Segment']} × {r['Content_Pillar']}: "
                    f"avg engagement {r['Engagement']:.1f}"
                    for _, r in top_eng_rec.head(3).iterrows()
                )
                imp_ctx = "\n".join(
                    f"- {r['ICP_Segment']} × {r['Content_Pillar']}: "
                    f"avg impressions {r['Impressions']:.1f}"
                    for _, r in top_imp_rec.head(3).iterrows()
                )

            fmt_ctx = "\n".join(
                f"- {r['Platform']} — {r['Format']}: avg engagement {r['Avg_Engagement']:.1f}"
                for _, r in fmt_data.sort_values("Avg_Engagement", ascending=False).head(6).iterrows()
            ) if not fmt_data.empty else "No format data."

            skill_context = _load_analytics_skill()

            prompt = f"""Analyze this performance data and give specific, actionable recommendations.

PLATFORM FORECASTS ({forecast_metric}, next {forecast_horizon} weeks):
{chr(10).join(fc_lines) if fc_lines else "Insufficient historical data for forecast."}

TOP SEGMENT × PILLAR COMBOS BY ENGAGEMENT:
{seg_ctx}

TOP SEGMENT × PILLAR COMBOS BY IMPRESSIONS:
{imp_ctx}

TOP CONTENT FORMATS BY AVG ENGAGEMENT:
{fmt_ctx}

Provide exactly:
1. Which 1-2 platforms to prioritize and why (cite the trend data)
2. The top 2 Segment × Pillar combos to double down on
3. The best content format to use per platform
4. One specific tactical recommendation for the next 2 weeks

Be concise and direct. No generic advice — every recommendation must cite specific numbers from the data."""

            label = "Gemma-4 (LM Studio)" if model_backend == "local" else "Claude Opus"
            with st.spinner(f"Generating strategic analysis with {label}…"):
                try:
                    text = llm_client.chat(
                        prompt,
                        system=skill_context,
                        api_key=resolved_key,
                        model_backend=model_backend,
                        claude_model="claude-opus-4-6",
                        max_tokens=900,
                    )
                    st.markdown(text)
                except Exception as e:
                    st.error(f"API error: {e}")
