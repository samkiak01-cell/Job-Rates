"""
Job Rate Finder — Powered by Claude AI
myBasePay brand: clean white UI, Emerald/Wisteria/Marigold palette.
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
from search import search_web
from ai_extract import claude_extract, process_extraction


# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(page_title="Job Rate Finder", page_icon="💼", layout="centered")


# ─────────────────────────────────────────────
# CSS — myBasePay palette
# ─────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --emerald:   #006633;
  --prussian:  #121631;
  --wisteria:  #7393f9;
  --marigold:  #ffbf00;
  --f-mint:    #e7fcdb;
  --icy-blue:  #b7d4f7;
  --alabaster: #e8e8e8;
  --gray-50:   #f9fafb;
  --gray-100:  #f3f4f6;
  --gray-200:  #e5e7eb;
  --gray-400:  #9ca3af;
  --gray-500:  #6b7280;
  --gray-700:  #374151;
  --mono: 'JetBrains Mono', monospace;
  --sans: 'Inter', system-ui, sans-serif;
}

/* ── Global ── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {
  background: #ffffff !important;
  color: var(--prussian) !important;
  font-family: var(--sans) !important;
}
.block-container {
  padding-top: 0 !important;
  padding-bottom: 4rem !important;
  max-width: 900px !important;
}
[data-testid="stHeader"] { display: none !important; }
#MainMenu, footer { visibility: hidden; }

/* ── Input card ── */
div[data-testid="stContainer"] {
  background: #ffffff !important;
  border: 1px solid var(--gray-200) !important;
  border-radius: 16px !important;
  padding: 24px 28px !important;
}

/* ── Form labels ── */
label,
.stMarkdown p {
  color: var(--gray-700) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  font-family: var(--sans) !important;
}

/* ── Text inputs / textareas ── */
.stTextInput input,
.stTextArea textarea {
  background: var(--gray-50) !important;
  border: 1px solid var(--gray-200) !important;
  color: var(--prussian) !important;
  border-radius: 10px !important;
  font-family: var(--sans) !important;
  font-size: 14px !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
  border-color: var(--emerald) !important;
  box-shadow: 0 0 0 3px rgba(0,102,51,.1) !important;
}

/* ── Selectboxes ── */
.stSelectbox [data-baseweb="select"] > div {
  background: var(--gray-50) !important;
  border: 1px solid var(--gray-200) !important;
  color: var(--prussian) !important;
  border-radius: 10px !important;
  font-family: var(--sans) !important;
}

/* ── Marigold CTA button ── */
.stButton button {
  width: 100%;
  border: none;
  border-radius: 12px;
  padding: 14px 20px;
  font-weight: 700;
  font-size: 15px;
  color: #121631 !important;
  background: #ffbf00 !important;
  box-shadow: 0 4px 20px rgba(255,191,0,.35);
  font-family: var(--sans) !important;
  transition: all .15s ease;
}
.stButton button:hover {
  box-shadow: 0 8px 30px rgba(255,191,0,.5);
  transform: translateY(-1px);
}
.stButton button:disabled { opacity: .45; box-shadow: none; transform: none; }

/* ── AI summary card ── */
.ai-card {
  border-left: 3px solid;
  border-image: linear-gradient(180deg,#006633,#7393f9) 1;
  background: #f0fdf4;
  border-radius: 0 14px 14px 0;
  padding: 20px 24px;
  margin: 18px 0;
}
.ai-badge {
  font-size: 10px; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; color: var(--emerald); margin-bottom: 8px;
  display: flex; align-items: center; gap: 6px;
}
.ai-badge::before {
  content: ''; width: 5px; height: 5px; border-radius: 50%;
  background: var(--emerald); display: inline-block;
}
.ai-text { color: var(--prussian); font-size: 14px; line-height: 1.75; margin: 0; }

/* ── Confidence banner ── */
.conf-banner {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px; border-radius: 10px; font-size: 13px;
  border: 1px solid var(--gray-200); background: var(--gray-50);
  color: var(--gray-700); margin: 6px 0 14px;
}
.conf-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* ── Recommended range card ── */
.range-card {
  background: #ffffff;
  border: 1px solid var(--gray-200);
  border-radius: 16px;
  padding: 28px 32px;
  margin: 14px 0 22px;
  position: relative; overflow: hidden;
}
.range-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0;
  height: 3px; background: linear-gradient(90deg, #006633, #7393f9);
}
.range-grid { display: flex; align-items: flex-end; gap: 24px; flex-wrap: wrap; }
.range-lbl  { font-size: 10px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--gray-500); margin-bottom: 6px; }
.range-val  { font-family: var(--mono); font-size: 36px; font-weight: 700; letter-spacing: -.03em; line-height: 1; color: var(--prussian); }
.range-unit { font-size: 12px; color: var(--gray-500); margin-top: 6px; }
.range-sep  { font-size: 28px; color: var(--gray-300,#d1d5db); padding-bottom: 10px; }
.range-mid  { margin-left: auto; text-align: center; }
.range-mid-val { font-family: var(--mono); font-size: 22px; font-weight: 700; color: var(--emerald); }
.range-mid-lbl { font-size: 10px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--emerald); opacity: .7; margin-bottom: 4px; }

/* ── Stats bar ── */
.stats-bar {
  display: flex; flex-wrap: wrap; gap: 4px 18px;
  padding: 11px 18px; border-radius: 12px;
  background: var(--gray-50); border: 1px solid var(--gray-200);
  margin-bottom: 14px; font-size: 13px; color: var(--gray-700);
}

/* ── Low-data warning ── */
.low-data-warn {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px; border-radius: 10px;
  border: 1px solid rgba(217,119,6,.35);
  background: rgba(255,191,0,.08);
  font-size: 13px; color: #92400e; margin-bottom: 14px;
}

/* ── Band rows ── */
.bd-row {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 16px 20px;
  border: 1px solid var(--gray-200); border-radius: 14px;
  margin-bottom: 8px; background: #ffffff;
  transition: border-color .15s, box-shadow .15s;
}
.bd-row:hover { border-color: var(--gray-400); box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.bd-tag {
  font-size: 11px; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; padding: 4px 10px; border-radius: 8px;
  white-space: nowrap; flex-shrink: 0; margin-top: 1px;
}
.bd-content { flex: 1; min-width: 0; }
.bd-desc    { font-size: 12px; color: var(--gray-500); margin-bottom: 4px; }
.bd-right   { text-align: right; flex-shrink: 0; }
.bd-range   { font-family: var(--mono); font-size: 15px; font-weight: 600; color: var(--prussian); white-space: nowrap; }
.bd-avg     { font-family: var(--mono); font-size: 11px; color: var(--gray-500); margin-top: 3px; }
.pts-badge  {
  font-size: 10px; font-weight: 700; letter-spacing: .05em;
  padding: 2px 8px; border-radius: 20px;
  display: inline-block; margin-top: 5px; font-family: var(--mono);
}

/* ── Source pills ── */
.src-pills  { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
.src-pill   {
  display: inline-block; padding: 3px 9px; border-radius: 20px; border: 1px solid;
  font-size: 11px; font-family: var(--mono); text-decoration: none;
  transition: opacity .12s; white-space: nowrap; background: transparent;
}
.src-pill:hover { opacity: .7; }

/* ── Source list (expander) ── */
.src-item {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 10px 14px; border: 1px solid var(--gray-200);
  border-radius: 10px; text-decoration: none; margin-bottom: 6px;
  transition: all .15s; background: #ffffff;
}
.src-item:hover { border-color: var(--emerald); background: #f0fdf4; }
.src-dot   { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; margin-top: 6px; }
.src-title { color: var(--prussian); font-weight: 600; font-size: 13px; }
.src-meta  { color: var(--gray-500); font-size: 11px; margin-top: 2px; }

.band-divider { height: 1px; background: var(--gray-100); margin: 4px 0 10px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#006633,#7393f9);padding:40px 32px;
  border-radius:0 0 24px 24px;margin-bottom:28px;">
  <div style="font-size:30px;font-weight:800;color:#fff;letter-spacing:-.02em;">
    💼 Job Rate Finder
  </div>
  <div style="color:rgba(255,255,255,.82);font-size:14px;margin-top:6px;">
    Salary intelligence powered by Claude AI
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def compact_money(annual_usd: float, currency: str, rate_type: str) -> str:
    """Compact format for source pills: 72k, 1.2M, 38/hr."""
    val = to_currency(annual_usd, currency)
    if rate_type == "hourly":
        return f"{val / HOURS_PER_YEAR:,.0f}/hr"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:.0f}k"
    return f"{val:,.0f}"


def render_source_pills(
    lo_usd: float,
    hi_usd: float,
    currency: str,
    rate_type: str,
    data_points: List[Dict],
    accent_color: str,
    max_pills: int = 5,
) -> str:
    """Return HTML for source pills within [lo_usd, hi_usd]."""
    hits = [dp for dp in data_points if dp.get("annual_usd") and lo_usd <= dp["annual_usd"] <= hi_usd]
    hits.sort(key=lambda d: d.get("confidence", 0), reverse=True)
    if not hits:
        return ""
    pills = ""
    for dp in hits[:max_pills]:
        val  = compact_money(dp["annual_usd"], currency, rate_type)
        host = html_mod.escape((dp.get("host") or "source")[:28])
        url  = html_mod.escape(dp.get("url", "#"), quote=True)
        pills += (
            f'<a class="src-pill" href="{url}" target="_blank" '
            f'style="border-color:{accent_color};color:{accent_color};">'
            f'{host} {currency} {val}</a>'
        )
    return f'<div class="src-pills">{pills}</div>' if pills else ""


def pts_badge(n: int, band: str) -> str:
    """Point count badge with colour from plan spec."""
    if band == "ai":
        # Marigold for AI band
        color, bg = "#92400e", "rgba(255,191,0,.18)"
    elif n >= 8:
        color, bg = "#006633", "#e7fcdb"   # emerald
    elif n >= 3:
        color, bg = "#4f46e5", "#eff6ff"   # wisteria
    else:
        color, bg = "#92400e", "rgba(255,191,0,.18)"  # amber
    return (
        f'<span class="pts-badge" style="color:{color};background:{bg};">'
        f'{n} pt{"s" if n != 1 else ""}</span>'
    )


def render_band_row(
    label: str,
    desc: str,
    tag_color: str,
    tag_bg: str,
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
<div class="bd-row">
  <span class="bd-tag" style="color:{tag_color};background:{tag_bg};">{label}</span>
  <div class="bd-content">
    <div class="bd-desc">{desc}</div>
    {pills_html}
  </div>
  <div class="bd-right">
    <div class="bd-range">{curr} {lo_s} &ndash; {hi_s}</div>
    <div class="bd-avg">avg {curr} {avg_s} {unit}</div>
    {badge}
  </div>
</div>"""


# Band style specs: (label, desc, tag_color, tag_bg, pill_accent)
BAND_SPECS = {
    "ai": (
        "AI Recommended",
        "Recommended offer range from Claude&rsquo;s data analysis",
        "#92400e", "rgba(255,191,0,.15)", "#d97706",
    ),
    1: (
        "1&sigma; Typical",
        "Where most salaries fall &mdash; within 1 standard deviation (~68%)",
        "#006633", "#e7fcdb", "#006633",
    ),
    2: (
        "2&sigma; Extended",
        "Above- and below-average roles &mdash; within 2&sigma; (~95%)",
        "#4f46e5", "#eff6ff", "#4f46e5",
    ),
    3: (
        "3&sigma; Full Spread",
        "Nearly all reported salaries &mdash; within 3&sigma; (~99.7%)",
        "#374151", "#f3f4f6", "#374151",
    ),
    "obs": (
        "Observed Min / Max",
        "Actual lowest and highest values after outlier removal",
        "#6b7280", "#f9fafb", "#6b7280",
    ),
}


# ─────────────────────────────────────────────
# Confidence helper
# ─────────────────────────────────────────────
def compute_confidence(stats: Optional[Dict], n_sources: int) -> tuple:
    if stats is None:
        return ("Low", "Very limited data — treat as a rough estimate.", "#d97706")
    n  = stats["count"]
    cv = stats["stdev"] / stats["mean"] if stats["mean"] > 0 else 1.0
    if n >= 10 and cv < 0.35 and n_sources >= 5:
        return ("High", f"{n} data points from {n_sources} sources with consistent values.", "#006633")
    elif n >= 5 and cv < 0.5:
        return ("Moderate", f"{n} data points with some variation in reported salaries.", "#7393f9")
    else:
        parts = [f"{n} data points."]
        if cv >= 0.5:
            parts.append("Wide variation suggests mixed roles or seniority levels.")
        if n < 5:
            parts.append("More data would improve accuracy.")
        return ("Low", " ".join(parts), "#d97706")


# ─────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────
def run_analysis(
    job: str, country: str, state: str, city: str,
    exp_years: str, rate_type: str, job_desc: str,
) -> Dict:
    core_job = job.strip()
    sources  = search_web(core_job, country, state, city)
    if not sources:
        raise RuntimeError("No search results found. Try a different job title or location.")

    ai_data = claude_extract(
        job=core_job, country=country, state=state, city=city,
        exp_years=exp_years, rate_type=rate_type, job_desc=job_desc,
        sources=sources,
    )
    annual_values, data_points = process_extraction(ai_data, sources)
    if not annual_values:
        raise RuntimeError("Could not extract salary data. Try a more common job title or broader location.")

    ai_min = parse_num(ai_data.get("ai_recommended_min_usd")) or min(annual_values)
    ai_max = parse_num(ai_data.get("ai_recommended_max_usd")) or max(annual_values)
    ai_mid = parse_num(ai_data.get("ai_recommended_mid_usd")) or ((ai_min + ai_max) / 2)
    if ai_min > ai_max:
        ai_min, ai_max = ai_max, ai_min

    stats = compute_stats(annual_values, ai_min=ai_min, ai_max=ai_max)
    if stats:
        data_points = [
            dp for dp in data_points
            if dp.get("annual_usd") and stats["min"] <= dp["annual_usd"] <= stats["max"]
        ]

    return {
        "job": core_job,
        "location": ", ".join(x for x in [city, state, country] if x),
        "rate_type": rate_type,
        "sources": sources[:MAX_DISPLAYED_SOURCES],
        "data_points": data_points,
        "annual_values": annual_values,
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
    st.session_state["state"] = ""
    st.session_state["city"]  = ""
    st.session_state["currency"] = get_meta(st.session_state["country"]).get("currency", "USD")


def on_state_change():
    st.session_state["city"] = ""


# ─────────────────────────────────────────────
# Input card
# ─────────────────────────────────────────────
with st.container(border=True):
    c1, c2 = st.columns([2, 1])
    with c1:
        st.text_input("Job Title *", key="job_title", placeholder="e.g. Video Editor, Senior Software Engineer")
    with c2:
        st.text_input("Years of Experience", key="exp_years", placeholder="e.g. 3–5 years")

    with st.expander("Job Description (optional)"):
        st.text_area("Paste key responsibilities for better accuracy", key="job_desc", height=100,
                     label_visibility="collapsed")

        uploaded = st.file_uploader("Or upload JD (.txt)", type=["txt"], accept_multiple_files=False)
        if uploaded:
            fkey = f"{uploaded.name}_{uploaded.size}"
            if st.session_state.get("_fkey") != fkey:
                try:
                    st.session_state["job_desc"] = uploaded.read().decode("utf-8", errors="ignore")
                    st.session_state["_fkey"] = fkey
                except Exception:
                    pass

    try:
        countries = get_countries()
    except Exception:
        countries = []

    st.selectbox(
        "Country *", [""] + countries, key="country",
        on_change=on_country_change,
        format_func=lambda x: "— Select country —" if not x else x,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        states = get_states(st.session_state["country"]) if st.session_state["country"] else []
        if st.session_state["state"] not in [""] + states:
            st.session_state["state"] = ""
        st.selectbox("State / Province", [""] + states, key="state",
                     on_change=on_state_change, format_func=lambda x: "— Any —" if not x else x)
    with col2:
        cities = get_cities(st.session_state["country"], st.session_state["state"]) if st.session_state["country"] else []
        if st.session_state["city"] not in [""] + cities:
            st.session_state["city"] = ""
        st.selectbox("City", [""] + cities, key="city",
                     format_func=lambda x: "— Any —" if not x else x)
    with col3:
        rate_choice = st.radio("Pay Type", ["Annual Salary", "Hourly Rate"], horizontal=True)
        st.session_state["rate_type"] = "hourly" if "Hourly" in rate_choice else "salary"

    fx = get_fx()
    currencies = sorted(fx.keys()) if fx else ["USD"]
    if st.session_state["currency"] not in currencies:
        st.session_state["currency"] = "USD"
    st.selectbox(
        "Display Currency", currencies, key="currency",
        index=currencies.index(st.session_state["currency"]) if st.session_state["currency"] in currencies else 0,
    )

    can_go = bool(st.session_state["job_title"].strip() and st.session_state["country"])
    st.button("Analyze Salary", disabled=not can_go, key="go_btn")


# ─────────────────────────────────────────────
# Run analysis
# ─────────────────────────────────────────────
if st.session_state.get("go_btn"):
    st.session_state["error"]  = None
    st.session_state["result"] = None
    with st.spinner("Searching salary databases & analyzing with Claude AI…"):
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
dps    = res.get("data_points", [])
unit   = display_unit(rt, curr)
n_vals = len(res["annual_values"])
n_src  = len(res.get("sources", []))

# ── AI Summary ──
if res.get("ai_summary"):
    st.markdown(f"""
<div class="ai-card">
  <div class="ai-badge">✦ Claude AI Analysis</div>
  <p class="ai-text">{html_mod.escape(res['ai_summary'])}</p>
</div>""", unsafe_allow_html=True)

# ── Warnings ──
for w in res.get("warnings") or []:
    if w and w.strip():
        st.warning(w)

# ── Confidence banner ──
conf_lbl, conf_desc, conf_color = compute_confidence(stats, n_src)
st.markdown(f"""
<div class="conf-banner">
  <div class="conf-dot" style="background:{conf_color};box-shadow:0 0 6px {conf_color};"></div>
  <div><strong>{conf_lbl} confidence</strong> &middot; {html_mod.escape(conf_desc)}</div>
</div>""", unsafe_allow_html=True)

# ── Recommended Range hero card ──
ai_min_s = display_money(res["ai_min_usd"], curr, rt)
ai_max_s = display_money(res["ai_max_usd"], curr, rt)
ai_mid_s = display_money(res["ai_mid_usd"], curr, rt)

# Pills from the AI range
ai_pills = render_source_pills(
    res["ai_min_usd"], res["ai_max_usd"], curr, rt, dps,
    accent_color="#d97706",
)

st.markdown(f"""
<div class="range-card">
  <div class="range-grid">
    <div class="range-col">
      <div class="range-lbl">Low End</div>
      <div class="range-val">{ai_min_s}</div>
      <div class="range-unit">{unit}</div>
    </div>
    <div class="range-sep">&mdash;</div>
    <div class="range-col">
      <div class="range-lbl">High End</div>
      <div class="range-val">{ai_max_s}</div>
      <div class="range-unit">{unit}</div>
    </div>
    <div class="range-mid">
      <div class="range-mid-lbl">Midpoint</div>
      <div class="range-mid-val">{curr} {ai_mid_s}</div>
      <div class="range-unit">{unit}</div>
    </div>
  </div>
  {ai_pills}
</div>""", unsafe_allow_html=True)


# ── Market Breakdown ──
if stats:
    st.markdown('<div style="font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#6b7280;margin:24px 0 12px;">Market Breakdown</div>', unsafe_allow_html=True)

    mean_s   = display_money(stats["mean"],   curr, rt)
    median_s = display_money(stats["median"], curr, rt)
    min_s    = display_money(stats["min"],    curr, rt)
    max_s    = display_money(stats["max"],    curr, rt)
    count    = stats["count"]
    outliers = stats["count_raw"] - count

    stat_parts = [
        f"<strong>Average:</strong> {curr} {mean_s}",
        f"<strong>Median:</strong> {curr} {median_s}",
        f"<strong>{count} data point{'s' if count != 1 else ''}</strong>",
    ]
    if outliers > 0:
        stat_parts.append(f"{outliers} outlier{'s' if outliers != 1 else ''} removed")

    st.markdown(f"""
<div class="stats-bar">{"&nbsp;&middot;&nbsp;".join(stat_parts)}</div>""",
        unsafe_allow_html=True,
    )

    # Low-data warning
    if count < 5:
        st.markdown(f"""
<div class="low-data-warn">
  &#9888;&nbsp; Only {count} data point{"s" if count != 1 else ""} found — ranges are estimates.
  Broaden your search or remove location filters for more reliable results.
</div>""", unsafe_allow_html=True)

    rows_html = ""

    # ── Band 0: AI Recommended ──
    lbl, desc, tc, tbg, ac = BAND_SPECS["ai"]
    ai_n = sum(1 for dp in dps if dp.get("annual_usd") and res["ai_min_usd"] <= dp["annual_usd"] <= res["ai_max_usd"])
    ai_p = render_source_pills(res["ai_min_usd"], res["ai_max_usd"], curr, rt, dps, ac)
    rows_html += render_band_row(
        lbl, desc, tc, tbg,
        ai_min_s, ai_max_s, ai_mid_s,
        curr, unit, ai_p, ai_n, band_key="ai",
    )
    rows_html += '<div class="band-divider"></div>'

    # ── Bands 1–3: sigma rows ──
    for sig in [1, 2, 3]:
        lo_d, hi_d = stats[f"sigma{sig}_display"]
        lbl, desc, tc, tbg, ac = BAND_SPECS[sig]
        lo_s  = display_money(lo_d, curr, rt)
        hi_s  = display_money(hi_d, curr, rt)
        avg_s = display_money(stats["mean"], curr, rt)
        sig_n = stats[f"sigma{sig}_count"]
        pills = render_source_pills(lo_d, hi_d, curr, rt, dps, ac)
        rows_html += render_band_row(
            lbl, desc, tc, tbg,
            lo_s, hi_s, avg_s,
            curr, unit, pills, sig_n,
        )

    rows_html += '<div class="band-divider"></div>'

    # ── Band 4: Observed Min/Max ──
    lbl, desc, tc, tbg, ac = BAND_SPECS["obs"]
    obs_pills = render_source_pills(stats["min"], stats["max"], curr, rt, dps, ac)
    rows_html += render_band_row(
        lbl, desc, tc, tbg,
        min_s, max_s, mean_s,
        curr, unit, obs_pills, count, band_key="obs",
    )

    st.markdown(rows_html, unsafe_allow_html=True)

elif n_vals == 1:
    val_s = display_money(res["annual_values"][0], curr, rt)
    st.markdown(f"""
<div style="padding:14px 18px;border-radius:12px;border:1px solid rgba(255,191,0,.4);
  background:rgba(255,191,0,.08);font-size:13px;color:#92400e;margin-top:12px;">
  Only 1 data point found ({curr} {val_s} {unit}).
  Try a broader job title or remove location filters.
</div>""", unsafe_allow_html=True)


# ── Sources expander ──
if res.get("sources"):
    with st.expander(f"View {len(res['sources'])} sources"):
        for s in res["sources"]:
            title = html_mod.escape((s.get("title") or pretty_host(s["url"]))[:90])
            host  = html_mod.escape(pretty_host(s["url"]))
            url   = html_mod.escape(s["url"], quote=True)
            q     = s.get("quality", 50)
            dot   = "#006633" if q >= 80 else "#7393f9" if q >= 60 else "#9ca3af"
            st.markdown(f"""
<a class="src-item" href="{url}" target="_blank">
  <div class="src-dot" style="background:{dot};"></div>
  <div>
    <div class="src-title">{title}</div>
    <div class="src-meta">{host}</div>
  </div>
</a>""", unsafe_allow_html=True)
