"""
Job Rate Finder — Powered by Claude AI
Statistical salary intelligence with sigma-range analysis.
"""

from __future__ import annotations

import html
from typing import Dict, List

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


# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(page_title="Job Rate Finder", page_icon="💼", layout="centered")


# ─────────────────────────────────────────────
# Styling
# ─────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --bg:         #04080f;
  --surface:    #0b1120;
  --surface2:   #111b2e;
  --surface3:   #162036;
  --border:     rgba(255,255,255,.06);
  --border2:    rgba(255,255,255,.10);
  --border3:    rgba(255,255,255,.16);
  --text:       #e4eaf6;
  --text2:      #c0cbdf;
  --muted:      #6b7fa3;
  --accent:     #3b82f6;
  --accent-dim: rgba(59,130,246,.12);
  --teal:       #14b8a6;
  --teal-dim:   rgba(20,184,166,.10);
  --amber:      #f59e0b;
  --amber-dim:  rgba(245,158,11,.10);
  --rose:       #f43f5e;
  --rose-dim:   rgba(244,63,94,.10);
  --mono:       'JetBrains Mono', monospace;
  --sans:       'DM Sans', system-ui, sans-serif;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
  background: var(--bg) !important;
  color: var(--text);
  font-family: var(--sans);
}
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 880px; }

/* --- Card containers --- */
div[data-testid="stContainer"] {
  background: var(--surface) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 16px !important;
  padding: 20px 24px !important;
}

/* --- Inputs --- */
label, .stMarkdown p {
  color: var(--muted) !important;
  font-size: 13px !important;
  font-family: var(--sans) !important;
  font-weight: 500 !important;
}
.stTextInput input, .stTextArea textarea {
  background: var(--surface2) !important;
  border: 1px solid var(--border2) !important;
  color: var(--text) !important;
  border-radius: 10px !important;
  font-family: var(--sans) !important;
  font-size: 14px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px var(--accent-dim) !important;
}
.stSelectbox [data-baseweb="select"] > div {
  background: var(--surface2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
  font-family: var(--sans) !important;
}

/* --- Button --- */
.stButton button {
  width: 100%;
  border: none;
  border-radius: 12px;
  padding: 14px 20px;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: .01em;
  color: #fff;
  background: var(--accent);
  box-shadow: 0 4px 20px rgba(59,130,246,.25);
  font-family: var(--sans) !important;
  transition: all .15s ease;
}
.stButton button:hover {
  box-shadow: 0 8px 30px rgba(59,130,246,.35);
  transform: translateY(-1px);
}
.stButton button:disabled {
  opacity: .4;
  box-shadow: none;
  transform: none;
}

/* --- Hero --- */
.hero { text-align: center; margin: 0 0 2rem; padding: 1rem 0; }
.hero h1 {
  font-size: 42px; font-weight: 800; margin: 0 0 6px;
  letter-spacing: -.03em; line-height: 1.1;
  color: var(--text);
}
.hero p { color: var(--muted); font-size: 14px; margin: 0; font-weight: 400; }

/* --- Section dividers --- */
.sec { margin: 32px 0 14px; display: flex; align-items: center; gap: 12px; }
.sec span {
  font-size: 11px; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: var(--muted); white-space: nowrap;
}
.sec::after { content: ''; flex: 1; height: 1px; background: var(--border); }

/* --- AI summary --- */
.ai-card {
  background: linear-gradient(135deg, var(--surface2), var(--surface));
  border: 1px solid rgba(59,130,246,.25);
  border-radius: 16px;
  padding: 24px 28px;
  margin: 20px 0;
  position: relative;
  overflow: hidden;
}
.ai-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--accent), var(--teal));
}
.ai-badge {
  font-size: 10px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
  color: var(--accent); margin-bottom: 10px;
  display: flex; align-items: center; gap: 6px;
}
.ai-badge::before {
  content: ''; width: 5px; height: 5px; border-radius: 50%;
  background: var(--accent); display: inline-block;
  box-shadow: 0 0 8px var(--accent);
}
.ai-text { color: var(--text2); font-size: 14px; line-height: 1.75; margin: 0; }

/* --- Data point badge --- */
.dp-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 99px;
  background: var(--accent-dim); border: 1px solid rgba(59,130,246,.2);
  font-size: 12px; color: var(--accent); font-weight: 600;
  font-family: var(--mono);
}

/* --- Recommended range hero --- */
.range-card {
  background: var(--surface);
  border: 1px solid var(--border3);
  border-radius: 16px;
  padding: 28px 32px;
  margin: 16px 0 24px;
  position: relative;
  overflow: hidden;
}
.range-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--accent), var(--teal), var(--amber));
}
.range-row {
  display: flex; align-items: flex-end; gap: 20px; flex-wrap: wrap;
}
.range-block {}
.range-lbl {
  font-size: 10px; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: var(--muted); margin-bottom: 6px;
}
.range-val {
  font-family: var(--mono); font-size: 44px; font-weight: 700;
  letter-spacing: -.03em; line-height: 1; color: var(--text);
}
.range-unit { font-size: 12px; color: var(--muted); margin-top: 6px; }
.range-sep { font-size: 32px; color: var(--border3); padding-bottom: 10px; }
.range-mid {
  margin-left: auto; text-align: right;
}
.range-mid-val {
  font-family: var(--mono); font-size: 26px; font-weight: 600; color: var(--teal);
}

/* --- Quick stats grid --- */
.stats-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px; margin: 14px 0;
}
.stat-box {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
}
.stat-lbl {
  font-size: 10px; font-weight: 700; letter-spacing: .1em;
  text-transform: uppercase; color: var(--muted); margin-bottom: 6px;
}
.stat-val {
  font-family: var(--mono); font-size: 18px; font-weight: 600; color: var(--text);
}
.stat-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }

/* --- Sigma cards --- */
.sigma-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px; margin: 14px 0;
}
.sigma-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px 20px;
  transition: border-color .15s;
}
.sigma-card:hover { border-color: var(--border3); }
.sigma-card[data-highlight="true"] {
  border-color: rgba(59,130,246,.3);
  background: linear-gradient(135deg, rgba(59,130,246,.04), var(--surface2));
}
.sigma-hdr {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
}
.sigma-tag {
  font-size: 10px; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; padding: 3px 8px; border-radius: 6px;
}
.sigma-pct { font-size: 11px; color: var(--muted); font-weight: 500; }
.sigma-range {
  font-family: var(--mono); font-size: 17px; font-weight: 600;
  color: var(--text); margin-bottom: 4px;
}
.sigma-avg {
  font-family: var(--mono); font-size: 12px; color: var(--teal); font-weight: 500;
}
.sigma-bar {
  height: 3px; background: var(--border); border-radius: 99px;
  margin-top: 12px; overflow: hidden;
}
.sigma-fill { height: 100%; border-radius: 99px; }

/* --- Evidence pills --- */
.ev-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.ev-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 8px;
  border: 1px solid var(--border); background: rgba(255,255,255,.02);
  font-size: 11px; font-family: var(--mono); color: var(--muted);
  text-decoration: none; transition: all .15s;
}
.ev-pill:hover { border-color: var(--accent); color: var(--accent); }
.ev-val { color: var(--text); font-weight: 600; }

/* --- Source cards --- */
.src {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 10px 14px; border: 1px solid var(--border);
  border-radius: 12px; background: rgba(255,255,255,.015);
  text-decoration: none; margin-bottom: 8px;
  transition: all .15s;
}
.src:hover { border-color: var(--accent); background: var(--accent-dim); }
.src-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; margin-top: 6px; }
.src-title { color: var(--text); font-weight: 600; font-size: 13px; margin: 0; line-height: 1.4; }
.src-meta { color: var(--muted); font-size: 11px; margin: 2px 0 0; }

/* --- Methodology note --- */
.method-note {
  margin-top: 12px; padding: 12px 16px; border-radius: 10px;
  border: 1px solid var(--border); background: rgba(255,255,255,.015);
  font-size: 12px; color: var(--muted); line-height: 1.6;
}

header, footer { visibility: hidden; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Render helpers
# ─────────────────────────────────────────────
def render_evidence_pills(
    lo_usd: float, hi_usd: float, currency: str, rate_type: str,
    data_points: List[Dict], exclude_ids: set = None,
) -> tuple[str, set]:
    """
    Render up to 3 evidence pills for data points within a range.
    Returns (html_string, set_of_used_dp_ids) so callers can deduplicate.
    """
    if exclude_ids is None:
        exclude_ids = set()

    hits = find_evidence_for_range(lo_usd, hi_usd, data_points, max_evidence=6)
    # Filter out already-shown evidence
    hits = [dp for dp in hits if id(dp) not in exclude_ids][:3]

    if not hits:
        return "", exclude_ids

    used = set(exclude_ids)
    pills = ""
    for dp in hits:
        used.add(id(dp))
        val_str = display_money(dp["annual_usd"], currency, rate_type)
        lbl = html.escape((dp.get("label", "") or dp.get("host", "source"))[:50])
        url_safe = html.escape(dp.get("url", "#"), quote=True)
        orig = html.escape(dp.get("original_value", "")[:30])
        title_attr = f' title="{orig}"' if orig else ""
        pills += (
            f'<a class="ev-pill" href="{url_safe}" target="_blank"{title_attr}>'
            f'<span class="ev-val">{currency} {val_str}</span> {lbl}</a>'
        )
    return f'<div class="ev-row">{pills}</div>', used


def sigma_styles(sigma: int) -> tuple[str, str, str]:
    """Return (color, bg_color, tag_label) for a sigma level."""
    if sigma == 1:
        return "var(--accent)", "var(--accent-dim)", "± 1σ"
    elif sigma == 2:
        return "var(--teal)", "var(--teal-dim)", "± 2σ"
    else:
        return "var(--amber)", "var(--amber-dim)", "± 3σ"


def render_sigma_card(
    sigma: int,
    lo_usd: float,
    hi_usd: float,
    mean_usd: float,
    currency: str,
    rate_type: str,
    data_points: List[Dict],
    observed_min: float,
    observed_max: float,
    exclude_ids: set = None,
) -> tuple[str, set]:
    """
    Render a single sigma range card.
    Clamps displayed range to observed min/max so we don't show "$0".
    Returns (html_string, updated_exclude_ids).
    """
    color, bg, tag = sigma_styles(sigma)
    pct = {1: "68%", 2: "95%", 3: "99.7%"}[sigma]

    # Clamp to observed data range — no "$0" or unrealistic extremes
    display_lo = max(lo_usd, observed_min)
    display_hi = min(hi_usd, observed_max)

    lo_s = display_money(display_lo, currency, rate_type)
    hi_s = display_money(display_hi, currency, rate_type)
    avg_s = display_money(mean_usd, currency, rate_type)
    unit = display_unit(rate_type, currency)
    ev, used = render_evidence_pills(display_lo, display_hi, currency, rate_type, data_points, exclude_ids)
    highlight = "true" if sigma == 1 else "false"
    bar_pct = {1: 68, 2: 95, 3: 100}[sigma]

    return f"""
<div class="sigma-card" data-highlight="{highlight}">
  <div class="sigma-hdr">
    <span class="sigma-tag" style="color:{color};background:{bg};">{tag}</span>
    <span class="sigma-pct">{pct} of market</span>
  </div>
  <div class="sigma-range">{currency} {lo_s} — {hi_s}</div>
  <div class="sigma-avg">avg {currency} {avg_s} {unit}</div>
  <div class="sigma-bar"><div class="sigma-fill" style="width:{bar_pct}%;background:{color};"></div></div>
  {ev}
</div>""", used


# ─────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────
def run_analysis(
    job: str,
    country: str,
    state: str,
    city: str,
    exp_years: str,
    rate_type: str,
    job_desc: str,
) -> Dict:
    """Full pipeline: search → AI extract → statistics → display bundle."""

    # 1. Search — use ONLY the job title (no JD text) for queries
    core_job = job.strip()
    sources = search_web(core_job, country, state, city)
    if not sources:
        raise RuntimeError("No search results found. Try a different job title or location.")

    # 2. AI extraction — send JD as context to Claude only
    ai_data = claude_extract(
        job=core_job,
        country=country,
        state=state,
        city=city,
        exp_years=exp_years,
        rate_type=rate_type,
        job_desc=job_desc,
        sources=sources,
    )

    # 3. Process extraction results
    annual_values, data_points = process_extraction(ai_data, sources)

    if not annual_values:
        raise RuntimeError(
            "Could not extract salary data from search results. "
            "Try a more common job title or broader location."
        )

    # 4. AI recommended range (extract first — needed for stats filtering)
    ai_min = parse_num(ai_data.get("ai_recommended_min_usd")) or min(annual_values)
    ai_max = parse_num(ai_data.get("ai_recommended_max_usd")) or max(annual_values)
    ai_mid = parse_num(ai_data.get("ai_recommended_mid_usd")) or ((ai_min + ai_max) / 2)
    if ai_min > ai_max:
        ai_min, ai_max = ai_max, ai_min

    # 5. Statistics — pass AI range for sanity-check outlier removal
    stats = compute_stats(annual_values, ai_min=ai_min, ai_max=ai_max)

    # 6. Filter data_points to match what stats kept (remove outliers from evidence too)
    if stats:
        kept_min = stats["min"]
        kept_max = stats["max"]
        data_points_filtered = [
            dp for dp in data_points
            if dp.get("annual_usd") and kept_min <= dp["annual_usd"] <= kept_max
        ]
    else:
        data_points_filtered = data_points

    return {
        "job": core_job,
        "location": ", ".join(x for x in [city, state, country] if x),
        "rate_type": rate_type,
        "sources": sources[:MAX_DISPLAYED_SOURCES],
        "data_points": data_points_filtered,
        "annual_values": annual_values,
        "stats": stats,
        "ai_min_usd": ai_min,
        "ai_max_usd": ai_max,
        "ai_mid_usd": ai_mid,
        "ai_summary": ai_data.get("ai_summary", ""),
        "warnings": ai_data.get("warnings") or [],
    }


# ─────────────────────────────────────────────
# Session state init
# ─────────────────────────────────────────────
DEFAULTS = {
    "job_title": "", "exp_years": "", "job_desc": "",
    "country": "", "state": "", "city": "",
    "rate_type": "salary", "currency": "USD",
    "result": None, "error": None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def on_country_change():
    st.session_state["state"] = ""
    st.session_state["city"] = ""
    st.session_state["currency"] = get_meta(st.session_state["country"]).get("currency", "USD")


def on_state_change():
    st.session_state["city"] = ""


# ─────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>💼 Job Rate Finder</h1>
  <p>Statistical salary intelligence · Powered by Claude AI</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Input form
# ─────────────────────────────────────────────
with st.container(border=True):
    c1, c2 = st.columns([2, 1])
    with c1:
        st.text_input(
            "Job Title *",
            key="job_title",
            placeholder="e.g. Video Editor, Senior Software Engineer, Data Analyst",
        )
    with c2:
        st.text_input(
            "Years of Experience",
            key="exp_years",
            placeholder="e.g. 3-5 years, 10+",
        )

    st.text_area(
        "Job Description (optional — helps Claude understand the exact role)",
        key="job_desc",
        height=90,
        placeholder="Paste key responsibilities & skills for better accuracy…",
    )

    uploaded = st.file_uploader("Or upload JD (.txt)", type=["txt"], accept_multiple_files=False)
    if uploaded:
        fkey = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.get("_fkey") != fkey:
            try:
                st.session_state["job_desc"] = uploaded.read().decode("utf-8", errors="ignore")
                st.session_state["_fkey"] = fkey
            except Exception:
                pass

    # Country / State / City
    try:
        countries = get_countries()
    except Exception:
        countries = []

    st.selectbox(
        "Country *", [""] + countries,
        key="country",
        on_change=on_country_change,
        format_func=lambda x: "— Select country —" if not x else x,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        states = get_states(st.session_state["country"]) if st.session_state["country"] else []
        if st.session_state["state"] not in [""] + states:
            st.session_state["state"] = ""
        st.selectbox(
            "State / Province", [""] + states,
            key="state",
            on_change=on_state_change,
            format_func=lambda x: "— Any —" if not x else x,
        )
    with col2:
        cities = get_cities(st.session_state["country"], st.session_state["state"]) if st.session_state["country"] else []
        if st.session_state["city"] not in [""] + cities:
            st.session_state["city"] = ""
        st.selectbox(
            "City", [""] + cities,
            key="city",
            format_func=lambda x: "— Any —" if not x else x,
        )
    with col3:
        rate_choice = st.radio("Pay Type", ["Annual Salary", "Hourly Rate"], horizontal=True)
        st.session_state["rate_type"] = "hourly" if "Hourly" in rate_choice else "salary"

    # Currency
    fx = get_fx()
    currencies = sorted(fx.keys()) if fx else ["USD"]
    if st.session_state["currency"] not in currencies:
        st.session_state["currency"] = "USD"
    st.selectbox(
        "Display Currency",
        currencies,
        key="currency",
        index=currencies.index(st.session_state["currency"]) if st.session_state["currency"] in currencies else 0,
    )

    can_go = bool(st.session_state["job_title"].strip() and st.session_state["country"])
    st.button("🔍  Analyze Salary Data", disabled=not can_go, key="go_btn")


# ─────────────────────────────────────────────
# Run analysis
# ─────────────────────────────────────────────
if st.session_state.get("go_btn"):
    st.session_state["error"] = None
    st.session_state["result"] = None

    with st.spinner("Searching salary databases & analyzing with Claude AI…"):
        try:
            result = run_analysis(
                job=st.session_state["job_title"].strip(),
                country=st.session_state["country"],
                state=st.session_state["state"],
                city=st.session_state["city"],
                exp_years=st.session_state["exp_years"],
                rate_type=st.session_state["rate_type"],
                job_desc=st.session_state["job_desc"],
            )
            st.session_state["result"] = result
        except Exception as e:
            st.session_state["error"] = str(e)


# ─────────────────────────────────────────────
# Error display
# ─────────────────────────────────────────────
if st.session_state.get("error"):
    st.error(f"❌ {st.session_state['error']}")


# ─────────────────────────────────────────────
# Results display
# ─────────────────────────────────────────────
res = st.session_state.get("result")
if res:
    curr = st.session_state["currency"]
    rt = res["rate_type"]
    stats = res.get("stats")
    dps = res.get("data_points", [])
    unit = display_unit(rt, curr)

    # ── AI Summary ──
    if res.get("ai_summary"):
        st.markdown(f"""
<div class="ai-card">
  <div class="ai-badge">Claude AI Analysis</div>
  <p class="ai-text">{html.escape(res['ai_summary'])}</p>
</div>
""", unsafe_allow_html=True)

    # ── Warnings ──
    for w in res.get("warnings") or []:
        if w and w.strip():
            st.warning(w)

    # ── Data points count ──
    n = len(res["annual_values"])
    st.markdown(
        f'<div class="dp-badge">📊 {n} data point{"s" if n != 1 else ""} extracted from '
        f'{len(res.get("sources", []))} sources</div>',
        unsafe_allow_html=True,
    )

    # ── AI Recommended Range ──
    st.markdown('<div class="sec"><span>AI Recommended Range</span></div>', unsafe_allow_html=True)

    ai_min_s = display_money(res["ai_min_usd"], curr, rt)
    ai_max_s = display_money(res["ai_max_usd"], curr, rt)
    ai_mid_s = display_money(res["ai_mid_usd"], curr, rt)
    ev_pills, _ = render_evidence_pills(res["ai_min_usd"], res["ai_max_usd"], curr, rt, dps)

    st.markdown(f"""
<div class="range-card">
  <div class="range-row">
    <div class="range-block">
      <div class="range-lbl">Minimum</div>
      <div class="range-val">{ai_min_s}</div>
      <div class="range-unit">{unit}</div>
    </div>
    <div class="range-sep">—</div>
    <div class="range-block">
      <div class="range-lbl">Maximum</div>
      <div class="range-val">{ai_max_s}</div>
      <div class="range-unit">{unit}</div>
    </div>
    <div class="range-block range-mid">
      <div class="range-lbl">Midpoint</div>
      <div class="range-mid-val">{curr} {ai_mid_s}</div>
      <div class="range-unit">{unit}</div>
    </div>
  </div>
  {ev_pills}
</div>
""", unsafe_allow_html=True)

    # ── Statistical Distribution ──
    if stats:
        st.markdown('<div class="sec"><span>Statistical Distribution</span></div>', unsafe_allow_html=True)

        mean_s = display_money(stats["mean"], curr, rt)
        median_s = display_money(stats["median"], curr, rt)
        min_s = display_money(stats["min"], curr, rt)
        max_s = display_money(stats["max"], curr, rt)

        st.markdown(f"""
<div class="stats-grid">
  <div class="stat-box">
    <div class="stat-lbl">Mean</div>
    <div class="stat-val">{curr} {mean_s}</div>
    <div class="stat-sub">{unit}</div>
  </div>
  <div class="stat-box">
    <div class="stat-lbl">Median</div>
    <div class="stat-val">{curr} {median_s}</div>
    <div class="stat-sub">{unit}</div>
  </div>
  <div class="stat-box">
    <div class="stat-lbl">Market Min</div>
    <div class="stat-val">{curr} {min_s}</div>
    <div class="stat-sub">{unit}</div>
  </div>
  <div class="stat-box">
    <div class="stat-lbl">Market Max</div>
    <div class="stat-val">{curr} {max_s}</div>
    <div class="stat-sub">{unit}</div>
  </div>
  <div class="stat-box">
    <div class="stat-lbl">Data Points</div>
    <div class="stat-val" style="color:var(--accent);">{stats['count']}</div>
    <div class="stat-sub">observations{f" ({stats['count_raw']} raw, {stats['count_raw'] - stats['count']} outliers removed)" if stats['count_raw'] != stats['count'] else ""}</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # Sigma cards — cascade evidence deduplication across cards
        sigma_html = '<div class="sigma-grid">'
        used_evidence: set = set()
        for sig in [1, 2, 3]:
            lo, hi = stats[f"sigma{sig}"]
            card_html, used_evidence = render_sigma_card(
                sigma=sig,
                lo_usd=lo,
                hi_usd=hi,
                mean_usd=stats["mean"],
                currency=curr,
                rate_type=rt,
                data_points=dps,
                observed_min=stats["min"],
                observed_max=stats["max"],
                exclude_ids=used_evidence,
            )
            sigma_html += card_html
        sigma_html += "</div>"
        st.markdown(sigma_html, unsafe_allow_html=True)

        # Methodology note
        stdev_s = display_money(stats["stdev"], curr, rt)
        st.markdown(f"""
<div class="method-note">
  σ ranges computed from {stats['count']} data points after IQR-based outlier removal.
  Standard deviation: {curr} {stdev_s} {unit}.
  ± 1σ covers ~68% of market rates, ± 2σ covers ~95%, ± 3σ covers ~99.7%.
  Wide ranges may indicate mixed seniority levels in the source data.
</div>
""", unsafe_allow_html=True)

    elif len(res["annual_values"]) == 1:
        # Single data point — show what we have
        val = res["annual_values"][0]
        val_s = display_money(val, curr, rt)
        st.markdown(f"""
<div class="method-note" style="border-color:var(--amber);background:var(--amber-dim);">
  Only 1 data point found ({curr} {val_s} {unit}).
  Statistical ranges require 2+ data points. Try a broader job title or remove location filters.
</div>
""", unsafe_allow_html=True)

    # ── Sources ──
    if res.get("sources"):
        st.markdown('<div class="sec"><span>Data Sources</span></div>', unsafe_allow_html=True)

        for s in res["sources"]:
            title_txt = html.escape((s.get("title", "") or pretty_host(s["url"]))[:90])
            host_txt = html.escape(pretty_host(s["url"]))
            url_safe = html.escape(s["url"], quote=True)
            q = s.get("quality", 50)
            dot_color = (
                "var(--accent)" if q >= 80 else
                "var(--teal)" if q >= 60 else
                "var(--muted)"
            )

            st.markdown(f"""
<a class="src" href="{url_safe}" target="_blank">
  <div class="src-dot" style="background:{dot_color};"></div>
  <div>
    <div class="src-title">{title_txt}</div>
    <div class="src-meta">{host_txt} · quality {q}/100</div>
  </div>
</a>
""", unsafe_allow_html=True)
