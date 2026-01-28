from __future__ import annotations

import os
import re
import math
import json
import html
from typing import Any, Dict, List, Tuple, Optional

import requests
import streamlit as st


# ============================================================
# Constants
# ============================================================
MAX_CANDIDATES_FOR_AI = 15
MAX_SEARCH_RESULTS = 25
DEFAULT_STRENGTH_SCORE = 55
RELIABILITY_BOOST = 28
MAX_SOURCES_TO_DISPLAY = 8
HOURS_PER_YEAR = 2080


# ============================================================
# Page Config
# ============================================================
st.set_page_config(page_title="Job Rate Finder", page_icon="💼", layout="centered")


# ============================================================
# Styling
# ============================================================
APP_CSS = """
<style>
  :root{
    --bg0:#0b1220;--bg1:#0f1b33;--text:#e8eefc;--muted:#a9b7d6;
    --border:rgba(255,255,255,.10);--accent:#6d5efc;--accent2:#9b4dff;
    --shadow:0 18px 60px rgba(0,0,0,.45);
  }
  html,body,[data-testid="stAppViewContainer"]{
    background:radial-gradient(1200px 700px at 20% -10%,rgba(109,94,252,.30),transparent 60%),
               radial-gradient(900px 600px at 110% 10%,rgba(155,77,255,.22),transparent 55%),
               linear-gradient(180deg,var(--bg0),var(--bg1));
    color:var(--text);
  }
  .block-container{padding-top:2.1rem;padding-bottom:2.5rem;max-width:880px;}
  .jr-title{text-align:center;margin-bottom:.35rem;font-size:44px;font-weight:800;letter-spacing:-0.02em;color:var(--text);}
  .jr-subtitle{text-align:center;margin-bottom:1.5rem;color:var(--muted);font-size:15px;}
  div[data-testid="stContainer"]{
    background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.03));
    border:1px solid var(--border)!important;border-radius:16px!important;
    box-shadow:var(--shadow);backdrop-filter:blur(10px);
  }
  div[data-testid="stContainer"]>div{padding:12px 14px 14px 14px;}
  label,.stMarkdown p{color:var(--muted)!important;}
  .stTextInput input,.stTextArea textarea{
    background:rgba(0,0,0,.28)!important;border:1px solid var(--border)!important;
    color:var(--text)!important;border-radius:10px!important;
  }
  .stSelectbox [data-baseweb="select"]>div{
    background:rgba(0,0,0,.28)!important;border:1px solid var(--border)!important;
    border-radius:10px!important;color:var(--text)!important;
  }
  .stButton button{
    width:100%;border:0;border-radius:12px;padding:12px 14px;font-weight:700;color:white;
    background:linear-gradient(90deg,var(--accent),var(--accent2));
    box-shadow:0 12px 35px rgba(109,94,252,.35);
  }
  .stButton button:hover{filter:brightness(1.05);}
  .jr-range{
    background:linear-gradient(135deg,#6d5efc 0%,#9b4dff 50%,#c840e9 100%);
    border-radius:24px;padding:32px 40px;color:white;
    box-shadow:0 20px 60px rgba(109,94,252,.4);
    border:1px solid rgba(255,255,255,.2);margin-top:24px;
  }
  .jr-range-top{display:flex;gap:16px;align-items:center;margin-bottom:24px;}
  .jr-range-icon{width:44px;height:44px;border-radius:14px;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:900;}
  .jr-range-title{font-size:26px;font-weight:800;margin:0;letter-spacing:-0.02em;}
  .jr-range-grid{display:flex;align-items:flex-end;gap:40px;flex-wrap:wrap;}
  .jr-range-label{font-size:11px;color:rgba(255,255,255,.6);margin:0 0 8px 0;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;}
  .jr-range-amt{font-size:72px;font-weight:900;margin:0;line-height:1;letter-spacing:-0.03em;text-shadow:0 4px 30px rgba(0,0,0,.3);}
  .jr-range-unit{font-size:16px;color:rgba(255,255,255,.65);margin:12px 0 0 0;font-weight:600;}
  .jr-dash{font-size:48px;color:rgba(255,255,255,.35);margin:0 15px;padding-bottom:24px;font-weight:200;}
  .jr-source{
    display:flex;gap:12px;align-items:flex-start;padding:14px 16px;
    border:1px solid var(--border);border-radius:14px;background:rgba(0,0,0,.18);
    text-decoration:none!important;margin-bottom:12px;transition:all .2s ease;
  }
  .jr-source:hover{border-color:rgba(109,94,252,.6);background:rgba(109,94,252,.12);transform:translateY(-1px);}
  .jr-source-ico{
    width:24px;height:24px;border-radius:8px;background:rgba(109,94,252,.25);
    display:flex;align-items:center;justify-content:center;flex:0 0 auto;margin-top:2px;font-size:12px;color:var(--accent);
  }
  .jr-source-main{color:var(--text);font-weight:700;margin:0;font-size:14px;line-height:1.3;}
  .jr-source-sub{color:var(--muted);margin:4px 0 0 0;font-size:12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
  .jr-score-pill{
    display:inline-flex;align-items:center;gap:8px;padding:4px 8px;border-radius:999px;
    border:1px solid rgba(255,255,255,.14);background:rgba(0,0,0,.18);
    color:rgba(232,238,252,.95);font-size:11px;font-weight:700;
  }
  .jr-score-bar{width:84px;height:7px;border-radius:999px;background:rgba(255,255,255,.14);overflow:hidden;display:inline-block;}
  .jr-score-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,rgba(109,94,252,.95),rgba(155,77,255,.95));}
  .jr-geo-pill{
    display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:999px;
    border:1px solid rgba(255,255,255,.14);background:rgba(0,0,0,.18);
    color:rgba(232,238,252,.90);font-size:11px;font-weight:700;
  }
  .jr-note{
    margin-top:12px;padding:12px;border-radius:12px;
    border:1px solid rgba(255,204,102,.30);background:rgba(255,204,102,.10);
    color:rgba(255,224,170,.95);font-size:12px;
  }
  header,footer{visibility:hidden;}
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)


# ============================================================
# HTTP helpers
# ============================================================
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "JobRateFinder/1.0", "Accept": "application/json"})


def http_get(url: str, *, timeout: int = 25, params: Optional[dict] = None) -> requests.Response:
    return SESSION.get(url, timeout=timeout, params=params)


def http_post(url: str, *, timeout: int = 25, json_body: Optional[dict] = None, headers: Optional[dict] = None) -> requests.Response:
    return SESSION.post(url, timeout=timeout, json=json_body, headers=headers)


def require_secret_or_env(name: str) -> str:
    v = (os.getenv(name, "") or "").strip()
    if not v:
        try:
            v = str(st.secrets.get(name, "")).strip()
        except:
            pass
    if not v:
        raise RuntimeError(f"Missing: {name}")
    return v


# ============================================================
# Geo data
# ============================================================
COUNTRIESNOW = "https://countriesnow.space/api/v0.1"


@st.cache_data(ttl=86400, show_spinner=False)
def get_country_list() -> List[str]:
    r = http_get(f"{COUNTRIESNOW}/countries", timeout=25)
    r.raise_for_status()
    return sorted(set(c.get("country", "").strip() for c in (r.json().get("data") or []) if c.get("country")), key=str.lower)


@st.cache_data(ttl=86400, show_spinner=False)
def get_states_for_country(country: str) -> List[str]:
    if not country:
        return []
    try:
        r = http_post(f"{COUNTRIESNOW}/countries/states", json_body={"country": country}, timeout=25)
        if not r.ok:
            return []
        return sorted(set(s.get("name", "").strip() for s in ((r.json().get("data") or {}).get("states") or []) if s.get("name")), key=str.lower)
    except:
        return []


@st.cache_data(ttl=86400, show_spinner=False)
def get_cities(country: str, state: str) -> List[str]:
    if not country:
        return []
    try:
        if state:
            r = http_post(f"{COUNTRIESNOW}/countries/state/cities", json_body={"country": country, "state": state}, timeout=25)
        else:
            r = http_post(f"{COUNTRIESNOW}/countries/cities", json_body={"country": country}, timeout=25)
        if not r.ok:
            return []
        cities = r.json().get("data") or []
        return sorted(set(c.strip() for c in cities if isinstance(c, str) and c.strip()), key=str.lower)
    except:
        return []


# ============================================================
# Country metadata
# ============================================================
COUNTRY_META = {
    "Brazil": {"currency": "BRL", "fx": 5.0, "period": "monthly", "months": 13},
    "United States": {"currency": "USD", "fx": 1.0, "period": "annual", "months": 12},
    "United Kingdom": {"currency": "GBP", "fx": 0.79, "period": "annual", "months": 12},
    "Germany": {"currency": "EUR", "fx": 0.92, "period": "annual", "months": 12},
    "Canada": {"currency": "CAD", "fx": 1.36, "period": "annual", "months": 12},
    "Australia": {"currency": "AUD", "fx": 1.53, "period": "annual", "months": 12},
    "India": {"currency": "INR", "fx": 83.0, "period": "annual", "months": 12},
    "Mexico": {"currency": "MXN", "fx": 17.0, "period": "monthly", "months": 12},
    "France": {"currency": "EUR", "fx": 0.92, "period": "annual", "months": 12},
    "Spain": {"currency": "EUR", "fx": 0.92, "period": "annual", "months": 14},
    "Japan": {"currency": "JPY", "fx": 150.0, "period": "monthly", "months": 12},
    "Philippines": {"currency": "PHP", "fx": 56.0, "period": "monthly", "months": 13},
}


def get_meta(country: str) -> Dict[str, Any]:
    return COUNTRY_META.get(country, {"currency": "USD", "fx": 1.0, "period": "annual", "months": 12})


# ============================================================
# FX
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_fx_rates() -> Dict[str, float]:
    try:
        r = http_get("https://open.er-api.com/v6/latest/USD", timeout=25)
        r.raise_for_status()
        rates = r.json().get("rates") or {}
        return {k.upper(): float(v) for k, v in rates.items() if isinstance(v, (int, float)) and v > 0}
    except:
        return {"USD": 1.0}


def to_display_currency(usd: float, currency: str) -> float:
    if currency == "USD":
        return usd
    rates = get_fx_rates()
    return usd * rates.get(currency, 1.0)


# ============================================================
# URL helpers
# ============================================================
def host_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return (urlparse(url).hostname or "").replace("www.", "").lower()
    except:
        return ""


def pretty_label(url: str) -> str:
    try:
        from urllib.parse import urlparse, unquote
        u = urlparse(url)
        host = (u.hostname or "").replace("www.", "")
        path = [p for p in (u.path or "").split("/") if p]
        slug = unquote(path[-1]) if path else ""
        slug = re.sub(r"\.(html?|php|aspx?)$", "", slug, flags=re.I)
        slug = re.sub(r"[-_]+", " ", slug).strip()[:50]
        return f"{host} — {slug}" if slug and len(slug) > 5 else host
    except:
        return "Source"


# ============================================================
# Parsing
# ============================================================
def parse_num(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)) and math.isfinite(x):
        return float(x)
    if not isinstance(x, str):
        return None
    s = re.sub(r"[^\d.\-kmKM]", "", x.replace(",", ""))
    m = re.search(r"([\d.]+)\s*([kKmM])?", s)
    if not m:
        return None
    n = float(m.group(1))
    if m.group(2) and m.group(2).lower() == "k":
        n *= 1000
    elif m.group(2) and m.group(2).lower() == "m":
        n *= 1000000
    return n if math.isfinite(n) else None


# ============================================================
# Experience
# ============================================================
def normalize_exp(exp: str) -> str:
    e = (exp or "").lower()
    if any(x in e for x in ["entry", "junior", "jr", "0-2", "1-2", "grad", "intern"]):
        return "entry-level"
    if any(x in e for x in ["senior", "sr", "5+", "lead", "6+", "7+"]):
        return "senior"
    if any(x in e for x in ["principal", "staff", "director", "10+", "architect"]):
        return "principal"
    return "mid-level"


# ============================================================
# Reliability
# ============================================================
GOOD_HOSTS = ["salaryexpert", "levels.fyi", "glassdoor", "indeed", "salary.com", "payscale", "linkedin", "ziprecruiter", "builtin"]
BAD_HOSTS = ["pinterest", "facebook", "instagram", "tiktok", "youtube", "reddit", "quora", "wikipedia", "github"]


def is_blocked(url: str) -> bool:
    h = host_of(url)
    return any(b in h for b in BAD_HOSTS)


def source_score(url: str) -> int:
    h = host_of(url)
    return 75 if any(g in h for g in GOOD_HOSTS) else 50


# ============================================================
# Geo tag
# ============================================================
def geo_tag(url: str, title: str, snippet: str, country: str, state: str, city: str) -> str:
    blob = f"{title} {snippet} {url}".lower()
    if country.lower() not in blob:
        return "Nearby"
    if city and city.lower() in blob:
        return "Exact"
    if state and state.lower() in blob:
        return "Exact"
    return "Country"


# ============================================================
# Search
# ============================================================
def search_salaries(job: str, country: str, state: str, city: str, rate_type: str, exp: str) -> List[Dict[str, Any]]:
    key = require_secret_or_env("SERPAPI_API_KEY")
    meta = get_meta(country)
    
    rate_word = "hourly rate" if rate_type == "hourly" else "salary"
    exp_word = normalize_exp(exp)
    
    queries = [
        f'{job} {exp_word} {rate_word} {country}',
        f'{job} {rate_word} {country} {state}' if state else f'{job} average {rate_word} {country}',
        f'site:glassdoor.com {job} salary {country}',
    ]
    
    results = []
    seen_urls = set()
    
    for q in queries:
        try:
            r = http_get("https://serpapi.com/search.json", params={"engine": "google", "q": q, "api_key": key, "num": 10}, timeout=30)
            r.raise_for_status()
            for item in (r.json().get("organic_results") or []):
                url = (item.get("link") or "").strip()
                if not url or not url.startswith("http") or is_blocked(url) or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append({
                    "url": url,
                    "title": (item.get("title") or "")[:150],
                    "snippet": (item.get("snippet") or "")[:300],
                    "host": host_of(url),
                    "geo": geo_tag(url, item.get("title", ""), item.get("snippet", ""), country, state, city),
                    "score": source_score(url),
                })
        except:
            continue
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:MAX_SEARCH_RESULTS]


# ============================================================
# AI Estimation - THE KEY FUNCTION
# ============================================================
def estimate_salary(job: str, country: str, state: str, city: str, rate_type: str, exp: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    key = require_secret_or_env("OPENAI_API_KEY")
    meta = get_meta(country)
    
    location = ", ".join(x for x in [city, state, country] if x)
    exp_level = normalize_exp(exp)
    
    # Build source text
    source_text = ""
    for i, s in enumerate(sources[:MAX_CANDIDATES_FOR_AI], 1):
        source_text += f"\n[SOURCE {i}]\nTitle: {s['title']}\nContent: {s['snippet']}\n"
    
    # Always ask for ANNUAL salary - we'll convert to hourly ourselves if needed
    prompt = f"""Extract salary data for "{job}" in {location}.

READ EACH SOURCE BELOW AND:
1. Find any numbers that look like salaries
2. Determine the TIME PERIOD by looking for keywords:
   - HOURLY: "per hour", "/hr", "/hour", "hourly", "an hour", "por hora"
   - MONTHLY: "per month", "/month", "monthly", "a month", "por mes", "mensal", "/mo"
   - YEARLY/ANNUAL: "per year", "/year", "annual", "yearly", "a year", "por ano", "anual", "/yr", "p.a."
   - If no period keyword found, assume {meta['period'].upper()} (default for {country})

3. Convert ALL found values to ANNUAL USD:
   - If HOURLY: multiply by 2080 to get annual
   - If MONTHLY: multiply by 12 to get annual (or 13 for Brazil)
   - If already ANNUAL: use as-is
   - Convert {meta['currency']} to USD: divide by {meta['fx']}

SOURCES:
{source_text}

IMPORTANT: Look at the ACTUAL numbers in the sources. Common patterns:
- "R$ 2.500" or "R$2500" = 2,500 BRL
- "$50/hour" = 50 USD hourly
- "45k-65k" = 45,000-65,000
- "3.000 - 5.000" = 3,000-5,000

For experience level "{exp_level}":
- entry-level: use lower numbers from ranges
- mid-level: use middle of ranges
- senior: use higher numbers from ranges

Return ONLY this JSON:
{{"min_usd": <ANNUAL USD number>, "max_usd": <ANNUAL USD number>, "period_found": "<hourly/monthly/annual>", "original_values": "<what you found>"}}"""

    resp = http_post(
        "https://api.openai.com/v1/chat/completions",
        json_body={
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 400
        },
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=60
    )
    resp.raise_for_status()
    
    text = (resp.json().get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
    
    # Clean markdown
    text = re.sub(r'^```json?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    
    min_annual, max_annual = None, None
    try:
        data = json.loads(text)
        min_annual = parse_num(data.get("min_usd"))
        max_annual = parse_num(data.get("max_usd"))
    except:
        nums = [parse_num(n) for n in re.findall(r'[\d,]+(?:\.\d+)?', text)]
        nums = sorted([n for n in nums if n and n > 50])
        if len(nums) >= 2:
            min_annual, max_annual = nums[0], nums[-1]
    
    if not min_annual or not max_annual or min_annual <= 0 or max_annual <= 0:
        raise RuntimeError(f"Could not extract salary: {text[:200]}")
    
    if min_annual > max_annual:
        min_annual, max_annual = max_annual, min_annual
    
    # Now convert to requested rate type
    if rate_type == "hourly":
        # Always calculate hourly from annual (annual / 2080 hours)
        min_result = round(min_annual / HOURS_PER_YEAR, 2)
        max_result = round(max_annual / HOURS_PER_YEAR, 2)
        # Ensure we don't return 0
        if min_result < 1:
            min_result = round(min_annual / HOURS_PER_YEAR, 2)
        if max_result < 1:
            max_result = round(max_annual / HOURS_PER_YEAR, 2)
    else:
        min_result = int(round(min_annual))
        max_result = int(round(max_annual))
    
    # Build source list - no duplicates
    final_sources = []
    seen = set()
    for s in sources:
        if len(final_sources) >= MAX_SOURCES_TO_DISPLAY:
            break
        if s["url"] not in seen:
            seen.add(s["url"])
            final_sources.append(s)
    
    return {
        "min_usd": min_result,
        "max_usd": max_result,
        "pay_type": rate_type,
        "sources": final_sources,
    }


# ============================================================
# UI State
# ============================================================
if "job_title" not in st.session_state:
    st.session_state.update({
        "job_title": "", "experience_level": "", "job_desc": "",
        "country": "", "state": "", "city": "",
        "rate_type": "salary", "currency": "USD",
        "last_result": None, "error": None
    })


def on_country_change():
    st.session_state["state"] = ""
    st.session_state["city"] = ""
    st.session_state["currency"] = get_meta(st.session_state["country"]).get("currency", "USD")


def on_state_change():
    st.session_state["city"] = ""


# ============================================================
# UI
# ============================================================
st.markdown('<div class="jr-title">Job Rate Finder</div>', unsafe_allow_html=True)
st.markdown('<div class="jr-subtitle">Get competitive salary and hourly rate information for any position</div>', unsafe_allow_html=True)

with st.container(border=True):
    st.text_input("Job Title *", key="job_title", placeholder="e.g., Video Editor, Software Engineer")
    st.text_input("Experience Level", key="experience_level", placeholder="e.g., Senior, 5+ years, Entry-level")
    
    st.text_area("Job Description (optional)", key="job_desc", placeholder="Paste job description to help find more accurate salary data...", height=120)
    
    uploaded = st.file_uploader("Upload Job Description (optional)", type=["txt", "pdf"], accept_multiple_files=False)
    if uploaded is not None:
        file_key = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.get("_uploaded_key") != file_key:
            try:
                text = uploaded.read().decode("utf-8", errors="ignore")
                st.session_state["job_desc"] = text
                st.session_state["_uploaded_key"] = file_key
            except:
                pass
    
    try:
        countries = get_country_list()
    except:
        countries = []
    
    st.selectbox("Country *", [""] + countries, key="country", on_change=on_country_change, format_func=lambda x: "— Select —" if not x else x)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        states = get_states_for_country(st.session_state["country"]) if st.session_state["country"] else []
        if st.session_state["state"] not in [""] + states:
            st.session_state["state"] = ""
        st.selectbox("State/Province", [""] + states, key="state", on_change=on_state_change, format_func=lambda x: "— Any —" if not x else x)
    
    with col2:
        cities = get_cities(st.session_state["country"], st.session_state["state"]) if st.session_state["country"] else []
        if st.session_state["city"] not in [""] + cities:
            st.session_state["city"] = ""
        st.selectbox("City", [""] + cities, key="city", format_func=lambda x: "— Any —" if not x else x)
    
    with col3:
        rate = st.radio("Rate Type", ["Annual Salary", "Hourly Rate"], horizontal=True)
        st.session_state["rate_type"] = "hourly" if "Hourly" in rate else "salary"
    
    fx = get_fx_rates()
    currencies = sorted(fx.keys()) if fx else ["USD"]
    if st.session_state["currency"] not in currencies:
        st.session_state["currency"] = "USD"
    st.selectbox("Display Currency", currencies, key="currency", index=currencies.index(st.session_state["currency"]) if st.session_state["currency"] in currencies else 0)
    
    can_go = st.session_state["job_title"].strip() and st.session_state["country"]
    go = st.button("Get Rates!", disabled=not can_go)


# ============================================================
# Process
# ============================================================
if go:
    st.session_state["error"] = None
    st.session_state["last_result"] = None
    
    with st.spinner("Searching for salary data..."):
        try:
            sources = search_salaries(
                st.session_state["job_title"],
                st.session_state["country"],
                st.session_state["state"],
                st.session_state["city"],
                st.session_state["rate_type"],
                st.session_state["experience_level"]
            )
            
            if not sources:
                st.warning("No sources found. Try a different job title.")
            else:
                with st.spinner("Analyzing salary data..."):
                    result = estimate_salary(
                        st.session_state["job_title"],
                        st.session_state["country"],
                        st.session_state["state"],
                        st.session_state["city"],
                        st.session_state["rate_type"],
                        st.session_state["experience_level"],
                        sources
                    )
                
                # Convert to display currency
                curr = st.session_state["currency"]
                min_disp = to_display_currency(result["min_usd"], curr)
                max_disp = to_display_currency(result["max_usd"], curr)
                
                st.session_state["last_result"] = {
                    "min": int(round(min_disp)),
                    "max": int(round(max_disp)),
                    "currency": curr,
                    "rate_type": result["pay_type"],
                    "sources": result["sources"],
                }
                
        except Exception as e:
            st.session_state["error"] = str(e)
            st.error(f"Error: {str(e)[:200]}")


# ============================================================
# Results
# ============================================================
res = st.session_state.get("last_result")
if res:
    unit = "per hour" if res["rate_type"] == "hourly" else "per year"
    
    st.markdown(f"""
    <div class="jr-range">
      <div class="jr-range-top">
        <div class="jr-range-icon">$</div>
        <div class="jr-range-title">Estimated Rate Range</div>
      </div>
      <div class="jr-range-grid">
        <div>
          <p class="jr-range-label">Minimum</p>
          <p class="jr-range-amt">{res["currency"]} {res["min"]:,}</p>
          <p class="jr-range-unit">{unit}</p>
        </div>
        <div class="jr-dash">-</div>
        <div>
          <p class="jr-range-label">Maximum</p>
          <p class="jr-range-amt">{res["currency"]} {res["max"]:,}</p>
          <p class="jr-range-unit">{unit}</p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    if res.get("sources"):
        with st.container(border=True):
            st.markdown("#### Sources")
            for s in res["sources"]:
                title = html.escape(pretty_label(s["url"]))
                url = html.escape(s["url"], quote=True)
                score = s.get("score", 50)
                geo = s.get("geo", "Nearby")
                
                st.markdown(f"""
                <a class="jr-source" href="{url}" target="_blank">
                  <div class="jr-source-ico">+</div>
                  <div style="min-width:0;width:100%;">
                    <div class="jr-source-main">{title}</div>
                    <div class="jr-source-sub">
                      <span class="jr-geo-pill">{geo}</span>
                      <span class="jr-score-pill">
                        Strength {score}/100
                        <span class="jr-score-bar"><span class="jr-score-fill" style="width:{score}%;"></span></span>
                      </span>
                    </div>
                  </div>
                </a>
                """, unsafe_allow_html=True)

if st.session_state.get("error"):
    with st.expander("Debug"):
        st.code(st.session_state["error"])
