"""
Content Generator tab — uses analytics data to recommend and then generate
on-brand social posts for LinkedIn, Instagram, and Facebook via Claude API.
"""

import os
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

import llm_client
from constants import C, CARD_BG_SOLID, BORDER, ICP_COLORS, PILLAR_COLORS, PLATFORM_COLORS

# ── Skill file paths ───────────────────────────────────────────────────────────
SKILLS_DIR = Path(__file__).parent.parent / "skills"

SKILL_FILES = {
    "LinkedIn":  SKILLS_DIR / "hidalga-linkedin-post.skill",
    "Instagram": SKILLS_DIR / "hidalga-instagram-caption.skill",
    "Facebook":  SKILLS_DIR / "hidalga-facebook-post.skill",
}

ICP_SEGMENTS = [
    "Oncology Operations Leader",
    "Oncology Financial Leader",
    "Oncology Technical Leader",
    "Oncology Clinic Leader",
]

VALUES = [
    "Innovation",
    "Efficiency",
    "Integrity",
    "Accountability",
    "Collaboration",
    "Mission Alignment",
    "Clinic-Centric Focus",
    "Work Culture",
]

PILLARS = [
    "Thought Leadership & Industry Insights",
    "Product Development & Innovations",
    "Events & Partnerships",
    "Patient-Centered Storytelling",
    "Team Spotlights & Company Culture",
]


@st.cache_data
def _load_skill(platform: str) -> str:
    """Extract and return the SKILL.md content from a .skill zip archive."""
    path = SKILL_FILES.get(platform)
    if path is None or not path.exists():
        return ""
    with zipfile.ZipFile(path, "r") as zf:
        # find the SKILL.md entry (platform-agnostic name lookup)
        md_entries = [n for n in zf.namelist() if n.endswith("SKILL.md")]
        if not md_entries:
            return ""
        return zf.read(md_entries[0]).decode("utf-8")


def _top_combos(df: pd.DataFrame, platform: str | None, n: int = 3) -> pd.DataFrame:
    """Return top ICP × Pillar combos by avg engagement for the given platform."""
    sub = df.dropna(subset=["ICP_Segment", "Content_Pillar"])
    sub = sub[sub["ICP_Segment"] != "Untagged"]
    sub = sub[sub["Content_Pillar"] != "Untagged"]
    if platform:
        sub = sub[sub["Platform"] == platform]
    if sub.empty:
        return pd.DataFrame()
    return (
        sub.groupby(["ICP_Segment", "Content_Pillar"])
        .agg(Avg_Engagement=("Engagement", "mean"), Posts=("Date", "count"))
        .reset_index()
        .query("Posts >= 2")
        .sort_values("Avg_Engagement", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def _engagement_rate(df: pd.DataFrame, platform: str) -> float:
    """Overall mean engagement rate for a platform."""
    sub = df[df["Platform"] == platform]
    if sub.empty or sub["Impressions"].sum() == 0:
        return 0.0
    return sub["Engagement"].sum() / sub["Impressions"].sum() * 100


def render(df: pd.DataFrame, sidebar_api_key: str, model_backend: str = "claude") -> None:
    st.markdown(
        f"""<div style="padding:0 0 20px 0">
          <h1 style="margin:0;font-size:26px;font-weight:800;">Content Generator</h1>
          <p style="margin:4px 0 0 0;color:{C['muted']};font-size:14px">
          Generate data-driven social posts for LinkedIn, Instagram, and Facebook —
          recommendations based on your actual engagement history.
          </p></div>""",
        unsafe_allow_html=True,
    )

    resolved_key = sidebar_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    ai_ready = model_backend == "local" or bool(resolved_key)

    if not ai_ready:
        st.warning(
            "Add your Anthropic API key in the sidebar to generate content.",
            icon="🔑",
        )

    # ── Section 1: Data-driven recommendations ────────────────────────────────
    st.markdown("### 📊 What the Data Says to Post Next")
    st.markdown(
        f'<p style="color:{C["muted"]};font-size:13px;margin-top:-8px">'
        "Top-performing ICP Segment × Content Pillar combos from your engagement history. "
        "Use these to inform your next post or accept a recommendation below.</p>",
        unsafe_allow_html=True,
    )

    has_seg = (
        "ICP_Segment" in df.columns
        and df["ICP_Segment"].notna().any()
        and (df["ICP_Segment"] != "Untagged").any()
    )

    rec_platform = None
    rec_segment = None
    rec_pillar = None

    if not has_seg:
        st.info(
            "No ICP segment data found yet. Tag posts in `data/post_segments.csv` "
            "to unlock data-driven recommendations."
        )
    else:
        plat_cols = st.columns(3)
        platform_names = ["Instagram", "Facebook", "LinkedIn"]
        best_combos_by_platform: dict[str, pd.DataFrame] = {}

        for col, plat in zip(plat_cols, platform_names):
            combos = _top_combos(df, plat, n=3)
            best_combos_by_platform[plat] = combos
            color = PLATFORM_COLORS.get(plat, C["accent"])

            with col:
                st.markdown(
                    f'<div style="background:{CARD_BG_SOLID};border:1px solid {color};'
                    f'border-radius:12px;padding:14px 18px;min-height:160px">',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="font-size:11px;color:{color};text-transform:uppercase;'
                    f'font-weight:700;letter-spacing:.7px;margin-bottom:8px">{plat}</div>',
                    unsafe_allow_html=True,
                )
                if combos.empty:
                    st.markdown(
                        f'<div style="color:{C["muted"]};font-size:13px">'
                        "Not enough tagged data yet.</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    for i, row in combos.iterrows():
                        ic = ICP_COLORS.get(row["ICP_Segment"], C["accent"])
                        pc = PILLAR_COLORS.get(row["Content_Pillar"], C["muted"])
                        rank = "#1" if i == 0 else f"#{i+1}"
                        st.markdown(
                            f'<div style="margin:4px 0;padding:8px 10px;'
                            f'background:rgba(57,122,114,0.08);border-radius:8px">'
                            f'<span style="color:{C["muted"]};font-size:10px">{rank} </span>'
                            f'<span style="color:{ic};font-weight:700;font-size:12px">'
                            f'{row["ICP_Segment"]}</span><br>'
                            f'<span style="color:{pc};font-size:11px">{row["Content_Pillar"]}</span>'
                            f'<span style="color:{C["green"]};font-size:11px;float:right">'
                            f'avg {row["Avg_Engagement"]:.0f} eng</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                st.markdown("</div>", unsafe_allow_html=True)

        # Determine overall best recommendation
        all_combos = _top_combos(df, None, n=1)
        if not all_combos.empty:
            # Find which platform has the best ER for the top segment × pillar
            sub = df.dropna(subset=["ICP_Segment", "Content_Pillar"])
            top_seg = all_combos.iloc[0]["ICP_Segment"]
            top_pil = all_combos.iloc[0]["Content_Pillar"]
            plat_er = (
                sub[(sub["ICP_Segment"] == top_seg) & (sub["Content_Pillar"] == top_pil)]
                .groupby("Platform")["Engagement"]
                .mean()
                .idxmax()
                if not sub[
                    (sub["ICP_Segment"] == top_seg) & (sub["Content_Pillar"] == top_pil)
                ].empty
                else "Instagram"
            )
            rec_platform = plat_er
            rec_segment = top_seg
            rec_pillar = top_pil

    st.markdown("---")

    # ── Section 2: Content generation form ────────────────────────────────────
    st.markdown("### ✍️ Generate a Post")

    form_c1, form_c2 = st.columns([1, 1])

    with form_c1:
        platform = st.selectbox(
            "Platform",
            ["LinkedIn", "Instagram", "Facebook"],
            index=(
                ["LinkedIn", "Instagram", "Facebook"].index(rec_platform)
                if rec_platform in ["LinkedIn", "Instagram", "Facebook"]
                else 0
            ),
            key="cg_platform",
        )

        topic = st.text_area(
            "Topic / Post Idea",
            placeholder="e.g. We just closed a new clinic partnership in Texas",
            height=90,
            key="cg_topic",
        )

        value = st.selectbox(
            "Value to Highlight (optional — leave blank to auto-select)",
            ["— auto-select —"] + VALUES,
            key="cg_value",
        )

    with form_c2:
        # ICP segment — pre-fill from recommendation if available
        seg_default = (
            ICP_SEGMENTS.index(rec_segment) + 1
            if rec_segment in ICP_SEGMENTS
            else 0
        )
        segment = st.selectbox(
            "ICP Segment (optional — pre-filled from data)",
            ["— auto-select —"] + ICP_SEGMENTS,
            index=seg_default,
            key="cg_segment",
        )

        # Content pillar — pre-fill from recommendation
        pil_default = (
            PILLARS.index(rec_pillar) + 1
            if rec_pillar in PILLARS
            else 0
        )
        pillar = st.selectbox(
            "Content Pillar (optional — pre-filled from data)",
            ["— auto-select —"] + PILLARS,
            index=pil_default,
            key="cg_pillar",
        )

        # Show current data signal for chosen platform + segment + pillar
        if has_seg and segment != "— auto-select —" and pillar != "— auto-select —":
            sub = df.dropna(subset=["ICP_Segment", "Content_Pillar"])
            match = sub[
                (sub["Platform"] == platform)
                & (sub["ICP_Segment"] == segment)
                & (sub["Content_Pillar"] == pillar)
            ]
            overall_mean = (
                sub[sub["Platform"] == platform]["Engagement"].mean()
                if not sub[sub["Platform"] == platform].empty
                else 0
            )
            if not match.empty and overall_mean > 0:
                combo_avg = match["Engagement"].mean()
                ratio = combo_avg / overall_mean
                signal = (
                    "HIGH signal" if ratio >= 1.5
                    else "LOW signal" if ratio < 0.5
                    else "MID signal"
                )
                sig_color = (
                    C["green"] if ratio >= 1.5
                    else C["red"] if ratio < 0.5
                    else C["yellow"]
                )
                st.markdown(
                    f'<div style="background:rgba(57,122,114,0.08);border:1px solid {BORDER};'
                    f'border-radius:8px;padding:10px 14px;margin-top:8px">'
                    f'<span style="font-size:12px;color:{C["muted"]}">Data signal for this combo on {platform}:</span><br>'
                    f'<span style="font-size:15px;font-weight:700;color:{sig_color}">{signal}</span>'
                    f'<span style="font-size:12px;color:{C["muted"]}"> — avg engagement {combo_avg:.0f} '
                    f'vs. platform mean {overall_mean:.0f} ({match.shape[0]} posts)</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            elif not match.empty:
                st.markdown(
                    f'<div style="font-size:12px;color:{C["muted"]};margin-top:8px">'
                    f'{match.shape[0]} post(s) found for this combo on {platform}.'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="font-size:12px;color:{C["muted"]};margin-top:8px">'
                    f'No historical data for this combo on {platform} yet.</div>',
                    unsafe_allow_html=True,
                )

    generate_btn = st.button(
        "Generate Post",
        type="primary",
        disabled=not ai_ready or not topic.strip(),
        key="cg_generate",
    )

    if not topic.strip() and not generate_btn:
        st.caption("Enter a topic above to generate content.")

    # ── Section 3: Generation ─────────────────────────────────────────────────
    if generate_btn:
        if model_backend == "claude" and not resolved_key:
            st.error("API key required. Add it in the sidebar.")
            return
        if not topic.strip():
            st.error("Please enter a topic.")
            return

        skill_md = _load_skill(platform)
        if not skill_md:
            st.error(f"Could not load skill file for {platform}. Check the skills/ directory.")
            return

        # Strip frontmatter from skill (--- ... ---) before using as system prompt
        import re
        skill_body = re.sub(r"^---\n.*?\n---\n", "", skill_md, flags=re.DOTALL).strip()

        # Build the user message
        user_parts = [f"Topic: {topic.strip()}"]
        if value != "— auto-select —":
            user_parts.append(f"Value to highlight: {value}")
        if segment != "— auto-select —":
            user_parts.append(f"ICP segment: {segment}")
        if pillar != "— auto-select —":
            user_parts.append(f"Content pillar: {pillar}")

        # Append the data signal as context if we have it
        if has_seg:
            combos = _top_combos(df, platform, n=3)
            if not combos.empty:
                lines = [
                    f"  - {r['ICP_Segment']} × {r['Content_Pillar']}: "
                    f"avg engagement {r['Avg_Engagement']:.0f} ({int(r['Posts'])} posts)"
                    for _, r in combos.iterrows()
                ]
                user_parts.append(
                    "Data context — top-performing combos on "
                    + platform
                    + " based on engagement history:\n"
                    + "\n".join(lines)
                )

        user_msg = "\n".join(user_parts)

        label = "Gemma-4 (LM Studio)" if model_backend == "local" else "Claude"
        with st.spinner(f"Generating {platform} post with {label}…"):
            try:
                generated = llm_client.chat(
                    user_msg,
                    system=skill_body,
                    api_key=resolved_key,
                    model_backend=model_backend,
                    claude_model="claude-sonnet-4-6",
                    max_tokens=1500,
                )
            except Exception as e:
                st.error(f"API error: {e}")
                return

        st.markdown("---")
        st.markdown(
            f'<div style="font-size:11px;color:{C["muted"]};margin-bottom:6px">'
            f'Generated for <strong style="color:{PLATFORM_COLORS.get(platform, C["accent"])}">'
            f'{platform}</strong> · ICP: {segment} · Pillar: {pillar}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(generated)

        # Copy-friendly expander
        with st.expander("Copy raw text"):
            st.code(generated, language=None)
