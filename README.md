# Hidalga Marketing Dashboard

This project was built as a final project for a Gen AI course at Vanderbilt. The goal was to build a tool that Hidalga Technologies — an oncology software company — could actually use to run their social media marketing with structure, AI-assisted analysis, and AI-generated content.

---

## The Problem

Hidalga publishes posts across LinkedIn, Facebook, and Instagram through Loomly. The raw exports are messy CSVs with inconsistent formatting, and there was no systematic way to ask: *which posts are actually working, and for which audience?* There was also no consistent process for turning performance data into better content.

---

## Step 1 — Clean the Data

The first thing built was a data cleaning pipeline (`data_loader.py`) that reads the three Loomly CSVs and normalizes them into a single unified dataframe.

Each platform exports data in a slightly different shape. Facebook tracks reactions, comments, shares, and clicks. Instagram exports engagement totals and saves but no link clicks (Loomly does not export those). LinkedIn tracks reactions, comments, shares, and clicks with an engagement rate. The loader handles all three, aligns column names, computes derived fields like `Engagement`, `KeyActions`, and `WeekStart`, and caches the result for fast rerenders.

---

## Step 2 — Define the Audiences

Hidalga sells to oncology practices. Their buyers are not a monolith. A practice administrator cares about operational reliability and staffing. A revenue cycle director cares about denial rates and cash flow. A clinical informaticist cares about FHIR compliance and avoiding fragile integrations. A physician cares about not adding clicks to their workflow.

Four **ICP segments** were defined and documented:

- **Oncology Operations Leader** — practice admins, COOs, directors of operations
- **Oncology Financial Leader** — revenue cycle managers, billing directors, CFOs
- **Oncology Technical Leader** — IT directors, CIOs, CISOs, clinical informaticists
- **Oncology Clinic Leader** — medical directors, lead oncologists, nursing directors

Each segment is stored in `data/icp_segments.csv` and `skills/marketing-analytics/references/icp-segments.md`, including their buyer role, primary motivations, content interests, and which content pillars resonate with them.

Five **content pillars** were also defined, mapped to brand colors:

- Thought Leadership & Industry Insights
- Product Development & Innovations
- Events & Partnerships
- Patient-Centered Storytelling
- Team Spotlights & Company Culture

A `data/post_segments.csv` file lets each post be tagged with an ICP segment, content pillar, and conversion count from GA4.

---

## Step 3 — Build the Dashboard

The dashboard (`app.py`) is a Streamlit app with five tabs. It loads the cleaned data, merges in segment assignments, and applies sidebar filters for platform and date range.

### Overview Tab

The first tab surfaces the big picture: total impressions, engagement, clicks, and posts published as KPI cards. Below that, a time-series line chart shows impressions by platform over the selected date range. Side panels show a platform donut chart and engagement breakdown by format.

A month-over-month comparison table shows percentage deltas so the team can spot trends at a glance. The top-performing posts table is sortable by any metric and color-coded by platform and ICP segment. An export button lets users download the full filtered dataset as CSV or multi-sheet Excel.

At the bottom, an **AI insights** button sends the filtered summary to the selected AI backend and streams a structured analysis back into the page.

### Weekly Review Tab

Every Monday the team reviews the prior week. This tab makes that process concrete.

Select a week, and the tab shows five KPIs for that week (impressions, clicks, CTR, key actions, conversions), followed by a segment performance table that breaks down every metric by ICP segment. Each segment is automatically flagged:

- **🟢 Overperformer** — CTR ≥ 1.5× the weekly average
- **🔴 Underperformer** — CTR ≤ 0.5× the weekly average
- **⚠️ Low reach** — fewer than 10 impressions

Below the table, two bar charts show impressions and CTR side-by-side by segment. A post drill-down table shows every individual post for the week, filterable by segment, with per-post CTR flags.

At the bottom is a notes section. The team types their observations and decisions, clicks **Save Notes**, and the entry is written to `data/weekly_notes.json`. A **Download Summary** button exports the full review — KPIs, segment breakdown, notes — as a formatted `.txt` file. Previous weeks' notes are visible in a collapsed log.

A discussion checklist (expandable) prompts the team through seven standard questions each Monday, including content pillar coverage, LinkedIn concentration, clinical audience resonance on Instagram and Facebook, and conversion attribution.

### UTM Standards Tab

This tab documents and enforces the UTM naming convention used across all posts. Every link posted on any platform should carry five UTM parameters: `utm_source` (platform), `utm_medium` (organic-social or paid-social), `utm_campaign` (year-quarter-initiative), `utm_content` (format-icp-short), and `utm_term` (optional keyword).

ICP short codes are defined: `ops`, `financial`, `technical`, `clinical`. These map `utm_content` values back to audience segments in GA4.

The **UTM Builder** form lets the team fill in their parameters and get a tagged URL instantly, without typing manually. It auto-populates the current year and quarter, combines format and ICP short code into `utm_content`, and shows a parameter breakdown table. A download button exports the parameters as CSV.

An expandable guide walks through the full GA4 implementation: adding custom dimensions for `utm_content` and `utm_campaign`, writing the weekly attribution query in GA4 Explore, and the path to connecting the GA4 API directly to the dashboard.

### Forecast & Strategy Tab

The forecast tab applies a linear regression to weekly aggregated performance data per platform and projects it forward 2–8 weeks. The forecast chart shows historical data as solid lines and the projected period as dashed lines, with confidence bounds.

Below the chart, a content strategy recommendations panel uses the ICP × content pillar combinations from the actual post data, ranks them by average engagement, and presents the top opportunities. An AI-generated strategy memo (triggered by the sidebar button) synthesizes the forecast trends and segment data into a structured recommendation with prioritized actions.

### Content Generator Tab

The final tab closes the loop from analytics to content creation.

The tab reads the post data to identify which ICP segment and content pillar combination has the highest average engagement for each platform, and pre-populates those as recommendations. The user selects a platform (LinkedIn, Instagram, or Facebook), an ICP segment, a content pillar, a brand value, and writes a short topic brief.

Clicking **Generate** loads the corresponding **Claude Code skill file** for that platform — a `.skill` zip archive containing `SKILL.md`, which encodes Hidalga's brand voice, tone guidelines, audience-specific messaging rules, and post structure for that platform. The skill content is injected as the system prompt, and the user's brief becomes the user message. The AI streams the generated post directly into the page.

Three skill files were built:

- `skills/hidalga-linkedin-post.skill` — LinkedIn posts for B2B oncology audiences, professional tone, thought leadership framing
- `skills/hidalga-instagram-caption.skill` — Instagram captions, patient-centered and culture-forward
- `skills/hidalga-facebook-post.skill` — Facebook posts, blending clinical storytelling with operational messaging

A fourth skill, `skills/marketing-analytics/marketing-analytics-skill.skill`, encodes the ICP framework and content strategy for use as a reference context in AI analysis calls.

---

## The AI Backend

The sidebar exposes two AI options:

**Claude (Anthropic)** — calls `claude-opus-4-6` via the Anthropic API. Requires an API key passed either through the sidebar or the `ANTHROPIC_API_KEY` environment variable. Used for AI insights on the Overview tab, strategy memos on the Forecast tab, and post generation in the Content Generator.

**Local — Gemma-4 (LM Studio)** — calls a locally running instance of Gemma 4 E4B via LM Studio's OpenAI-compatible endpoint on `localhost:1234`. This runs entirely offline — no API key required. The same prompt interface is used for both backends; `llm_client.py` abstracts the routing.

---

## Running It

```bash
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`.

For AI features with Claude, set your API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

For local AI, open LM Studio, load Gemma 4 E4B, start the server on port 1234, and select **Local — Gemma-4** in the sidebar.

---

## Data Files

| File | Description |
|---|---|
| `data/Facebook-data(data-cleaned).csv` | Facebook post metrics from Loomly |
| `data/Instagram-data(data-cleaned).csv` | Instagram post metrics from Loomly |
| `data/linkedin-data(data-cleaned).csv` | LinkedIn post metrics from Loomly |
| `data/icp_segments.csv` | ICP segment definitions |
| `data/post_segments.csv` | Maps each post to an ICP segment, content pillar, and conversion count |
| `data/weekly_notes.json` | Auto-created on first save; stores weekly discussion notes |

To update: export new CSVs from Loomly in the same column format, replace the files in `data/`, and restart the app. The `st.cache_data` cache reloads automatically.

---

## Project Structure

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
│   ├── overview.py                   # KPIs, charts, top posts, AI insights
│   ├── weekly_review.py              # Segment flags, drill-down, discussion notes
│   ├── utm_standards.py              # Convention reference and UTM builder
│   ├── forecast_strategy.py          # Linear trend projections, strategy memos
│   └── content_generator.py         # Skill-based post generation
└── skills/
    ├── hidalga-linkedin-post.skill
    ├── hidalga-instagram-caption.skill
    ├── hidalga-facebook-post.skill
    └── marketing-analytics/
        ├── marketing-analytics-skill.skill
        └── references/
            └── icp-segments.md
```
