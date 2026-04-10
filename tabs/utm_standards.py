from datetime import datetime
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

from constants import C


def render():
    st.markdown(
        f'<h2 style="font-size:22px;font-weight:800;margin-bottom:4px">UTM Naming Standards</h2>'
        f'<p style="color:{C["muted"]};font-size:14px;margin-bottom:20px">'
        f'Consistent UTM tagging enables accurate conversion attribution in GA4. '
        f'Apply to every link posted across all platforms.</p>',
        unsafe_allow_html=True,
    )

    # ── Standards reference ───────────────────────────────────────────────────
    st.markdown("### Parameter Reference")

    standards = {
        "utm_source": {
            "Rule": "Lowercase platform name — no spaces",
            "Allowed Values": "`linkedin` · `facebook` · `instagram`",
            "Example": "`linkedin`",
            "Notes": "Never use 'LinkedIn' or 'LI'",
        },
        "utm_medium": {
            "Rule": "Channel type with hyphen",
            "Allowed Values": "`organic-social` · `paid-social`",
            "Example": "`organic-social`",
            "Notes": "Paid posts use `paid-social`",
        },
        "utm_campaign": {
            "Rule": "`[year]-[quarter]-[initiative]`",
            "Allowed Values": "Free text — lowercase, hyphens only",
            "Example": "`2026-q2-thought-leadership` · `2026-q2-product-launch` · `2026-q1-revenue-cycle`",
            "Notes": "Use consistent initiative names across quarters; align to content pillar where possible",
        },
        "utm_content": {
            "Rule": "`[format]-[icp-short]`",
            "Allowed Values": "See ICP short codes below",
            "Example": "`image-ops` · `video-technical` · `carousel-clinical` · `link-financial`",
            "Notes": "Identifies both creative type and target ICP segment",
        },
        "utm_term": {
            "Rule": "Oncology topic keyword (optional)",
            "Allowed Values": "Lowercase, hyphens, no spaces",
            "Example": "`prior-auth` · `denial-reduction` · `ehr-integration` · `treatment-delays`",
            "Notes": "Use for A/B testing oncology-specific messaging themes",
        },
    }

    rows_std = [
        {"Parameter": k, **v} for k, v in standards.items()
    ]
    st.dataframe(pd.DataFrame(rows_std).set_index("Parameter"),
                 use_container_width=True, height=240)

    # ICP short codes
    st.markdown("### ICP Short Codes for `utm_content`")
    icp_codes = pd.DataFrame([
        {"ICP Segment": "Oncology Operations Leader", "Short Code": "ops",       "Primary Platforms": "LI, FB, IG", "Example content tag": "image-ops"},
        {"ICP Segment": "Oncology Financial Leader",  "Short Code": "financial", "Primary Platforms": "LI",         "Example content tag": "link-financial"},
        {"ICP Segment": "Oncology Technical Leader",  "Short Code": "technical", "Primary Platforms": "LI",         "Example content tag": "video-technical"},
        {"ICP Segment": "Oncology Clinic Leader",     "Short Code": "clinical",  "Primary Platforms": "IG, FB",     "Example content tag": "carousel-clinical"},
    ])
    st.dataframe(icp_codes.set_index("ICP Segment"), use_container_width=True, height=200)

    # Examples table
    st.markdown("### Example Tagged URLs by Platform")
    base = "https://hidalga.com/solutions"
    examples = [
        ("LinkedIn", "organic-social", "2026-q2-thought-leadership", "image-ops",       "prior-auth"),
        ("LinkedIn", "organic-social", "2026-q2-product-launch",     "video-technical",  "ehr-integration"),
        ("LinkedIn", "organic-social", "2026-q1-revenue-cycle",      "link-financial",   "denial-reduction"),
        ("Facebook", "organic-social", "2026-q2-patient-stories",    "carousel-clinical","treatment-delays"),
        ("Instagram","organic-social", "2026-q2-team-culture",       "image-clinical",   ""),
    ]
    example_rows = []
    for src, med, camp, cont, term in examples:
        params = {"utm_source": src.lower(), "utm_medium": med,
                  "utm_campaign": camp, "utm_content": cont}
        if term:
            params["utm_term"] = term
        tagged = f"{base}?{urlencode(params)}"
        example_rows.append({"Platform": src, "utm_campaign": camp, "utm_content": cont, "Tagged URL": tagged})

    st.dataframe(pd.DataFrame(example_rows), use_container_width=True, height=220)

    # ── UTM Builder ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### UTM URL Builder")

    b1, b2 = st.columns([1, 1])

    with b1:
        base_url   = st.text_input("Base URL", value="https://hidalga.com/",
                                   placeholder="https://hidalga.com/page")
        utm_source = st.selectbox("utm_source (platform)", ["linkedin", "facebook", "instagram"])
        utm_medium = st.selectbox("utm_medium", ["organic-social", "paid-social"])

        current_q  = f"q{((datetime.now().month - 1) // 3) + 1}"
        utm_campaign = st.text_input(
            "utm_campaign",
            value=f"{datetime.now().year}-{current_q}-brand",
            help="Format: [year]-[quarter]-[initiative]",
        )

    with b2:
        fmt_opts   = ["image", "video", "carousel", "link", "simple-status", "multi-image"]
        icp_opts   = ["ops", "financial", "technical", "clinical"]
        sel_fmt    = st.selectbox("Content format (for utm_content)", fmt_opts)
        sel_icp    = st.selectbox("ICP short code (for utm_content)", icp_opts)
        utm_content = st.text_input("utm_content (auto-built, editable)",
                                    value=f"{sel_fmt}-{sel_icp}")
        utm_term   = st.text_input("utm_term (optional keyword)", value="",
                                   placeholder="ai-solutions")

    if base_url:
        params = {
            "utm_source":   utm_source,
            "utm_medium":   utm_medium,
            "utm_campaign": utm_campaign,
            "utm_content":  utm_content,
        }
        if utm_term.strip():
            params["utm_term"] = utm_term.strip()

        separator = "&" if "?" in base_url else "?"
        tagged_url = base_url.rstrip("?&") + separator + urlencode(params)

        st.markdown("**Generated URL**")
        st.code(tagged_url, language=None)

        st.markdown("**Parameter breakdown**")
        param_df = pd.DataFrame([{"Parameter": k, "Value": v} for k, v in params.items()])
        st.dataframe(param_df.set_index("Parameter"), use_container_width=True, height=220)

        cp1, cp2 = st.columns([2, 8])
        cp1.download_button(
            "📋 Copy as CSV",
            data=param_df.to_csv(index=False).encode(),
            file_name="utm_params.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── How-to guide ─────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📘 How to implement UTM tracking end-to-end", expanded=False):
        st.markdown(f"""
**1. Tag every link before scheduling**
Use the builder above before pasting links into Loomly. Never post an untagged link to a trackable page.

**2. Update `data/post_segments.csv` with conversions weekly**
After reviewing GA4 each Monday, record conversions for the prior week in the CSV:
```
Date,Platform,ICP_Segment,Conversions
2026-03-24,LinkedIn,Enterprise Decision Makers,3
```

**3. GA4 setup — custom dimensions**
In GA4 → Admin → Custom Definitions, add:
- `utm_content` as a session-scoped dimension
- `utm_campaign` as a session-scoped dimension

This lets you filter conversions by ICP segment (`utm_content` contains `enterprise`, `smb`, etc.).

**4. Weekly attribution query (GA4 Explore)**
Dimensions: `Session source`, `Session medium`, `Session campaign`, `Session content`
Metrics: `Sessions`, `Conversions`, `Revenue` (if applicable)
Filter: `Session medium` = `organic-social` OR `paid-social`

**5. Connect GA4 to this dashboard (future)**
Replace the manual Conversions column in `post_segments.csv` with a GA4 API integration using the `google-analytics-data` Python library.
""")
