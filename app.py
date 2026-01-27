# app.py
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st


# ============================================================
# Page config (ONLY ONCE)
# ============================================================
st.set_page_config(page_title="Job Rate Finder", page_icon="💼", layout="centered")


# ============================================================
# Styling (pure UI)
# ============================================================
APP_CSS = """
<style>
  :root{
    --bg0:#070A12;
    --bg1:#0B1020;
    --card:rgba(17, 24, 39, 0.65);
    --text:#E5E7EB;
    --muted:#CBD5E1;
    --border:rgba(148, 163, 184, 0.18);
    --accent:#4F46E5;
    --accent2:#A855F7;
    --shadow:0 20px 60px rgba(0,0,0,0.35);
  }

  .stApp {
    background: radial-gradient(1200px 800px at 20% 0%, rgba(124, 58, 237, 0.35), transparent 60%),
                radial-gradient(1200px 800px at 80% 10%, rgba(99, 102, 241, 0.30), transparent 55%),
                linear-gradient(180deg, var(--bg0) 0%, var(--bg1) 100%);
    color: var(--text);
  }

  .block-container {
    padding-top: 2.2rem;
    padding-bottom: 3rem;
    max-width: 860px;
  }

  .jr-title{
    text-align:center;
    margin-bottom: .25rem;
    font-size: 44px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: var(--text);
  }
  .jr-subtitle{
    text-align:center;
    margin-top: 0;
    margin-bottom: 1.35rem;
    color: rgba(203,213,225,0.75);
    font-size: 15px;
  }

  .jr-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 18px 8px 18px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
  }

  .jr-gradient {
    background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 50%, #A855F7 100%);
    border-radius: 16px;
    padding: 18px;
    color: white;
    box-shadow: var(--shadow);
    border: 1px solid rgba(255,255,255,0.14);
  }

  .jr-range {
    display: flex;
    gap: 24px;
    align-items: baseline;
  }
  .jr-range .jr-sep {
    font-size: 26px;
    opacity: 0.6;
    margin: 0 4px;
  }
  .jr-label {
    font-size: 12px;
    opacity: 0.78;
    margin-bottom: 2px;
  }
  .jr-money {
    font-size: 34px;
    font-weight: 700;
    line-height: 1.2;
  }
  .jr-unit {
    font-size: 12px;
    opacity: 0.78;
    margin-top: 4px;
  }

  .jr-sources {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
  }

  .jr-source {
    display: flex;
    gap: 12px;
    padding: 12px 12px;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.14);
    background: rgba(2, 6, 23, 0.35);
    transition: all 0.15s ease;
    text-decoration: none !important;
    margin-bottom: 10px;
  }
  .jr-source:hover {
    border-color: rgba(99, 102, 241, 0.55);
    background: rgba(2, 6, 23, 0.55);
    transform: translateY(-1px);
  }
  .jr-ico {
    width: 22px;
    height: 22px;
    border-radius: 7px;
    background: rgba(99, 102, 241, 0.22);
    display: grid;
    place-items: center;
    flex: 0 0 22px;
    margin-top: 2px;
    color: white;
    font-weight: 800;
    font-size: 12px;
  }
  .jr-source-main {
    color: var(--text) !important;
    font-weight: 600;
    font-size: 13px;
    line-height: 1.2;
    margin: 0;
  }
  .jr-source-sub {
    color: #9CA3AF !important;
    font-size: 12px;
    margin-top: 4px;
    margin-bottom: 0;
  }

  .jr-note {
    margin-top: 14px;
    padding: 12px;
    border-radius: 12px;
    border: 1px solid rgba(251, 191, 36, 0.35);
    background: rgba(251, 191, 36, 0.10);
    color: #FDE68A;
    font-size: 12px;
  }

  .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    background: rgba(2, 6, 23, 0.35) !important;
    color: var(--text) !important;
    border-color: rgba(148, 163, 184, 0.18) !important;
  }
  .stTextArea textarea::placeholder, .stTextInput input::placeholder {
    color: rgba(203, 213, 225, 0.55) !important;
  }

  .stButton button, .stForm button {
    background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 60%, #A855F7 100%) !important;
    color: white !important;
    border: 0 !important;
    border-radius: 12px !important;
    padding: 0.65rem 1rem !important;
    font-weight: 700 !important;
    width: 100% !important;
  }
  .stButton button:hover, .stForm button:hover { filter: brightness(1.05); }

  header, footer { visibility: hidden; }
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)


# ============================================================
# Types
# ============================================================
@dataclass
class SourceItem:
    title: str
    url: str
    range: str


# ============================================================
# Env helpers
# ============================================================
def require_env(name: str) -> str:
    v = (os.getenv(name) or "").strip()
    if not v:
        raise RuntimeError(f"Missing environment variable: {name}")
    return v


# ============================================================
# Geo dropdowns (CountriesNow - no key required)
# ============================================================
COUNTRIESNOW_BASE = "https://countriesnow.space/api/v0.1"

@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_country_list() -> List[str]:
    url = f"{COUNTRIESNOW_BASE}/countries"
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    data = r.json()
    countries: List[str] = []
    for item in (data.get("data") or []):
        name = item.get("country")
        if isinstance(name, str) and name.strip():
            countries.append(name.strip())
    return sorted(set(countries), key=lambda x: x.lower())

@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_states_for_country(country: str) -> List[str]:
    if not country:
        return ["N/A"]
    url = f"{COUNTRIESNOW_BASE}/countries/states"
    r = requests.post(url, json={"country": country}, timeout=25)
    if not r.ok:
        return ["N/A"]
    data = r.json()
    states: List[str] = []
    for s in (data.get("data") or {}).get("states") or []:
        nm = s.get("name")
        if isinstance(nm, str) and nm.strip():
            states.append(nm.strip())
    states = sorted(set(states), key=lambda x: x.lower())
    return states if states else ["N/A"]

@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_cities(country: str, state: str) -> List[str]:
    if not country:
        return ["N/A"]

    # If state is N/A, try country-level city list
    if not state or state == "N/A":
        url = f"{COUNTRIESNOW_BASE}/countries/cities"
        r = requests.post(url, json={"country": country}, timeout=25)
        if not r.ok:
            return ["N/A"]
        cities = r.json().get("data") or []
        cities = [c.strip() for c in cities if isinstance(c, str) and c.strip()]
        cities = sorted(set(cities), key=lambda x: x.lower())
        return cities if cities else ["N/A"]

    # Else: try state-specific city list
    url = f"{COUNTRIESNOW_BASE}/countries/state/cities"
    r = requests.post(url, json={"country": country, "state": state}, timeout=25)
    if not r.ok:
        return ["N/A"]
    cities = r.json().get("data") or []
    cities = [c.strip() for c in cities if isinstance(c, str) and c.strip()]
    cities = sorted(set(cities), key=lambda x: x.lower())
    return cities if cities else ["N/A"]


# ============================================================
# FX conversion (free)
# ============================================================
@st.cache_data(ttl=60 * 60, show_spinner=False)
def get_fx_table_usd() -> Dict[str, float]:
    r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=25)
    r.raise_for_status()
    data = r.json()
    rates = data.get("rates") or {}
    out: Dict[str, float] = {"USD": 1.0}
    for k, v in rates.items():
        if isinstance(k, str) and isinstance(v, (int, float)) and v and v > 0:
            out[k.upper()] = float(v)
    return out

def convert_from_usd(amount: float, to_ccy: str) -> float:
    to_ccy = (to_ccy or "USD").upper()
    rate = get_fx_table_usd().get(to_ccy)
    return amount * rate if rate else amount


# ============================================================
# Pretty source labels (NO raw URLs in UI)
# ============================================================
def pretty_url_label(raw_url: str) -> str:
    """
    Returns a readable label like:
      "salary.com — marketing director salary (los angeles ca)"
    """
    try:
        from urllib.parse import urlparse, unquote
        u = urlparse(raw_url)
        host = (u.hostname or "").replace("www.", "") or "source"
        path = (u.path or "").strip("/")
        if not path:
            return host
        parts = [p for p in path.split("/") if p]
        last = unquote(parts[-1]) if parts else ""
        last = re.sub(r"\.(html|htm|php|aspx)$", "", last, flags=re.I)
        last = re.sub(r"[-_]+", " ", last)
        last = re.sub(r"\s+", " ", last).strip()
        if not last:
            last = unquote(path)
            last = re.sub(r"[-_]+", " ", last)
            last = re.sub(r"\s+", " ", last).strip()
        if len(last) > 70:
            last = last[:70].rstrip() + "…"
        return f"{host} — {last}" if last else host
    except Exception:
        return "Source"


def format_money(n: float) -> str:
    try:
        return f"{int(round(float(n))):,}"
    except Exception:
        return "—"


# ============================================================
# SerpAPI search (real)
# ============================================================
def serpapi_search(job_title: str, country: str, state: str, city: str, rate_type: str) -> List[str]:
    serp_key = require_env("SERPAPI_API_KEY")

    loc_bits = [b for b in [city, state, country] if b and b != "N/A"]
    loc = ", ".join(loc_bits) if loc_bits else country

    q = f'{job_title} salary range {loc} {"hourly rate" if rate_type=="hourly" else "annual salary"}'
    params = {
        "engine": "google",
        "q": q,
        "api_key": serp_key,
        "num": 10,
    }

    r = requests.get("https://serpapi.com/search.json", params=params, timeout=35)
    r.raise_for_status()
    data = r.json()

    urls: List[str] = []
    for item in (data.get("organic_results") or []):
        link = item.get("link")
        if isinstance(link, str) and link.startswith("http"):
            urls.append(link)

    # de-dupe preserving order
    seen = set()
    out: List[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


# ============================================================
# OpenAI call (real) -> returns dict with min/max + links
# Tries Responses API first, then falls back to Chat Completions.
# ============================================================
def _openai_post(url: str, payload: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    openai_key = require_env("OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()

def openai_estimate(
    job_title: str,
    job_desc: str,
    country: str,
    state: str,
    city: str,
    rate_type: str,
    urls: List[str],
) -> Dict[str, Any]:
    pay_type = "HOURLY" if rate_type == "hourly" else "ANNUAL"

    loc_bits = [b for b in [city, state, country] if b and b != "N/A"]
    loc = ", ".join(loc_bits) if loc_bits else country

    url_block = "\n".join(f"- {u}" for u in urls[:10]) if urls else "- (no links found)"

    prompt = f"""
You are estimating compensation ranges from recent job postings/listings and reputable salary pages.

Task:
- Job title: "{job_title}"
- Job description (optional): "{job_desc or ""}"
- Location: "{loc}"
- Pay type: "{pay_type}" (HOURLY means hourly rate; ANNUAL means yearly salary)
- Consider only listings/open postings within the last ~3 months (best effort).

Use these candidate links (some may be irrelevant; pick only those that truly support the range):
{url_block}

Output STRICT JSON only (no markdown, no commentary) in this exact shape:
{{
  "min_usd": <number>,
  "max_usd": <number>,
  "pay_type": "HOURLY"|"ANNUAL",
  "sources_used": [<url>, ...],
  "min_links": [<url>, ...],
  "max_links": [<url>, ...]
}}

Rules:
- min_usd must be <= max_usd and both realistic for the role/location.
- Use only the links you actually relied on. If you are not confident, return fewer links.
- Provide 0-3 links for min_links and 0-3 links for max_links when possible.
- sources_used should be a de-duplicated list of all relied-upon links (may be empty).
""".strip()

    model = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()

    text_out = ""

    # 1) Responses API
    try:
        data = _openai_post(
            "https://api.openai.com/v1/responses",
            {"model": model, "input": prompt, "temperature": 0},
            timeout=60,
        )
        parts: List[str] = []
        for o in (data.get("output") or []):
            for c in (o.get("content") or []):
                if c.get("type") == "output_text" and isinstance(c.get("text"), str):
                    parts.append(c["text"])
        text_out = "".join(parts).strip()
    except Exception:
        text_out = ""

    # 2) Fallback: Chat Completions
    if not text_out:
        data = _openai_post(
            "https://api.openai.com/v1/chat/completions",
            {
                "model": model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": "Return only valid JSON. No markdown."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        text_out = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        text_out = text_out.strip()

    if not text_out:
        raise RuntimeError("OpenAI returned an empty response.")

    # Parse JSON (recover if there's extra text)
    try:
        parsed = json.loads(text_out)
    except Exception:
        m = re.search(r"\{.*\}\s*$", text_out, re.S)
        if not m:
            raise RuntimeError("OpenAI did not return valid JSON.")
        parsed = json.loads(m.group(0))

    # Validate + normalize
    min_usd = float(parsed.get("min_usd"))
    max_usd = float(parsed.get("max_usd"))
    if not math.isfinite(min_usd) or not math.isfinite(max_usd):
        raise RuntimeError("OpenAI returned non-numeric min/max.")
    if min_usd > max_usd:
        min_usd, max_usd = max_usd, min_usd

    pay_type_out = parsed.get("pay_type")
    if pay_type_out not in ("HOURLY", "ANNUAL"):
        pay_type_out = pay_type

    def clean_urls(x: Any) -> List[str]:
        if not isinstance(x, list):
            return []
        out: List[str] = []
        seen = set()
        for item in x:
            if isinstance(item, str) and item.startswith("http") and item not in seen:
                seen.add(item)
                out.append(item)
        return out

    return {
        "min_usd": round(min_usd),
        "max_usd": round(max_usd),
        "pay_type": pay_type_out,
        "sources_used": clean_urls(parsed.get("sources_used")),
        "min_links": clean_urls(parsed.get("min_links")),
        "max_links": clean_urls(parsed.get("max_links")),
    }


# ============================================================
# THIS is the function Streamlit uses
# (wired to SerpAPI + OpenAI now)
# ============================================================
def estimate_job_rate(
    job_title: str,
    job_description: str,
    country: str,
    state: str,
    city: str,
    rate_type: str,
    currency: str,
) -> Dict[str, Any]:
    urls = serpapi_search(job_title, country, state, city, rate_type)
    result = openai_estimate(job_title, job_description, country, state, city, rate_type, urls)

    # Convert to selected currency for display (min/max returned in USD)
    min_usd = float(result["min_usd"])
    max_usd = float(result["max_usd"])

    min_disp = min_usd
    max_disp = max_usd
    if (currency or "USD").upper() != "USD":
        min_disp = convert_from_usd(min_usd, currency)
        max_disp = convert_from_usd(max_usd, currency)

    pay_type = result.get("pay_type", "ANNUAL")

    sources: List[Dict[str, str]] = []
    for u in result.get("min_links") or []:
        sources.append({"title": pretty_url_label(u), "url": u, "range": "Min (Annual)" if pay_type == "ANNUAL" else "Min (Hourly)"})
    for u in result.get("max_links") or []:
        sources.append({"title": pretty_url_label(u), "url": u, "range": "Max (Annual)" if pay_type == "ANNUAL" else "Max (Hourly)"})

    # If min/max links are empty, fall back to sources_used
    if not sources:
        for u in result.get("sources_used") or []:
            sources.append({"title": pretty_url_label(u), "url": u, "range": "Source"})

    # De-dupe sources by URL
    seen = set()
    deduped: List[Dict[str, str]] = []
    for s in sources:
        u = s.get("url") or ""
        if not u or u in seen:
            continue
        seen.add(u)
        deduped.append(s)

    return {
        "min": int(round(min_disp)),
        "max": int(round(max_disp)),
        "currency": (currency or "USD").upper(),
        "rateType": "hourly" if pay_type == "HOURLY" else "salary",
        "sources": deduped,
    }


# ============================================================
# UI
# ============================================================
st.markdown('<div class="jr-title">Job Rate Finder</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="jr-subtitle">Get competitive salary and hourly rate information for any position</div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="jr-card">', unsafe_allow_html=True)

with st.form("job_rate_form", clear_on_submit=False):
    job_title = st.text_input("Job Title *", value="", placeholder="e.g., Senior Software Engineer", key="job_title")
    job_desc = st.text_area("Job Description (optional)", value="", placeholder="Paste job description here...", height=130, key="job_desc")

    uploaded = st.file_uploader("Upload Job Description (optional)", type=["txt"], accept_multiple_files=False, key="job_desc_file")
    if uploaded is not None:
        try:
            txt = uploaded.read().decode("utf-8", errors="ignore").strip()
            if txt:
                job_desc = txt
                st.session_state["job_desc"] = txt
        except Exception:
            pass

    # Geo (all dropdowns; state/city optional)
    try:
        countries = get_country_list()
    except Exception:
        countries = []

    c1, c2, c3 = st.columns(3)

    with c1:
        country = st.selectbox("Country *", options=countries, index=0 if countries else 0, key="country")

    with c2:
        states = get_states_for_country(country) if country else ["N/A"]
        state = st.selectbox("State/Province (optional)", options=states, index=0, key="state")

    with c3:
        cities = get_cities(country, state) if country else ["N/A"]
        city = st.selectbox("City (optional)", options=cities, index=0, key="city")

    rt_col, ccy_col = st.columns([1, 2])
    with rt_col:
        rate_type_label = st.radio("Rate Type *", options=["Salaried", "Hourly"], horizontal=True, index=0, key="rate_type")
        rate_type = "hourly" if rate_type_label == "Hourly" else "salary"
    with ccy_col:
        fx = get_fx_table_usd()
        currency_codes = sorted(fx.keys())
        currency = st.selectbox("Currency *", options=currency_codes, index=currency_codes.index("USD") if "USD" in currency_codes else 0, key="currency")

    submitted = st.form_submit_button("Get Rates!")

st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# Run + render results
# ============================================================
if submitted:
    if not (job_title or "").strip():
        st.warning("Job Title is required.")
    elif not (country or "").strip():
        st.warning("Country is required.")
    else:
        # Send empty strings if N/A (keeps “optional” behavior)
        state_send = "" if state == "N/A" else state
        city_send = "" if city == "N/A" else city

        with st.spinner("Analyzing recent market data..."):
            res = estimate_job_rate(
                job_title=job_title.strip(),
                job_description=(job_desc or "").strip(),
                country=country.strip(),
                state=state_send.strip(),
                city=city_send.strip(),
                rate_type=rate_type,
                currency=currency.strip(),
            )

        unit = "per hour" if res["rateType"] == "hourly" else "per year"

        st.markdown(
            f"""
            <div class="jr-gradient">
              <div style="display:flex; align-items:center; gap:10px; margin-bottom: 8px;">
                <div style="width:22px;height:22px;border-radius:7px;background:rgba(255,255,255,0.18);display:grid;place-items:center;font-weight:800;">$</div>
                <div style="font-weight:700;">Estimated Rate Range</div>
              </div>

              <div class="jr-range">
                <div>
                  <div class="jr-label">Minimum</div>
                  <div class="jr-money">{res["currency"]}{format_money(res["min"])}</div>
                  <div class="jr-unit">{unit}</div>
                </div>

                <div class="jr-sep">—</div>

                <div>
                  <div class="jr-label">Maximum</div>
                  <div class="jr-money">{res["currency"]}{format_money(res["max"])}</div>
                  <div class="jr-unit">{unit}</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div class='jr-sources'>", unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0;'>Rate Justification Sources</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p style='margin-top:0; color: rgba(203,213,225,0.75);'>"
            "The above rate range is based on data from the following industry sources:"
            "</p>",
            unsafe_allow_html=True,
        )

        sources = res.get("sources") or []
        if not sources:
            st.markdown(
                "<p style='color: rgba(203,213,225,0.75);'>No sources were returned confidently for this query.</p>",
                unsafe_allow_html=True,
            )
        else:
            for s in sources:
                title = (s.get("title") or "Source").replace("<", "&lt;").replace(">", "&gt;")
                url = (s.get("url") or "").replace('"', "%22")
                rng = (s.get("range") or "Source").replace("<", "&lt;").replace(">", "&gt;")
                st.markdown(
                    f"""
                    <a class="jr-source" href="{url}" target="_blank" rel="noopener noreferrer">
                      <div class="jr-ico">↗</div>
                      <div style="min-width:0;">
                        <div class="jr-source-main">{title}</div>
                        <div class="jr-source-sub">Reported Range: {rng}</div>
                      </div>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown(
            """
            <div class="jr-note">
              <strong>Note:</strong> These rates are estimates based on aggregated market data.
              Actual compensation may vary based on experience, skills, company size, and other factors.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
