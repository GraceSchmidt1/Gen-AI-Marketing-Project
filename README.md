# Hidalga Marketing Dashboard
### AI-Powered Social Media Analytics & Content Generation
**Final Project — Generative AI Course, Vanderbilt University**

---

## Table of Contents
1. [Problem Statement & Overview](#1-problem-statement--overview)
2. [Methodology](#2-methodology)
3. [Implementation & Demo](#3-implementation--demo)
4. [Assessment & Evaluation](#4-assessment--evaluation)
5. [Model & Data Cards](#5-model--data-cards)
6. [Critical Analysis](#6-critical-analysis)
7. [Documentation & Resource Links](#7-documentation--resource-links)
8. [Appendix: Skill File Reference](#appendix-skill-file-reference)

---

## 1. Problem Statement & Overview

Hidalga Technologies is an oncology software company that publishes content across LinkedIn, Facebook, and Instagram through Loomly. Despite a consistent publishing cadence, the team had no systematic way to answer two critical questions:

- Which posts are actually working — and for which audience segment?
- How do we turn that performance data into better content decisions?

The raw Loomly exports are messy CSVs with inconsistent column formats across platforms, no audience tagging, and no connection between analytics and content creation. Marketing decisions were made by intuition rather than data.

This project solves that end-to-end: clean the data, define the audiences, analyze performance by segment, forecast trends, and close the loop back to AI-assisted content generation — all in a single Streamlit dashboard.

---

## 2. Methodology

### Course Concepts Applied

| Course Concept | Where Applied in This Project |
|---|---|
| Prompt Engineering (role prompting, structured prompts) | Two-layer skill-file architecture in Content Generator |
| Chain-of-Thought / Structured Output | Skill files guide model reasoning step-by-step through brand rules before generating output |
| RAG / Context Injection | Marketing reference documents injected as system-prompt context at inference time |
| Multi-modal / Multi-backend LLM routing | `llm_client.py` routes between Claude API and local Gemma 4 via LM Studio |
| Feature Engineering | Derived fields (`Engagement`, `KeyActions`, `WeekStart`) computed in ETL pipeline |
| Regression / Predictive Modeling | Linear regression forecasting in Forecast & Strategy tab |
| Persona / ICP Segmentation | Four buyer personas defined and used to segment and evaluate post performance |
| Ethical AI & Bias Considerations | Forbidden words, human-review gate, PHI exclusion, attribution transparency |
| Data Cards & Model Cards | Documented in Section 5 following standard ML disclosure practices |

---

### 2.1 Data Cleaning & Normalization

A custom ETL pipeline (`data_loader.py`) reads three platform-specific Loomly CSVs and normalizes them into a unified dataframe. Each platform exports data in a different shape:

- **Facebook:** reactions, comments, shares, clicks
- **Instagram:** engagement totals and saves (no link clicks — Loomly limitation)
- **LinkedIn:** reactions, comments, shares, clicks, and engagement rate

The loader aligns column names, computes derived fields (`Engagement`, `KeyActions`, `WeekStart`), and uses `st.cache_data` for fast rerenders. This applies data preprocessing and feature engineering concepts from the course.

### 2.2 ICP Segmentation Framework

Rather than treating all posts as targeting a generic audience, four Ideal Customer Profile (ICP) segments were defined based on Hidalga's actual buyer personas in oncology:

| ICP Segment | Roles | Primary Motivations |
|---|---|---|
| Oncology Operations Leader | Practice admins, COOs | Operational reliability, staffing efficiency |
| Oncology Financial Leader | Revenue cycle managers, CFOs | Denial rates, cash flow, billing accuracy |
| Oncology Technical Leader | IT directors, CIOs, CISOs | FHIR compliance, integration stability, security |
| Oncology Clinic Leader | Medical directors, lead oncologists | Workflow efficiency, fewer clicks, clinical outcomes |

Five content pillars were also defined and mapped to brand colors: Thought Leadership & Industry Insights, Product Development & Innovations, Events & Partnerships, Patient-Centered Storytelling, and Team Spotlights & Company Culture. Each post is tagged with an ICP segment and content pillar via `data/post_segments.csv`.

### 2.3 Statistical Forecasting

The Forecast & Strategy tab applies linear regression to weekly aggregated performance data per platform and projects it forward 2–8 weeks. Historical data is shown as solid lines; projections appear as dashed lines with confidence bounds. This applies regression-based forecasting techniques from the course to a real business problem.

### 2.4 Prompt Engineering & Skill-Based Content Generation

The Content Generator tab uses a two-layer prompt architecture:

- **Layer 1 — Reference context:** The `hidalga-marketing-reference` skill file injects brand voice, forbidden words, tone standards, ICP personas, and content pillar definitions as the system prompt.
- **Layer 2 — Platform skills:** A platform-specific skill file (LinkedIn, Instagram, or Facebook) is stacked on top, providing channel-specific formatting, tone, and structural rules.

The user's brief becomes the user message. This separation of reference context from task instruction is a direct application of structured prompt engineering and role prompting from the course.

### 2.5 Multi-Backend LLM Routing

`llm_client.py` abstracts routing between two AI backends:

- **Claude (Anthropic API)** — `claude-opus-4-6` for cloud-based generation with full skill context injection
- **Local Gemma-4 (LM Studio)** — Gemma 4 E4B running via LM Studio's OpenAI-compatible endpoint on `localhost:1234`, operating fully offline with no API key required

---

## 3. Implementation & Demo

### 3.1 Setup Instructions

**Requirements:** Python 3.9+, pip

```bash
git clone https://github.com/[your-username]/Gen-AI-Marketing-Project
cd Gen-AI-Marketing-Project
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`.

**For AI features with Claude**, set your API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**For local AI (no API key required):** Open LM Studio, load Gemma 4 E4B, start the server on port 1234, and select *Local — Gemma-4* in the sidebar.

### 3.2 Demo Walkthrough

A recommended path for demonstrating the project end-to-end:

1. **Overview tab** — show the KPI cards and platform breakdown charts; click "Generate AI Insights" to demonstrate live LLM summarization of the data
2. **Weekly Review tab** — pick a post flagged as an underperformer (red indicator), drill into its segment and pillar, and use the notes field to record a follow-up action
3. **Forecast & Strategy tab** — walk through the regression projections for LinkedIn; click "Generate Strategy Memo" to show AI synthesis of the forecast into a recommended plan
4. **Content Generator tab** — enter a brief (e.g., "Write a LinkedIn post announcing our new oncology billing module"), select an ICP segment, and generate output using both Claude and Local Gemma to compare results
5. **UTM Standards tab** — demonstrate the URL builder auto-populating UTM parameters from a campaign name

### 3.3 Skills Integration — Pseudocode

The Content Generator is the core AI pipeline. It has two distinct algorithmic flows: **skill assembly** (how context is built) and **LLM routing** (how that context is delivered to a model). Both are shown below as pseudocode, with references to the actual source files.

#### Flow 1: Skill Context Assembly (`tabs/content_generator.py`)

```
FUNCTION assemble_system_prompt(platform, model_backend):

    # Step 1 — Load the platform-specific skill file (.skill = renamed .zip)
    skill_zip = open("skills/hidalga-{platform}-post.skill")
    skill_body = extract("SKILL.md" from skill_zip)
    skill_body = strip_frontmatter(skill_body)   # remove YAML --- block

    # Step 2 — For Claude only: prepend the shared marketing reference context
    #           (Gemma's context window is too small to hold both files)
    IF model_backend != "local":
        ref_zip = open("skills/hidalga-marketing-reference.skill")
        brand_doc   = extract("references/brand-and-values.md" from ref_zip)
        icp_doc     = extract("references/icp-and-content-pillars.md" from ref_zip)
        system_prompt = brand_doc + "---" + icp_doc + "---" + skill_body
    ELSE:
        system_prompt = skill_body   # Gemma gets platform skill only

    RETURN system_prompt


FUNCTION build_user_message(topic, platform, segment, pillar, value, df):

    parts = ["Topic: " + topic]

    IF value selected:      parts.append("Value to highlight: " + value)
    IF segment selected:    parts.append("ICP segment: " + segment)
    IF pillar selected:     parts.append("Content pillar: " + pillar)

    # Step 3 — Append live engagement data as context signal
    top_combos = get_top_ICP_pillar_combos(df, platform, n=3)
    IF top_combos not empty:
        parts.append("Top-performing combos on " + platform + ":\n" + format(top_combos))

    RETURN join(parts, "\n")
```

#### Flow 2: LLM Routing (`llm_client.py`)

```
FUNCTION chat(user_msg, system_prompt, model_backend, api_key):

    IF model_backend == "local":

        # Gemma via LM Studio — OpenAI-compatible REST endpoint, no API key
        # System prompt folded into the user message (Gemma has no system role)
        content  = system_prompt + "\n---\n" + user_msg
        messages = [{ role: "user", content: content }]

        response = POST "http://localhost:1234/v1/chat/completions"
                        body: { model: GEMMA_MODEL_ID, messages, max_tokens }
        RETURN response["choices"][0]["message"]["content"]

    ELSE:  # "claude"

        # Claude via Anthropic SDK — system and user roles are separate
        client   = Anthropic(api_key)
        response = client.messages.create(
                       model    = "claude-sonnet-4-6",
                       system   = system_prompt,      # injected as dedicated system role
                       messages = [{ role: "user", content: user_msg }],
                       max_tokens = 1500
                   )
        RETURN response.content[0].text
```

**Why the two-layer system matters:** The skill files separate *what the brand is* (reference layer: voice, personas, forbidden words) from *how to write for this channel* (platform layer: LinkedIn character limits, Instagram hashtag rules, etc.). Stacking them at inference time means either layer can be updated independently without touching the other — a direct application of the separation-of-concerns principle to prompt engineering.

### 3.4 Dashboard Tabs

| Tab | Description |
|---|---|
| **Overview** | KPI cards, time-series impressions chart, platform breakdown, top-posts table, month-over-month comparison, AI insights |
| **Weekly Review** | Segment performance flags (🟢 Overperformer / 🔴 Underperformer / ⚠️ Low reach), post drill-down, saved notes, downloadable summary |
| **UTM Standards** | UTM naming convention reference and URL builder with auto-population |
| **Forecast & Strategy** | Linear regression projections, ICP × pillar recommendations, AI strategy memo |
| **Content Generator** | Skill-based post generation for LinkedIn, Instagram, and Facebook |

### 3.5 Project Structure

```
Gen-AI-Marketing-Project/
├── app.py                            # Main Streamlit app — tabs, sidebar, data merge
├── data_loader.py                    # CSV cleaning, normalization, caching
├── constants.py                      # Hidalga brand colors, ICP colors, pillar colors
├── llm_client.py                     # Abstracts Claude API vs. LM Studio routing
├── requirements.txt
├── data/
│   ├── Facebook-data(data-cleaned).csv
│   ├── Instagram-data(data-cleaned).csv
│   ├── linkedin-data(data-cleaned).csv
│   ├── icp_segments.csv
│   ├── post_segments.csv
│   └── weekly_notes.json
├── tabs/
│   ├── overview.py
│   ├── weekly_review.py
│   ├── utm_standards.py
│   ├── forecast_strategy.py
│   └── content_generator.py
└── skills/
    ├── hidalga-linkedin-post.skill
    ├── hidalga-instagram-caption.skill
    ├── hidalga-facebook-post.skill
    ├── hidalga-marketing-reference/
    │   ├── hidalga-marketing-reference.skill
    │   └── references/
    │       ├── brand-and-values.md
    │       ├── icp-and-content-pillars.md
    │       ├── social-strategy-sop.md
    │       ├── workflow-and-tools.md
    │       ├── canva-image-sop.md
    │       ├── video-content-sop.md
    │       └── conversion-sprint-template.md
    └── marketing-analytics/
        ├── marketing-analytics-skill.skill
        └── references/
            └── icp-segments.md
```

---

## 4. Assessment & Evaluation

### 4.1 Model Architecture

| Property | Details |
|---|---|
| **Cloud Model** | `claude-opus-4-6` (Anthropic) |
| **Model Family** | Claude 4 series — instruction-following, long-context, tool-use capable |
| **Context Window** | 200K tokens (sufficient to inject full skill context + post data) |
| **Local Model** | Gemma 4 E4B (Google DeepMind) via LM Studio |
| **Local Interface** | OpenAI-compatible REST endpoint on `localhost:1234` |
| **Routing** | `llm_client.py` abstracts both backends behind a shared interface |

### 4.2 Licenses

| Model / Component | License |
|---|---|
| `claude-opus-4-6` (Anthropic) | Proprietary — [Anthropic Usage Policy](https://www.anthropic.com/legal/usage-policy); API access requires key; no redistribution of model weights |
| Gemma 4 E4B (Google DeepMind) | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) — free for research and commercial use with attribution; model weights distributable under Gemma license |
| This project codebase | MIT License — open for educational and commercial reuse with attribution |
| Loomly CSV exports | Proprietary Hidalga Technologies data — not included in the public repository; sample/anonymized data provided for demo purposes |

### 4.3 Intended Uses

- **Primary use:** Internal marketing tool for Hidalga Technologies to analyze social media performance and generate on-brand content
- **Secondary use:** Reference implementation for AI-assisted marketing dashboards in B2B SaaS contexts
- **Not intended for:** Automated publishing without human review, medical advice generation, or patient data processing

### 4.4 Ethical Considerations & Bias

**ICP Segmentation Bias**
Assigning posts to audience segments relies on manual tagging in `post_segments.csv`. Systematic tagging errors could skew recommendations toward certain segments. Mitigation: the Weekly Review tab includes a checklist prompt to review whether all four segments received coverage each week.

**AI Content Generation**
Generated posts reflect the biases present in the underlying model (`claude-opus-4-6` or Gemma 4 E4B). The skill files include explicit forbidden words and tone standards to reduce the risk of generating content inconsistent with Hidalga's values or inappropriate for an oncology audience. All generated content requires human review before publishing.

**Data Privacy**
The dashboard processes only aggregated public post metrics exported from Loomly. No patient data, PHI, or personally identifiable information is processed at any point.

**Attribution Accuracy**
Conversion counts in `post_segments.csv` are manually entered from GA4 and subject to attribution error. The UTM Standards tab provides a systematic framework to improve attribution accuracy over time.

---

## 5. Model & Data Cards

### 5.1 Model Card

| Property | Details |
|---|---|
| **Model Name** | `claude-opus-4-6` |
| **Developer** | Anthropic |
| **Version** | Claude 4 series |
| **Access** | Anthropic API — requires `ANTHROPIC_API_KEY` |
| **License** | Proprietary — [Anthropic usage policy](https://www.anthropic.com/legal/usage-policy) applies |
| **Intended Use** | Post generation, analytics summarization, strategy memos |
| **Limitations** | May reflect training data biases; not domain-tuned for oncology |
| **Secondary Model** | Gemma 4 E4B (Google DeepMind) via LM Studio |
| **Gemma License** | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) — free for research and commercial use with attribution |
| **Gemma Use Case** | Offline fallback; smaller context window, no skill injection |

### 5.2 Data Card

| File | Source | Contents |
|---|---|---|
| `Facebook-data(data-cleaned).csv` | Loomly export | Post metrics: reactions, comments, shares, clicks |
| `Instagram-data(data-cleaned).csv` | Loomly export | Post metrics: engagement totals, saves |
| `linkedin-data(data-cleaned).csv` | Loomly export | Post metrics: reactions, comments, shares, clicks, engagement rate |
| `icp_segments.csv` | Manually defined | ICP segment names, buyer roles, motivations, pillar affinities |
| `post_segments.csv` | Manually tagged | ICP segment, content pillar, GA4 conversion count per post |
| `weekly_notes.json` | App-generated | Weekly discussion notes; auto-created on first save |

> **To update data:** Export new CSVs from Loomly in the same column format, replace the files in `data/`, and restart the app. The `st.cache_data` cache reloads automatically.

---

## 6. Critical Analysis

### 6.1 Impact

This dashboard transforms a fragmented, intuition-driven marketing process into a structured, data-informed one. The most concrete impact: the team can now answer "which ICP segment and content pillar combination drives the most engagement on LinkedIn this month" in under 30 seconds, rather than manually pivoting a CSV export. The Weekly Review tab institutionalizes a Monday review process that previously had no consistent format. The Content Generator closes the loop from analytics to publishing without leaving the tool.

### 6.2 What It Reveals

Building this dashboard surfaced several non-obvious findings:

- **Platform performance varies significantly by ICP segment** — segments that perform on LinkedIn do not reliably perform on Instagram or Facebook, suggesting platform-native content strategies matter more than cross-posting the same content.
- **Loomly's data exports are inconsistent enough across platforms** that a dedicated cleaning layer is not optional — it's a prerequisite for any downstream analysis.
- **The absence of UTM discipline in historical posts** makes GA4 attribution nearly impossible to reconstruct retroactively, which is why the UTM Standards tab was prioritized as a forward-looking fix rather than a historical analysis tool.
- **Skill-file-based prompt architecture is significantly more consistent** than single-shot prompting for brand-constrained content generation — the two-layer system (reference + platform) produced fewer tone violations than a single combined prompt in testing.

### 6.3 Next Steps

- **GA4 API direct integration** — replace manual conversion entry with an automated pull from GA4 Explore using the Data API, eliminating the main data quality bottleneck
- **Hubspot API integration** — replace CSV file uploads with a direct API connection so the dashboard always reflects the latest data without manual exports
- **Automated ICP tagging** — use a classification prompt to auto-tag new posts by ICP segment and content pillar, reducing manual overhead
- **A/B experiment tracking** — extend the conversion sprint template into a tracked experiment module with hypothesis, variant, and result logging
- **Multi-user support** — the current `weekly_notes.json` is a flat file; a lightweight database (SQLite or Supabase) would support team collaboration

---

## 7. Documentation & Resource Links

### 7.1 Tools & Libraries

| Library / Tool | Purpose |
|---|---|
| [Streamlit](https://streamlit.io) | Dashboard framework |
| [Pandas](https://pandas.pydata.org) | Data cleaning and aggregation |
| [scikit-learn](https://scikit-learn.org) | Linear regression for forecasting |
| [Plotly](https://plotly.com/python) | Interactive charts |
| [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) | Claude API integration |
| [LM Studio](https://lmstudio.ai) | Local Gemma inference |
| [Loomly](https://www.loomly.com) | Social media publishing and CSV export |
| [OpenPyXL](https://openpyxl.readthedocs.io) | Multi-sheet Excel export |

### 7.2 Referenced Papers & Concepts

**Prompting & LLM Behavior**
- Wei et al. (2022). *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.* [arXiv:2201.11903](https://arxiv.org/abs/2201.11903) — informs the structured skill-file prompting architecture.
- Liu et al. (2023). *Pre-train, Prompt, and Predict: A Systematic Survey of Prompting Methods in NLP.* ACM Computing Surveys — background for the two-layer prompt design.
- White et al. (2023). *A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT.* [arXiv:2302.11382](https://arxiv.org/abs/2302.11382) — reference for persona, template, and output-automator prompt patterns used in the skill files.

**Models & Architecture**
- [Anthropic Claude Model Card](https://www.anthropic.com/model-card) — used to inform the model card section above.
- [Google DeepMind Gemma Technical Report (2024)](https://ai.google.dev/gemma) — reference for the local model architecture and licensing terms.

**Retrieval-Augmented Generation**
- Lewis et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* [arXiv:2005.11401](https://arxiv.org/abs/2005.11401) — theoretical basis for injecting reference documents as context at inference time.

**Analytics & Attribution**
- [Google Analytics 4 Developer Documentation](https://developers.google.com/analytics) — used to design the UTM schema and GA4 attribution query in the UTM Standards tab.

**Related Open-Source Codebases**
- [Streamlit Gallery — LLM Examples](https://streamlit.io/gallery?category=llms) — reference implementations for LLM-integrated Streamlit apps.
- [LM Studio Documentation](https://lmstudio.ai/docs) — local inference setup used for the Gemma 4 backend.

---

## Appendix: Skill File Reference

| Skill File | Used In | Purpose |
|---|---|---|
| `hidalga-marketing-reference.skill` | Content Generator (all platforms) | Brand voice, forbidden words, ICP personas, content pillar rules |
| `hidalga-linkedin-post.skill` | Content Generator — LinkedIn | B2B tone, thought leadership structure, character limits |
| `hidalga-instagram-caption.skill` | Content Generator — Instagram | Patient-centered tone, hashtag rules, visual prompts |
| `hidalga-facebook-post.skill` | Content Generator — Facebook | Blended clinical/operational tone, engagement hooks |
| `marketing-analytics-skill.skill` | Overview & Forecast tabs | ICP framework context for AI insights and strategy memos |
| `brand-and-values.md` | Reference hub | Mission, values, forbidden words, tone standards |
| `icp-and-content-pillars.md` | Reference hub | Full ICP personas and content pillar definitions |
| `social-strategy-sop.md` | Reference hub | Posting cadence, content direction, monthly review process |
| `conversion-sprint-template.md` | Reference hub | Monthly experiment sprint structure and hypothesis framework |
