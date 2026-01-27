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
# Page / Layout
# ============================================================
st.set_page_config(page_title="Job Rate Finder", page_icon="💲", layout="centered")


# ============================================================
# Styling (keep your dark sleek UI)
# ============================================================
APP_CSS = """
<style>
  :root{
    --bg0:#070A12;
    --bg1:#0B1020;
    --text:#E5E7EB;
    --muted:#CBD5E1;
    --muted2:rgba(203,213,225,0.75);
    --border:rgba(148,163,184,0.18);
    --card:rgba(17,24,39,0.65);
    --chip:rgba(2,6,23,0.35);
    --accent1:#4F46E5;
    --accent2:#7C3AED;
    --accent3:#A855F7;
    --shadow:0 20px 60px rgba(0,0,0,0.35);
  }

  .stApp{
    background:
      radial-gradient(1200px 800px at 20% 0%, rgba(124, 58, 237, 0.35), transparent 60%),
      radial-gradient(1200px 800px at 80% 10%, rgba(99, 102, 241, 0.30), transparent 55%),
      linear-gradient(180deg, var(--bg0) 0%, var(--bg1) 100%);
    color: var(--text);
  }

  .block-container{
    padding-top: 2.2rem;
    padding-bottom: 3rem;
    max-width: 860px;
  }

  header, footer { visibility: hidden; }

  .jr-title{
    text-align:center;
    margin-bottom: 4px;
    font-size: 44px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: var(--text);
  }
  .jr-subtitle{
    text-align:center;
    margin-top: 0;
    margin-bottom: 1.5rem;
    color: var(--muted2);
    font-size: 15px;
  }

  .jr-card{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 18px 6px 18px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
  }

  /* Inputs */
  .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div{
    background: var(--chip) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
    border-radius: 10px !important;
  }
  .stTextArea textarea::placeholder, .stTextInput input::placeholder{
    color: rgba(203,213,225,0.55) !important;
  }

  /* Buttons */
  .stForm button{
    background: linear-gradient(90deg, var(--accent1) 0%, var(--accent2) 60%, var(--accent3) 100%) !important;
    color: white !important;
    border: 0 !important;
    border-radius: 12px !important;
    padding: 0.65rem 1rem !important;
    font-weight: 800 !important;
    width: 100% !important;
  }
  .stForm button:hover{ filter: brightness(1.05); }

  /* Result gradient card */
  .jr-gradient{
    background: linear-gradient(90deg, var(--accent1) 0%, var(--accent2) 50%, var(--accent3) 100%);
    border-radius: 16px;
    padding: 18px;
    color: white;
    box-shadow: 0 18px 50px rgba(0,0,0,0.35);
    border: 1px solid rgba(255,255,255,0.14);
  }
  .jr-range{
    display:flex;
    gap:24px;
    align-items: baseline;
  }
  .jr-range .jr-sep{
    font-size: 26px;
    opacity: .6;
    margin: 0 4px;
  }
  .jr-label{
    font-size: 12px;
    opacity: .78;
    margin-bottom: 2px;
  }
  .jr-money{
    font-size: 34px;
    font-weight: 900;
    line-height: 1.15;
  }
  .jr-unit{
    font-size: 12px;
    opacity: .78;
    margin-top: 4px;
  }

  /* Sources card */
  .jr-sources{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px;
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
  }
  .jr-source{
    display:flex;
    gap: 12px;
    padding: 12px;
    border-radius: 12px;
    border: 1px solid rgba(148,163,184,0.14);
    background: rgba(2,6,23,0.35);
    transition: all 0.15s ease;
    text-decoration: none !important;
    margin-top: 10px;
  }
  .jr-source:hover{
    border-color: rgba(99,102,241,0.55);
    background: rgba(2,6,23,0.55);
    transform: translateY(-1px);
  }
  .jr-ico{
    width: 22px;
    height: 22px;
    border-radius: 7px;
    background: rgba(99,102,241,0.22);
    display: grid;
    place-items: center;
    flex: 0 0 22px;
    margin-top: 2px;
    color: white;
    font-weight: 900;
    font-size: 12px;
  }
  .jr-source-main{
    color: var(--text) !important;
    font-weight: 800;
    font-size: 13px;
    line-height: 1.2;
  }
  .jr-source-sub{
    color: rgba(156,163,175,1) !important;
    font-size: 12px;
    margin-top: 4px;
  }

  .jr-note{
    margin-top: 14px;
    padding: 12px;
    border-radius: 12px;
    border: 1px solid rgba(251,191,36,0.35);
    background: rgba(251,191,36,0.10);
    color: #FDE68A;
    font-size: 12px;
  }
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
# Helpers
# ============================================================
def require_env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing environment variable: {name}")
    return v


def format_money(n: Any) -> str:
    try:
        return f"{int(round(float(n))):,}"
    except Exception:
        return "—"


def safe_host(url: str) -> str:
    try:
        host = re.sub(r"^https?://", "", (url or "").strip(), flags=re.I)
        host = host.split("/")[0]
        host = re.sub(r"^www\.", "", host, flags=re.I)
        return host or "source"
    except Exception:
        return "source"


def prettify_url_label(url: str) -> str:
    host = safe_host(url)
    tail = ""
    try:
        s = re.sub(r"^https?://", "", (url or "").strip(), flags=re.I)
        s = s.split("/", 1)[1] if "/" in s else ""
        s = re.sub(r"[?#].*$", "", s)
        s = re.sub(r"\.(html|htm|php|aspx)$", "", s, flags=re.I)
        s = s.replace("-", " ").replace("_", " ")
        s = re.sub(r"\s+", " ", s).strip()
        tail = s[:58].rstrip() + ("…" if len(s) > 58 else "")
    except Exception:
        tail = ""
    return f"{host} — {tail}" if tail else host


def html_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============================================================
# FIX: Sources parsing (prevents the “big code box”)
# ============================================================
def parse_source_blob(blob: Any, default_range: str = "Source") -> Optional[SourceItem]:
    """
    Accepts:
      - dict {title,url,range}
      - plain URL string
      - HTML <a ... href="..."> ... Reported Range: X ... </a>
    Returns clean SourceItem so we NEVER render raw HTML.
    """
    if blob is None:
        return None

    # already structured
    if isinstance(blob, dict):
        url = str(blob.get("url", "")).strip()
        if not url:
            return None
        title = str(blob.get("title", "")).strip() or prettify_url_label(url)
        rng = str(blob.get("range", "")).strip() or default_range
        return SourceItem(title=title, url=url, range=rng)

    # plain URL
    if isinstance(blob, str) and blob.strip().lower().startswith(("http://", "https://")):
        url = blob.strip()
        return SourceItem(title=prettify_url_label(url), url=url, range=default_range)

    # HTML anchor
    if isinstance(blob, str) and "<a" in blob and "href=" in blob:
        s = blob

        href_match = re.search(r'href\s*=\s*"([^"]+)"', s, flags=re.I)
        if not href_match:
            href_match = re.search(r"href\s*=\s*'([^']+)'", s, flags=re.I)
        url = href_match.group(1).strip() if href_match else ""
        if not url:
            return None

        rr_match = re.search(r"Reported\s*Range:\s*([^<]+)", s, flags=re.I)
        rng = rr_match.group(1).strip() if rr_match else default_range

        # try to pull the “main” text if present
        main_match = re.search(r'jr-source-main"\s*>\s*([^<]+)\s*<', s, flags=re.I)
        title = main_match.group(1).strip() if main_match else prettify_url_label(url)

        return SourceItem(title=title, url=url, range=rng)

    return None


def normalize_sources(raw_sources: Any) -> List[SourceItem]:
    if not raw_sources:
        return []
    if not isinstance(raw_sources, list):
        raw_sources = [raw_sources]

    out: List[SourceItem] = []
    for item in raw_sources:
        parsed = parse_source_blob(item)
        if parsed and parsed.url:
            out.append(parsed)

    # de-dupe by url
    seen = set()
    deduped: List[SourceItem] = []
    for s in out:
        if s.url in seen:
            continue
        seen.add(s.url)
        deduped.append(s)
    return deduped[:12]


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
    payload = {"country": country}
    r = requests.post(url, json=payload, timeout=25)
    if not r.ok:
        return ["N/A"]
    data = r.json()
    states: List[str] = []
    for s in ((data.get("data") or {}).get("states") or []):
        name = s.get("name")
        if isinstance(name, str) and name.strip():
            states.append(name.strip())
    states = sorted(set(states), key=lambda x: x.lower())
    return states if states else ["N/A"]


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_cities(country: str, state: str) -> List[str]:
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
    rates = get_fx_table_usd()
    rate = rates.get(to_ccy)
    return amount if not rate else amount * rate


# ============================================================
# SerpAPI + OpenAI estimation (same wiring)
# ============================================================
def serpapi_search(job_title: str, country: str, state: str, city: str, rate_type: str) -> List[str]:
    serp_key = require_env("SERPAPI_API_KEY")

    location_bits = [b for b in [city, state, country] if b and b != "N/A"]
    loc = ", ".join(location_bits) if location_bits else country

    query = f'{job_title} salary range {loc} {"hourly rate" if rate_type=="hourly" else "annual salary"}'
    params = {"engine": "google", "q": query, "api_key": serp_key, "num": 10}

    r = requests.get("https://serpapi.com/search.json", params=params, timeout=35)
    r.raise_for_status()
    data = r.json()

    urls: List[str] = []
    for item in (data.get("organic_results") or []):
        link = item.get("link")
        if isinstance(link, str) and link.startswith("http"):
            urls.append(link)

    seen = set()
    out: List[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out[:10]


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
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

    pay_type = "HOURLY" if rate_type == "hourly" else "ANNUAL"
    location_bits = [b for b in [city, state, country] if b and b != "N/A"]
    loc = ", ".join(location_bits) if location_bits else country

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
""".strip()

    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": prompt, "temperature": 0}

    resp = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=75)
    resp.raise_for_status()
    data = resp.json()

    text_out = ""
    for o in data.get("output", []) or []:
        for c in o.get("content", []) or []:
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


def estimate_job_rate(
    job_title: str,
    job_description: str,
    country: str,
    state: str,
    city: str,
    rate_type: str,
) -> Dict[str, Any]:
    urls = serpapi_search(job_title, country, state, city, rate_type)
    return openai_estimate(job_title, job_description, country, state, city, rate_type, urls)


# ============================================================
# State init (safe keys; no widget-key collisions)
# ============================================================
def init_state():
    defaults = {
        "job_title": "",
        "job_desc": "",
        "country_val": "",
        "state_val": "N/A",
        "city_val": "N/A",
        "rate_type_val": "salary",
        "currency_val": "USD",
        "last_result": None,
        "prev_country": None,
        "prev_state": None,
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
# Form (WORKING: includes submit button; no session_state collisions)
# ============================================================
st.markdown('<div class="jr-card">', unsafe_allow_html=True)

with st.form("job_rate_form", clear_on_submit=False):
    job_title = st.text_input(
        "Job Title *",
        value=st.session_state["job_title"],
        placeholder="e.g., Senior Software Engineer",
        key="job_title_input",
    )
    st.session_state["job_title"] = job_title

    job_desc = st.text_area(
        "Job Description (optional)",
        value=st.session_state["job_desc"],
        placeholder="Paste job description here or upload a file below...",
        height=130,
        key="job_desc_input",
    )
    st.session_state["job_desc"] = job_desc

    uploaded = st.file_uploader("Upload Job Description (optional)", type=["txt"], accept_multiple_files=False, key="job_desc_file")
    if uploaded is not None:
        try:
            text = uploaded.read().decode("utf-8", errors="ignore")
            st.session_state["job_desc"] = text
            job_desc = text
        except Exception:
            pass

    try:
        countries = get_country_list()
    except Exception:
        countries = []

    if not countries:
        st.error("Could not load country list. Check your internet connection and try again.")
        countries = ["(unavailable)"]

    c1, c2, c3 = st.columns(3)

    # Country select (widget key is country_select; value stored in country_val)
    with c1:
        if countries[0] == "(unavailable)":
            st.selectbox("Country *", options=["(unavailable)"], key="country_select")
            country = ""
        else:
            if st.session_state["country_val"] not in countries:
                st.session_state["country_val"] = countries[0]
            idx = countries.index(st.session_state["country_val"]) if st.session_state["country_val"] in countries else 0
            country = st.selectbox("Country *", options=countries, index=idx, key="country_select")
        st.session_state["country_val"] = country

    # Reset dependent fields if country changed
    if st.session_state["country_val"] != st.session_state["prev_country"]:
        st.session_state["prev_country"] = st.session_state["country_val"]
        st.session_state["state_val"] = "N/A"
        st.session_state["city_val"] = "N/A"
        st.session_state["prev_state"] = None

    # States
    states = get_states_for_country(st.session_state["country_val"]) if st.session_state["country_val"] else ["N/A"]
    if "N/A" not in states:
        states = ["N/A"] + states
    if st.session_state["state_val"] not in states:
        st.session_state["state_val"] = "N/A"

    with c2:
        state = st.selectbox(
            "State/Province (optional)",
            options=states,
            index=states.index(st.session_state["state_val"]),
            key="state_select",
        )
        st.session_state["state_val"] = state

    # Reset city if state changed
    if st.session_state["state_val"] != st.session_state["prev_state"]:
        st.session_state["prev_state"] = st.session_state["state_val"]
        st.session_state["city_val"] = "N/A"

    # Cities
    cities = get_cities(st.session_state["country_val"], st.session_state["state_val"]) if st.session_state["country_val"] else ["N/A"]
    if "N/A" not in cities:
        cities = ["N/A"] + cities
    if st.session_state["city_val"] not in cities:
        st.session_state["city_val"] = "N/A"

    with c3:
        city = st.selectbox(
            "City (optional)",
            options=cities,
            index=cities.index(st.session_state["city_val"]),
            key="city_select",
        )
        st.session_state["city_val"] = city

    rate_type_label = st.radio(
        "Rate Type *",
        options=["Salary", "Hourly"],
        index=0 if st.session_state["rate_type_val"] == "salary" else 1,
        horizontal=True,
        key="rate_type_radio",
    )
    st.session_state["rate_type_val"] = "hourly" if rate_type_label == "Hourly" else "salary"

    fx_rates = get_fx_table_usd()
    currency_codes = sorted(fx_rates.keys())
    if st.session_state["currency_val"] not in currency_codes:
        st.session_state["currency_val"] = "USD"

    currency = st.selectbox(
        "Currency *",
        options=currency_codes,
        index=currency_codes.index(st.session_state["currency_val"]),
        key="currency_select",
    )
    st.session_state["currency_val"] = currency

    submitted = st.form_submit_button("Get Rates!")

st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# Run estimation
# ============================================================
def is_valid() -> Tuple[bool, str]:
    if not (st.session_state["job_title"] or "").strip():
        return False, "Job Title is required."
    if not (st.session_state["country_val"] or "").strip():
        return False, "Country is required."
    if not (st.session_state["currency_val"] or "").strip():
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
                country = st.session_state["country_val"].strip()
                state = (st.session_state["state_val"] or "N/A").strip()
                city = (st.session_state["city_val"] or "N/A").strip()
                rate_type = st.session_state["rate_type_val"]
                currency = st.session_state["currency_val"]

                state_send = "" if state == "N/A" else state
                city_send = "" if city == "N/A" else city

                result = estimate_job_rate(
                    job_title=job_title,
                    job_description=job_desc,
                    country=country,
                    state=state_send,
                    city=city_send,
                    rate_type=rate_type,
                )

                min_usd = float(result["min_usd"])
                max_usd = float(result["max_usd"])
                pay_type = result.get("pay_type", "ANNUAL")

                min_disp = min_usd
                max_disp = max_usd
                if currency.upper() != "USD":
                    min_disp = convert_from_usd(min_usd, currency)
                    max_disp = convert_from_usd(max_usd, currency)

                # Build clean sources (NO raw HTML stored)
                sources: List[SourceItem] = []

                if result.get("min_links"):
                    rng = "Min (Hourly)" if pay_type == "HOURLY" else "Min (Annual)"
                    for u in result["min_links"]:
                        sources.append(SourceItem(title=prettify_url_label(u), url=u, range=rng))

                if result.get("max_links"):
                    rng = "Max (Hourly)" if pay_type == "HOURLY" else "Max (Annual)"
                    for u in result["max_links"]:
                        sources.append(SourceItem(title=prettify_url_label(u), url=u, range=rng))

                if not sources:
                    # fallback
                    for u in (result.get("sources_used") or []):
                        sources.append(SourceItem(title=prettify_url_label(u), url=u, range="Source"))

                # de-dupe
                seen = set()
                deduped: List[Dict[str, str]] = []
                for s in sources:
                    if not s.url or s.url in seen:
                        continue
                    seen.add(s.url)
                    deduped.append({"title": s.title, "url": s.url, "range": s.range})

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
# Render results
# ============================================================
res = st.session_state.get("last_result")
if res:
    unit = "per hour" if res["rateType"] == "hourly" else "per year"
    cur = res["currency"]
    min_v = res["min"]
    max_v = res["max"]

    st.markdown(
        f"""
        <div class="jr-gradient">
          <div style="display:flex; align-items:center; gap:10px; margin-bottom: 10px;">
            <div style="width:22px;height:22px;border-radius:7px;background:rgba(255,255,255,0.18);display:grid;place-items:center;font-weight:900;">$</div>
            <div style="font-weight:900;">Estimated Rate Range</div>
          </div>

          <div class="jr-range">
            <div>
              <div class="jr-label">Minimum</div>
              <div class="jr-money">{cur}{min_v:,}</div>
              <div class="jr-unit">{unit}</div>
            </div>

            <div class="jr-sep">—</div>

            <div>
              <div class="jr-label">Maximum</div>
              <div class="jr-money">{cur}{max_v:,}</div>
              <div class="jr-unit">{unit}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="jr-sources">', unsafe_allow_html=True)
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
            title = html_escape(s.get("title", "Source"))
            url = (s.get("url", "") or "").replace('"', "%22")
            rng = html_escape(s.get("range", "Source"))
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
