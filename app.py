"""
Job Rate Finder -- Powered by Claude AI
Adaptive salary intelligence that adjusts to the data it receives.
"""

from __future__ import annotations

import html as html_mod
from typing import Dict, List, Optional

import streamlit as st

from utils import (
    MAX_DISPLAYED_SOURCES,
    HOURS_PER_YEAR,
    compute_stats,
    display_money,
    display_unit,
    find_evidence_for_range,
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


# -----------------------------------------------------------------
# Page config
# -----------------------------------------------------------------
st.set_page_config(page_title="Job Rate Finder", page_icon="briefcase", layout="centered")


# -----------------------------------------------------------------
# Styling
# -----------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700;9..40,800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --bg:       #060a11;
  --s1:       #0c1322;
  --s2:       #111c30;
  --s3:       #17243c;
  --b1:       rgba(255,255,255,.05);
  --b2:       rgba(255,255,255,.09);
  --b3:       rgba(255,255,255,.15);
  --tx:       #e2e8f4;
  --tx2:      #bcc8de;
  --mt:       #6a7d9f;
  --blue:     #3b82f6;
  --blue-d:   rgba(59,130,246,.10);
  --teal:     #14b8a6;
  --teal-d:   rgba(20,184,166,.08);
  --amber:    #f59e0b;
  --amber-d:  rgba(245,158,11,.08);
  --mono:     'JetBrains Mono', monospace;
  --sans:     'DM Sans', system-ui, sans-serif;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
  background: var(--bg) !important; color: var(--tx); font-family: var(--sans);
}
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 860px; }

div[data-testid="stContainer"] {
  background: var(--s1) !important; border: 1px solid var(--b2) !important;
  border-radius: 14px !important; padding: 20px 24px !important;
}

label, .stMarkdown p { color: var(--mt) !important; font-size: 13px !important; font-family: var(--sans) !important; font-weight: 500 !important; }
.stTextInput input, .stTextArea textarea {
  background: var(--s2) !important; border: 1px solid var(--b2) !important;
  color: var(--tx) !important; border-radius: 10px !important; font-family: var(--sans) !important; font-size: 14px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--blue) !important; box-shadow: 0 0 0 2px var(--blue-d) !important; }
.stSelectbox [data-baseweb="select"] > div {
  background: var(--s2) !important; border: 1px solid var(--b2) !important;
  border-radius: 10px !important; color: var(--tx) !important; font-family: var(--sans) !important;
}

.stButton button {
  width: 100%; border: none; border-radius: 12px; padding: 14px 20px;
  font-weight: 700; font-size: 14px; color: #fff; background: var(--blue);
  box-shadow: 0 4px 20px rgba(59,130,246,.25); font-family: var(--sans) !important;
  transition: all .15s ease;
}
.stButton button:hover { box-shadow: 0 8px 30px rgba(59,130,246,.35); transform: translateY(-1px); }
.stButton button:disabled { opacity: .4; box-shadow: none; transform: none; }

.hero { text-align: center; margin: 0 0 2rem; }
.hero h1 { font-size: 40px; font-weight: 800; margin: 0 0 4px; letter-spacing: -.03em; color: var(--tx); }
.hero p  { color: var(--mt); font-size: 14px; margin: 0; }

.sec { margin: 30px 0 12px; display: flex; align-items: center; gap: 12px; }
.sec span { font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--mt); white-space: nowrap; }
.sec::after { content: ''; flex: 1; height: 1px; background: var(--b1); }

.ai-card {
  background: var(--s1); border: 1px solid rgba(59,130,246,.2);
  border-radius: 14px; padding: 22px 26px; margin: 18px 0; position: relative; overflow: hidden;
}
.ai-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, var(--blue), var(--teal)); }
.ai-badge { font-size: 10px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: var(--blue); margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
.ai-badge::before { content: ''; width: 5px; height: 5px; border-radius: 50%; background: var(--blue); display: inline-block; box-shadow: 0 0 6px var(--blue); }
.ai-text { color: var(--tx2); font-size: 14px; line-height: 1.75; margin: 0; }

.conf-banner {
  display: flex; align-items: center; gap: 10px; margin: 6px 0 14px;
  padding: 10px 16px; border-radius: 10px; font-size: 13px; color: var(--tx2);
  border: 1px solid var(--b1); background: rgba(255,255,255,.02);
}
.conf-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.conf-banner strong { color: var(--tx); }

.range-card {
  background: var(--s1); border: 1px solid var(--b3); border-radius: 14px;
  padding: 26px 30px; margin: 14px 0 22px; position: relative; overflow: hidden;
}
.range-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, var(--blue), var(--teal)); }
.range-row { display: flex; align-items: flex-end; gap: 20px; flex-wrap: wrap; }
.range-lbl { font-size: 10px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--mt); margin-bottom: 6px; }
.range-val { font-family: var(--mono); font-size: 42px; font-weight: 700; letter-spacing: -.03em; line-height: 1; color: var(--tx); }
.range-unit { font-size: 12px; color: var(--mt); margin-top: 6px; }
.range-sep { font-size: 30px; color: var(--b3); padding-bottom: 10px; }
.range-mid { margin-left: auto; text-align: right; }
.range-mid-val { font-family: var(--mono); font-size: 24px; font-weight: 600; color: var(--teal); }

.bd-row {
  display: flex; align-items: center; gap: 14px; padding: 14px 18px;
  border: 1px solid var(--b1); border-radius: 12px; margin-bottom: 8px;
  background: var(--s1); transition: border-color .15s;
}
.bd-row:hover { border-color: var(--b3); }
.bd-row[data-featured="true"] { border-color: rgba(59,130,246,.25); background: linear-gradient(135deg, rgba(59,130,246,.03), var(--s1)); }
.bd-label-wrap { flex: 1; min-width: 0; }
.bd-desc  { font-size: 12px; color: var(--mt); margin: 0; }
.bd-range { font-family: var(--mono); font-size: 16px; font-weight: 600; color: var(--tx); white-space: nowrap; }
.bd-avg   { font-family: var(--mono); font-size: 12px; color: var(--teal); margin-top: 2px; text-align: right; }
.bd-tag {
  font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  padding: 3px 8px; border-radius: 6px; white-space: nowrap; flex-shrink: 0;
}

.ev-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.ev-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 8px; border: 1px solid var(--b1);
  background: rgba(255,255,255,.02); font-size: 11px; font-family: var(--mono);
  color: var(--mt); text-decoration: none; transition: all .15s;
}
.ev-pill:hover { border-color: var(--blue); color: var(--blue); }
.ev-val { color: var(--tx); font-weight: 600; }

.src {
  display: flex; gap: 10px; align-items: flex-start; padding: 10px 14px;
  border: 1px solid var(--b1); border-radius: 10px; background: rgba(255,255,255,.015);
  text-decoration: none; margin-bottom: 6px; transition: all .15s;
}
.src:hover { border-color: var(--blue); background: var(--blue-d); }
.src-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; margin-top: 6px; }
.src-title { color: var(--tx); font-weight: 600; font-size: 13px; margin: 0; }
.src-meta  { color: var(--mt); font-size: 11px; margin: 2px 0 0; }

.note {
  margin-top: 12px; padding: 12px 16px; border-radius: 10px; border: 1px solid var(--b1);
  background: rgba(255,255,255,.015); font-size: 12px; color: var(--mt); line-height: 1.6;
}

header, footer { visibility: hidden; }

.bd-reliability {
  font-size: 10px; font-weight: 600; letter-spacing: .06em;
  padding: 2px 7px; border-radius: 5px; white-space: nowrap; flex-shrink: 0; font-family: var(--mono);
}
.bd-reliability[data-level="high"]   { color: var(--teal);  background: var(--teal-d);  }
.bd-reliability[data-level="medium"] { color: var(--blue);  background: var(--blue-d);  }
.bd-reliability[data-level="low"]    { color: var(--amber); background: var(--amber-d); }
.low-data-warning {
  display:flex; align-items:center; gap:10px; margin:0 0 14px; padding:12px 16px;
  border-radius:10px; border:1px solid rgba(245,158,11,.35); background:rgba(245,158,11,.06);
  font-size:13px; color:var(--amber); line-height:1.5;
}
.band-divider { height:1px; background:var(--b1); margin:6px 0 10px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------
# Evidence rendering
# -----------------------------------------------------------------
def render_evidence(
    lo_usd: float, hi_usd: float, currency: str, rate_type: str,
    data_points: List[Dict], exclude_ids: Optional[set] = None,
) -> tuple:
    """Render up to 3 evidence pills. Returns (html, used_ids)."""
    if exclude_ids is None:
        exclude_ids = set()
    hits = find_evidence_for_range(lo_usd, hi_usd, data_points, max_evidence=6)
    hits = [dp for dp in hits if id(dp) not in exclude_ids][:3]
    if not hits:
        return "", set(exclude_ids)
    used = set(exclude_ids)
    pills = ""
    for dp in hits:
        used.add(id(dp))
        val = display_money(dp["annual_usd"], currency, rate_type)
        lbl = html_mod.escape((dp.get("label", "") or dp.get("host", ""))[:50])
        url = html_mod.escape(dp.get("url", "#"), quote=True)
        pills += f'<a class="ev-pill" href="{url}" target="_blank"><span class="ev-val">{currency} {val}</span> {lbl}</a>'
    return f'<div class="ev-row">{pills}</div>', used


# -----------------------------------------------------------------
# Adaptive range logic
# -----------------------------------------------------------------
RANGE_LABELS = {
    0: ("AI Recommended",   "Recommended offer range based on Claude's data analysis",              "var(--blue)",  "var(--blue-d)"),
    1: ("Typical Range",    "Where most salaries fall — within 1 standard deviation (~68%)",        "var(--teal)",  "var(--teal-d)"),
    2: ("Extended Range",   "Includes above- and below-average roles — within 2σ (~95%)",           "var(--teal)",  "rgba(20,184,166,.04)"),
    3: ("Full Spread",      "Nearly all reported salaries — within 3 standard deviations (~99.7%)", "var(--amber)", "var(--amber-d)"),
    4: ("Observed Min/Max", "Actual lowest and highest values after outlier removal",                "var(--mt)",    "rgba(255,255,255,.02)"),
}


def compute_confidence(stats: Optional[Dict], n_sources: int) -> tuple:
    """Return (label, description, color) for data confidence."""
    if stats is None:
        return ("Low", "Very limited data -- treat as a rough estimate.", "var(--amber)")
    n = stats["count"]
    cv = stats["stdev"] / stats["mean"] if stats["mean"] > 0 else 1.0
    if n >= 10 and cv < 0.35 and n_sources >= 5:
        return ("High", f"{n} data points from {n_sources} sources with consistent values.", "var(--teal)")
    elif n >= 5 and cv < 0.5:
        return ("Moderate", f"{n} data points with some variation in reported salaries.", "var(--blue)")
    else:
        parts = [f"{n} data points."]
        if cv >= 0.5:
            parts.append("Wide variation suggests mixed roles or seniority levels.")
        if n < 5:
            parts.append("More data would improve accuracy.")
        return ("Low", " ".join(parts), "var(--amber)")


# -----------------------------------------------------------------
# Reliability badge + band row helpers
# -----------------------------------------------------------------
def reliability_badge(n_points: int) -> str:
    if n_points >= 5:
        return f'<span class="bd-reliability" data-level="high">{n_points} pts</span>'
    elif n_points >= 2:
        return f'<span class="bd-reliability" data-level="medium">{n_points} pts</span>'
    return f'<span class="bd-reliability" data-level="low">{n_points} pts</span>'


def render_band_row(label, desc, color, bg_color, lo_s, hi_s, avg_s, curr, unit, ev_html, n_points, featured=False) -> str:
    badge = reliability_badge(n_points)
    feat_attr = 'data-featured="true"' if featured else 'data-featured="false"'
    return f"""
<div class="bd-row" {feat_attr}>
  <span class="bd-tag" style="color:{color};background:{bg_color};">{label}</span>
  <div class="bd-label-wrap">
    <div class="bd-desc">{desc}</div>
    {ev_html}
  </div>
  <div style="text-align:right;flex-shrink:0;">
    <div class="bd-range">{curr} {lo_s} &ndash; {hi_s}</div>
    <div class="bd-avg">avg {curr} {avg_s} {unit}</div>
  </div>
  {badge}
</div>"""


# -----------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------
def run_analysis(
    job: str, country: str, state: str, city: str,
    exp_years: str, rate_type: str, job_desc: str,
) -> Dict:
    core_job = job.strip()
    sources = search_web(core_job, country, state, city)
    if not sources:
        raise RuntimeError("No search results found. Try a different job title or location.")

    ai_data = claude_extract(
        job=core_job, country=country, state=state, city=city,
        exp_years=exp_years, rate_type=rate_type, job_desc=job_desc, sources=sources,
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
        data_points = [dp for dp in data_points if dp.get("annual_usd") and stats["min"] <= dp["annual_usd"] <= stats["max"]]

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


# -----------------------------------------------------------------
# Session state
# -----------------------------------------------------------------
for k, v in {"job_title": "", "exp_years": "", "job_desc": "", "country": "", "state": "", "city": "", "rate_type": "salary", "currency": "USD", "result": None, "error": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def on_country_change():
    st.session_state["state"] = ""
    st.session_state["city"] = ""
    st.session_state["currency"] = get_meta(st.session_state["country"]).get("currency", "USD")


def on_state_change():
    st.session_state["city"] = ""


# -----------------------------------------------------------------
# Hero
# -----------------------------------------------------------------
st.markdown('<div class="hero"><h1>Job Rate Finder</h1><p>Salary intelligence powered by Claude AI</p></div>', unsafe_allow_html=True)


# -----------------------------------------------------------------
# Input
# -----------------------------------------------------------------
with st.container(border=True):
    c1, c2 = st.columns([2, 1])
    with c1:
        st.text_input("Job Title *", key="job_title", placeholder="e.g. Video Editor, Senior Software Engineer")
    with c2:
        st.text_input("Years of Experience", key="exp_years", placeholder="e.g. 3-5 years")

    st.text_area("Job Description (optional)", key="job_desc", height=80, placeholder="Paste key responsibilities for better accuracy...")

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

    st.selectbox("Country *", [""] + countries, key="country", on_change=on_country_change, format_func=lambda x: "-- Select --" if not x else x)

    col1, col2, col3 = st.columns(3)
    with col1:
        states = get_states(st.session_state["country"]) if st.session_state["country"] else []
        if st.session_state["state"] not in [""] + states:
            st.session_state["state"] = ""
        st.selectbox("State / Province", [""] + states, key="state", on_change=on_state_change, format_func=lambda x: "-- Any --" if not x else x)
    with col2:
        cities = get_cities(st.session_state["country"], st.session_state["state"]) if st.session_state["country"] else []
        if st.session_state["city"] not in [""] + cities:
            st.session_state["city"] = ""
        st.selectbox("City", [""] + cities, key="city", format_func=lambda x: "-- Any --" if not x else x)
    with col3:
        rate_choice = st.radio("Pay Type", ["Annual Salary", "Hourly Rate"], horizontal=True)
        st.session_state["rate_type"] = "hourly" if "Hourly" in rate_choice else "salary"

    fx = get_fx()
    currencies = sorted(fx.keys()) if fx else ["USD"]
    if st.session_state["currency"] not in currencies:
        st.session_state["currency"] = "USD"
    st.selectbox("Display Currency", currencies, key="currency", index=currencies.index(st.session_state["currency"]) if st.session_state["currency"] in currencies else 0)

    can_go = bool(st.session_state["job_title"].strip() and st.session_state["country"])
    st.button("Analyze Salary Data", disabled=not can_go, key="go_btn")


# -----------------------------------------------------------------
# Run
# -----------------------------------------------------------------
if st.session_state.get("go_btn"):
    st.session_state["error"] = None
    st.session_state["result"] = None
    with st.spinner("Searching salary databases & analyzing with Claude AI..."):
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


# -----------------------------------------------------------------
# Results
# -----------------------------------------------------------------
res = st.session_state.get("result")
if res:
    curr = st.session_state["currency"]
    rt = res["rate_type"]
    stats = res.get("stats")
    dps = res.get("data_points", [])
    unit = display_unit(rt, curr)
    n_vals = len(res["annual_values"])
    n_src = len(res.get("sources", []))

    # -- AI Summary --
    if res.get("ai_summary"):
        st.markdown(f"""
<div class="ai-card">
  <div class="ai-badge">Claude AI Analysis</div>
  <p class="ai-text">{html_mod.escape(res['ai_summary'])}</p>
</div>""", unsafe_allow_html=True)

    # -- Warnings --
    for w in res.get("warnings") or []:
        if w and w.strip():
            st.warning(w)

    # -- Confidence --
    conf_lbl, conf_desc, conf_col = compute_confidence(stats, n_src)
    st.markdown(f"""
<div class="conf-banner">
  <div class="conf-dot" style="background:{conf_col};box-shadow:0 0 6px {conf_col};"></div>
  <div><strong>{conf_lbl} confidence</strong> &middot; {html_mod.escape(conf_desc)}</div>
</div>""", unsafe_allow_html=True)

    # -- Recommended Range --
    st.markdown('<div class="sec"><span>Recommended Salary Range</span></div>', unsafe_allow_html=True)

    ai_min_s = display_money(res["ai_min_usd"], curr, rt)
    ai_max_s = display_money(res["ai_max_usd"], curr, rt)
    ai_mid_s = display_money(res["ai_mid_usd"], curr, rt)
    ev_html, ev_used = render_evidence(res["ai_min_usd"], res["ai_max_usd"], curr, rt, dps)

    st.markdown(f"""
<div class="range-card">
  <div class="range-row">
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
      <div class="range-lbl">Midpoint</div>
      <div class="range-mid-val">{curr} {ai_mid_s}</div>
      <div class="range-unit">{unit}</div>
    </div>
  </div>
  {ev_html}
</div>""", unsafe_allow_html=True)

    # -- Market Breakdown (always 5 bands) --
    if stats:
        st.markdown('<div class="sec"><span>Market Breakdown</span></div>', unsafe_allow_html=True)

        mean_s = display_money(stats["mean"], curr, rt)
        median_s = display_money(stats["median"], curr, rt)
        min_s = display_money(stats["min"], curr, rt)
        max_s = display_money(stats["max"], curr, rt)
        count = stats["count"]
        outliers = stats["count_raw"] - count

        parts = [
            f"<strong>Average:</strong> {curr} {mean_s}",
            f"<strong>Median:</strong> {curr} {median_s}",
            f"<strong>Range:</strong> {curr} {min_s} &mdash; {curr} {max_s}",
            f"<strong>Data points:</strong> {count}",
        ]
        if outliers > 0:
            parts.append(f"<strong>Outliers removed:</strong> {outliers}")

        st.markdown(f"""
<div style="display:flex;flex-wrap:wrap;gap:8px 20px;padding:14px 18px;border-radius:12px;
  background:var(--s1);border:1px solid var(--b1);margin-bottom:14px;font-size:13px;color:var(--tx2);">
  {"&nbsp;&middot;&nbsp;".join(parts)}
</div>""", unsafe_allow_html=True)

        # Low-data warning above bands
        if count < 3:
            st.markdown(f"""
<div class="low-data-warning">
  &#9888; Only {count} data point{"s" if count != 1 else ""} found — these ranges are rough estimates.
  Try a broader job title or remove location filters for more reliable results.
</div>""", unsafe_allow_html=True)

        used_ev = set()
        rows_html = ""

        # Band 0: AI Recommended
        label0, desc0, color0, bg0 = RANGE_LABELS[0]
        ai_min_usd = res["ai_min_usd"]
        ai_max_usd = res["ai_max_usd"]
        ai_avg_usd = res["ai_mid_usd"]
        ai_n = sum(1 for dp in dps if dp.get("annual_usd") and ai_min_usd <= dp["annual_usd"] <= ai_max_usd)
        ev0, used_ev = render_evidence(ai_min_usd, ai_max_usd, curr, rt, dps, used_ev)
        rows_html += render_band_row(
            label0, desc0, color0, bg0,
            display_money(ai_min_usd, curr, rt), display_money(ai_max_usd, curr, rt),
            display_money(ai_avg_usd, curr, rt),
            curr, unit, ev0, ai_n, featured=True,
        )

        rows_html += '<div class="band-divider"></div>'

        # Bands 1–3: sigma rows
        for sig in [1, 2, 3]:
            lo, hi = stats[f"sigma{sig}"]
            label_s, desc_s, color_s, bg_s = RANGE_LABELS[sig]
            obs_lo = max(lo, stats["min"])
            obs_hi = min(hi, stats["max"])
            lo_s = display_money(obs_lo, curr, rt)
            hi_s = display_money(obs_hi, curr, rt)
            avg_s = display_money(stats["mean"], curr, rt)
            sig_n = stats[f"sigma{sig}_count"]
            ev_h, used_ev = render_evidence(obs_lo, obs_hi, curr, rt, dps, used_ev)
            rows_html += render_band_row(
                label_s, desc_s, color_s, bg_s,
                lo_s, hi_s, avg_s, curr, unit, ev_h, sig_n,
            )

        rows_html += '<div class="band-divider"></div>'

        # Band 4: Observed Min/Max
        label4, desc4, color4, bg4 = RANGE_LABELS[4]
        ev4, used_ev = render_evidence(stats["min"], stats["max"], curr, rt, dps, used_ev)
        rows_html += render_band_row(
            label4, desc4, color4, bg4,
            min_s, max_s, mean_s, curr, unit, ev4, count,
        )

        st.markdown(rows_html, unsafe_allow_html=True)

    elif n_vals == 1:
        val_s = display_money(res["annual_values"][0], curr, rt)
        st.markdown(f"""
<div class="note" style="border-color:var(--amber);background:var(--amber-d);">
  Only 1 data point found ({curr} {val_s} {unit}).
  Try a broader job title or remove location filters.
</div>""", unsafe_allow_html=True)

    # -- Sources (collapsed by default) --
    if res.get("sources"):
        with st.expander(f"View {len(res['sources'])} data sources"):
            for s in res["sources"]:
                title = html_mod.escape((s.get("title", "") or pretty_host(s["url"]))[:90])
                host = html_mod.escape(pretty_host(s["url"]))
                url = html_mod.escape(s["url"], quote=True)
                q = s.get("quality", 50)
                dot = "var(--blue)" if q >= 80 else "var(--teal)" if q >= 60 else "var(--mt)"
                st.markdown(f"""
<a class="src" href="{url}" target="_blank">
  <div class="src-dot" style="background:{dot};"></div>
  <div><div class="src-title">{title}</div><div class="src-meta">{host}</div></div>
</a>""", unsafe_allow_html=True)
