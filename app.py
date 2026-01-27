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

  .jr-card{
    background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 18px 14px 18px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
  }

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
  .stButton button:hover{
    filter: brightness(1.05);
  }

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
# HTTP helpers (additional edit 11: friendlier network handling)
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


def http_post(url: str, *, timeout: int = 25, json_body: Optional[dict] = None) -> requests.Response:
    return SESSION.post(url, timeout=timeout, json=json_body)


# ============================================================
# Helpers: Geo dropdowns (CountriesNow - no key required)
# ============================================================
COUNTRIESNOW_BASE = "https://countriesnow.space/api/v0.1"


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_country_list() -> List[str]:
    url = f"{COUNTRIESNOW_BASE}/countries"
    r = http_get(url, timeout=25)
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
    # additional edit 12: robust try/except inside geo calls
    try:
        if not country:
            return ["N/A"]
        url = f"{COUNTRIESNOW_BASE}/countries/states"
        payload = {"country": country}
        r = http_post(url, json_body=payload, timeout=25)
        if not r.ok:
            return ["N/A"]
        data = r.json()
        states: List[str] = []
        for s in (data.get("data") or {}).get("states") or []:
            name = s.get("name")
            if isinstance(name, str) and name.strip():
                states.append(name.strip())
        states = sorted(set(states), key=lambda x: x.lower())
        return states if states else ["N/A"]
    except Exception:
        return ["N/A"]


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_cities(country: str, state: str) -> List[str]:
    # additional edit 12: robust try/except inside geo calls
    try:
        if not country:
            return ["N/A"]

        if not state or state == "N/A":
            url = f"{COUNTRIESNOW_BASE}/countries/cities"
            payload = {"country": country}
            r = http_post(url, json_body=payload, timeout=25)
            if not r.ok:
                return ["N/A"]
            data = r.json()
            cities = data.get("data") or []
            cities = [c.strip() for c in cities if isinstance(c, str) and c.strip()]
            cities = sorted(set(cities), key=lambda x: x.lower())
            return cities if cities else ["N/A"]

        url = f"{COUNTRIESNOW_BASE}/countries/state/cities"
        payload = {"country": country, "state": state}
        r = http_post(url, json_body=payload, timeout=25)
        if not r.ok:
            return ["N/A"]
        data = r.json()
        cities = data.get("data") or []
        cities = [c.strip() for c in cities if isinstance(c, str) and c.strip()]
        cities = sorted(set(cities), key=lambda x: x.lower())
        return cities if cities else ["N/A"]
    except Exception:
        return ["N/A"]


# ============================================================
# Helpers: FX conversion (free)
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
# Helpers: URL label (Edit 7)
# ============================================================
def safe_host(url: str) -> str:
    try:
        from urllib.parse import urlparse

        u = urlparse(url)
        host = (u.hostname or "").strip().lower()
        host = host.replace("www.", "")
        return host or "source"
    except Exception:
        return "source"


def pretty_url_label(raw_url: str) -> Tuple[str, str]:
    """
    Returns (host, readable tail).
    Edit 7 improvement: if path slug is empty/ugly, use a friendly fallback.
    """
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

        # Fallbacks
        if not cleaned or len(cleaned) < 6:
            path = unquote(u.path or "").strip()
            path = re.sub(r"\s+", " ", path)
            if path and len(path) >= 6:
                cleaned = path[:70]
            else:
                cleaned = "salary page"

        return (host, cleaned[:70])
    except Exception:
        return ("Source", "salary page")


# ============================================================
# Edit 6: sanitize parsing helpers
# ============================================================
def parse_number_like(x: Any) -> Optional[float]:
    """
    Accepts numbers or strings like:
      "120,000", "$120k", "120k", "120000", "85.5", "85/hr"
    Returns float or None.
    """
    if x is None:
        return None
    if isinstance(x, (int, float)) and math.isfinite(float(x)):
        return float(x)

    if not isinstance(x, str):
        return None

    s = x.strip().lower()
    if not s:
        return None

    # remove currency symbols / commas
    s = s.replace(",", "")
    s = re.sub(r"[\$€£aedcadusd]", "", s, flags=re.I).strip()

    # pull first numeric token
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
    """
    Simple safety clamps to prevent nonsense.
    You can tune these later.
    """
    if pay_type == "HOURLY":
        # clamp hourly to [1, 1000]
        min_v = max(1.0, min(min_v, 1000.0))
        max_v = max(1.0, min(max_v, 1500.0))
    else:
        # annual clamp to [10k, 5M]
        min_v = max(10_000.0, min(min_v, 5_000_000.0))
        max_v = max(10_000.0, min(max_v, 7_500_000.0))

    if min_v > max_v:
        min_v, max_v = max_v, min_v

    # ensure some separation if identical
    if abs(max_v - min_v) < 1e-6:
        max_v = min_v

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
# AI logic (SerpAPI + OpenAI)
# Edit 8: consistent pay_type mapping
# Edit 9: prefer ~5 sources
# Edit 10: source strength 0-100
# ============================================================
def require_env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing environment variable: {name}")
    return v


def rate_type_to_pay_type(rate_type: str) -> str:
    # rate_type in app state: "hourly" or "salary"
    return "HOURLY" if (rate_type or "").strip().lower() == "hourly" else "ANNUAL"


def pay_type_to_rate_type(pay_type: str) -> str:
    # pay_type from model: "HOURLY" or "ANNUAL"
    return "hourly" if (pay_type or "").strip().upper() == "HOURLY" else "salary"


def serpapi_search(job_title: str, country: str, state: str, city: str, rate_type: str) -> List[str]:
    serp_key = require_env("SERPAPI_API_KEY")

    location_bits = [b for b in [city, state, country] if b and b != "N/A"]
    loc = ", ".join(location_bits) if location_bits else country

    pay_type = rate_type_to_pay_type(rate_type)
    query = f'{job_title} salary range {loc} {"hourly rate" if pay_type=="HOURLY" else "annual salary"}'

    # Edit 9: fetch a bit more candidate links to help the model pick ~5 sources
    params = {"engine": "google", "q": query, "api_key": serp_key, "num": 15}

    r = http_get("https://serpapi.com/search.json", params=params, timeout=35)
    r.raise_for_status()
    data = r.json()

    urls: List[str] = []
    for item in (data.get("organic_results") or []):
        link = item.get("link")
        if isinstance(link, str) and link.startswith(("http://", "https://")):
            urls.append(link)

    # de-dupe preserving order
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
    openai_key = require_env("OPENAI_API_KEY")
    pay_type = rate_type_to_pay_type(rate_type)

    location_bits = [b for b in [city, state, country] if b and b != "N/A"]
    loc = ", ".join(location_bits) if location_bits else country

    url_block = "\n".join(f"- {u}" for u in urls[:12]) if urls else "- (no links found)"

    # Edit 9 + 10:
    # - ask for ~5 sources_used when possible
    # - provide a 0-100 "strength" score per source
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
- Prefer returning ~5 strong sources when available. If the role/location is niche and you can only confidently return 2-3, that's fine.
- Avoid low-quality or irrelevant sources.
- strength is how strong the page is as a compensation source (0-100). Use higher scores for reputable salary aggregators, job boards with actual postings, and well-known compensation datasets.
- min_links and max_links: 0-4 each when possible.
- sources_used should be a de-duplicated list of relied-upon links (may be empty).
""".strip()

    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
    payload = {"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "input": prompt, "temperature": 0}

    resp = http_post("https://api.openai.com/v1/responses", json_body=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # Extract output text
    text_out = ""
    try:
        for o in data.get("output", []) or []:
            for c in o.get("content", []) or []:
                if c.get("type") == "output_text":
                    text_out += c.get("text", "")
    except Exception:
        text_out = ""

    text_out = (text_out or "").strip()
    if not text_out:
        raise RuntimeError("OpenAI returned an empty response.")

    # Parse JSON, with recovery
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

    # Edit 6: sanitize min/max robustly
    min_raw = parsed.get("min_usd")
    max_raw = parsed.get("max_usd")
    min_usd = parse_number_like(min_raw)
    max_usd = parse_number_like(max_raw)

    if min_usd is None or max_usd is None:
        raise RuntimeError("OpenAI returned invalid min/max values.")

    min_usd, max_usd = clamp_min_max(float(min_usd), float(max_usd), pay_type_out)
    min_usd = round(min_usd)
    max_usd = round(max_usd)

    sources_used = clean_urls(parsed.get("sources_used"))
    min_links = clean_urls(parsed.get("min_links"))
    max_links = clean_urls(parsed.get("max_links"))

    # Normalize scored sources
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
            strength = item.get("strength")
            strength_num = parse_number_like(strength) if not isinstance(strength, (int, float)) else float(strength)
            if strength_num is None:
                strength_num = 50.0
            strength_int = int(max(0, min(100, round(strength_num))))

            scored_sources.append(
                {
                    "url": url.strip(),
                    "range_tag": range_tag if range_tag in ("Min", "Max", "General") else "General",
                    "strength": strength_int,
                }
            )

    # If model didn't provide scored sources, backfill from sources_used
    if not scored_sources and sources_used:
        for u in sources_used[:6]:
            scored_sources.append({"url": u, "range_tag": "General", "strength": 55})

    # De-dupe scored sources by URL
    seen = set()
    dedup_scored: List[Dict[str, Any]] = []
    for s in scored_sources:
        u = s["url"]
        if u in seen:
            continue
        seen.add(u)
        dedup_scored.append(s)

    return {
        "min_usd": int(min_usd),
        "max_usd": int(max_usd),
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
        "state": "N/A",
        "city": "N/A",
        "rate_type": "salary",  # "salary" or "hourly"
        "currency": "USD",
        "last_result": None,
        "debug_last_error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ============================================================
# Callbacks for dependent dropdowns
# ============================================================
def on_country_change():
    st.session_state["state"] = "N/A"
    st.session_state["city"] = "N/A"


def on_state_change():
    st.session_state["city"] = "N/A"


# ============================================================
# Header
# ============================================================
st.markdown('<div class="jr-title">Job Rate Finder</div>', unsafe_allow_html=True)
st.markdown('<div class="jr-subtitle">Get competitive salary and hourly rate information for any position</div>', unsafe_allow_html=True)


# ============================================================
# Form Card (no st.form so geo dropdowns refresh live)
# ============================================================
st.markdown('<div class="jr-card">', unsafe_allow_html=True)

st.text_input("Job Title *", key="job_title", placeholder="e.g., Senior Software Engineer")
st.text_area("Job Description (optional)", key="job_desc", placeholder="Paste job description here...", height=130)

uploaded = st.file_uploader("Upload Job Description (optional)", type=["txt"], accept_multiple_files=False)
if uploaded is not None:
    try:
        text = uploaded.read().decode("utf-8", errors="ignore")
        st.session_state["job_desc"] = text
    except Exception:
        pass

# Country list
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

# State options
state_options = ["N/A"]
if st.session_state["country"] and st.session_state["country"] != "(unavailable)":
    state_options = get_states_for_country(st.session_state["country"]) or ["N/A"]
    if not state_options:
        state_options = ["N/A"]

if st.session_state["state"] not in state_options:
    st.session_state["state"] = "N/A"

# City options
city_options = ["N/A"]
if st.session_state["country"] and st.session_state["country"] != "(unavailable)":
    city_options = get_cities(st.session_state["country"], st.session_state["state"]) or ["N/A"]
    if not city_options:
        city_options = ["N/A"]

if st.session_state["city"] not in city_options:
    st.session_state["city"] = "N/A"

c1, c2, c3 = st.columns(3)

with c1:
    st.selectbox(
        "State/Province (optional)",
        options=state_options,
        index=state_options.index(st.session_state["state"]) if st.session_state["state"] in state_options else 0,
        key="state",
        on_change=on_state_change,
    )

with c2:
    # recompute cities after state changes (live rerun)
    city_options = ["N/A"]
    if st.session_state["country"] and st.session_state["country"] != "(unavailable)":
        city_options = get_cities(st.session_state["country"], st.session_state["state"]) or ["N/A"]
        if not city_options:
            city_options = ["N/A"]
    if st.session_state["city"] not in city_options:
        st.session_state["city"] = "N/A"

    st.selectbox(
        "City (optional)",
        options=city_options,
        index=city_options.index(st.session_state["city"]) if st.session_state["city"] in city_options else 0,
        key="city",
    )

with c3:
    # Edit 8: keep rate_type consistent
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
st.selectbox(
    "Currency *",
    options=currency_codes,
    index=currency_codes.index(st.session_state["currency"])
    if st.session_state["currency"] in currency_codes
    else currency_codes.index("USD"),
    key="currency",
)

# ============================================================
# Edit 3: Disable button until valid
# ============================================================
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

st.markdown("</div>", unsafe_allow_html=True)


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
            state = (st.session_state["state"] or "N/A").strip()
            city = (st.session_state["city"] or "N/A").strip()
            rate_type = st.session_state["rate_type"]  # "salary" or "hourly"
            currency = st.session_state["currency"]

            urls = serpapi_search(job_title, country, state, city, rate_type)
            result = openai_estimate(job_title, job_desc, country, state, city, rate_type, urls)

            min_usd = float(result["min_usd"])
            max_usd = float(result["max_usd"])
            pay_type = str(result.get("pay_type", rate_type_to_pay_type(rate_type))).upper()

            # Convert from USD for display
            min_disp = min_usd
            max_disp = max_usd
            if currency.upper() != "USD":
                min_disp = convert_from_usd(min_usd, currency)
                max_disp = convert_from_usd(max_usd, currency)

            # Build sources (Edit 7 + 10)
            min_links = result.get("min_links") or []
            max_links = result.get("max_links") or []
            scored = result.get("scored_sources") or []
            score_map: Dict[str, int] = {}
            range_map: Dict[str, str] = {}

            for item in scored:
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    u = item["url"].strip()
                    if u:
                        score_map[u] = int(item.get("strength", 50))
                        range_map[u] = str(item.get("range_tag", "General"))

            sources: List[Dict[str, Any]] = []

            def add_source(u: str, rng: str):
                host, slug = pretty_url_label(u)
                title = f"{host} — {slug}" if slug else host
                strength = int(score_map.get(u, 55))
                sources.append({"title": title, "url": u, "range": rng, "strength": strength})

            for u in min_links:
                add_source(u, "Min (Annual)" if pay_type == "ANNUAL" else "Min (Hourly)")
            for u in max_links:
                add_source(u, "Max (Annual)" if pay_type == "ANNUAL" else "Max (Hourly)")

            # If min/max links missing, use scored sources to fill up (Edit 9: prefer more sources)
            if len(sources) < 4 and scored:
                for item in scored:
                    u = item.get("url")
                    if isinstance(u, str) and u.startswith(("http://", "https://")):
                        tag = item.get("range_tag", "General")
                        if tag == "Min":
                            rng = "Min (Annual)" if pay_type == "ANNUAL" else "Min (Hourly)"
                        elif tag == "Max":
                            rng = "Max (Annual)" if pay_type == "ANNUAL" else "Max (Hourly)"
                        else:
                            rng = "Source"
                        add_source(u, rng)
                        if len(sources) >= 6:
                            break

            # De-dupe sources by URL
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
                "rateType": pay_type_to_rate_type(pay_type),  # Edit 8
                "sources": deduped[:8],
            }

        except Exception as e:
            # Additional edit 11: user-friendly error, keep debug details hidden
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
            strength = s.get("strength", 55)
            try:
                strength_i = int(max(0, min(100, int(strength))))
            except Exception:
                strength_i = 55

            sources_html += f"""
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

    sources_html += """
      <div class="jr-note"><strong>Note:</strong> These rates are estimates based on aggregated market data. Actual compensation may vary based on experience, skills, company size, and other factors.</div>
    </div>
    """
    st.markdown(sources_html, unsafe_allow_html=True)

# Optional: hidden debug details (additional edit 11)
if st.session_state.get("debug_last_error"):
    with st.expander("Debug details", expanded=False):
        st.code(st.session_state["debug_last_error"])
