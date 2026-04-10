import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
NOTES_FILE = DATA_DIR / "weekly_notes.json"


def _strip_format(val: str) -> str:
    return re.sub(r"^[^\w\s]+", "", str(val)).strip()


def _clean_numeric(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0)
    )


def clean_raw(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    mask = df["DATE"].astype(str).str.strip().str.match(r"^\d{1,2}-[A-Za-z]{3}-\d{2,4}$")
    df = df[mask].reset_index(drop=True)
    df["DATE"] = pd.to_datetime(df["DATE"], format="%d-%b-%y", errors="coerce")
    df = df.dropna(subset=["DATE"])
    df["FORMAT"] = df["FORMAT"].astype(str).apply(_strip_format)
    for col in df.columns:
        if col not in ("DATE", "FORMAT"):
            df[col] = _clean_numeric(df[col])
    return df


@st.cache_data
def load_all() -> pd.DataFrame:
    frames = []

    fb = clean_raw(pd.read_csv(DATA_DIR / "Facebook-data(data-cleaned).csv", encoding="latin-1"))
    fb["Platform"] = "Facebook"
    fb["Engagement"] = fb.get("REACTIONS", 0) + fb.get("COMMENTS", 0) + fb.get("SHARES", 0)
    fb["KeyActions"] = fb["Engagement"] + fb.get("CLICKS", 0)
    fb = fb.rename(columns={
        "DATE": "Date", "FORMAT": "Format", "IMPRESSIONS": "Impressions",
        "REACTIONS": "Reactions", "COMMENTS": "Comments", "SHARES": "Shares",
        "CLICKS": "Clicks", "VIDEO-VIEWS": "VideoViews",
    })
    frames.append(fb)

    ig = clean_raw(pd.read_csv(DATA_DIR / "Instagram-data(data-cleaned).csv", encoding="latin-1"))
    ig["Platform"] = "Instagram"
    ig["Engagement"] = ig.get("ENGAGEMENT", pd.Series(dtype=float)).fillna(0)
    ig["EngagementRate"] = ig.get("ENGAGEMENT-RATE", pd.Series(dtype=float)).fillna(0)
    ig["Clicks"] = 0.0   # Instagram does not export link clicks in Loomly
    ig["KeyActions"] = ig["Engagement"] + ig.get("SAVES", 0)
    ig = ig.rename(columns={
        "DATE": "Date", "FORMAT": "Format", "IMPRESSIONS": "Impressions",
        "LIKES": "Likes", "COMMENTS": "Comments", "REACH": "Reach",
        "SAVES": "Saves", "REELS-PLAYS": "ReelsPlays",
    })
    ig = ig.drop(columns=["ENGAGEMENT", "ENGAGEMENT-RATE"], errors="ignore")
    frames.append(ig)

    li = clean_raw(pd.read_csv(DATA_DIR / "linkedin-data(data-cleaned).csv", encoding="latin-1"))
    li["Platform"] = "LinkedIn"
    li["Engagement"] = li.get("REACTIONS", 0) + li.get("COMMENTS", 0)
    li["EngagementRate"] = li.get("ENGAGEMENT-RATE", pd.Series(dtype=float)).fillna(0)
    li["KeyActions"] = li["Engagement"] + li.get("CLICKS", 0) + li.get("SHARES", 0)
    li = li.rename(columns={
        "DATE": "Date", "FORMAT": "Format", "IMPRESSIONS": "Impressions",
        "REACTIONS": "Reactions", "COMMENTS": "Comments",
        "SHARES": "Shares", "CLICKS": "Clicks",
    })
    li = li.drop(columns=["ENGAGEMENT-RATE"], errors="ignore")
    frames.append(li)

    df = pd.concat(frames, ignore_index=True)
    df["Month"] = df["Date"].dt.to_period("M")
    df["MonthLabel"] = df["Date"].dt.strftime("%b %Y")
    df["WeekStart"] = df["Date"] - pd.to_timedelta(df["Date"].dt.dayofweek, unit="D")
    df["WeekLabel"] = df["WeekStart"].dt.strftime("Week of %b %d, %Y")
    return df


@st.cache_data
def load_segments() -> pd.DataFrame:
    path = DATA_DIR / "post_segments.csv"
    if not path.exists():
        return pd.DataFrame(columns=["Date", "Platform", "ICP_Segment", "Content_Pillar", "Conversions"])
    seg = pd.read_csv(path)
    seg["Date"] = pd.to_datetime(seg["Date"])
    seg["Conversions"] = pd.to_numeric(seg.get("Conversions", 0), errors="coerce").fillna(0)
    if "Content_Pillar" not in seg.columns:
        seg["Content_Pillar"] = "Untagged"
    return seg


def load_notes() -> dict:
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_notes(notes: dict) -> None:
    NOTES_FILE.write_text(json.dumps(notes, indent=2))
