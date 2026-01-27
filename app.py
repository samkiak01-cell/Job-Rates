# app.py
from __future__ import annotations

import os
import re
import math
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st


# ============================================================
# Page / Layout
# ============================================================
st.set_page_config(page_title="Job Rate Finder", page_icon="💼", layout="centered")


# ============================================================
# Styling (no hardcoded values in inputs; only UI styling)
# ============================================================
APP_CSS = """
<style>
  :root{
    --bg0:#0b1220;
    --bg1:#0f1b33;
    --card:#0f1a30;
    --card2:#0c162a;
    --text:#e8eefc;
    --muted:#a9b7d6;
    --border:rgba(255,255,255,.10);
    --accent:#6d5efc;
    --accent2:#9b4dff;
    --good:#19c37d;
    --warn:#ffcc66;
    --shadow:0 18px 60px rgba(0,0,0,.45);
  }

  html, body, [data-testid="stAppViewContainer"]{
    background: radial-gradient(1200px 700px at 20% -10%, rgba(109,94,252,.30), transparent 60%),
                radial-gradient(900px 600px at 110% 10%, rgba(155,77,255,.22), transparent 55%),
                linear-gradient(180deg, var(--bg0), var(--bg1));
    color: var(--text);
  }

  /* tighten default spacing */
  .block-container { padding-top: 2.1rem; padding-bottom: 2.5rem; max-width: 880px; }

  /* header */
  .jr-title{
    text-align:center;
    margin-bottom: .35rem;
    font-size: 44px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: var(--text);
  }
  .jr-subtitle{
    text-align:center;
    margin-bottom: 1.5rem;
    color: var(--muted);
    font-size: 15px;
  }

  /* cards */
  .jr-card{
    background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 18px 14px 18px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
  }
  .jr-card-inner{
    background: rgba(0,0,0,.12);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px;
  }

  /* streamlit widgets */
  label, .st-emotion-cache-16idsys p, .stMarkdown p { color: var(--muted) !important; }
  .stTextInput input, .stTextArea textarea{
    background: rgba(0,0,0,.28) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 10px !important;
  }
  .stSelectbox [data-baseweb="select"] > div{
    background: rgba(0,0,0,.28) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
  }

  /* button */
  .stButton button, .stForm button{
    width: 100%;
    border: 0;
    border-radius: 12px;
    padding: 12px 14px;
    font-weight: 700;
    color: white;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    box-shadow: 0 12px 35px rgba(109,94,252,.35);
  }
  .stButton button:hover, .stForm button:hover{
    filter: brightness(1.05);
  }

  /* results range card */
  .jr-range{
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 16px;
    padding: 18px;
    color: white;
    box-shadow: var(--shadow);
    border: 1px solid rgba(255,255,255,.10);
  }
  .jr-range-top{
    display:flex;
    gap:12px;
    align-items:center;
    margin-bottom: 10px;
  }
  .jr-range-title{
    font-size: 18px;
    font-weight: 800;
    margin:0;
  }
  .jr-range-grid{
    display:flex;
    align-items:flex-end;
    gap: 22px;
  }
  .jr-range-label{
    font-size: 12px;
    color: rgba(255,255,255,.75);
    margin:0 0 2px 0;
  }
  .jr-range-amt{
    font-size: 34px;
    font-weight: 900;
    margin: 0;
    line-height: 1.05;
  }
  .jr-range-unit{
    font-size: 12px;
    color: rgba(255,255,255,.75);
    margin: 3px 0 0 0;
  }
  .jr-dash{
    font-size: 26px;
    color: rgba(255,255,255,.70);
    margin: 0 2px;
    padding-bottom: 12px;
  }

  /* sources */
  .jr-sources-card{
    background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.03));
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: var(--shadow);
  }
  .jr-sources-title{
    font-size: 18px;
    font-weight: 800;
    margin: 0 0 6px 0;
    color: var(--text);
  }
  .jr-sources-sub{
    color: var(--muted);
    margin: 0 0 12px 0;
    font-size: 13px;
  }
  .jr-source{
    display:flex;
    gap: 12px;
    align-items:flex-start;
    padding: 12px 12px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: rgba(0,0,0,.14);
    text-decoration: none !important;
    margin-bottom: 10px;
  }
  .jr-source:hover{
    border-color: rgba(109,94,252,.55);
    background: rgba(109,94,252,.08);
  }
  .jr-source-ico{
    width: 22px;
    height: 22px;
    border-radius: 8px;
    background: rgba(109,94,252,.22);
    display:flex;
    align-items:center;
    justify-content:center;
    flex: 0 0 auto;
    margin-top: 1px;
  }
  .jr-source-main{
    color: var(--text);
    font-weight: 700;
    margin: 0;
    font-size: 13px;
    line-height: 1.2;
  }
  .jr-source-sub{
    color: var(--muted);
    margin: 3px 0 0 0;
    font-size: 12px;
  }
  .jr-note{
    margin-top: 12px;
    padding: 12px 12px;
    border-radius: 12px;
    border: 1px solid rgba(255,204,102,.30);
    background: rgba(255,204,102,.10);
    color: rgba(255,224,170,.95);
    font-size: 12px;
  }

  /* remove streamlit header/footer */
  header, footer { visibility: hidden; }
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)


# ============================================================
# Helpers: Geo dropdowns (CountriesNow - no key required)
# ============================================================
COUNTRIESNOW_BASE = "https://countriesnow.space/api/v0.1"

@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_country_list() -> List[str]:
    """
    Returns a list of country names using CountriesNow.
    No API key required.
    """
    url = f"{COUNTRIESNOW_BASE}/countries"
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    data = r.json()
    countries = []
    for item in (data.get("data") or []):
        name = item.get("country")
        if isinstance(name, str) and name.strip():
            countries.append(name.strip())
    countries = sorted(set(countries), key=lambda x: x.lower())
    return countries

@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_states_for_country(country: str) -> List[str]:
    """
    Returns states/provinces for a country using CountriesNow.
    If none exist or API doesn't return any, returns ["N/A"].
    """
    if not country:
        return ["N/A"]
    url = f"{COUNTRIESNOW_BASE}/countries/states"
    payload = {"country": country}
    r = requests.post(url, json=payload, timeout=25)
    if not r.ok:
        return ["N/A"]
    data = r.json()
    states = []
    for s in (data.get("data") or {}).get("states") or []:
        name = s.get("name")
        if isinstance(name, str) and name.strip():
            states.append(name.strip())
    states = sorted(set(states), key=lambda x: x.lower())
    return states if states else ["N/A"]

@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_cities(country: str, state: str) -> List[str]:
    """
    Returns city list.
    - If state == "N/A": fetch all cities in country (CountriesNow /countries/cities)
    - Else: fetch cities in state (CountriesNow /countries/state/cities)
    If none, returns ["N/A"].
    """
    if not country:
        return ["N/A"]

    if not state or state == "N/A":
        url = f"{COUNTRIESNOW_BASE}/countries/cities"
        payload = {"country": country}
        r = requests.post(url, json=payload, timeout=25)
        if not r.ok:
            return ["N/A"]
        data = r.json()
        cities = data.get("data") or []
        cities = [c.strip() for c in cities if isinstance(c, str) and c.strip()]
        cities = sorted(set(cities), key=lambda x: x.lower())
        return cities if cities else ["N/A"]

    url = f"{COUNTRIESNOW_BASE}/countries/state/cities"
    payload = {"country": country, "state": state}
    r = requests.post(url, json=payload, timeout=25)
    if not r.ok:
        return ["N/A"]
    data = r.json()
    cities = data.get("data") or []
    cities = [c.strip() for c in cities if isinstance(c, str) and c.strip()]
    cities = sorted(set(cities), key=lambda x: x.lower())
    return cities if cities else ["N/A"]


# ============================================================
# Helpers: FX conversion (free)
# ============================================================
_fx_cache: Dict[str, float] = {"USD": 1.0}

@st.cache_data(ttl=60 * 60, show_spinner=False)
def get_fx_table_usd() -> Dict[str, float]:
    r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=25)
    r.raise_for_status()
    data = r.json()
    rates = data.get("rates") or {}
    out = {}
    for k, v in rates.items():
        if isinstance(k, str) and isinstance(v, (int, float)) and v and v > 0:
            out[k.upper()] = float(v)
    out["USD"] = 1.0
    return out

def convert_from_usd(amount: float, to_ccy: str) -> float:
    to_ccy = (to_ccy or "USD").upper()
    rates = get_fx_table_usd()
    rate = rates.get(to_ccy)
    if not rate:
        return amount
    return amount * rate


# ============================================================
# Helpers: URL label (for sources list)
# ============================================================
def pretty_url_label(raw_url: str) -> Tuple[str, str]:
    try:
        from urllib.parse import urlparse, unquote
        u = urlparse(raw_url)
        host = (u.hostname or "").replace("www.", "")
        parts = [p for p in (u.path or "").split("/") if p]
        last = parts[-1] if parts else ""
        cleaned = unquote(last)
        cleaned = re.sub(r"\.(html|htm|php|aspx)$", "", cleaned, flags=re.I)
        cleaned = re.sub(r"[-_]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if cleaned and len(cleaned) >= 6:
            secondary = cleaned[:70]
        else:
            secondary = unquote(u.path or "")[:70].strip() or raw_url[:70]

        return (host or "Source", secondary)
    except Exception:
        return ("Source", raw_url)


# ============================================================
# AI logic (SerpAPI + OpenAI)
# - No hardcoded responses
# - No prefilled form values
# ============================================================
def require_env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing environment variable: {name}")
    return v

def serpapi_search(job_title: str, country: str, state: str, city: str, rate_type: str) -> List[str]:
    """
    Uses SerpAPI to fetch recent job/salary listing pages.
    Returns a de-duped list of URLs.
    """
    serp_key = require_env("SERPAPI_API_KEY")

    location_bits = [b for b in [city, state, country] if b and b != "N/A"]
    loc = ", ".join(location_bits) if location_bits else country

    # Focus on salary range signals. Keep query natural.
    # Also include "last 3 months" constraint in prompt to OpenAI later; search uses recency-ish terms.
    query = f'{job_title} salary range {loc} {"hourly rate" if rate_type=="hourly" else "annual salary"}'
    params = {
        "engine": "google",
        "q": query,
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
    out = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)

    return out[:12]

def openai_estimate(job_title: str, job_desc: str, country: str, state: str, city: str, rate_type: str, urls: List[str]) -> Dict[str, Any]:
    """
    Calls OpenAI and returns a structured response:
      {
        "min_usd": number,
        "max_usd": number,
        "pay_type": "HOURLY"|"ANNUAL",
        "sources_used": [url...],
        "min_links": [url...],
        "max_links": [url...],
      }
    """
    openai_key = require_env("OPENAI_API_KEY")

    # Prefer "ANNUAL"/"HOURLY" tokens for downstream compatibility
    pay_type = "HOURLY" if rate_type == "hourly" else "ANNUAL"

    location_bits = [b for b in [city, state, country] if b and b != "N/A"]
    loc = ", ".join(location_bits) if location_bits else country

    # We do NOT force 5 sources. We allow fewer, but must be "confident".
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
- Avoid low-quality or irrelevant sources.
- Provide 0-3 links for min_links and 0-3 links for max_links when possible.
- sources_used should be a de-duplicated list of all relied-upon links (may be empty).
""".strip()

    # Minimal OpenAI call via HTTPS (no SDK required)
    # Uses Responses API format compatible with modern OpenAI endpoints.
    # If your org only allows Chat Completions, we can swap it later.
    headers = {
        "Authorization": f"Bearer {openai_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "input": prompt,
        "temperature": 0,
    }

    resp = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # Extract text output
    # responses: output[0].content[0].text is typical
    text_out = ""
    try:
        for o in data.get("output", []):
            for c in o.get("content", []):
                if c.get("type") == "output_text":
                    text_out += c.get("text", "")
    except Exception:
        text_out = ""

    text_out = (text_out or "").strip()
    if not text_out:
        raise RuntimeError("OpenAI returned an empty response.")

    # Parse JSON
    try:
        parsed = json.loads(text_out)
    except Exception:
        # Sometimes the model may return leading/trailing text; try to recover JSON object
        m = re.search(r"\{.*\}\s*$", text_out, re.S)
        if not m:
            raise RuntimeError("OpenAI did not return valid JSON.")
        parsed = json.loads(m.group(0))

    # Validate
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
        out = []
        seen = set()
        for item in x:
            if isinstance(item, str) and item.startswith("http") and item not in seen:
                seen.add(item)
                out.append(item)
        return out

    sources_used = clean_urls(parsed.get("sources_used"))
    min_links = clean_urls(parsed.get("min_links"))
    max_links = clean_urls(parsed.get("max_links"))

    return {
        "min_usd": round(min_usd),
        "max_usd": round(max_usd),
        "pay_type": pay_type_out,
        "sources_used": sources_used,
        "min_links": min_links,
        "max_links": max_links,
    }


# ============================================================
# State init (NO prefilled answers)
# ============================================================
def init_state():
    defaults = {
        "job_title": "",
        "job_desc": "",
        "country": "",
        "state": "N/A",
        "city": "N/A",
        "rate_type": "salary",   # selection default is OK; not an answer
        "currency": "USD",       # selection default is OK; not an answer
        "last_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ============================================================
# Header
# ============================================================
st.markdown('<div class="jr-title">Job Rate Finder</div>', unsafe_allow_html=True)
st.markdown('<div class="jr-subtitle">Get competitive salary and hourly rate information for any position</div>', unsafe_allow_html=True)


# ============================================================
# Form Card
# ============================================================
st.markdown('<div class="jr-card">', unsafe_allow_html=True)

with st.form("job_rate_form", clear_on_submit=False):
    # Title
    job_title = st.text_input(
        "Job Title *",
        key="job_title",
        placeholder="e.g., Senior Software Engineer",
        value=st.session_state["job_title"] or "",
    )

    # Description (optional)
    job_desc = st.text_area(
        "Job Description (optional)",
        key="job_desc",
        placeholder="Paste job description here...",
        height=130,
        value=st.session_state["job_desc"] or "",
    )

    uploaded = st.file_uploader("Upload Job Description (optional)", type=["txt"], accept_multiple_files=False)
    if uploaded is not None:
        try:
            text = uploaded.read().decode("utf-8", errors="ignore")
            st.session_state["job_desc"] = text
            job_desc = text
        except Exception:
            pass

    # Geo dropdowns (no free text)
    try:
        countries = get_country_list()
    except Exception:
        countries = []

    if not countries:
        st.error("Could not load country list. Check your internet connection and try again.")
        countries = ["(unavailable)"]

    # Country
    country = st.selectbox(
        "Country *",
        options=[""] + countries if countries[0] != "(unavailable)" else ["(unavailable)"],
        index=([""] + countries).index(st.session_state["country"]) if (st.session_state["country"] in ([""] + countries)) else 0,
        key="country_select",
    )
    # keep in session
    st.session_state["country"] = "" if country == "(unavailable)" else country

    # States
    state_options = ["N/A"]
    if st.session_state["country"]:
        state_options = get_states_for_country(st.session_state["country"])
        if not state_options:
            state_options = ["N/A"]

    # If current state not in list, reset to N/A
    if st.session_state["state"] not in state_options:
        st.session_state["state"] = "N/A"

    # Cities depend on country + state
    city_options = ["N/A"]
    if st.session_state["country"]:
        city_options = get_cities(st.session_state["country"], st.session_state["state"])
        if not city_options:
            city_options = ["N/A"]

    if st.session_state["city"] not in city_options:
        st.session_state["city"] = "N/A"

    c1, c2, c3 = st.columns(3)
    with c1:
        st_state = st.selectbox(
            "State/Province (optional)",
            options=state_options,
            index=state_options.index(st.session_state["state"]) if st.session_state["state"] in state_options else 0,
            key="state_select",
        )
        st.session_state["state"] = st_state

    with c2:
        st_city = st.selectbox(
            "City (optional)",
            options=city_options,
            index=city_options.index(st.session_state["city"]) if st.session_state["city"] in city_options else 0,
            key="city_select",
        )
        st.session_state["city"] = st_city

    with c3:
        # rate type
        rate_type_label = st.radio(
            "Rate Type *",
            options=["Salary", "Hourly"],
            index=0 if st.session_state["rate_type"] == "salary" else 1,
            horizontal=True,
            key="rate_type_radio",
        )
        st.session_state["rate_type"] = "hourly" if rate_type_label == "Hourly" else "salary"

    # Currency
    fx_rates = get_fx_table_usd()
    currency_codes = sorted(fx_rates.keys())
    currency = st.selectbox(
        "Currency *",
        options=currency_codes,
        index=currency_codes.index(st.session_state["currency"]) if st.session_state["currency"] in currency_codes else currency_codes.index("USD"),
        key="currency_select",
    )
    st.session_state["currency"] = currency

    # Submit
    submitted = st.form_submit_button("Get Rates!")

st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# Run estimation on submit
# ============================================================
def is_valid() -> Tuple[bool, str]:
    if not (st.session_state["job_title"] or "").strip():
        return False, "Job Title is required."
    if not (st.session_state["country"] or "").strip():
        return False, "Country is required."
    if not (st.session_state["currency"] or "").strip():
        return False, "Currency is required."
    return True, ""

if submitted:
    ok, msg = is_valid()
    if not ok:
        st.warning(msg)
    else:
        with st.spinner("Analyzing recent market data..."):
            try:
                job_title = st.session_state["job_title"].strip()
                job_desc = (st.session_state["job_desc"] or "").strip()
                country = st.session_state["country"].strip()
                state = (st.session_state["state"] or "N/A").strip()
                city = (st.session_state["city"] or "N/A").strip()
                rate_type = st.session_state["rate_type"]
                currency = st.session_state["currency"]

                urls = serpapi_search(job_title, country, state, city, rate_type)
                result = openai_estimate(job_title, job_desc, country, state, city, rate_type, urls)

                # Convert from USD for display
                min_usd = float(result["min_usd"])
                max_usd = float(result["max_usd"])
                pay_type = result.get("pay_type", "ANNUAL")

                min_disp = min_usd
                max_disp = max_usd
                if currency.upper() != "USD":
                    min_disp = convert_from_usd(min_usd, currency)
                    max_disp = convert_from_usd(max_usd, currency)

                # build sources list objects
                sources_used = result.get("sources_used") or []
                min_links = result.get("min_links") or []
                max_links = result.get("max_links") or []

                sources: List[Dict[str, str]] = []

                for u in min_links:
                    host, slug = pretty_url_label(u)
                    sources.append({"title": f"{host} — {slug}", "url": u, "range": "Min (Annual)" if pay_type == "ANNUAL" else "Min (Hourly)"})
                for u in max_links:
                    host, slug = pretty_url_label(u)
                    sources.append({"title": f"{host} — {slug}", "url": u, "range": "Max (Annual)" if pay_type == "ANNUAL" else "Max (Hourly)"})

                if not sources:
                    for u in sources_used:
                        host, slug = pretty_url_label(u)
                        sources.append({"title": f"{host} — {slug}", "url": u, "range": "Source"})

                # de-dupe URLs
                seen = set()
                deduped = []
                for s in sources:
                    if s["url"] in seen:
                        continue
                    seen.add(s["url"])
                    deduped.append(s)

                st.session_state["last_result"] = {
                    "min": int(round(min_disp)),
                    "max": int(round(max_disp)),
                    "currency": currency.upper(),
                    "rateType": "hourly" if pay_type == "HOURLY" else "salary",
                    "sources": deduped,
                }

            except Exception as e:
                st.session_state["last_result"] = None
                st.error(str(e))


# ============================================================
# Render results (NO HTML shown as code; only markdown HTML blocks)
# ============================================================
res = st.session_state.get("last_result")

if res:
    unit = "per hour" if res["rateType"] == "hourly" else "per year"
    cur = res["currency"]
    min_v = res["min"]
    max_v = res["max"]

    # Range Card (rendered as HTML; not printed anywhere else)
    range_html = f"""
    <div class="jr-range">
      <div class="jr-range-top">
        <div style="width:28px;height:28px;border-radius:10px;background:rgba(255,255,255,.16);display:flex;align-items:center;justify-content:center;font-weight:900;">$</div>
        <div class="jr-range-title">Estimated Rate Range</div>
      </div>
      <div class="jr-range-grid">
        <div>
          <p class="jr-range-label">Minimum</p>
          <p class="jr-range-amt">{cur} {min_v:,}</p>
          <p class="jr-range-unit">{unit}</p>
        </div>
        <div class="jr-dash">—</div>
        <div>
          <p class="jr-range-label">Maximum</p>
          <p class="jr-range-amt">{cur} {max_v:,}</p>
          <p class="jr-range-unit">{unit}</p>
        </div>
      </div>
    </div>
    """
    st.markdown(range_html, unsafe_allow_html=True)

    # Sources
    sources: List[Dict[str, str]] = res.get("sources") or []
    sources_html = """
    <div class="jr-sources-card">
      <div class="jr-sources-title">Rate Justification Sources</div>
      <div class="jr-sources-sub">The above rate range is based on data from the following industry sources:</div>
    """
    if not sources:
        sources_html += '<div style="color:var(--muted);font-size:13px;">No sources were returned confidently for this query.</div>'
    else:
        for s in sources:
            title = (s.get("title") or "Source").replace("<", "&lt;").replace(">", "&gt;")
            url = (s.get("url") or "").replace('"', "%22")
            rng = (s.get("range") or "Source").replace("<", "&lt;").replace(">", "&gt;")
            sources_html += f"""
              <a class="jr-source" href="{url}" target="_blank" rel="noopener noreferrer">
                <div class="jr-source-ico">↗</div>
                <div style="min-width:0;">
                  <div class="jr-source-main">{title}</div>
                  <div class="jr-source-sub">Reported Range: {rng}</div>
                </div>
              </a>
            """

    sources_html += """
      <div class="jr-note"><strong>Note:</strong> These rates are estimates based on aggregated market data. Actual compensation may vary based on experience, skills, company size, and other factors.</div>
    </div>
    """
    st.markdown(sources_html, unsafe_allow_html=True)
