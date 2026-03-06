"""
Job Rate Finder — Powered by Claude AI
Dark theme, myBasePay palette: Emerald / Wisteria / Marigold / Prussian.
"""

from __future__ import annotations

import html as html_mod
from typing import Dict, List, Optional

import streamlit as st

from utils import (
    HOURS_PER_YEAR,
    MAX_DISPLAYED_SOURCES,
    compute_stats,
    display_money,
    display_unit,
    get_cities,
    get_countries,
    get_fx,
    get_meta,
    get_states,
    parse_num,
    pretty_host,
    to_currency,
)
import site_planner
from search import search_web
from ai_extract import claude_extract, process_extraction


# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(page_title="Job Rate Finder", page_icon="💼", layout="centered")


# ─────────────────────────────────────────────
# CSS  — dark myBasePay theme
# ─────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;0,14..32,800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  /* surfaces */
  --bg:    #060c18;
  --s1:    #0d1729;
  --s2:    #131f38;
  --s3:    #1a2a4a;
  /* borders */
  --b0: rgba(115,147,249,.07);
  --b1: rgba(115,147,249,.14);
  --b2: rgba(115,147,249,.28);
  --b3: rgba(115,147,249,.5);
  /* text */
  --tx:  #e2e9f8;
  --tx2: #b4ccec;
  --mt:  #6a90b8;
  /* brand */
  --emerald:    #00cc55;
  --emerald-d:  rgba(0,204,85,.12);
  --prussian:   #121631;
  --wisteria:   #7393f9;
  --wisteria-d: rgba(115,147,249,.12);
  --marigold:   #ffbf00;
  --marigold-d: rgba(255,191,0,.12);
  /* fonts */
  --mono: 'JetBrains Mono', monospace;
  --sans: 'Inter', system-ui, sans-serif;
}

/* ── Global ─────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"],
section[data-testid="stSidebar"] {
  background: var(--bg) !important;
  color: var(--tx) !important;
  font-family: var(--sans) !important;
}
[data-testid="stHeader"] { display: none !important; }
#MainMenu, footer { visibility: hidden; }
.block-container {
  padding-top: 0 !important;
  padding-bottom: 5rem !important;
  max-width: 920px !important;
}

/* ── Expander ──────────────────────────────── */
details summary {
  color: var(--tx2) !important;
  font-size: 13px !important;
}
.stExpander { border: 1px solid var(--b1) !important; border-radius: 12px !important; background: var(--s1) !important; }

/* ── Input card ────────────────────────────── */
div[data-testid="stContainer"] {
  background: var(--s1) !important;
  border: 1px solid var(--b1) !important;
  border-radius: 18px !important;
  padding: 28px 32px !important;
  box-shadow: 0 8px 40px rgba(0,0,0,.4) !important;
}

/* ── Labels ─────────────────────────────────── */
label,
.stMarkdown p {
  color: var(--tx2) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  letter-spacing: .04em !important;
  text-transform: uppercase !important;
  font-family: var(--sans) !important;
}

/* ── Text inputs ────────────────────────────── */
.stTextInput input {
  background: var(--s2) !important;
  border: 1px solid var(--b1) !important;
  color: var(--tx) !important;
  border-radius: 10px !important;
  padding: 12px 16px !important;
  font-size: 15px !important;
  font-family: var(--sans) !important;
  transition: border-color .18s, box-shadow .18s !important;
}
.stTextInput input::placeholder { color: var(--mt) !important; }
.stTextInput input:focus {
  border-color: var(--wisteria) !important;
  box-shadow: 0 0 0 3px rgba(115,147,249,.18) !important;
  background: var(--s3) !important;
}

/* ── Text area ──────────────────────────────── */
.stTextArea textarea {
  background: var(--s2) !important;
  border: 1px solid var(--b1) !important;
  color: var(--tx) !important;
  border-radius: 10px !important;
  font-size: 14px !important;
  font-family: var(--sans) !important;
}
.stTextArea textarea:focus {
  border-color: var(--wisteria) !important;
  box-shadow: 0 0 0 3px rgba(115,147,249,.18) !important;
}

/* ── Selectbox ──────────────────────────────── */
.stSelectbox [data-baseweb="select"] > div {
  background: var(--s2) !important;
  border: 1px solid var(--b1) !important;
  color: var(--tx) !important;
  border-radius: 10px !important;
  font-family: var(--sans) !important;
  transition: border-color .18s !important;
}
.stSelectbox [data-baseweb="select"] > div:hover { border-color: var(--b2) !important; }
.stSelectbox [data-baseweb="select"] > div:focus-within {
  border-color: var(--wisteria) !important;
  box-shadow: 0 0 0 3px rgba(115,147,249,.18) !important;
}
/* dropdown menu */
[data-baseweb="popover"] ul,
[data-baseweb="menu"] {
  background: var(--s2) !important;
  border: 1px solid var(--b2) !important;
  border-radius: 10px !important;
}
[data-baseweb="menu"] li { color: var(--tx) !important; }
[data-baseweb="menu"] li:hover { background: var(--s3) !important; }

/* ── Radio buttons ──────────────────────────── */
.stRadio > div { gap: 12px !important; }
.stRadio label { text-transform: none !important; letter-spacing: 0 !important; font-size: 13px !important; color: var(--tx2) !important; }
.stRadio [data-testid="stMarkdownContainer"] p { text-transform: none !important; letter-spacing: 0 !important; }

/* ── Marigold CTA ───────────────────────────── */
.stButton > button {
  width: 100%;
  border: none !important;
  border-radius: 12px !important;
  padding: 15px 20px !important;
  font-weight: 700 !important;
  font-size: 15px !important;
  color: #0d1729 !important;
  background: var(--marigold) !important;
  box-shadow: 0 4px 24px rgba(255,191,0,.3) !important;
  font-family: var(--sans) !important;
  letter-spacing: .02em !important;
  transition: all .18s ease !important;
}
.stButton > button:hover {
  box-shadow: 0 8px 36px rgba(255,191,0,.45) !important;
  transform: translateY(-1px) !important;
}
.stButton > button:disabled { opacity: .4 !important; box-shadow: none !important; transform: none !important; }

/* ── Section divider ────────────────────────── */
.sec-label {
  font-size: 12px; font-weight: 700; letter-spacing: .16em;
  text-transform: uppercase; color: var(--mt);
  margin: 28px 0 12px; display: flex; align-items: center; gap: 12px;
}
.sec-label::after { content: ''; flex: 1; height: 1px; background: var(--b0); }

/* ── AI summary ─────────────────────────────── */
.ai-card {
  position: relative; overflow: hidden;
  background: var(--s1);
  border: 1px solid var(--b1);
  border-radius: 16px;
  padding: 22px 26px;
  margin: 18px 0;
}
.ai-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--emerald), var(--wisteria));
}
.ai-badge {
  font-size: 12px; font-weight: 700; letter-spacing: .15em;
  text-transform: uppercase; color: var(--emerald); margin-bottom: 10px;
  display: flex; align-items: center; gap: 7px;
}
.ai-badge::before {
  content: ''; width: 6px; height: 6px; border-radius: 50%;
  background: var(--emerald); display: inline-block;
  box-shadow: 0 0 8px var(--emerald);
}
.ai-text { color: var(--tx2); font-size: 15px; line-height: 1.8; margin: 0; }

/* ── Confidence banner ──────────────────────── */
.conf-banner {
  display: flex; align-items: center; gap: 10px; margin: 8px 0 16px;
  padding: 10px 16px; border-radius: 10px; font-size: 13px;
  border: 1px solid var(--b0); background: rgba(255,255,255,.025);
  color: var(--tx2);
}
.conf-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* ── Range hero card ────────────────────────── */
.range-card {
  position: relative; overflow: hidden;
  background: var(--s1);
  border: 1px solid var(--b1);
  border-radius: 18px;
  padding: 30px 34px;
  margin: 14px 0 24px;
}
.range-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--emerald), var(--wisteria));
}
.range-glow {
  position: absolute; top: -60px; left: -40px; width: 300px; height: 200px;
  background: radial-gradient(ellipse, rgba(0,204,85,.06) 0%, transparent 70%);
  pointer-events: none;
}
.range-grid { display: flex; align-items: flex-end; gap: 28px; flex-wrap: wrap; }
.range-lbl  { font-size: 12px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: var(--tx2); margin-bottom: 7px; }
.range-val  { font-family: var(--mono); font-size: 38px; font-weight: 700; letter-spacing: -.03em; line-height: 1; color: var(--tx); }
.range-unit { font-size: 13px; color: var(--tx2); margin-top: 7px; }
.range-sep  { font-size: 26px; color: var(--b2); padding-bottom: 12px; }
.range-mid  { margin-left: auto; text-align: center; }
.range-mid-val { font-family: var(--mono); font-size: 24px; font-weight: 700; color: var(--emerald); }
.range-mid-lbl { font-size: 12px; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; color: var(--emerald); opacity: .85; margin-bottom: 6px; }

/* ── Stats bar ──────────────────────────────── */
.stats-bar {
  display: flex; flex-wrap: wrap; gap: 4px 20px;
  padding: 11px 18px; border-radius: 12px;
  background: var(--s1); border: 1px solid var(--b0);
  margin-bottom: 12px; font-size: 13px; color: var(--tx2);
}

/* ── Low-data warning ───────────────────────── */
.low-data-warn {
  display: flex; align-items: center; gap: 10px;
  padding: 11px 16px; border-radius: 10px;
  border: 1px solid rgba(255,191,0,.25);
  background: rgba(255,191,0,.06);
  font-size: 13px; color: #f5d060;
  margin-bottom: 12px;
}

/* ── Band rows ──────────────────────────────── */
.bd-row {
  position: relative;
  background: var(--s1);
  border: 1px solid var(--b0);
  border-radius: 14px;
  padding: 16px 20px 14px 22px;
  margin-bottom: 8px;
  transition: border-color .2s, box-shadow .2s;
}
.bd-row:hover {
  border-color: var(--b2);
  box-shadow: 0 4px 20px rgba(0,0,0,.25);
}
.bd-top {
  display: flex; align-items: center;
  justify-content: space-between; gap: 14px;
  margin-bottom: 6px;
}
.bd-left  { display: flex; align-items: center; gap: 10px; }
.bd-tag   {
  font-size: 12px; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; padding: 4px 10px;
  border-radius: 7px; white-space: nowrap;
}
.bd-desc  { font-size: 14px; color: var(--tx2); }
.bd-right { text-align: right; flex-shrink: 0; }
.bd-range { font-family: var(--mono); font-size: 15px; font-weight: 600; color: var(--tx); white-space: nowrap; }
.bd-avg   { font-family: var(--mono); font-size: 13px; color: var(--tx2); margin-top: 3px; }
.pts-badge {
  font-size: 11px; font-weight: 700; font-family: var(--mono);
  padding: 2px 8px; border-radius: 20px; white-space: nowrap;
}

/* ── Source pills ───────────────────────────── */
.src-pills { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }
.src-pill  {
  display: inline-block; padding: 4px 12px; border-radius: 20px;
  border: 1px solid; font-size: 13px; font-family: var(--mono);
  text-decoration: none; white-space: nowrap;
  transition: opacity .15s, transform .12s;
}
.src-pill:hover { opacity: .75; transform: translateY(-1px); }

/* ── Band left-accent bar ───────────────────── */
.bd-row::before {
  content: ''; position: absolute;
  left: 0; top: 8px; bottom: 8px;
  width: 3px; border-radius: 3px;
}

/* ── Source expander list ───────────────────── */
.src-item {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 10px 14px; border: 1px solid var(--b0);
  border-radius: 10px; text-decoration: none;
  margin-bottom: 6px; background: var(--s1);
  transition: border-color .15s, background .15s;
}
.src-item:hover { border-color: var(--b2); background: var(--s2); }
.src-dot   { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; margin-top: 6px; }
.src-title { color: var(--tx); font-weight: 600; font-size: 14px; }
.src-meta  { color: var(--tx2); font-size: 12px; margin-top: 2px; }

.band-divider { height: 1px; background: var(--b0); margin: 4px 0 10px; }
.note-box {
  padding: 14px 18px; border-radius: 12px; font-size: 13px;
  border: 1px solid; margin-top: 12px; line-height: 1.6;
}

/* ── Stat cards ─────────────────────────────── */
.stat-card {
  background: var(--s1); border: 1px solid var(--b1);
  border-radius: 12px; padding: 14px 16px; text-align: center;
  margin-bottom: 8px;
}
.stat-card-lbl {
  font-size: 12px; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: var(--mt); margin-bottom: 6px;
}
.stat-card-val {
  font-family: var(--mono); font-size: 22px; font-weight: 700;
  color: var(--tx); line-height: 1.1;
}
.stat-card-unit {
  font-size: 12px; color: var(--tx2); margin-top: 4px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Hero header
# ─────────────────────────────────────────────
st.markdown("""
<div style="
  background: linear-gradient(135deg, #001a0e 0%, #0d1729 55%, #0b102e 100%);
  padding: 48px 36px 40px;
  border-radius: 0 0 28px 28px;
  margin-bottom: 30px;
  position: relative;
  overflow: hidden;
">
  <!-- ambient glows -->
  <div style="position:absolute;top:-60px;left:-40px;width:340px;height:260px;
    background:radial-gradient(ellipse,rgba(0,204,85,.13) 0%,transparent 70%);pointer-events:none;"></div>
  <div style="position:absolute;top:-40px;right:-20px;width:280px;height:220px;
    background:radial-gradient(ellipse,rgba(115,147,249,.1) 0%,transparent 70%);pointer-events:none;"></div>
  <!-- content -->
  <div style="position:relative;">
    <div style="font-size:11px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;
      color:rgba(115,147,249,.7);margin-bottom:10px;">Salary Intelligence</div>
    <div style="font-size:34px;font-weight:800;color:#e2e9f8;letter-spacing:-.03em;line-height:1.1;">
      Job Rate Finder
    </div>
    <div style="color:rgba(226,233,248,.5);font-size:14px;margin-top:8px;font-weight:400;">
      100+ sources &middot; AI-powered analysis &middot; live FX conversion
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def compact_money(annual_usd: float, currency: str, rate_type: str) -> str:
    val = to_currency(annual_usd, currency)
    if rate_type == "hourly":
        return f"{val / HOURS_PER_YEAR:,.0f}/hr"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:.0f}k"
    return f"{val:,.0f}"


def render_band_sources(
    lo_usd: float,
    hi_usd: float,
    mean_usd: float,
    currency: str,
    rate_type: str,
    data_points: List[Dict],
    accent_color: str,
) -> str:
    """
    2–3 source pills per band:
      • Source closest to the band low  (supports the min)
      • Source closest to the band high (supports the max)
      • Source closest to the mean      (supports the average) — only if distinct
    """
    hits = [
        dp for dp in data_points
        if dp.get("annual_usd") and lo_usd <= dp["annual_usd"] <= hi_usd
    ]
    if not hits:
        return ""

    src_lo  = min(hits, key=lambda d: abs(d["annual_usd"] - lo_usd))
    src_hi  = min(hits, key=lambda d: abs(d["annual_usd"] - hi_usd))
    src_avg = min(hits, key=lambda d: abs(d["annual_usd"] - mean_usd))

    # Deduplicate by identity, then sort ascending by value
    seen: set = set()
    ordered: List[Dict] = []
    for dp in [src_lo, src_avg, src_hi]:
        if id(dp) not in seen:
            ordered.append(dp)
            seen.add(id(dp))
    ordered.sort(key=lambda d: d["annual_usd"])

    pills = ""
    for dp in ordered:
        v_min = dp.get("value_min_usd")
        v_max = dp.get("value_max_usd")
        if v_min and v_max:
            val = f"{compact_money(v_min, currency, rate_type)}–{compact_money(v_max, currency, rate_type)}"
        else:
            val = compact_money(dp["annual_usd"], currency, rate_type)
        host = html_mod.escape((dp.get("host") or "source")[:24])
        url  = html_mod.escape(dp.get("url", "#"), quote=True)
        pills += (
            f'<a class="src-pill" href="{url}" target="_blank" '
            f'style="border-color:{accent_color}55;color:{accent_color};'
            f'background:{accent_color}12;">'
            f'{host}&nbsp;{currency}&nbsp;{val}</a>'
        )
    return f'<div class="src-pills">{pills}</div>' if pills else ""


def pts_badge(n: int, band_key: str) -> str:
    if band_key == "ai":
        c, bg = "#f5d060", "rgba(255,191,0,.18)"
    elif n >= 8:
        c, bg = "#00cc55", "rgba(0,204,85,.15)"
    elif n >= 3:
        c, bg = "#7393f9", "rgba(115,147,249,.15)"
    else:
        c, bg = "#f5d060", "rgba(255,191,0,.18)"
    return f'<span class="pts-badge" style="color:{c};background:{bg};">{n}&thinsp;pts</span>'


def render_band_row(
    label: str,
    desc: str,
    tag_color: str,
    tag_bg: str,
    left_accent: str,
    lo_s: str,
    hi_s: str,
    avg_s: str,
    curr: str,
    unit: str,
    pills_html: str,
    n_points: int,
    band_key: str = "stat",
) -> str:
    badge = pts_badge(n_points, band_key)
    return f"""
<div class="bd-row" style="border-left-color:{left_accent}33;">
  <div style="position:absolute;left:0;top:8px;bottom:8px;width:3px;
    border-radius:3px;background:{left_accent};opacity:.7;"></div>
  <div class="bd-top">
    <div class="bd-left">
      <span class="bd-tag" style="color:{tag_color};background:{tag_bg};">{label}</span>
      <span class="bd-desc">{desc}</span>
    </div>
    <div class="bd-right">
      <div class="bd-range">{curr}&nbsp;{lo_s}&nbsp;&ndash;&nbsp;{hi_s}</div>
      <div class="bd-avg">avg&nbsp;{curr}&nbsp;{avg_s}&nbsp;{unit}</div>
      {badge}
    </div>
  </div>
  {pills_html}
</div>"""


# Band style map: label, desc, tag_color, tag_bg, left_accent, pill_accent
BAND_SPECS = {
    "ai": (
        "AI Recommended",
        "Claude&rsquo;s recommended offer range",
        "#f5d060", "rgba(255,191,0,.14)", "#ffbf00", "#ffbf00",
    ),
    1: (
        "1&sigma;&nbsp;Typical",
        "Middle 68% &mdash; 16th to 84th percentile",
        "#00cc55", "rgba(0,204,85,.12)", "#00cc55", "#00cc55",
    ),
    2: (
        "2&sigma;&nbsp;Full Range",
        "Observed full range after outlier removal",
        "#7393f9", "rgba(115,147,249,.12)", "#7393f9", "#7393f9",
    ),
}


# ─────────────────────────────────────────────
# Confidence
# ─────────────────────────────────────────────
def compute_confidence(stats: Optional[Dict], n_sources: int) -> tuple:
    if stats is None:
        return ("Low", "Very limited data — treat as a rough estimate.", "#f5d060")
    n  = stats["count"]
    s1_lo, s1_hi = stats.get("sigma1", (stats["mean"], stats["mean"]))
    cv = ((s1_hi - s1_lo) / 2) / stats["mean"] if stats["mean"] > 0 else 1.0
    if n >= 10 and cv < 0.35 and n_sources >= 5:
        return ("High", f"{n} data points from {n_sources} sources, consistent values.", "#00cc55")
    elif n >= 5 and cv < 0.5:
        return ("Moderate", f"{n} data points with some variation in reported salaries.", "#7393f9")
    else:
        parts = [f"{n} data point{'s' if n != 1 else ''}."]
        if cv >= 0.5:
            parts.append("Wide variation — mixed roles or seniority levels.")
        if n < 5:
            parts.append("More data would improve accuracy.")
        return ("Low", " ".join(parts), "#f5d060")


# ─────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────
def run_analysis(
    job: str, country: str, state: str, city: str,
    exp_years: str, rate_type: str, job_desc: str,
) -> Dict:
    core_job = job.strip()

    plan = site_planner.plan_search(core_job, country, state, city, exp_years)

    sources = search_web(core_job, country, state, city, plan)
    if not sources:
        raise RuntimeError("No search results found. Try a different job title or location.")

    ai_data = claude_extract(
        job=core_job, country=country, state=state, city=city,
        exp_years=exp_years, rate_type=rate_type, job_desc=job_desc,
        sources=sources,
        period_hint=plan.get("period_hint"),
        market_notes=plan.get("market_notes"),
    )
    data_table = process_extraction(ai_data, sources)
    if not data_table:
        raise RuntimeError("Could not extract salary data. Try a more common job title or broader location.")

    annual_values = [row["annual_usd"] for row in data_table]
    ai_min = parse_num(ai_data.get("ai_recommended_min_usd")) or min(annual_values)
    ai_max = parse_num(ai_data.get("ai_recommended_max_usd")) or max(annual_values)
    ai_mid = parse_num(ai_data.get("ai_recommended_mid_usd")) or ((ai_min + ai_max) / 2)
    if ai_min > ai_max:
        ai_min, ai_max = ai_max, ai_min

    stats = compute_stats(data_table, ai_min=ai_min, ai_max=ai_max)
    if stats:
        data_table = [
            row for row in data_table
            if stats["min"] <= row["annual_usd"] <= stats["max"]
        ]

    return {
        "job": core_job,
        "location": ", ".join(x for x in [city, state, country] if x),
        "rate_type": rate_type,
        "sources": sources[:MAX_DISPLAYED_SOURCES],
        "data_table": data_table,
        "stats": stats,
        "ai_min_usd": ai_min, "ai_max_usd": ai_max, "ai_mid_usd": ai_mid,
        "ai_summary": ai_data.get("ai_summary", ""),
        "warnings": ai_data.get("warnings") or [],
    }


# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
_DEFAULTS = {
    "job_title": "", "exp_years": "", "job_desc": "",
    "country": "", "state": "", "city": "",
    "rate_type": "salary", "currency": "USD",
    "result": None, "error": None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def on_country_change():
    st.session_state["state"]    = ""
    st.session_state["city"]     = ""
    st.session_state["currency"] = get_meta(st.session_state["country"]).get("currency", "USD")

def on_state_change():
    st.session_state["city"] = ""


# ─────────────────────────────────────────────
# Input form
# ─────────────────────────────────────────────
with st.container(border=True):

    # Row 1 — Job title + experience
    c1, c2 = st.columns([3, 1])
    with c1:
        st.text_input("Job Title", key="job_title",
                      placeholder="e.g. Senior Software Engineer")
    with c2:
        st.text_input("Experience", key="exp_years",
                      placeholder="e.g. 5 yrs")

    # Row 2 — Location cascade
    try:
        countries = get_countries()
    except Exception:
        countries = []

    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        st.selectbox(
            "Country", [""] + countries, key="country",
            on_change=on_country_change,
            format_func=lambda x: "— Select —" if not x else x,
        )
    with lc2:
        states = get_states(st.session_state["country"]) if st.session_state["country"] else []
        if st.session_state["state"] not in [""] + states:
            st.session_state["state"] = ""
        st.selectbox("State / Province", [""] + states, key="state",
                     on_change=on_state_change,
                     format_func=lambda x: "— Any —" if not x else x)
    with lc3:
        cities = get_cities(st.session_state["country"], st.session_state["state"]) if st.session_state["country"] else []
        if st.session_state["city"] not in [""] + cities:
            st.session_state["city"] = ""
        st.selectbox("City", [""] + cities, key="city",
                     format_func=lambda x: "— Any —" if not x else x)

    # Row 3 — Settings
    pc1, pc2 = st.columns([2, 1])
    with pc1:
        rate_choice = st.radio(
            "Pay Type", ["Annual Salary", "Hourly Rate"],
            horizontal=True, key="_rate_radio",
        )
        st.session_state["rate_type"] = "hourly" if "Hourly" in rate_choice else "salary"
    with pc2:
        fx = get_fx()
        currencies = sorted(fx.keys()) if fx else ["USD"]
        if st.session_state["currency"] not in currencies:
            st.session_state["currency"] = "USD"
        st.selectbox(
            "Currency", currencies, key="currency",
            index=currencies.index(st.session_state["currency"])
            if st.session_state["currency"] in currencies else 0,
        )

    # Job description — collapsible
    with st.expander("Job description (optional — improves accuracy)"):
        st.text_area(
            "Paste key responsibilities or a full JD",
            key="job_desc", height=90, label_visibility="collapsed",
        )
        uploaded = st.file_uploader("Or upload .txt", type=["txt"])
        if uploaded:
            fkey = f"{uploaded.name}_{uploaded.size}"
            if st.session_state.get("_fkey") != fkey:
                try:
                    st.session_state["job_desc"] = uploaded.read().decode("utf-8", errors="ignore")
                    st.session_state["_fkey"] = fkey
                except Exception:
                    pass

    # CTA
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    can_go = bool(st.session_state["job_title"].strip() and st.session_state["country"])
    st.button("◆  Analyze Salary", disabled=not can_go, key="go_btn")


# ─────────────────────────────────────────────
# Run analysis
# ─────────────────────────────────────────────
if st.session_state.get("go_btn"):
    st.session_state["error"]  = None
    st.session_state["result"] = None
    with st.spinner("Searching 100+ salary sources and analyzing…"):
        try:
            st.session_state["result"] = run_analysis(
                job=st.session_state["job_title"].strip(),
                country=st.session_state["country"],
                state=st.session_state["state"],
                city=st.session_state["city"],
                exp_years=st.session_state["exp_years"],
                rate_type=st.session_state["rate_type"],
                job_desc=st.session_state["job_desc"],
            )
        except Exception as e:
            st.session_state["error"] = str(e)

if st.session_state.get("error"):
    st.error(st.session_state["error"])


# ─────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────
res = st.session_state.get("result")
if not res:
    st.stop()

curr   = st.session_state["currency"]
rt     = res["rate_type"]
stats  = res.get("stats")
dps    = res.get("data_table", [])
unit   = display_unit(rt, curr)
n_vals = len(res["data_table"])
n_src  = len(res.get("sources", []))
mean_usd = stats["mean"] if stats else (res["ai_mid_usd"])


# ── AI Summary ──────────────────────────────────────────────────
if res.get("ai_summary"):
    st.markdown(f"""
<div class="ai-card">
  <div class="ai-badge">AI Market Analysis</div>
  <p class="ai-text">{html_mod.escape(res['ai_summary'])}</p>
</div>""", unsafe_allow_html=True)

# ── Warnings ────────────────────────────────────────────────────
for w in res.get("warnings") or []:
    if w and w.strip():
        st.warning(w)

# ── Confidence ──────────────────────────────────────────────────
conf_lbl, conf_desc, conf_color = compute_confidence(stats, n_src)
st.markdown(f"""
<div class="conf-banner">
  <div class="conf-dot" style="background:{conf_color};box-shadow:0 0 6px {conf_color};"></div>
  <div><strong style="color:{conf_color};">{conf_lbl} confidence</strong>
    &nbsp;&middot;&nbsp;{html_mod.escape(conf_desc)}</div>
</div>""", unsafe_allow_html=True)


# ── Recommended Range hero ───────────────────────────────────────
ai_min_s = display_money(res["ai_min_usd"], curr, rt)
ai_max_s = display_money(res["ai_max_usd"], curr, rt)
ai_mid_s = display_money(res["ai_mid_usd"], curr, rt)
ai_pills = render_band_sources(
    res["ai_min_usd"], res["ai_max_usd"], res["ai_mid_usd"],
    curr, rt, dps, "#ffbf00",
)

st.markdown(f"""
<div class="range-card">
  <div class="range-glow"></div>
  <div class="ai-badge" style="margin-bottom:18px;font-size:13px;letter-spacing:.1em;">
    AI Recommended Range
  </div>
  <div class="range-grid">
    <div>
      <div class="range-lbl">Low End</div>
      <div class="range-val">{ai_min_s}</div>
      <div class="range-unit">{unit}</div>
    </div>
    <div class="range-sep">&mdash;</div>
    <div>
      <div class="range-lbl">High End</div>
      <div class="range-val">{ai_max_s}</div>
      <div class="range-unit">{unit}</div>
    </div>
    <div class="range-mid">
      <div class="range-mid-lbl">Midpoint</div>
      <div class="range-mid-val">{curr}&nbsp;{ai_mid_s}</div>
      <div class="range-unit">{unit}</div>
    </div>
  </div>
  {ai_pills}
</div>""", unsafe_allow_html=True)


# ── Market Breakdown ─────────────────────────────────────────────
if stats:
    st.markdown('<div class="sec-label">Market Breakdown</div>', unsafe_allow_html=True)

    mean_s   = display_money(stats["mean"],   curr, rt)
    median_s = display_money(stats["median"], curr, rt)
    min_s    = display_money(stats["min"],    curr, rt)
    max_s    = display_money(stats["max"],    curr, rt)
    count    = stats["count"]
    outliers = stats["count_raw"] - count

    # 4-column stat cards
    mc1, mc2, mc3, mc4 = st.columns(4)
    for col, lbl, val in [
        (mc1, "Average",  mean_s),
        (mc2, "Median",   median_s),
        (mc3, "Min",      min_s),
        (mc4, "Max",      max_s),
    ]:
        col.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-card-lbl">{lbl}</div>'
            f'<div class="stat-card-val">{curr}&nbsp;{val}</div>'
            f'<div class="stat-card-unit">{unit}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    caption_parts = [f"{count} data point{'s' if count != 1 else ''}"]
    if outliers > 0:
        caption_parts.append(f"{outliers} outlier{'s' if outliers != 1 else ''} removed")
    st.caption(" · ".join(caption_parts))

    if count < 5:
        st.markdown(f"""
<div class="low-data-warn">
  &#9888;&nbsp;Only {count} data point{"s" if count != 1 else ""} found —
  ranges are estimates. Broaden your search for better accuracy.
</div>""", unsafe_allow_html=True)

    rows_html = ""

    # Band 0 — AI Recommended
    lbl, desc, tc, tbg, la, ac = BAND_SPECS["ai"]
    ai_n = sum(1 for dp in dps if dp.get("annual_usd") and res["ai_min_usd"] <= dp["annual_usd"] <= res["ai_max_usd"])
    ai_p = render_band_sources(res["ai_min_usd"], res["ai_max_usd"], res["ai_mid_usd"], curr, rt, dps, ac)
    rows_html += render_band_row(lbl, desc, tc, tbg, la, ai_min_s, ai_max_s, ai_mid_s, curr, unit, ai_p, ai_n, "ai")
    rows_html += '<div class="band-divider"></div>'

    # Bands 1–2 — sigma (sigma3 collapses to sigma2 with typical data volumes, so omit)
    for sig in [1, 2]:
        lo_d, hi_d  = stats[f"sigma{sig}"]
        lbl, desc, tc, tbg, la, ac = BAND_SPECS[sig]
        lo_s  = display_money(lo_d, curr, rt)
        hi_s  = display_money(hi_d, curr, rt)
        avg_s = display_money(stats["mean"], curr, rt)
        sig_n = stats[f"sigma{sig}_count"]
        pills = render_band_sources(lo_d, hi_d, stats["mean"], curr, rt, dps, ac)
        rows_html += render_band_row(lbl, desc, tc, tbg, la, lo_s, hi_s, avg_s, curr, unit, pills, sig_n)

    st.markdown(rows_html, unsafe_allow_html=True)

elif n_vals == 1:
    val_s = display_money(res["data_table"][0]["annual_usd"], curr, rt)
    st.markdown(f"""
<div class="note-box" style="color:#f5d060;border-color:rgba(255,191,0,.3);background:rgba(255,191,0,.06);">
  Only 1 data point found ({curr} {val_s} {unit}). Try a broader job title or remove location filters.
</div>""", unsafe_allow_html=True)


# ── Debug sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Debug: Data Table")
    st.caption(f"{len(dps)} rows after outlier filter")
    if dps:
        import pandas as pd
        debug_rows = []
        for i, dp in enumerate(dps):
            debug_rows.append({
                "#": i + 1,
                "host": dp.get("host", ""),
                "annual_usd": dp.get("annual_usd"),
                "val_min_usd": dp.get("value_min_usd"),
                "val_max_usd": dp.get("value_max_usd"),
                "original": dp.get("original_value", ""),
                "label": dp.get("label", ""),
                "conf": dp.get("confidence", ""),
                "note": dp.get("conversion_note", ""),
                "url": dp.get("url", ""),
            })
        df = pd.DataFrame(debug_rows)
        st.dataframe(
            df,
            use_container_width=True,
            height=600,
            column_config={
                "url": st.column_config.LinkColumn("url", display_text="link"),
                "annual_usd": st.column_config.NumberColumn("annual_usd", format="$%.0f"),
                "val_min_usd": st.column_config.NumberColumn("val_min", format="$%.0f"),
                "val_max_usd": st.column_config.NumberColumn("val_max", format="$%.0f"),
            },
        )
    else:
        st.info("No data points.")

# ── Sources expander ─────────────────────────────────────────────
if res.get("sources"):
    with st.expander(f"View {len(res['sources'])} sources"):
        for s in res["sources"]:
            title = html_mod.escape((s.get("title") or pretty_host(s["url"]))[:90])
            host  = html_mod.escape(pretty_host(s["url"]))
            url   = html_mod.escape(s["url"], quote=True)
            q     = s.get("quality", 50)
            dot   = "#00cc55" if q >= 80 else "#7393f9" if q >= 60 else "#4a6080"
            st.markdown(f"""
<a class="src-item" href="{url}" target="_blank">
  <div class="src-dot" style="background:{dot};box-shadow:0 0 4px {dot};"></div>
  <div>
    <div class="src-title">{title}</div>
    <div class="src-meta">{host}</div>
  </div>
</a>""", unsafe_allow_html=True)
