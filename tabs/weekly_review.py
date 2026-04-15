from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from constants import C, PLATFORM_COLORS, CARD_BG, CARD_BG_SOLID, BORDER, ICP_COLORS
from data_loader import load_notes, save_notes


def render(df_all_seg):
    st.markdown(
        f'<h2 style="font-size:22px;font-weight:800;margin-bottom:4px">Weekly Performance Review</h2>'
        f'<p style="color:{C["muted"]};font-size:14px;margin-bottom:20px">'
        f'Impressions · Clicks · CTR · Key Actions — by ICP Segment</p>',
        unsafe_allow_html=True,
    )

    # ── Week selector ─────────────────────────────────────────────────────────
    weeks_available = sorted(df_all_seg["WeekStart"].dt.date.unique(), reverse=True)
    week_labels = [f"Week of {w.strftime('%b %d, %Y')}" for w in weeks_available]

    w_col, _, info_col = st.columns([3, 1, 4])
    selected_week_label = w_col.selectbox("Select week", week_labels, index=0)
    selected_week_start = weeks_available[week_labels.index(selected_week_label)]
    selected_week_end   = selected_week_start + timedelta(days=6)

    info_col.markdown(
        f'<div style="background:{CARD_BG_SOLID};border:1px solid {BORDER};border-radius:10px;'
        f'padding:12px 16px;margin-top:4px;font-size:13px;color:{C["muted"]}">'
        f'📅 <strong style="color:{C["accent"]}">{selected_week_start.strftime("%b %d")} – '
        f'{selected_week_end.strftime("%b %d, %Y")}</strong>'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;Review cadence: <strong style="color:{C["accent"]}">Every Wednesday</strong>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Filter to selected week
    dw = df_all_seg[df_all_seg["WeekStart"].dt.date == selected_week_start].copy()

    if dw.empty:
        st.warning("No posts found for this week.")
    else:
        # ── Week KPIs ─────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        w_imp  = int(dw["Impressions"].sum())
        w_clk  = int(dw["Clicks"].sum())
        w_eng  = int(dw["Engagement"].sum())
        w_ka   = int(dw["KeyActions"].sum())
        w_conv = int(dw["Conversions"].sum())
        w_posts = len(dw)
        # CTR: only posts with Clicks capability (FB + LI)
        dw_ctr = dw[dw["Platform"] != "Instagram"]
        w_ctr = (dw_ctr["Clicks"].sum() / dw_ctr["Impressions"].sum() * 100
                 ) if dw_ctr["Impressions"].sum() > 0 else 0.0

        wk1, wk2, wk3, wk4, wk5 = st.columns(5)
        wk1.metric("Impressions",  f"{w_imp:,}")
        wk2.metric("Clicks",       f"{w_clk:,}")
        wk3.metric("CTR",          f"{w_ctr:.2f}%",  help="Facebook + LinkedIn only (Instagram link clicks not exported)")
        wk4.metric("Key Actions",  f"{w_ka:,}",      help="Reactions + Comments + Shares + Clicks + Saves")
        wk5.metric("Conversions",  f"{w_conv:,}",    help="From post_segments.csv — update manually or connect GA4")

        # ── Segment performance table ─────────────────────────────────────────
        st.markdown("---")
        st.markdown("### Performance by ICP Segment")

        seg_week = (
            dw.groupby("ICP_Segment").agg(
                Posts       = ("Date",        "count"),
                Impressions = ("Impressions", "sum"),
                Clicks      = ("Clicks",      "sum"),
                Engagement  = ("Engagement",  "sum"),
                KeyActions  = ("KeyActions",  "sum"),
                Conversions = ("Conversions", "sum"),
            ).reset_index()
        )

        # CTR per segment (exclude IG impressions from denominator per segment)
        seg_ctr_data = (
            dw[dw["Platform"] != "Instagram"]
            .groupby("ICP_Segment")
            .agg(IG_excl_Imp=("Impressions","sum"), IG_excl_Clk=("Clicks","sum"))
            .reset_index()
        )
        seg_week = seg_week.merge(seg_ctr_data, on="ICP_Segment", how="left").fillna(0)
        seg_week["CTR_%"] = seg_week.apply(
            lambda r: round(r["IG_excl_Clk"] / r["IG_excl_Imp"] * 100, 2)
            if r["IG_excl_Imp"] > 0 else 0.0, axis=1
        )
        avg_ctr = seg_week["CTR_%"].mean()

        # Flag over/underperformers
        OVER_THRESH = 1.5
        UNDER_THRESH = 0.5
        MIN_IMP = 10

        def _flag(row):
            if row["Impressions"] < MIN_IMP:
                return "⚠️ Low reach"
            if avg_ctr == 0:
                return ""
            ratio = row["CTR_%"] / avg_ctr if avg_ctr > 0 else 1
            if ratio >= OVER_THRESH:
                return "🟢 Overperformer"
            if ratio <= UNDER_THRESH:
                return "🔴 Underperformer"
            return "✅ On track"

        seg_week["Status"] = seg_week.apply(_flag, axis=1)
        seg_week = seg_week.drop(columns=["IG_excl_Imp","IG_excl_Clk"])

        # Display
        display_seg = seg_week[["ICP_Segment","Posts","Impressions","Clicks","CTR_%",
                                 "Engagement","KeyActions","Conversions","Status"]].copy()
        display_seg = display_seg.rename(columns={"CTR_%": "CTR (%)", "ICP_Segment": "ICP Segment"})

        def _style_seg(row):
            s = [""] * len(row)
            status = row.get("Status", "")
            bg = ""
            if "Overperformer" in str(status):
                bg = "background-color: rgba(52,211,153,0.12)"
            elif "Underperformer" in str(status):
                bg = "background-color: rgba(248,113,113,0.12)"
            elif "Low reach" in str(status):
                bg = "background-color: rgba(251,191,36,0.08)"
            if "ICP Segment" in row.index:
                seg_name = row["ICP Segment"]
                i = row.index.get_loc("ICP Segment")
                s[i] = f"color: {ICP_COLORS.get(seg_name, C['accent'])}; font-weight: bold; {bg}"
            return [bg] * len(s) if bg else s

        st.dataframe(
            display_seg.style.apply(_style_seg, axis=1)
            .format({"CTR (%)": "{:.3f}", "Impressions": "{:,.0f}",
                     "Clicks": "{:,.0f}", "Engagement": "{:,.0f}",
                     "KeyActions": "{:,.0f}", "Conversions": "{:,.0f}"}),
            use_container_width=True, height=220,
        )

        # Threshold legend
        st.markdown(
            f'<div style="font-size:12px;color:{C["muted"]};margin-top:-8px">'
            f'🟢 Overperformer = CTR ≥ {OVER_THRESH:.0f}× weekly avg &nbsp;|&nbsp; '
            f'🔴 Underperformer = CTR ≤ {UNDER_THRESH:.0f}× weekly avg &nbsp;|&nbsp; '
            f'⚠️ Low reach = &lt;{MIN_IMP} impressions &nbsp;|&nbsp; '
            f'Weekly avg CTR (FB+LI): <strong style="color:#e2f0ee">{avg_ctr:.2f}%</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Segment chart ─────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        ch1, ch2 = st.columns(2)
        with ch1:
            fig_seg = px.bar(
                seg_week.sort_values("Impressions", ascending=True),
                x="Impressions", y="ICP_Segment", orientation="h",
                color="ICP_Segment", color_discrete_map=ICP_COLORS,
                template="plotly_dark", text="Impressions",
            )
            fig_seg.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_seg.update_layout(
                paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                margin=dict(l=0,r=60,t=30,b=0), height=300,
                showlegend=False, xaxis_title=None, yaxis_title=None,
                title=dict(text="Impressions by Segment", font=dict(size=13), x=0),
            )
            st.plotly_chart(fig_seg, use_container_width=True)
        with ch2:
            fig_ctr = px.bar(
                seg_week.sort_values("CTR_%", ascending=True),
                x="CTR_%", y="ICP_Segment", orientation="h",
                color="ICP_Segment", color_discrete_map=ICP_COLORS,
                template="plotly_dark", text="CTR_%",
            )
            fig_ctr.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            fig_ctr.update_layout(
                paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                margin=dict(l=0,r=60,t=30,b=0), height=300,
                showlegend=False, xaxis_title=None, yaxis_title=None,
                title=dict(text="CTR (%) by Segment  — FB + LI only", font=dict(size=13), x=0),
            )
            st.plotly_chart(fig_ctr, use_container_width=True)

        # ── Post-level drill-down ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### Post Detail — This Week")

        seg_filter_opts = ["All Segments"] + sorted(dw["ICP_Segment"].unique().tolist())
        seg_filter = st.selectbox("Filter by segment", seg_filter_opts, key="wk_seg_filter")
        dw_detail = dw if seg_filter == "All Segments" else dw[dw["ICP_Segment"] == seg_filter]

        detail_cols = [c for c in ["Date","Platform","Format","ICP_Segment","Content_Pillar",
                                    "Impressions","Clicks","Engagement","KeyActions","Conversions"]
                       if c in dw_detail.columns]
        detail_df = dw_detail[detail_cols].sort_values("Impressions", ascending=False).reset_index(drop=True)
        detail_df.index += 1
        detail_df["Date"] = pd.to_datetime(detail_df["Date"]).dt.strftime("%a, %b %d")

        # Flag individual over/underperformers in the post table
        week_avg_ctr = w_ctr
        def _post_ctr(row):
            if row.get("Platform") == "Instagram":
                return "—"
            imp = row.get("Impressions", 0)
            clk = row.get("Clicks", 0)
            if imp == 0:
                return "0.00%"
            return f"{clk/imp*100:.3f}%"

        detail_df["Post CTR"] = detail_df.apply(_post_ctr, axis=1)

        def _post_status(row):
            if row.get("Platform") == "Instagram":
                return ""
            imp = row.get("Impressions", 0)
            if imp < MIN_IMP:
                return "⚠️"
            try:
                ctr_val = float(str(row.get("Post CTR","0")).replace("%",""))
                if week_avg_ctr > 0:
                    ratio = ctr_val / week_avg_ctr
                    if ratio >= OVER_THRESH: return "🟢"
                    if ratio <= UNDER_THRESH: return "🔴"
            except Exception:
                pass
            return ""
        detail_df[""] = detail_df.apply(_post_status, axis=1)

        _detail_num_fmt = {c: "{:,.0f}" for c in ["Impressions","Clicks","Engagement","KeyActions","Conversions"]
                           if c in detail_df.columns}
        st.dataframe(
            detail_df.style.apply(
                lambda row: [
                    f"color: {PLATFORM_COLORS.get(row.get('Platform',''), C['accent'])}; font-weight:bold"
                    if row.index[i] == "Platform" else
                    f"color: {ICP_COLORS.get(row.get('ICP_Segment',''), C['muted'])}"
                    if row.index[i] == "ICP_Segment" else ""
                    for i in range(len(row))
                ], axis=1
            ).format(_detail_num_fmt),
            use_container_width=True, height=min(60 + len(detail_df) * 38, 420),
        )

        # ── Weekly discussion notes ───────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📝 Weekly Discussion Notes")
        st.markdown(
            f'<p style="color:{C["muted"]};font-size:13px;margin-top:-8px">Review cadence: <strong style="color:#e2f0ee">Every Monday</strong> — discuss prior week results, note anything that materially over/under-performed.</p>',
            unsafe_allow_html=True,
        )

        # Discussion prompts
        with st.expander("💬 Discussion checklist (click to expand)", expanded=False):
            li_pct = int(df_all_seg[df_all_seg['Platform']=='LinkedIn']['Impressions'].sum() / df_all_seg['Impressions'].sum() * 100)
            st.markdown(f"""
**Review these questions each week:**

1. **Standout performers** — Which ICP segment or post had the highest CTR / most key actions? Does it align with the intended content pillar?
2. **Underperformers** — Any 🔴 red flags this week? Root cause: wrong pillar for the audience, format mismatch, or low reach?
3. **Content pillar coverage** — Did we publish across all five pillars this week? Which pillars are underrepresented?
   - Thought Leadership & Industry Insights (LI) · Product Dev & Innovations (LI) · Events & Partnerships (All)
   - Patient-Centered Storytelling (IG/FB) · Team Spotlights & Company Culture (All)
4. **LinkedIn concentration** — LinkedIn drives {li_pct}% of total impressions. Are we reaching Oncology Operations, Financial, and Technical Leaders proportionally?
5. **Clinical audience (IG/FB)** — Is Patient-Centered Storytelling and Team Spotlights content resonating with Oncology Clinic Leaders on Instagram and Facebook?
6. **Conversions** — Did any UTM-tagged posts drive website conversions this week? Update `post_segments.csv` with GA4 data.
7. **Next week** — Which ICP segment needs more focus? Any pillar gaps to fill? Content format to test?
""")

        notes_dict = load_notes()
        week_key = str(selected_week_start)
        existing_note = notes_dict.get(week_key, {}).get("notes", "")

        note_text = st.text_area(
            f"Notes for {selected_week_label}",
            value=existing_note,
            height=140,
            placeholder="Record key observations, decisions, and next steps...",
            key=f"notes_{week_key}",
        )

        n1, n2, _ = st.columns([2, 2, 6])
        if n1.button("💾 Save Notes", key="save_notes", use_container_width=True):
            notes_dict[week_key] = {
                "notes": note_text,
                "week_label": selected_week_label,
                "saved": datetime.now().isoformat(),
            }
            try:
                save_notes(notes_dict)
                st.success("Notes saved.")
            except Exception as e:
                st.warning(f"Could not write to file ({e}). Use Download below.")

        # Download week summary
        summary_lines = [
            f"WEEKLY REVIEW — {selected_week_label}",
            f"Period: {selected_week_start.strftime('%b %d')} – {selected_week_end.strftime('%b %d, %Y')}",
            "",
            "KPIs",
            f"  Impressions : {w_imp:,}",
            f"  Clicks      : {w_clk:,}",
            f"  CTR (FB+LI) : {w_ctr:.2f}%",
            f"  Key Actions : {w_ka:,}",
            f"  Conversions : {w_conv:,}",
            f"  Posts       : {w_posts}",
            "",
            "SEGMENT BREAKDOWN",
        ]
        for _, row in display_seg.iterrows():
            summary_lines.append(
                f"  {row['ICP Segment']:<32} {row['Impressions']:>8,.0f} imp | "
                f"{row['CTR (%)']:>6.2f}% CTR | {row['Status']}"
            )
        summary_lines += ["", "DISCUSSION NOTES", note_text or "(none recorded)", ""]

        n2.download_button(
            "📄 Download Summary",
            data="\n".join(summary_lines).encode(),
            file_name=f"weekly_review_{selected_week_start.strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # ── Historical notes log ──────────────────────────────────────────────────
    all_notes = load_notes()
    if all_notes:
        with st.expander("📋 Previous week notes", expanded=False):
            for wk, entry in sorted(all_notes.items(), reverse=True):
                if isinstance(entry, dict) and entry.get("notes"):
                    st.markdown(
                        f'<div style="margin-bottom:12px">'
                        f'<strong style="color:{C["accent"]}">{entry.get("week_label", wk)}</strong>'
                        f'<span style="color:{C["muted"]};font-size:12px;margin-left:8px">'
                        f'saved {entry.get("saved","")[:10]}</span><br>'
                        f'<span style="font-size:13px">{entry["notes"]}</span></div>',
                        unsafe_allow_html=True,
                    )
