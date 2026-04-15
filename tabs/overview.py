import io
import os
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
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


def render(df, plat_summary, start_date, end_date, run_ai, sidebar_api_key, model_backend="claude"):
    st.markdown(
        f"""<div style="padding:0 0 20px 0">
          <h1 style="margin:0;font-size:26px;font-weight:800;">Social Media Analytics</h1>
          <p style="margin:4px 0 0 0;color:{C['muted']};font-size:14px">
            Hidalga Technologies &nbsp;·&nbsp;
            {start_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')}
          </p></div>""",
        unsafe_allow_html=True,
    )

    total_impressions = int(df["Impressions"].sum())
    total_engagement  = int(df["Engagement"].sum())
    total_clicks      = int(df["Clicks"].sum())
    total_posts       = len(df)
    eng_rate = (total_engagement / total_impressions * 100) if total_impressions > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Impressions", f"{total_impressions:,}")
    k2.metric("Total Engagement",  f"{total_engagement:,}")
    k3.metric("Total Clicks",      f"{total_clicks:,}")
    k4.metric("Posts Published",   f"{total_posts:,}")
    st.markdown("<br>", unsafe_allow_html=True)

    # Row 1 — Time series + Donut
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown("**Impressions Over Time**")
        ts = df.groupby(["Date", "Platform"])["Impressions"].sum().reset_index()
        fig = px.line(ts, x="Date", y="Impressions", color="Platform",
                      color_discrete_map=PLATFORM_COLORS, template="plotly_dark")
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                          margin=dict(l=0,r=0,t=8,b=0), height=280,
                          legend=dict(orientation="h", y=1.05, x=0),
                          xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**By Platform**")
        fig2 = px.pie(plat_summary, values="Impressions", names="Platform",
                      color="Platform", color_discrete_map=PLATFORM_COLORS,
                      template="plotly_dark", hole=0.6)
        fig2.update_traces(textinfo="percent")
        fig2.update_layout(paper_bgcolor=CARD_BG, margin=dict(l=0,r=0,t=8,b=0), height=280,
                           legend=dict(orientation="h", y=-0.05, x=0.1))
        st.plotly_chart(fig2, use_container_width=True)

    # Row 2 — Engagement bar + Format breakdown
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Engagement by Platform**")
        peng = plat_summary.sort_values("Engagement", ascending=True)
        fig3 = px.bar(peng, x="Engagement", y="Platform", orientation="h",
                      color="Platform", color_discrete_map=PLATFORM_COLORS,
                      template="plotly_dark", text="Engagement")
        fig3.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig3.update_layout(paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                           margin=dict(l=0,r=60,t=8,b=0), height=260,
                           showlegend=False, xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig3, use_container_width=True)
    with c4:
        st.markdown("**Posts by Content Pillar**")
        pillar_df = (df.groupby("Content_Pillar").size().reset_index(name="Count")
                     .sort_values("Count", ascending=True))
        fig4 = px.bar(pillar_df, x="Count", y="Content_Pillar", orientation="h",
                      color="Content_Pillar", color_discrete_map=PILLAR_COLORS,
                      template="plotly_dark", text="Count")
        fig4.update_traces(texttemplate="%{text}", textposition="outside")
        fig4.update_layout(paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                           margin=dict(l=0,r=40,t=8,b=0), height=260,
                           showlegend=False, xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig4, use_container_width=True)

    # Month-over-month
    st.markdown("---")
    st.markdown("### Month-over-Month Comparison")
    monthly = (df.groupby(["Month","MonthLabel"])
               .agg(Impressions=("Impressions","sum"), Engagement=("Engagement","sum"),
                    Posts=("Date","count"))
               .reset_index().sort_values("Month"))
    if len(monthly) >= 2:
        last, prev = monthly.iloc[-1], monthly.iloc[-2]
        def _delta(curr, pv):
            if pv == 0: return ""
            pct = (curr - pv) / pv * 100
            col = C["green"] if pct >= 0 else C["red"]
            arrow = "▲" if pct >= 0 else "▼"
            return f'<span style="color:{col};font-size:13px">{arrow} {abs(pct):.1f}% vs {prev["MonthLabel"]}</span>'
        m1, m2, m3 = st.columns(3)
        for col_st, metric, label in [(m1,"Impressions","Impressions"),(m2,"Engagement","Engagement"),(m3,"Posts","Posts Published")]:
            cv, pv = int(last[metric]), int(prev[metric])
            col_st.markdown(
                f"""<div style="background:{CARD_BG_SOLID};border:1px solid {BORDER};border-radius:12px;padding:16px 20px;">
                  <div style="font-size:11px;color:{C['muted']};text-transform:uppercase;letter-spacing:.6px">{label}</div>
                  <div style="font-size:26px;font-weight:800;color:{C['accent']};margin:6px 0 2px 0">{cv:,}</div>
                  <div style="font-size:12px;color:{C['muted']}">{last['MonthLabel']}</div>
                  <div style="margin-top:4px">{_delta(cv, pv)}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        melt = monthly.melt(id_vars=["MonthLabel"], value_vars=["Impressions","Engagement"],
                            var_name="Metric", value_name="Value")
        fig_m = px.bar(melt, x="MonthLabel", y="Value", color="Metric", barmode="group",
                       template="plotly_dark",
                       color_discrete_map={"Impressions": C["accent"], "Engagement": C["green"]})
        fig_m.update_layout(paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                            margin=dict(l=0,r=0,t=8,b=0), height=300,
                            xaxis_title=None, yaxis_title=None,
                            legend=dict(orientation="h", y=1.08, x=0))
        st.plotly_chart(fig_m, use_container_width=True)
    else:
        st.info("Need data from at least 2 months for month-over-month comparison.")

    # Top posts table
    st.markdown("---")
    st.markdown("### Top Performing Posts")
    sc1, sc2, _ = st.columns([2, 2, 6])
    sort_by = sc1.selectbox("Sort by",
        [c for c in ["Engagement","Impressions","Clicks","KeyActions","Reactions","Likes"]
         if c in df.columns])
    top_n = sc2.slider("Show top", 5, 25, 10)
    base_cols = ["Date","Platform","Format","ICP_Segment","Content_Pillar","Impressions","Clicks","Engagement","KeyActions"]
    extra_cols = [c for c in ["Reactions","Likes","Comments","Shares","Saves","Conversions"]
                  if c in df.columns and df[c].sum() > 0]
    disp_cols = [c for c in base_cols + extra_cols if c in df.columns]
    top_posts = (df[disp_cols].sort_values(sort_by, ascending=False).head(top_n).reset_index(drop=True))
    top_posts.index += 1
    top_posts["Date"] = pd.to_datetime(top_posts["Date"]).dt.strftime("%b %d, %Y")

    def _style_row(row):
        s = [""] * len(row)
        if "Platform" in row.index:
            i = row.index.get_loc("Platform")
            s[i] = f"color: {PLATFORM_COLORS.get(row['Platform'], C['accent'])}; font-weight: bold"
        if "ICP_Segment" in row.index:
            i = row.index.get_loc("ICP_Segment")
            s[i] = f"color: {ICP_COLORS.get(row['ICP_Segment'], C['muted'])}"
        if "Content_Pillar" in row.index:
            i = row.index.get_loc("Content_Pillar")
            s[i] = f"color: {PILLAR_COLORS.get(row['Content_Pillar'], C['muted'])}"
        return s

    _num_fmt = {c: "{:,.0f}" for c in ["Impressions","Clicks","Engagement","KeyActions",
                                        "Reactions","Likes","Comments","Shares","Saves","Conversions"]
                if c in top_posts.columns}
    st.dataframe(top_posts.style.apply(_style_row, axis=1).format(_num_fmt),
                 use_container_width=True, height=min(50 + top_n * 38, 500))

    # AI insights
    st.markdown("---")
    st.markdown("### AI-Generated Insights")
    if run_ai:
        resolved_key = sidebar_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if model_backend == "claude" and not resolved_key:
            st.error("No API key found. Enter it in the sidebar or set ANTHROPIC_API_KEY.")
        else:
            label = "Gemma-4 (LM Studio)" if model_backend == "local" else "Claude Opus"
            with st.spinner(f"Analyzing with {label}..."):
                try:
                    fmt_perf = (df.groupby(["Platform","Format"])
                                .agg(Posts=("Date","count"), AvgEngagement=("Engagement","mean"),
                                     AvgImpressions=("Impressions","mean"))
                                .reset_index().sort_values("AvgEngagement", ascending=False).head(10))
                    seg_perf = (df.groupby("ICP_Segment")
                                .agg(Impressions=("Impressions","sum"), Clicks=("Clicks","sum"),
                                     Engagement=("Engagement","sum"), Posts=("Date","count"))
                                .reset_index())
                    top5 = df.nlargest(5, "Engagement")[["Date","Platform","Format","ICP_Segment","Impressions","Engagement"]].copy()
                    top5["Date"] = pd.to_datetime(top5["Date"]).dt.strftime("%b %d, %Y")

                    pillar_perf = (df.groupby("Content_Pillar")
                                   .agg(Posts=("Date","count"), AvgEngagement=("Engagement","mean"),
                                        AvgImpressions=("Impressions","mean"), Clicks=("Clicks","sum"))
                                   .reset_index().sort_values("AvgEngagement", ascending=False))

                    # Analytics skill is too large for local Gemma context window
                    skill_context = _load_analytics_skill() if model_backend != "local" else ""

                    prompt = f"""Analyze this performance data and provide 4-5 specific, actionable insights.

PERIOD: {df["Date"].min().strftime("%B %d, %Y")} – {df["Date"].max().strftime("%B %d, %Y")}
TOTAL: {total_impressions:,} impressions | {total_engagement:,} engagement | {total_clicks:,} clicks | {total_posts} posts

BY PLATFORM:
{plat_summary.to_string(index=False)}

BY ICP SEGMENT:
{seg_perf.to_string(index=False)}

BY CONTENT PILLAR:
{pillar_perf.to_string(index=False)}

TOP FORMAT PERFORMANCE (avg engagement):
{fmt_perf.to_string(index=False)}

TOP 5 POSTS:
{top5.to_string(index=False)}

Format as numbered list. Each insight: **Bold headline** → 2-3 sentence observation with specific numbers → *Recommendation:* one concrete next step tied to the oncology audience or content pillar strategy.
No preamble. Start with insight 1."""

                    text = llm_client.chat(
                        prompt,
                        system=skill_context,
                        api_key=resolved_key,
                        model_backend=model_backend,
                        claude_model="claude-opus-4-6",
                        max_tokens=1500,
                    )
                    st.markdown(
                        f'<div style="background:{CARD_BG_SOLID};border:1px solid {BORDER};'
                        f'border-radius:12px;padding:24px 28px;line-height:1.8;">'
                        f'{text.replace(chr(10),"<br>")}</div>',
                        unsafe_allow_html=True)
                except Exception as exc:
                    st.error(f"Error: {exc}")
    else:
        if model_backend == "claude":
            st.info("Enter your Anthropic API key in the sidebar and click **Generate AI Insights**.")
        else:
            st.info("Click **Generate AI Insights** in the sidebar (LM Studio must be running on localhost:1234).")

    # Export
    st.markdown("---")
    st.markdown("### Export Data")
    export_df = df.drop(columns=["Month"], errors="ignore").copy()
    export_df["Date"] = pd.to_datetime(export_df["Date"]).dt.strftime("%Y-%m-%d")
    e1, e2, e3 = st.columns(3)
    with e1:
        st.download_button("📥 Download CSV", data=export_df.to_csv(index=False).encode(),
                           file_name=f"hidalga_social_{datetime.now().strftime('%Y%m%d')}.csv",
                           mime="text/csv", use_container_width=True)
    with e2:
        xl = io.BytesIO()
        with pd.ExcelWriter(xl, engine="openpyxl") as w:
            export_df.to_excel(w, sheet_name="All Data", index=False)
            for p in sorted(export_df["Platform"].dropna().unique()):
                export_df[export_df["Platform"] == p].to_excel(w, sheet_name=p, index=False)
            plat_summary.to_excel(w, sheet_name="Summary", index=False)
        st.download_button("📊 Download Excel", data=xl.getvalue(),
                           file_name=f"hidalga_social_{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    with e3:
        top_csv = top_posts.to_csv(index=False).encode()
        st.download_button("🏆 Top Posts CSV", data=top_csv,
                           file_name=f"hidalga_top_{datetime.now().strftime('%Y%m%d')}.csv",
                           mime="text/csv", use_container_width=True)
