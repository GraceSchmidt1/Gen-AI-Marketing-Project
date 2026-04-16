import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # load .env secrets into os.environ

from constants import C
from data_loader import load_all, load_segments, DATA_DIR
from tabs import overview, weekly_review, forecast_strategy, utm_standards, content_generator

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hidalga Social Media Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── dark mode (default) ─────────────────────────────── */
    div[data-testid="stMetric"] {
        background: rgba(57,122,114,0.12);
        border: 1px solid #397a72;
        border-radius: 12px; padding: 14px 18px;
    }
    div[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 800; }
    hr { border-color: #397a72 !important; opacity: 0.4; }
    div[data-testid="stTabs"] button { font-size: 15px; font-weight: 600; }

    /* card helper class — used by HTML divs injected via st.markdown */
    .hid-card {
        background: #131c1b;
        border: 1px solid #397a72;
        border-radius: 12px;
        padding: 16px 20px;
    }
    .hid-card-inner {
        background: rgba(57,122,114,0.08);
        border-radius: 8px;
        padding: 10px;
        margin: 8px 0;
    }

    /* ── light mode overrides ────────────────────────────── */
    [data-theme="light"] div[data-testid="stMetric"],
    .light div[data-testid="stMetric"] {
        background: rgba(57,122,114,0.07);
        border: 1px solid #397a72;
    }
    [data-theme="light"] .hid-card,
    .light .hid-card {
        background: #f0faf8;
        border: 1px solid #397a72;
    }
    [data-theme="light"] .hid-card-inner,
    .light .hid-card-inner {
        background: rgba(57,122,114,0.06);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Load data ─────────────────────────────────────────────────────────────────
df_all = load_all()
df_seg = load_segments()
icp_names = ["Oncology Operations Leader", "Oncology Financial Leader",
             "Oncology Technical Leader", "Oncology Clinic Leader"]
if (DATA_DIR / "icp_segments.csv").exists():
    icp_df = pd.read_csv(DATA_DIR / "icp_segments.csv")
    icp_names = icp_df["Name"].tolist()

# Merge segment data into main df
df_all_seg = df_all.merge(
    df_seg[["Date", "Platform", "ICP_Segment", "Content_Pillar", "Conversions"]],
    on=["Date", "Platform"], how="left"
)
df_all_seg["ICP_Segment"]    = df_all_seg["ICP_Segment"].fillna("Untagged")
df_all_seg["Content_Pillar"] = df_all_seg["Content_Pillar"].fillna("Untagged")
df_all_seg["Conversions"]    = df_all_seg["Conversions"].fillna(0)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Hidalga Analytics")
    st.markdown("---")
    st.markdown("### Filters")

    platforms = st.multiselect(
        "Platforms",
        options=["Facebook", "Instagram", "LinkedIn"],
        default=["Facebook", "Instagram", "LinkedIn"],
    )
    min_date = df_all["Date"].min().date()
    max_date = df_all["Date"].max().date()
    date_range = st.date_input(
        "Date Range", value=(min_date, max_date),
        min_value=min_date, max_value=max_date,
    )

    st.markdown("---")
    st.markdown("### AI Model")
    model_choice = st.radio(
        "Backend",
        ["Claude (Anthropic)", "Local — Gemma-4 (LM Studio)"],
        label_visibility="collapsed",
    )
    model_backend = "local" if model_choice == "Local — Gemma-4 (LM Studio)" else "claude"

    if model_backend == "claude":
        sidebar_api_key = st.text_input(
            "Anthropic API Key", type="password",
            placeholder="sk-ant-...",
            help="Or set ANTHROPIC_API_KEY env var",
        )
    else:
        sidebar_api_key = ""
        st.caption(
            "Requires **LM Studio** running on `localhost:1234` "
            "with **Gemma-4 E4B** loaded."
        )

    run_ai = st.button("Generate AI Insights", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("### Canva")
    canva_api_token = st.text_input(
        "Canva Access Token",
        value=os.environ.get("CANVA_ACCESS_TOKEN", ""),
        type="password",
        placeholder="Paste your Canva access token…",
        help="Connect to your company's Canva account to browse brand templates. "
             "Set CANVA_ACCESS_TOKEN in .env to pre-fill.",
    )

# ── Apply overview filters ────────────────────────────────────────────────────
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

df = df_all_seg[
    df_all_seg["Platform"].isin(platforms or ["Facebook", "Instagram", "LinkedIn"])
    & (df_all_seg["Date"].dt.date >= start_date)
    & (df_all_seg["Date"].dt.date <= end_date)
].copy()

# Platform summary (used in AI insights + export)
plat_summary = (
    df.groupby("Platform")
    .agg(Impressions=("Impressions", "sum"), Engagement=("Engagement", "sum"),
         Clicks=("Clicks", "sum"), Posts=("Date", "count"))
    .reset_index()
)

# ── Tab navigation ────────────────────────────────────────────────────────────
tab_overview, tab_weekly, tab_utm, tab_predict, tab_content = st.tabs(
    ["📊 Overview", "📅 Weekly Review", "🔗 UTM Standards", "🔮 Forecast & Strategy", "✍️ Content Generator"]
)

with tab_overview:
    overview.render(df, plat_summary, start_date, end_date, run_ai, sidebar_api_key, model_backend)

with tab_weekly:
    weekly_review.render(df_all_seg)

with tab_predict:
    forecast_strategy.render(df, sidebar_api_key, model_backend)

with tab_utm:
    utm_standards.render()

with tab_content:
    content_generator.render(df, sidebar_api_key, model_backend, canva_api_token=canva_api_token)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='text-align:center;color:{C['muted']};font-size:12px;padding:40px 0 16px 0'>"
    "Hidalga Technologies · Social Media Dashboard · Powered by Streamlit</div>",
    unsafe_allow_html=True,
)
