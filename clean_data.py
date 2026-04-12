"""
clean_data.py
Processes exported Loomly Excel / CSV files into cleaned CSVs for the dashboard.

Preferred input (./data/):
  Facebook-data.xlsx  |  Facebook-data(exported).csv
  Instagram-data.xlsx |  Instagram-data(exported).csv
  linkedin-data.xlsx  |  linkedin-data(exported).csv

Output (./data/):
  Facebook-data(data-cleaned).csv
  Instagram-data(data-cleaned).csv
  linkedin-data(data-cleaned).csv
  post_segments.csv   (new rows merged with preserved older rows)

Usage:
  python clean_data.py
"""

import re
import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

# ── Label vocabulary ──────────────────────────────────────────────────────────

ICP_SEGMENTS = [
    "Oncology Operations Leader",
    "Oncology Financial Leader",
    "Oncology Technical Leader",
    "Oncology Clinic Leader",
]

# Loomly label → canonical content pillar name
PILLAR_MAP = {
    "Thought Leadership & Industry Insights": "Thought Leadership & Industry Insights",
    "Product Development & Innovations":      "Product Development & Innovations",
    "Events & Partnerships":                  "Events & Partnerships",
    "Patient-Centered Storytelling":          "Patient-Centered Storytelling",
    "Team Spotlights & Company Culture":      "Team Spotlights & Company Culture",
    # Abbreviated Loomly variants
    "Patient-Centered Stories":               "Patient-Centered Storytelling",
    "Team & Culture":                         "Team Spotlights & Company Culture",
    "Thought Leadership":                     "Thought Leadership & Industry Insights",
    "Product Development":                    "Product Development & Innovations",
}

# Per-platform metric columns (in output order, matching existing cleaned CSVs)
PLATFORM_COLS = {
    "Facebook":  ["DATE", "FORMAT", "IMPRESSIONS", "REACTIONS", "COMMENTS",
                  "SHARES", "CLICKS", "VIDEO-VIEWS"],
    "Instagram": ["DATE", "FORMAT", "LIKES", "COMMENTS", "IMPRESSIONS",
                  "REACH", "ENGAGEMENT", "ENGAGEMENT-RATE", "SAVES", "REELS-PLAYS"],
    "LinkedIn":  ["DATE", "FORMAT", "SHARES", "CLICKS", "ENGAGEMENT-RATE",
                  "REACTIONS", "IMPRESSIONS", "COMMENTS"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_date_value(val) -> bool:
    """True when val is a real post date (datetime object or dd-Mon-yy string)."""
    if isinstance(val, (datetime.datetime, datetime.date)):
        return True
    if isinstance(val, str):
        return bool(re.match(r"^\d{1,2}-[A-Za-z]{3}-\d{2,4}$", val.strip()))
    return False


def _format_date(val) -> str:
    """Convert any date value to the project's dd-Mon-yy string format."""
    return pd.to_datetime(val).strftime("%-d-%b-%y")


def _strip_format(val) -> str:
    """Remove non-breaking space / leading junk that Loomly prepends to format labels."""
    return str(val).lstrip("\xa0").strip()


def _clean_engagement_rate(val) -> str:
    """
    Normalize ENGAGEMENT-RATE to 'XX.XX%' string.
    xlsx exports a decimal fraction (0.1918); CSV exports a percentage string ('19.18%').
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "0.00%"
    if isinstance(val, float):
        # xlsx decimal fraction → multiply to get percentage
        return f"{val * 100:.2f}%"
    s = str(val).strip()
    if s.endswith("%"):
        return s
    try:
        return f"{float(s) * 100:.2f}%"
    except ValueError:
        return "0.00%"


def _parse_labels(label_str) -> tuple:
    """
    Extract the first ICP segment and first content pillar from a
    concatenated Loomly label string (e.g. 'Oncology Operations LeaderTeam & Culture').
    Returns (icp_segment, content_pillar) — either may be empty string.
    """
    if not label_str or (isinstance(label_str, float) and pd.isna(label_str)):
        return "", ""

    s = str(label_str)
    icp = ""
    pillar = ""

    # Match ICP segments — longest first to avoid partial overlaps
    for seg in sorted(ICP_SEGMENTS, key=len, reverse=True):
        if seg in s and not icp:
            icp = seg

    # Match content pillars — longest key first
    for abbrev, canonical in sorted(PILLAR_MAP.items(), key=lambda kv: len(kv[0]), reverse=True):
        if abbrev in s and not pillar:
            pillar = canonical
            break

    return icp, pillar


def _read_source(xlsx_name: str, csv_name: str) -> pd.DataFrame:
    """Read the first sheet of xlsx if present, otherwise fall back to exported CSV."""
    xlsx_path = DATA_DIR / xlsx_name
    csv_path  = DATA_DIR / csv_name

    if xlsx_path.exists():
        return pd.read_excel(xlsx_path, sheet_name=0, header=0)
    if csv_path.exists():
        return pd.read_csv(csv_path, encoding="utf-8-sig")

    raise FileNotFoundError(
        f"No source file found — expected {xlsx_name} or {csv_name} in {DATA_DIR}"
    )


def _extract_post_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the header (data) row of each post — rows with a real DATE value."""
    return df[df["DATE"].apply(_is_date_value)].copy().reset_index(drop=True)


# ── Per-platform cleaners ─────────────────────────────────────────────────────

def _clean_platform(df: pd.DataFrame, platform: str) -> tuple:
    """
    Returns:
      cleaned  — DataFrame with DATE, FORMAT, and metric columns ready to write
      segments — DataFrame with segment/pillar rows for post_segments.csv
    """
    post_rows = _extract_post_rows(df)
    keep_cols = PLATFORM_COLS[platform]

    # ── Build cleaned metrics DataFrame ──────────────────────────────────────
    cleaned = post_rows[keep_cols].copy()
    cleaned["DATE"]   = post_rows["DATE"].apply(_format_date)
    cleaned["FORMAT"] = post_rows["FORMAT"].apply(_strip_format)

    if "ENGAGEMENT-RATE" in cleaned.columns:
        cleaned["ENGAGEMENT-RATE"] = post_rows["ENGAGEMENT-RATE"].apply(
            _clean_engagement_rate
        )

    # Write integer-valued metrics as ints (no trailing .0)
    for col in keep_cols:
        if col in ("DATE", "FORMAT", "ENGAGEMENT-RATE"):
            continue
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce").fillna(0).astype(int)

    # ── Build post_segments rows ──────────────────────────────────────────────
    seg_rows = []
    for _, row in post_rows.iterrows():
        icp, pillar = _parse_labels(row.get("LABELS"))
        seg_rows.append({
            "Date":          pd.to_datetime(row["DATE"]).strftime("%Y-%m-%d"),
            "Platform":      platform,
            "Format":        _strip_format(row.get("FORMAT", "")),
            "ICP_Segment":   icp,
            "Content_Pillar": pillar,
            "Conversions":   0,
        })
    segments = pd.DataFrame(seg_rows)

    return cleaned, segments


def clean_facebook():
    df = _read_source("Facebook-data.xlsx", "Facebook-data(exported).csv")
    return _clean_platform(df, "Facebook")


def clean_instagram():
    df = _read_source("Instagram-data.xlsx", "Instagram-data(exported).csv")
    return _clean_platform(df, "Instagram")


def clean_linkedin():
    df = _read_source("linkedin-data.xlsx", "linkedin-data(exported).csv")
    return _clean_platform(df, "LinkedIn")


# ── post_segments.csv merge ───────────────────────────────────────────────────

def _merge_segments(new_segs: pd.DataFrame) -> None:
    """
    Write updated post_segments.csv.
    New rows replace any existing rows with the same Date + Platform;
    older rows not present in the new data are preserved.
    """
    seg_path = DATA_DIR / "post_segments.csv"

    if seg_path.exists():
        existing = pd.read_csv(seg_path)
        # Drop rows whose Date+Platform appear in the new batch
        new_keys = set(zip(new_segs["Date"], new_segs["Platform"]))
        keep_mask = existing.apply(
            lambda r: (str(r["Date"]), r["Platform"]) not in new_keys, axis=1
        )
        existing = existing[keep_mask]
        combined = pd.concat([existing, new_segs], ignore_index=True)
    else:
        combined = new_segs

    combined = combined.sort_values(["Date", "Platform"]).reset_index(drop=True)
    combined.to_csv(seg_path, index=False)
    print(f"  post_segments.csv  → {len(combined)} total rows "
          f"({len(new_segs)} new / updated)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_segments = []

    print("Cleaning Facebook...")
    fb_clean, fb_segs = clean_facebook()
    fb_clean.to_csv(DATA_DIR / "Facebook-data(data-cleaned).csv", index=False)
    all_segments.append(fb_segs)
    print(f"  Facebook-data(data-cleaned).csv  → {len(fb_clean)} posts")

    print("Cleaning Instagram...")
    ig_clean, ig_segs = clean_instagram()
    ig_clean.to_csv(DATA_DIR / "Instagram-data(data-cleaned).csv", index=False)
    all_segments.append(ig_segs)
    print(f"  Instagram-data(data-cleaned).csv → {len(ig_clean)} posts")

    print("Cleaning LinkedIn...")
    li_clean, li_segs = clean_linkedin()
    li_clean.to_csv(DATA_DIR / "linkedin-data(data-cleaned).csv", index=False)
    all_segments.append(li_segs)
    print(f"  linkedin-data(data-cleaned).csv  → {len(li_clean)} posts")

    print("Updating post_segments.csv...")
    _merge_segments(pd.concat(all_segments, ignore_index=True))

    print("\nDone.")


if __name__ == "__main__":
    main()
