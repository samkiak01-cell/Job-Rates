# app.py
from __future__ import annotations

import os
import re
import math
import json
from typing import Any, Dict, List, Tuple, Optional

import requests
import streamlit as st


# ============================================================
# Page / Layout
# ============================================================
st.set_page_config(page_title="Job Rate Finder", page_icon="💼", layout="centered")


# ============================================================
# Styling (UI only)
# ============================================================
APP_CSS = """
<style>
  :root{
    --bg0:#0b1220;
    --bg1:#0f1b33;
    --text:#e8eefc;
    --muted:#a9b7d6;
    --border:rgba(255,255,255,.10);
    --accent:#6d5efc;
    --accent2:#9b4dff;
    --shadow:0 18px 60px rgba(0,0,0,.45);
  }

  html, body, [data-testid="stAppViewContainer"]{
    background: radial-gradient(1200px 700px at 20% -10%, rgba(109,94,252,.30), transparent 60%),
                radial-gradient(900px 600px at 110% 10%, rgba(155,77,255,.22), transparent 55%),
                linear-gradient(180deg, var(--bg0), var(--bg1));
    color: var(--text);
  }

  .block-container { padding-top: 2.1rem; padding-bottom: 2.5rem; max-width: 880px; }

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

  /* Streamlit card containers */
  div[data-testid="stContainer"]{
    background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
  }
  div[data-testid="stContainer"] > div{ padding: 12px 14px 14px 14px; }

  label, .stMarkdown p { color: var(--muted) !important; }

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

  .stButton button{
    width: 100%;
    border: 0;
    border-radius: 12px;
    padding: 12px 14px;
    font-weight: 700;
    color: white;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    box-shadow: 0 12px 35px rgba(109,94,252,.35);
  }
  .stButton button:hover{ filter: brightness(1.05); }

  /* Range block */
  .jr-range{
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 16px;
    padding: 18px;
    color: white;
    box-shadow: var(--shadow);
    border: 1px solid rgba(255,255,255,.10);
    margin-top: 16px;
  }
  .jr-range-top{ display:flex; gap:12px; align-items:center; margin-bottom: 10px; }
  .jr-range-title{ font-size: 18px; font-weight: 800; margin:0; }
  .jr-range-grid{ display:flex; align-items:flex-end; gap: 22px; }
  .jr-range-label{ font-size: 12px; color: rgba(255,255,255,.75); margin:0 0 2px 0; }
  .jr-range-amt{ font-size: 34px; font-weight: 900; margin: 0; line-height: 1.05; }
  .jr-range-unit{ font-size: 12px; color: rgba(255,255,255,.75); margin: 3px 0 0 0; }
  .jr-dash{ font-size: 26px; color: rgba(255,255,255,.70); margin: 0 2px; padding-bottom: 12px; }

  /* Sources rows */
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
  .jr-source:hover{ border-color: rgba(109,94,252,.55); background: rgba(109,94,252,.08); }
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
  .jr-source-main{ color: var(--text); font-weight: 700; margin: 0; font-size: 13px; line-height: 1.2; }
  .jr-source-sub{
    color: var(--muted);
    margin: 3px 0 0 0;
    font-size: 12px;
    display:flex;
    align-items:center;
    gap:10px;
    flex-wrap:wrap;
  }

  .jr-score-pill{
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,.14);
    background: rgba(0,0,0,.18);
    color: rgba(232,238,252,.95);
    font-size: 11px;
    font-weight: 700;
  }
  .jr-score-bar{
    width: 84px;
    height: 7px;
    border-radius: 999px;
    background: rgba(255,255,255,.14);
    overflow:hidden;
    display:inline-block;
  }
  .jr-score-fill{
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(109,94,252,.95), rgba(155,77,255,.95));
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

  header, footer { visibility: hidden; }
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)


# ============================================================
# HTTP helpers
# ============================================================
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "JobRateFinder/1.0 (+streamlit)",
        "Accept": "application/json,text/plain,*/*",
    }
)


def http_get(url: str, *, timeout: int = 25, params: Optional[dict] = None) -> requests.Response:
    return SESSION.get(url, timeout=timeout, params=params)


def http_post(
    url: str,
    *,
    timeout: int = 25,
    json_body: Optional[dict] = None,
    headers: Optional[dict] = None,
) -> requests.Response:
    return SESSION.post(url, timeout=timeout, json=json_body, headers=headers)


# ============================================================
# Secrets/env helper (fix for 401)
# ============================================================
def require_secret_or_env(name: str) -> str:
    v = (os.getenv(name, "") or "").strip()
    if not v:
        try:
            v = str(st.secrets.get(name, "")).strip()
        except Exception:
            v = ""
    if not v:
        raise RuntimeError(
            f"Missing API key/config: {name}. Set it in Streamlit Secrets or environment variables."
        )
    return v


# ============================================================
# Geo dropdowns (CountriesNow)
# ============================================================
COUNTRIESNOW_BASE = "https://countriesnow.space/api/v0.1"


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_country_list() -> List[str]:
    r = http_get(f"{COUNTRIESNOW_BASE}/countries", timeout=25)
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
    """
    Returns list of states/provinces.
    Returns [] if none or unavailable. (UI adds a blank option on top.)
    """
    try:
        if not country:
            return []
        r = http_post(f"{COUNTRIESNOW_BASE}/countries/states", json_body={"country": country}, timeout=25)
        if not r.ok:
            return []
        data = r.json()
        states: List[str] = []
        for s in (data.get("data") or {}).get("states") or []:
            name = s.get("name")
            if isinstance(name, str) and name.strip():
                states.append(name.strip())
        states = sorted(set(states), key=lambda x: x.lower())
        return states
    except Exception:
        return []


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_cities(country: str, state: str) -> List[str]:
    """
    City list.
    - If state is blank/unknown: fetch country-level cities.
    - Else: fetch state-level cities.
    Returns [] if unavailable. (UI adds a blank option on top.)
    """
    try:
        if not country:
            return []

        # If state is blank/unknown, search the whole country
        if not state:
            r = http_post(f"{COUNTRIESNOW_BASE}/countries/cities", json_body={"country": country}, timeout=25)
            if not r.ok:
                return []
            data = r.json()
            cities = data.get("data") or []
            cities = [c.strip() for c in cities if isinstance(c, str) and c.strip()]
            return sorted(set(cities), key=lambda x: x.lower())

        r = http_post(
            f"{COUNTRIESNOW_BASE}/countries/state/cities",
            json_body={"country": country, "state": state},
            timeout=25,
        )
        if not r.ok:
            return []
        data = r.json()
        cities = data.get("data") or []
        cities = [c.strip() for c in cities if isinstance(c, str) and c.strip()]
        return sorted(set(cities), key=lambda x: x.lower())
    except Exception:
        return []


# ============================================================
# FX conversion
# ============================================================
@st.cache_data(ttl=60 * 60, show_spinner=False)
def get_fx_table_usd() -> Dict[str, float]:
    r = http_get("https://open.er-api.com/v6/latest/USD", timeout=25)
    r.raise_for_status()
    data = r.json()
    rates = data.get("rates") or {}
    out: Dict[str, float] = {}
    for k, v in rates.items():
        if isinstance(k, str) and isinstance(v, (int, float)) and v and v > 0:
            out[k.upper()] = float(v)
    out["USD"] = 1.0
    return out


def convert_from_usd(amount: float, to_ccy: str) -> float:
    to_ccy = (to_ccy or "USD").upper()
    rate = get_fx_table_usd().get(to_ccy)
    return amount if not rate else amount * rate


# ============================================================
# URL label helper
# ============================================================
def pretty_url_label(raw_url: str) -> Tuple[str, str]:
    try:
        from urllib.parse import urlparse, unquote

        u = urlparse(raw_url)
        host = (u.hostname or "").replace("www.", "") or "Source"

        parts = [p for p in (u.path or "").split("/") if p]
        last = parts[-1] if parts else ""
        cleaned = unquote(last)
        cleaned = re.sub(r"\.(html|htm|php|aspx)$", "", cleaned, flags=re.I)
        cleaned = re.sub(r"[-_]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if not cleaned or len(cleaned) < 6:
            cleaned = "salary page"

        return (host, cleaned[:70])
    except Exception:
        return ("Source", "salary page")


# ============================================================
# Parsing helpers
# ============================================================
def parse_number_like(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)) and math.isfinite(float(x)):
        return float(x)
    if not isinstance(x, str):
        return None

    s = x.strip().lower()
    if not s:
        return None

    s = s.replace(",", "")
    s = re.sub(r"[\$€£]", "", s).strip()

    m = re.search(r"(-?\d+(\.\d+)?)\s*([kKmM])?", s)
    if not m:
        return None

    num = float(m.group(1))
    suf = m.group(3)
    if suf:
        if suf.lower() == "k":
            num *= 1_000
        elif suf.lower() == "m":
            num *= 1_000_000

    if not math.isfinite(num):
        return None
    return num


def clamp_min_max(min_v: float, max_v: float, pay_type: str) -> Tuple[float, float]:
    if pay_type == "HOURLY":
        min_v = max(1.0, min(min_v, 1000.0))
        max_v = max(1.0, min(max_v, 1500.0))
    else:
        min_v = max(10_000.0, min(min_v, 5_000_000.0))
        max_v = max(10_000.0, min(max_v, 7_500_000.0))

    if min_v > max_v:
        min_v, max_v = max_v, min_v
    return min_v, max_v


def clean_urls(x: Any) -> List[str]:
    if not isinstance(x, list):
        return []
    out: List[str] = []
    seen = set()
    for item in x:
        if isinstance(item, str) and item.startswith(("http://", "https://")):
            u = item.strip()
            if u and u not in seen:
                seen.add(u)
                out.append(u)
    return out


# ============================================================
# AI logic
# ============================================================
def rate_type_to_pay_type(rate_type: str) -> str:
    return "HOURLY" if (rate_type or "").strip().lower() == "hourly" else "ANNUAL"


def pay_type_to_rate_type(pay_type: str) -> str:
    return "hourly" if (pay_type or "").strip().upper() == "HOURLY" else "salary"


def serpapi_search(job_title: str, country: str, state: str, city: str, rate_type: str) -> List[str]:
    serp_key = require_secret_or_env("SERPAPI_API_KEY")

    location_bits = [b for b in [city, state, country] if b]
    loc = ", ".join(location_bits) if location_bits else country

    pay_type = rate_type_to_pay_type(rate_type)
    query = f'{job_title} salary range {loc} {"hourly rate" if pay_type=="HOURLY" else "annual salary"}'

    params = {"engine": "google", "q": query, "api_key": serp_key, "num": 15}
    r = http_get("https://serpapi.com/search.json", params=params, timeout=35)
    r.raise_for_status()
    data = r.json()

    urls: List[str] = []
    for item in (data.get("organic_results") or []):
        link = item.get("link")
        if isinstance(link, str) and link.startswith(("http://", "https://")):
            urls.append(link)

    seen = set()
    out: List[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)

    return out[:18]


def openai_estimate(
    job_title: str,
    job_desc: str,
    country: str,
    state: str,
    city: str,
    rate_type: str,
    urls: List[str],
) -> Dict[str, Any]:
    openai_key = require_secret_or_env("OPENAI_API_KEY")
    pay_type = rate_type_to_pay_type(rate_type)

    location_bits = [b for b in [city, state, country] if b]
    loc = ", ".join(location_bits) if location_bits else country

    url_block = "\n".join(f"- {u}" for u in urls[:12]) if urls else "- (no links found)"

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

  "sources": [
    {{
      "url": <url>,
      "range_tag": "Min"|"Max"|"General",
      "strength": <integer 0-100>
    }},
    ...
  ],

  "sources_used": [<url>, ...],
  "min_links": [<url>, ...],
  "max_links": [<url>, ...]
}}

Rules:
- min_usd must be <= max_usd and both realistic for the role/location.
- Try to return 5–8 strong sources if (and only if) there are 5–8 clearly relevant, reputable sources available in the candidate links.
- Do NOT force a minimum number of sources. If only 2–4 good sources exist, return only those.
- Only include a source if it materially supports the range for this role + location.
- Avoid low-quality or irrelevant sources.
- strength is how strong the page is as a compensation source (0-100).
- min_links and max_links: 0–5 each when it makes sense (do not pad with weak links).
- sources_used should be a de-duplicated list of relied-upon links.
""".strip()

    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
    payload = {"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "input": prompt, "temperature": 0}

    resp = http_post("https://api.openai.com/v1/responses", json_body=payload, timeout=60, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    text_out = ""
    for o in (data.get("output", []) or []):
        for c in (o.get("content", []) or []):
            if c.get("type") == "output_text":
                text_out += c.get("text", "")

    text_out = (text_out or "").strip()
    if not text_out:
        raise RuntimeError("OpenAI returned an empty response.")

    try:
        parsed = json.loads(text_out)
    except Exception:
        m = re.search(r"\{.*\}\s*$", text_out, re.S)
        if not m:
            raise RuntimeError("OpenAI did not return valid JSON.")
        parsed = json.loads(m.group(0))

    pay_type_out = str(parsed.get("pay_type") or pay_type).upper()
    if pay_type_out not in ("HOURLY", "ANNUAL"):
        pay_type_out = pay_type

    min_usd = parse_number_like(parsed.get("min_usd"))
    max_usd = parse_number_like(parsed.get("max_usd"))
    if min_usd is None or max_usd is None:
        raise RuntimeError("OpenAI returned invalid min/max values.")

    min_usd, max_usd = clamp_min_max(float(min_usd), float(max_usd), pay_type_out)

    sources_used = clean_urls(parsed.get("sources_used"))
    min_links = clean_urls(parsed.get("min_links"))
    max_links = clean_urls(parsed.get("max_links"))

    scored_sources: List[Dict[str, Any]] = []
    raw_sources = parsed.get("sources")
    if isinstance(raw_sources, list):
        for item in raw_sources:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if not (isinstance(url, str) and url.startswith(("http://", "https://"))):
                continue

            range_tag = str(item.get("range_tag") or "General").strip()
            if range_tag not in ("Min", "Max", "General"):
                range_tag = "General"

            strength_raw = item.get("strength")
            strength_num = (
                float(strength_raw)
                if isinstance(strength_raw, (int, float))
                else (parse_number_like(str(strength_raw)) or 55.0)
            )
            strength_int = int(max(0, min(100, round(strength_num))))
            scored_sources.append({"url": url.strip(), "range_tag": range_tag, "strength": strength_int})

    # dedupe scored sources by URL
    seen = set()
    dedup_scored: List[Dict[str, Any]] = []
    for s in scored_sources:
        u = s["url"]
        if u in seen:
            continue
        seen.add(u)
        dedup_scored.append(s)

    return {
        "min_usd": int(round(min_usd)),
        "max_usd": int(round(max_usd)),
        "pay_type": pay_type_out,
        "sources_used": sources_used,
        "min_links": min_links,
        "max_links": max_links,
        "scored_sources": dedup_scored,
    }


# ============================================================
# State init
# ============================================================
def init_state():
    defaults = {
        "job_title": "",
        "job_desc": "",
        "country": "",
        "state": "",   # blank = off
        "city": "",    # blank = off
        "rate_type": "salary",
        "currency": "USD",
        "last_result": None,
        "debug_last_error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ============================================================
# Callbacks
# ============================================================
def on_country_change():
    st.session_state["state"] = ""
    st.session_state["city"] = ""


def on_state_change():
    st.session_state["city"] = ""


# ============================================================
# Header
# ============================================================
st.markdown('<div class="jr-title">Job Rate Finder</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="jr-subtitle">Get competitive salary and hourly rate information for any position</div>',
    unsafe_allow_html=True,
)


# ============================================================
# Form card (everything inside the box)
# ============================================================
with st.container(border=True):
    st.text_input("Job Title *", key="job_title", placeholder="e.g., Senior Software Engineer")
    st.text_area("Job Description (optional)", key="job_desc", placeholder="Paste job description here...", height=130)

    uploaded = st.file_uploader("Upload Job Description (optional)", type=["txt"], accept_multiple_files=False)
    if uploaded is not None:
        try:
            text = uploaded.read().decode("utf-8", errors="ignore")
            st.session_state["job_desc"] = text
        except Exception:
            pass

    try:
        countries = get_country_list()
    except Exception:
        countries = []

    if not countries:
        st.error("Could not load country list. Check your internet connection and try again.")
        countries = ["(unavailable)"]

    country_options = [""] + countries if countries and countries[0] != "(unavailable)" else ["(unavailable)"]

    st.selectbox(
        "Country *",
        options=country_options,
        index=country_options.index(st.session_state["country"]) if st.session_state["country"] in country_options else 0,
        key="country",
        on_change=on_country_change,
    )

    # Build state list (blank option at top)
    states = []
    if st.session_state["country"] and st.session_state["country"] != "(unavailable)":
        states = get_states_for_country(st.session_state["country"]) or []
    state_options = [""] + states  # blank = off
    if st.session_state["state"] not in state_options:
        st.session_state["state"] = ""

    c1, c2, c3 = st.columns(3)

    with c1:
        st.selectbox(
            "State/Province (optional)",
            options=state_options,
            index=state_options.index(st.session_state["state"]) if st.session_state["state"] in state_options else 0,
            key="state",
            on_change=on_state_change,
            format_func=lambda x: "— Leave blank —" if x == "" else x,
        )

    # Build city list (blank option at top)
    cities = []
    if st.session_state["country"] and st.session_state["country"] != "(unavailable)":
        cities = get_cities(st.session_state["country"], st.session_state["state"]) or []
    city_options = [""] + cities  # blank = off
    if st.session_state["city"] not in city_options:
        st.session_state["city"] = ""

    with c2:
        st.selectbox(
            "City (optional)",
            options=city_options,
            index=city_options.index(st.session_state["city"]) if st.session_state["city"] in city_options else 0,
            key="city",
            format_func=lambda x: "— Leave blank —" if x == "" else x,
        )

    with c3:
        rate_type_label = st.radio(
            "Rate Type *",
            options=["Salary", "Hourly"],
            index=0 if st.session_state["rate_type"] == "salary" else 1,
            horizontal=True,
            key="rate_type_radio",
        )
        st.session_state["rate_type"] = "hourly" if rate_type_label == "Hourly" else "salary"

    fx_rates = get_fx_table_usd()
    currency_codes = sorted(fx_rates.keys())
    st.selectbox(
        "Currency *",
        options=currency_codes,
        index=currency_codes.index(st.session_state["currency"])
        if st.session_state["currency"] in currency_codes
        else currency_codes.index("USD"),
        key="currency",
    )

    def is_valid() -> Tuple[bool, str]:
        if not (st.session_state["job_title"] or "").strip():
            return False, "Job Title is required."
        if not (st.session_state["country"] or "").strip():
            return False, "Country is required."
        if st.session_state["country"] == "(unavailable)":
            return False, "Country list is unavailable right now. Please try again."
        if not (st.session_state["currency"] or "").strip():
            return False, "Currency is required."
        return True, ""

    ok, msg = is_valid()
    submitted = st.button("Get Rates!", disabled=not ok)
    if not ok and msg:
        st.caption(msg)


# ============================================================
# Run estimation on submit
# ============================================================
if submitted:
    st.session_state["debug_last_error"] = None

    with st.spinner("Analyzing recent market data..."):
        try:
            job_title = st.session_state["job_title"].strip()
            job_desc = (st.session_state["job_desc"] or "").strip()
            country = st.session_state["country"].strip()
            state = (st.session_state["state"] or "").strip()  # blank allowed
            city = (st.session_state["city"] or "").strip()    # blank allowed
            rate_type = st.session_state["rate_type"]
            currency = st.session_state["currency"]

            urls = serpapi_search(job_title, country, state, city, rate_type)
            result = openai_estimate(job_title, job_desc, country, state, city, rate_type, urls)

            min_usd = float(result["min_usd"])
            max_usd = float(result["max_usd"])
            pay_type = str(result.get("pay_type", rate_type_to_pay_type(rate_type))).upper()

            min_disp = min_usd
            max_disp = max_usd
            if currency.upper() != "USD":
                min_disp = convert_from_usd(min_usd, currency)
                max_disp = convert_from_usd(max_usd, currency)

            scored = result.get("scored_sources") or []
            score_map: Dict[str, int] = {}
            tag_map: Dict[str, str] = {}
            for item in scored:
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    u = item["url"].strip()
                    if u:
                        score_map[u] = int(item.get("strength", 55))
                        tag_map[u] = str(item.get("range_tag", "General"))

            sources: List[Dict[str, Any]] = []
            min_links = result.get("min_links") or []
            max_links = result.get("max_links") or []
            sources_used = result.get("sources_used") or []

            def add_source(u: str, rng: str):
                host, slug = pretty_url_label(u)
                title = f"{host} — {slug}" if slug else host
                strength = int(score_map.get(u, 55))
                sources.append({"title": title, "url": u, "range": rng, "strength": strength})

            for u in min_links:
                add_source(u, "Min (Annual)" if pay_type == "ANNUAL" else "Min (Hourly)")
            for u in max_links:
                add_source(u, "Max (Annual)" if pay_type == "ANNUAL" else "Max (Hourly)")

            # Prefer 5+ only if we truly have them: fill from scored, then sources_used
            if len(sources) < 5:
                for item in scored:
                    u = item.get("url")
                    if isinstance(u, str) and u.startswith(("http://", "https://")):
                        tag = tag_map.get(u, "General")
                        if tag == "Min":
                            rng = "Min (Annual)" if pay_type == "ANNUAL" else "Min (Hourly)"
                        elif tag == "Max":
                            rng = "Max (Annual)" if pay_type == "ANNUAL" else "Max (Hourly)"
                        else:
                            rng = "Source"
                        add_source(u, rng)
                        if len(sources) >= 10:
                            break

            if len(sources) < 3:
                for u in sources_used:
                    add_source(u, "Source")
                    if len(sources) >= 8:
                        break

            # dedupe
            seen = set()
            deduped: List[Dict[str, Any]] = []
            for s in sources:
                u = s.get("url")
                if not u or u in seen:
                    continue
                seen.add(u)
                deduped.append(s)

            st.session_state["last_result"] = {
                "min": int(round(min_disp)),
                "max": int(round(max_disp)),
                "currency": currency.upper(),
                "rateType": pay_type_to_rate_type(pay_type),
                # increased source list cap (previous update)
                "sources": deduped[:12],
            }

        except requests.HTTPError as e:
            st.session_state["last_result"] = None
            st.session_state["debug_last_error"] = repr(e)

            msg = "Something went wrong while calculating the rate range. Please try again in a moment."
            try:
                status = e.response.status_code if e.response is not None else None
            except Exception:
                status = None

            if status == 401:
                msg = (
                    "OpenAI authentication failed (401). "
                    "Make sure OPENAI_API_KEY is set in Streamlit Secrets or environment variables, "
                    "and that the key is valid."
                )
            st.error(msg)

        except Exception as e:
            st.session_state["last_result"] = None
            st.session_state["debug_last_error"] = repr(e)
            st.error("Something went wrong while calculating the rate range. Please try again in a moment.")


# ============================================================
# Render results
# ============================================================
res = st.session_state.get("last_result")
if res:
    unit = "per hour" if res["rateType"] == "hourly" else "per year"
    cur = res["currency"]
    min_v = res["min"]
    max_v = res["max"]

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

    sources: List[Dict[str, Any]] = res.get("sources") or []

    with st.container(border=True):
        st.markdown("### Rate Justification Sources")
        st.caption("The above rate range is based on data from the following industry sources:")

        if not sources:
            st.caption("No sources were returned confidently for this query.")
        else:
            for s in sources:
                title = (s.get("title") or "Source").replace("<", "&lt;").replace(">", "&gt;")
                url = (s.get("url") or "").replace('"', "%22")
                rng = (s.get("range") or "Source").replace("<", "&lt;").replace(">", "&gt;")

                try:
                    strength_i = int(max(0, min(100, int(s.get("strength", 55)))))
                except Exception:
                    strength_i = 55

                row_html = f"""
                <a class="jr-source" href="{url}" target="_blank" rel="noopener noreferrer">
                  <div class="jr-source-ico">↗</div>
                  <div style="min-width:0; width:100%;">
                    <div class="jr-source-main">{title}</div>
                    <div class="jr-source-sub">
                      <span>Reported Range: {rng}</span>
                      <span class="jr-score-pill">
                        <span>Source Strength</span>
                        <span>{strength_i}/100</span>
                        <span class="jr-score-bar">
                          <span class="jr-score-fill" style="width:{strength_i}%;"></span>
                        </span>
                      </span>
                    </div>
                  </div>
                </a>
                """
                st.markdown(row_html, unsafe_allow_html=True)

        st.markdown(
            """
            <div class="jr-note">
              <strong>Note:</strong> These rates are estimates based on aggregated market data.
              Actual compensation may vary based on experience, skills, company size, and other factors.
            </div>
            """,
            unsafe_allow_html=True,
        )

if st.session_state.get("debug_last_error"):
    with st.expander("Debug details", expanded=False):
        st.code(st.session_state["debug_last_error"])
