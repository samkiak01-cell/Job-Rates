import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import urlparse
from utils.countries import get_all_countries, get_display_currencies, get_regions, get_cities
from utils.pipeline import run_pipeline, compute_sigma_stats

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="myBasePay | Job Rate Agent",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design System CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ── Tokens ── */
:root {
    --bg:        #060c18;
    --surf1:     #0d1729;
    --surf2:     #131f38;
    --surf3:     #1a2a4a;
    --text-pri:  #e2e9f8;
    --text-sec:  #b4ccec;
    --text-mute: #6a90b8;
    --emerald:   #00cc55;
    --wisteria:  #7393f9;
    --marigold:  #ffbf00;
    --gold-tag:  #f5d060;
    --b07: rgba(115,147,249,.07);
    --b14: rgba(115,147,249,.14);
    --b28: rgba(115,147,249,.28);
    --b50: rgba(115,147,249,.5);
}

/* ── Base ── */
.stApp { background-color: var(--bg) !important; font-family: 'Inter', sans-serif !important; color: var(--text-pri) !important; }
section.main > div { background-color: var(--bg) !important; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Hero Header ── */
.hero {
    background: linear-gradient(135deg, #001a0e 0%, #0d1729 52%, #0b102e 100%);
    border-radius: 0 0 28px 28px;
    padding: 3rem 2.5rem 2.5rem;
    margin: -1rem -1rem 2rem;
    position: relative;
    overflow: hidden;
}
.hero-gl-em {
    position: absolute; top: -50px; left: -50px;
    width: 360px; height: 360px;
    background: radial-gradient(circle, rgba(0,204,85,.16) 0%, transparent 68%);
    pointer-events: none;
}
.hero-gl-wi {
    position: absolute; top: -70px; right: -50px;
    width: 420px; height: 420px;
    background: radial-gradient(circle, rgba(115,147,249,.12) 0%, transparent 68%);
    pointer-events: none;
}
.hero-eyebrow {
    font-size: 12px; font-weight: 700; letter-spacing: .14em;
    text-transform: uppercase; color: rgba(115,147,249,.55);
    margin-bottom: .6rem; position: relative;
}
.hero-title {
    font-size: 34px; font-weight: 700; color: var(--text-pri);
    margin: 0 0 .5rem; line-height: 1.15; position: relative;
}
.hero-sub {
    font-size: 14px; color: rgba(226,233,248,.5);
    margin: 0; position: relative;
}

/* ── Form card ── */
[data-testid="stForm"] {
    background: var(--surf1) !important;
    border: 1px solid var(--b14) !important;
    border-radius: 18px !important;
    padding: 28px 32px !important;
    box-shadow: 0 8px 40px rgba(0,0,0,.4) !important;
}

/* Text inputs & textarea */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: var(--surf2) !important;
    border: 1px solid var(--b14) !important;
    border-radius: 10px !important;
    color: var(--text-pri) !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--wisteria) !important;
    box-shadow: 0 0 0 3px rgba(115,147,249,.18) !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder { color: var(--text-mute) !important; }

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
    background: var(--surf2) !important;
    border: 1px solid var(--b14) !important;
    border-radius: 10px !important;
    color: var(--text-pri) !important;
    transition: border-color .18s ease !important;
}

/* Form labels */
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stSelectbox"] label,
[data-testid="stRadio"] > label {
    color: var(--text-sec) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: .04em !important;
}
[data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}
[data-testid="stRadio"] label,
[data-testid="stRadio"] label p,
[data-testid="stRadio"] span,
[data-testid="stRadio"] div[role="radiogroup"] p {
    color: var(--text-sec) !important;
    font-size: 13px !important;
}

/* CTA / submit button */
[data-testid="stFormSubmitButton"] button,
.stButton > button {
    background: var(--marigold) !important;
    color: #0d1729 !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    width: 100% !important;
    padding: .65rem 1.5rem !important;
    box-shadow: 0 4px 20px rgba(255,191,0,.3) !important;
    transition: transform .18s ease, box-shadow .18s ease !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: .02em !important;
}
[data-testid="stFormSubmitButton"] button:hover,
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 28px rgba(255,191,0,.45) !important;
    background: #e6ac00 !important;
}

/* Download button override */
[data-testid="stDownloadButton"] button {
    background: var(--surf3) !important;
    color: var(--text-sec) !important;
    border: 1px solid var(--b28) !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    padding: .4rem 1rem !important;
    box-shadow: none !important;
    width: auto !important;
    font-weight: 600 !important;
}

/* Caption */
[data-testid="stCaptionContainer"] { color: var(--text-mute) !important; font-size: 12px !important; }

/* Progress bar */
[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, var(--emerald), var(--wisteria)) !important;
    border-radius: 4px !important;
}
[data-testid="stProgressBar"] > div {
    background: var(--surf2) !important;
    border-radius: 4px !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: var(--surf1) !important;
    border: 1px solid var(--b14) !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p { color: var(--text-sec) !important; }
[data-testid="stExpander"] summary svg { fill: var(--text-mute) !important; }

/* Error / info / warning native */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* Dataframe */
[data-testid="stDataFrame"] { background: var(--surf1) !important; border-radius: 10px !important; }

/* ── AI Card ── */
.ai-card { background: var(--surf1); border-radius: 16px; border: 1px solid var(--b14); overflow: hidden; margin-bottom: 1.25rem; }
.ai-card-bar { height: 2px; background: linear-gradient(90deg, var(--emerald), var(--wisteria)); }
.ai-card-body { padding: 1.5rem 1.75rem; }
.ai-badge {
    display: inline-flex; align-items: center; gap: 7px;
    background: rgba(0,204,85,.1); border: 1px solid rgba(0,204,85,.28);
    border-radius: 20px; padding: 4px 12px; margin-bottom: 1rem;
    font-size: 12px; font-weight: 700; letter-spacing: .06em;
    text-transform: uppercase; color: var(--emerald);
}
.ai-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--emerald); box-shadow: 0 0 6px var(--emerald);
    animation: glow-pulse 2s ease-in-out infinite;
}
@keyframes glow-pulse { 0%,100%{opacity:1;box-shadow:0 0 6px var(--emerald)} 50%{opacity:.55;box-shadow:0 0 2px var(--emerald)} }
.ai-card-title { font-size: 16px; font-weight: 700; color: var(--text-pri); margin: 0 0 .75rem; }
.ai-card-text { color: var(--text-sec); font-size: 14px; line-height: 1.75; margin: 0 0 1rem; }
.ai-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.ai-chip {
    background: rgba(255,191,0,.12); border: 1px solid rgba(255,191,0,.35);
    border-radius: 20px; padding: 6px 14px;
    font-size: 13px; color: var(--gold-tag); font-weight: 600;
    letter-spacing: .01em;
}

/* ── Confidence Banner ── */
.conf-banner {
    display: flex; align-items: center; gap: 12px;
    background: var(--surf1); border: 1px solid var(--b14);
    border-radius: 10px; padding: .65rem 1.25rem;
    margin-bottom: 1.25rem; font-size: 14px;
}
.conf-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.conf-label { font-weight: 700; color: var(--text-pri); }
.conf-desc { color: var(--text-mute); font-size: 14px; }

/* ── Range Hero Card ── */
.range-card { background: var(--surf1); border-radius: 18px; border: 1px solid var(--b14); overflow: visible; margin-bottom: 1.25rem; position: relative; }
.range-card-bar { height: 2px; background: linear-gradient(90deg, var(--emerald), var(--wisteria)); border-radius: 18px 18px 0 0; }
.range-card-glow {
    position: absolute; top: 0; left: 0;
    width: 220px; height: 180px;
    background: radial-gradient(circle, rgba(0,204,85,.07) 0%, transparent 70%);
    pointer-events: none;
}
.range-card-body { padding: 1.5rem 1.75rem; }
.range-card-eyebrow { font-size: 13px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--text-mute); margin-bottom: 1.25rem; }
.range-flex { display: flex; align-items: flex-end; gap: 1rem; flex-wrap: wrap; }
.range-block { }
.range-num-label { font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--text-mute); margin-bottom: .3rem; }
.range-num { font-family: 'JetBrains Mono', monospace; font-size: 38px; font-weight: 700; letter-spacing: -.03em; color: var(--text-pri); line-height: 1; }
.range-sep { font-family: 'JetBrains Mono', monospace; font-size: 28px; color: rgba(115,147,249,.35); font-weight: 300; padding-bottom: .15rem; }
.range-mid { margin-left: auto; text-align: right; }
.range-mid-label { font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--emerald); margin-bottom: .3rem; }
.range-mid-num { font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 700; letter-spacing: -.02em; color: var(--emerald); }

/* ── Section Dividers ── */
.sec-label {
    display: flex; align-items: center; gap: 12px;
    font-size: 13px; font-weight: 700; letter-spacing: .12em;
    text-transform: uppercase; color: var(--text-mute);
    margin: 1.75rem 0 1rem;
}
.sec-label::after { content: ''; flex: 1; height: 1px; background: var(--b07); }

/* ── Stat Cards ── */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 1.25rem; }
.stat-card { background: var(--surf1); border: 1px solid var(--b14); border-radius: 12px; padding: 1rem .75rem; text-align: center; }
.stat-label { font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--text-mute); margin-bottom: .4rem; }
.stat-value { font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 700; color: var(--text-pri); line-height: 1.2; }
.stat-unit { font-size: 12px; color: var(--text-mute); margin-top: .25rem; }

/* ── Band Rows ── */
.bd-row {
    background: var(--surf1); border: 1px solid var(--b07);
    border-radius: 14px; padding: 1rem 1.25rem;
    margin-bottom: .75rem; display: flex;
    align-items: center; justify-content: space-between;
    gap: 1rem; position: relative; overflow: hidden;
    transition: border-color .18s ease, box-shadow .18s ease;
}
.bd-row:hover { border-color: var(--b28); box-shadow: 0 4px 20px rgba(0,0,0,.35); }
.bd-accent { position: absolute; left: 0; top: 0; bottom: 0; width: 3px; opacity: .7; }
.bd-left { display: flex; flex-direction: column; gap: .35rem; padding-left: .75rem; }
.bd-tag { display: inline-block; padding: 3px 10px; border-radius: 7px; font-size: 12px; font-weight: 700; letter-spacing: .04em; }
.bd-desc { font-size: 14px; color: var(--text-mute); }
.bd-right { text-align: right; flex-shrink: 0; }
.bd-range { font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 600; color: var(--text-pri); }
.bd-avg { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--text-mute); margin-top: 2px; }
.bd-pill { display: inline-block; background: var(--surf2); border: 1px solid var(--b14); border-radius: 20px; padding: 2px 8px; font-size: 12px; color: var(--text-mute); margin-top: 4px; }
.src-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: .6rem; }
.src-pill { display: inline-block; padding: 4px 11px; border-radius: 20px; font-size: 12px; font-weight: 500; transition: transform .18s ease, opacity .18s ease; text-decoration: none; }
.src-pill:hover { transform: translateY(-1px); opacity: .75; }

/* ── Source items ── */
.src-item { display: flex; align-items: flex-start; gap: 12px; background: var(--surf2); border-radius: 10px; padding: .65rem 1rem; margin-bottom: .5rem; }
.src-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 3px; flex-shrink: 0; }
.src-title { font-size: 13px; font-weight: 600; color: var(--text-pri); word-break: break-all; }
.src-host { font-size: 11px; color: var(--text-mute); margin-top: 1px; }

/* ── Low-data warning ── */
.low-warn { background: rgba(255,191,0,.06); border: 1px solid rgba(255,191,0,.28); border-radius: 10px; padding: .75rem 1.25rem; color: #f5d060; font-size: 13px; margin-bottom: 1rem; }

/* ── Stat card hover ── */
.stat-card { transition: border-color .18s ease, transform .18s ease; }
.stat-card:hover { border-color: var(--b28); transform: translateY(-1px); }

/* ── Responsive stat grid ── */
@media (max-width: 600px) { .stats-row { grid-template-columns: 1fr 1fr; } }

/* ── Progress text ── */
[data-testid="stProgressBar"] + div { color: var(--text-mute) !important; }

/* ── Two-panel layout ── */
.block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }

[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
    position: sticky !important;
    top: 1rem !important;
    align-self: flex-start !important;
    max-height: calc(100vh - 2rem) !important;
    overflow-y: auto !important;
}

.left-header { padding: 1rem 0 1.25rem; }
.left-subtitle { font-size: 13px; color: rgba(226,233,248,.4); margin-top: .5rem; line-height: 1.5; }

.empty-state {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    min-height: 60vh; color: var(--text-mute); font-size: 14px; text-align: center; gap: .75rem;
}
.empty-state-icon { font-size: 40px; opacity: .35; }
.empty-state-text { opacity: .5; }
</style>
""", unsafe_allow_html=True)

# ── Two-column layout ─────────────────────────────────────────────────────────
left_col, right_col = st.columns([5, 7], gap="large")

with left_col:
    # Logo + subtitle
    st.image("logo-light-1 (2).svg", width=180)
    st.markdown('<div class="left-subtitle">Job Rate Agent — AI-powered salary intelligence</div>', unsafe_allow_html=True)

    # ── Location selectors (outside form so they cascade dynamically) ─────────
    all_countries = get_all_countries()
    default_country_idx = all_countries.index("United States") if "United States" in all_countries else 0
    country = st.selectbox(
        "Country *",
        options=all_countries,
        index=default_country_idx,
        key="sel_country",
        help="Required. Select the target country.",
    )

    col3, col4 = st.columns(2)

    with col3:
        region_options = get_regions(country)
        # Reset region/city when country changes by encoding country in the key
        region_sel = st.selectbox(
            "State / Province / Region",
            options=["(Any)"] + region_options,
            key=f"sel_region_{country}",
            help="Optional — select a region to narrow results.",
        )
        region = "" if region_sel == "(Any)" else region_sel

    with col4:
        city_options = get_cities(country, region)
        city_sel = st.selectbox(
            "City",
            options=["(Any)"] + city_options,
            key=f"sel_city_{country}_{region}",
            help="Optional — select a city to narrow results.",
        )
        city = "" if city_sel == "(Any)" else city_sel

    # ── Input Form ────────────────────────────────────────────────────────────
    with st.form("job_rate_form"):
        job_title = st.text_input(
            "Job Title *",
            placeholder="e.g. Software Engineer",
            help="Required. Enter the job title to research."
        )

        description = st.text_area(
            "Job Description",
            placeholder="Optional: paste a job description or add context to improve matching accuracy.",
            height=90,
        )

        col5, col6 = st.columns(2)

        with col5:
            display_pref = st.radio(
                "Display As",
                options=["Annual Salary", "Hourly Pay Rate"],
                horizontal=True,
            )

        with col6:
            currency_options = get_display_currencies(country)
            display_currency = st.selectbox(
                "Display Currency",
                options=currency_options,
                index=0,
                help="Select the currency for displayed pay rates."
            )

        submit = st.form_submit_button("Search Job Rates", use_container_width=True)

        st.caption("⚠️ This tool fetches publicly available salary data for research purposes only.")

with right_col:
    if not submit:
        st.markdown('''
<div class="empty-state">
    <div class="empty-state-icon">📊</div>
    <div class="empty-state-text">Enter a job title and location,<br>then click <strong>Search Job Rates</strong> to see results.</div>
</div>
''', unsafe_allow_html=True)
    else:
        # ── Validation ────────────────────────────────────────────────────────
        if not job_title.strip():
            st.error("Job Title is required.")
            st.stop()

        try:
            serpapi_key      = st.secrets["SERPAPI_KEY"]
            anthropic_key    = st.secrets["ANTHROPIC_API_KEY"]
            exchangerate_key = st.secrets["EXCHANGERATE_KEY"]
        except KeyError as e:
            st.error(f"Missing secret: {e}. Please configure your Streamlit secrets.")
            st.stop()

        # ── Pipeline ──────────────────────────────────────────────────────────
        st.session_state["health_events"] = []
        st.markdown('<div class="sec-label">Pipeline</div>', unsafe_allow_html=True)

        progress_bar    = st.progress(0.0, text="Starting pipeline...")
        df_placeholder  = st.empty()

        collected_rows: list[dict] = []
        final_df: pd.DataFrame | None = None
        summary_data: dict | None = None

        SCHEMA = [
            "country_specific_site_url", "web_search_result_url", "job_title",
            "found_currency", "found_annual_pay", "found_hourly_pay",
            "found_pay_low", "found_pay_high", "remote_ok", "source_type",
            "display_currency", "display_pay_rate", "country", "region", "city", "valid",
            "error_message",
        ]

        try:
            for event in run_pipeline(
                job_title=job_title.strip(),
                country=country,
                region=region.strip(),
                city=city.strip(),
                description=description.strip(),
                display_pref=display_pref,
                display_currency=display_currency,
                serpapi_key=serpapi_key,
                anthropic_key=anthropic_key,
                exchangerate_key=exchangerate_key,
            ):
                etype = event.get("type")

                if etype == "progress":
                    progress_bar.progress(min(event["value"], 1.0), text=event.get("text", ""))

                elif etype == "row":
                    collected_rows.append(event["row"])
                    live_df = pd.DataFrame(collected_rows, columns=SCHEMA)
                    df_placeholder.dataframe(live_df, use_container_width=True, height=260)

                elif etype == "stats":
                    final_df = event["df"]
                    df_placeholder.dataframe(final_df, use_container_width=True, height=260)

                elif etype == "summary":
                    summary_data = event["data"]

                elif etype == "health":
                    if "health_events" not in st.session_state:
                        st.session_state["health_events"] = []
                    st.session_state["health_events"].append(event)

                elif etype == "error":
                    st.error(event["message"])
                    progress_bar.empty()
                    st.stop()

                elif etype == "complete":
                    progress_bar.progress(1.0, text="Complete")

        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()

        df_placeholder.empty()

        # ── Results ───────────────────────────────────────────────────────────
        pay_label = "/ yr" if display_pref == "Annual Salary" else "/ hr"

        def fmt(val):
            if val is None:
                return "—"
            return f"{display_currency} {val:,.0f}"

        def fmt_compact(val):
            """E.g. 120000 → '120K'"""
            if val is None:
                return "—"
            if val >= 1_000_000:
                return f"{val/1_000_000:.1f}M"
            if val >= 1_000:
                return f"{val/1_000:.0f}K"
            return f"{val:.0f}"

        # Confidence banner
        valid_count = int((final_df["valid"] == 1).sum()) if final_df is not None else 0
        total_count = len(final_df) if final_df is not None else 0

        if valid_count >= 10:
            conf_color = "#00cc55"
            conf_glow  = "0 0 8px rgba(0,204,85,.6)"
            conf_label = "High Confidence"
            conf_desc  = f"{valid_count} validated data points collected"
        elif valid_count >= 5:
            conf_color = "#7393f9"
            conf_glow  = "0 0 8px rgba(115,147,249,.6)"
            conf_label = "Moderate Confidence"
            conf_desc  = f"{valid_count} validated data points — results may vary slightly"
        else:
            conf_color = "#ffbf00"
            conf_glow  = "0 0 8px rgba(255,191,0,.6)"
            conf_label = "Limited Data"
            conf_desc  = f"Only {valid_count} validated data points — treat ranges as estimates"

        st.markdown(f"""
<div class="conf-banner">
    <div class="conf-dot" style="background:{conf_color};box-shadow:{conf_glow};"></div>
    <span class="conf-label">{conf_label}</span>
    <span class="conf-desc">{conf_desc}</span>
</div>
""", unsafe_allow_html=True)

        if valid_count == 0:
            st.markdown('<div class="low-warn">⚠️ <strong>No validated data found.</strong> Try broadening your search — remove the city/region, or try a different job title.</div>', unsafe_allow_html=True)

        # A. AI Summary Card
        if summary_data:
            summary_text = summary_data.get("summary", "")
            bullets      = summary_data.get("bullets", [])
            chips_html   = "".join(f'<span class="ai-chip">{b}</span>' for b in bullets)

            st.markdown(f"""
<div class="ai-card">
    <div class="ai-card-bar"></div>
    <div class="ai-card-body">
        <div class="ai-badge"><div class="ai-dot"></div>AI Market Analysis</div>
        <div class="ai-card-title">{job_title} — {country}</div>
        <div class="ai-card-text">{summary_text}</div>
        <div class="ai-chips">{chips_html}</div>
    </div>
</div>
""", unsafe_allow_html=True)

        # B. Range Hero Card
        rec = (summary_data or {}).get("recommended_range", {})
        rec_min  = rec.get("min")
        rec_max  = rec.get("max")

        if rec_min is not None and rec_max is not None:
            rec_mid = (rec_min + rec_max) / 2
            st.markdown('<div class="sec-label">Salary Range</div>', unsafe_allow_html=True)
            st.markdown(f"""
<div class="range-card">
    <div class="range-card-bar"></div>
    <div class="range-card-glow"></div>
    <div class="range-card-body">
        <div class="range-card-eyebrow">AI Recommended Pay Range &mdash; {display_pref} &mdash; {display_currency}</div>
        <div class="range-flex">
            <div class="range-block">
                <div class="range-num-label">Low End</div>
                <div class="range-num">{fmt_compact(rec_min)}</div>
            </div>
            <div class="range-sep">&mdash;</div>
            <div class="range-block">
                <div class="range-num-label">High End</div>
                <div class="range-num">{fmt_compact(rec_max)}</div>
            </div>
            <div class="range-mid">
                <div class="range-mid-label">Midpoint</div>
                <div class="range-mid-num">{fmt_compact(rec_mid)}</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

        # C. Market Breakdown — computed from validated data rows
        market_min = market_max = median_val = mean_val = None
        if final_df is not None:
            valid_rates = final_df[(final_df["valid"] == 1) & final_df["display_pay_rate"].notna()]["display_pay_rate"]
            if len(valid_rates) > 0:
                market_min = float(valid_rates.min())
                market_max = float(valid_rates.max())
                median_val = float(valid_rates.median())
                mean_val   = float(valid_rates.mean())

        if any(v is not None for v in [market_min, market_max, median_val, mean_val]):
            st.markdown('<div class="sec-label">Market Breakdown</div>', unsafe_allow_html=True)
            st.markdown(f"""
<div class="stats-row">
    <div class="stat-card">
        <div class="stat-label">Market Min</div>
        <div class="stat-value">{fmt_compact(market_min)}</div>
        <div class="stat-unit">{display_currency} {pay_label}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Median</div>
        <div class="stat-value">{fmt_compact(median_val)}</div>
        <div class="stat-unit">{display_currency} {pay_label}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Mean</div>
        <div class="stat-value">{fmt_compact(mean_val)}</div>
        <div class="stat-unit">{display_currency} {pay_label}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Market Max</div>
        <div class="stat-value">{fmt_compact(market_max)}</div>
        <div class="stat-unit">{display_currency} {pay_label}</div>
    </div>
</div>
""", unsafe_allow_html=True)

        # D. Pay Bands
        sigma_stats = compute_sigma_stats(final_df) if final_df is not None else None

        def get_band_source_pills(df, lo, hi, accent):
            valid = df[(df["valid"] == 1) & df["display_pay_rate"].notna()].copy()
            in_band = valid[(valid["display_pay_rate"] >= lo) & (valid["display_pay_rate"] <= hi)]
            if len(in_band) == 0:
                return ""
            min_row = in_band.loc[(in_band["display_pay_rate"] - lo).abs().idxmin()]
            max_row = in_band.loc[(in_band["display_pay_rate"] - hi).abs().idxmin()]
            pills = []
            for row in [min_row, max_row]:
                url = str(row.get("web_search_result_url") or row.get("country_specific_site_url") or "")
                host = urlparse(url).netloc.replace("www.", "") if url else "source"
                val_str = fmt(row["display_pay_rate"])
                href = f' href="{url}" target="_blank" rel="noopener"' if url else ""
                tag = "a" if url else "span"
                pills.append(
                    f'<{tag}{href} class="src-pill" style="background:rgba(0,0,0,.2);'
                    f'border:1px solid {accent};color:{accent};">'
                    f'{host}&nbsp;{val_str}</{tag}>'
                )
            return "".join(pills)

        bands = []
        if rec_min is not None and rec_max is not None:
            bands.append({
                "tag": "AI Recommended",
                "tag_color": "#f5d060",
                "tag_bg": "rgba(245,208,96,.12)",
                "accent": "#ffbf00",
                "desc": "AI-derived recommended pay range",
                "lo": rec_min, "hi": rec_max,
                "avg": (rec_min + rec_max) / 2,
                "count": None,
                "pills": "",
            })

        if sigma_stats:
            s1 = sigma_stats.get("sigma1")
            s2 = sigma_stats.get("sigma2")
            if s1:
                bands.append({
                    "tag": "1\u03c3 Typical (68%)",
                    "tag_color": "#00cc55",
                    "tag_bg": "rgba(0,204,85,.12)",
                    "accent": "#00cc55",
                    "desc": "Core market range — most roles fall here",
                    "lo": s1["min"], "hi": s1["max"], "avg": s1["mean"],
                    "count": s1["count"],
                    "pills": get_band_source_pills(final_df, s1["min"], s1["max"], "#00cc55"),
                })
            if s2:
                bands.append({
                    "tag": "2\u03c3 Full Range (95%)",
                    "tag_color": "#7393f9",
                    "tag_bg": "rgba(115,147,249,.12)",
                    "accent": "#7393f9",
                    "desc": "Full market spectrum including outliers",
                    "lo": s2["min"], "hi": s2["max"], "avg": s2["mean"],
                    "count": s2["count"],
                    "pills": get_band_source_pills(final_df, s2["min"], s2["max"], "#7393f9"),
                })

        if bands:
            st.markdown('<div class="sec-label">Pay Bands</div>', unsafe_allow_html=True)
            for b in bands:
                pills_html = f'<div class="src-pills">{b["pills"]}</div>' if b.get("pills") else ""
                count_html = f'<span class="bd-pill">{b["count"]} data pts</span>' if b.get("count") else ""
                st.markdown(
                    f'<div class="bd-row">'
                    f'<div class="bd-accent" style="background:{b["accent"]};"></div>'
                    f'<div class="bd-left">'
                    f'<span class="bd-tag" style="color:{b["tag_color"]};background:{b["tag_bg"]};">{b["tag"]}</span>'
                    f'<span class="bd-desc">{b["desc"]}</span>'
                    f'{pills_html}'
                    f'</div>'
                    f'<div class="bd-right">'
                    f'<div class="bd-range">{fmt(b["lo"])} &ndash; {fmt(b["hi"])}</div>'
                    f'<div class="bd-avg">avg {fmt(b["avg"])}</div>'
                    f'{count_html}'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        elif sigma_stats is None and final_df is not None and len(final_df) > 0:
            st.markdown('<div class="low-warn">⚠️ <strong>Insufficient data for statistical bands.</strong> Need at least 7 validated results to compute sigma ranges.</div>', unsafe_allow_html=True)

        # F. Detailed Data Table
        if final_df is not None and len(final_df) > 0:
            st.markdown('<div class="sec-label">Raw Data</div>', unsafe_allow_html=True)
            with st.expander("Detailed results table", expanded=False):
                st.dataframe(final_df, use_container_width=True, height=380)
                st.download_button(
                    label="Download CSV",
                    data=final_df.to_csv(index=False),
                    file_name="job_rate_results.csv",
                    mime="text/csv",
                )
        elif final_df is not None:
            st.info("No data rows were returned. Try a different job title, location, or check your API keys.")

        # Pipeline debug expander
        if st.session_state.get("health_events"):
            with st.expander("🔍 Pipeline Debug (domain health)", expanded=False):
                import pandas as pd
                health_df = pd.DataFrame(st.session_state["health_events"])
                # Drop the 'type' column if present
                if "type" in health_df.columns:
                    health_df = health_df.drop(columns=["type"])
                st.dataframe(health_df, use_container_width=True)
