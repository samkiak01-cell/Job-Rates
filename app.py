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
MAX_CANDIDATES_FOR_AI = 18
MAX_SEARCH_RESULTS = 30
MAX_SKILLS_TO_EXTRACT = 12
DEFAULT_STRENGTH_SCORE = 55
RELIABILITY_BOOST = 28
MAX_SOURCES_TO_DISPLAY = 12
HOURS_PER_YEAR = 2080


# ============================================================
# Page / Layout
# ============================================================
st.set_page_config(page_title="Job Rate Finder", page_icon="💼", layout="centered")


# ============================================================
# Styling
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
    text-align:center; margin-bottom: .35rem; font-size: 44px; font-weight: 800;
    letter-spacing: -0.02em; color: var(--text);
  }
  .jr-subtitle{ text-align:center; margin-bottom: 1.5rem; color: var(--muted); font-size: 15px; }

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

  .jr-range{
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 16px; padding: 18px; color: white;
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

  .jr-source{
    display:flex; gap: 12px; align-items:flex-start;
    padding: 12px 12px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: rgba(0,0,0,.14);
    text-decoration: none !important;
    margin-bottom: 10px;
  }
  .jr-source:hover{ border-color: rgba(109,94,252,.55); background: rgba(109,94,252,.08); }
  .jr-source-ico{
    width: 22px; height: 22px; border-radius: 8px;
    background: rgba(109,94,252,.22);
    display:flex; align-items:center; justify-content:center;
    flex: 0 0 auto; margin-top: 1px;
  }
  .jr-source-main{ color: var(--text); font-weight: 700; margin: 0; font-size: 13px; line-height: 1.2; }
  .jr-source-sub{
    color: var(--muted);
    margin: 3px 0 0 0;
    font-size: 12px;
    display:flex; align-items:center; gap:10px; flex-wrap:wrap;
  }

  .jr-score-pill{
    display:inline-flex; align-items:center; gap:8px;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,.14);
    background: rgba(0,0,0,.18);
    color: rgba(232,238,252,.95);
    font-size: 11px; font-weight: 700;
  }
  .jr-score-bar{
    width: 84px; height: 7px; border-radius: 999px;
    background: rgba(255,255,255,.14);
    overflow:hidden;
    display:inline-block;
  }
  .jr-score-fill{
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(109,94,252,.95), rgba(155,77,255,.95));
  }

  .jr-geo-pill{
    display:inline-flex; align-items:center; gap:6px;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,.14);
    background: rgba(0,0,0,.18);
    color: rgba(232,238,252,.90);
    font-size: 11px; font-weight: 700;
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
SESSION.headers.update({
    "User-Agent": "JobRateFinder/1.0 (+streamlit)",
    "Accept": "application/json,text/plain,*/*",
})


def http_get(url: str, *, timeout: int = 25, params: Optional[dict] = None) -> requests.Response:
    return SESSION.get(url, timeout=timeout, params=params)


def http_post(url: str, *, timeout: int = 25, json_body: Optional[dict] = None, headers: Optional[dict] = None) -> requests.Response:
    return SESSION.post(url, timeout=timeout, json=json_body, headers=headers)


def require_secret_or_env(name: str) -> str:
    v = (os.getenv(name, "") or "").strip()
    if not v:
        try:
            v = str(st.secrets.get(name, "")).strip()
        except Exception:
            v = ""
    if not v:
        raise RuntimeError(f"Missing API key: {name}")
    return v


# ============================================================
# Geo dropdowns
# ============================================================
COUNTRIESNOW_BASE = "https://countriesnow.space/api/v0.1"


@st.cache_data(ttl=86400, show_spinner=False)
def get_country_list() -> List[str]:
    r = http_get(f"{COUNTRIESNOW_BASE}/countries", timeout=25)
    r.raise_for_status()
    data = r.json()
    countries = [item.get("country") for item in (data.get("data") or []) if isinstance(item.get("country"), str)]
    return sorted(set(c.strip() for c in countries if c.strip()), key=str.lower)


@st.cache_data(ttl=86400, show_spinner=False)
def get_states_for_country(country: str) -> List[str]:
    if not country:
        return []
    try:
        r = http_post(f"{COUNTRIESNOW_BASE}/countries/states", json_body={"country": country}, timeout=25)
        if not r.ok:
            return []
        data = r.json()
        states = [s.get("name") for s in ((data.get("data") or {}).get("states") or []) if isinstance(s.get("name"), str)]
        return sorted(set(s.strip() for s in states if s.strip()), key=str.lower)
    except Exception:
        return []


@st.cache_data(ttl=86400, show_spinner=False)
def get_cities(country: str, state: str) -> List[str]:
    if not country:
        return []
    try:
        if state:
            r = http_post(f"{COUNTRIESNOW_BASE}/countries/state/cities", json_body={"country": country, "state": state}, timeout=25)
        else:
            r = http_post(f"{COUNTRIESNOW_BASE}/countries/cities", json_body={"country": country}, timeout=25)
        if not r.ok:
            return []
        data = r.json()
        cities = data.get("data") or []
        return sorted(set(c.strip() for c in cities if isinstance(c, str) and c.strip()), key=str.lower)
    except Exception:
        return []


# ============================================================
# Country metadata
# ============================================================
COUNTRY_METADATA = {
    "Brazil": {"aliases": ["Brazil", "Brasil", "BR"], "currency": "BRL", "salary_period": "monthly", "months": 13, "salary_sites": ["glassdoor.com.br", "vagas.com.br"]},
    "United States": {"aliases": ["United States", "USA", "US"], "currency": "USD", "salary_period": "annual", "months": 12, "salary_sites": []},
    "United Kingdom": {"aliases": ["United Kingdom", "UK"], "currency": "GBP", "salary_period": "annual", "months": 12, "salary_sites": []},
    "Germany": {"aliases": ["Germany", "Deutschland"], "currency": "EUR", "salary_period": "annual", "months": 12, "salary_sites": ["stepstone.de"]},
    "Canada": {"aliases": ["Canada", "CA"], "currency": "CAD", "salary_period": "annual", "months": 12, "salary_sites": []},
    "Australia": {"aliases": ["Australia", "AU"], "currency": "AUD", "salary_period": "annual", "months": 12, "salary_sites": ["seek.com.au"]},
    "India": {"aliases": ["India", "IN"], "currency": "INR", "salary_period": "annual", "months": 12, "salary_sites": ["naukri.com"]},
    "Mexico": {"aliases": ["Mexico", "México"], "currency": "MXN", "salary_period": "monthly", "months": 12, "salary_sites": []},
    "France": {"aliases": ["France", "FR"], "currency": "EUR", "salary_period": "annual", "months": 12, "salary_sites": []},
    "Spain": {"aliases": ["Spain", "España"], "currency": "EUR", "salary_period": "annual", "months": 14, "salary_sites": []},
    "Japan": {"aliases": ["Japan", "JP"], "currency": "JPY", "salary_period": "monthly", "months": 12, "salary_sites": []},
    "Philippines": {"aliases": ["Philippines", "PH"], "currency": "PHP", "salary_period": "monthly", "months": 13, "salary_sites": []},
}


def get_country_metadata(country: str) -> Dict[str, Any]:
    for key, meta in COUNTRY_METADATA.items():
        if country in meta["aliases"] or country == key:
            return {**meta, "name": key}
    return {"aliases": [country], "currency": "USD", "salary_period": "annual", "months": 12, "salary_sites": [], "name": country}


# ============================================================
# FX conversion
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_fx_table_usd() -> Dict[str, float]:
    r = http_get("https://open.er-api.com/v6/latest/USD", timeout=25)
    r.raise_for_status()
    rates = r.json().get("rates") or {}
    out = {k.upper(): float(v) for k, v in rates.items() if isinstance(v, (int, float)) and v > 0}
    out["USD"] = 1.0
    return out


def convert_from_usd(amount: float, to_ccy: str) -> float:
    rate = get_fx_table_usd().get((to_ccy or "USD").upper(), 1.0)
    return amount * rate


# ============================================================
# URL helpers
# ============================================================
def pretty_url_label(raw_url: str) -> Tuple[str, str]:
    try:
        from urllib.parse import urlparse, unquote
        u = urlparse(raw_url)
        host = (u.hostname or "").replace("www.", "") or "Source"
        parts = [p for p in (u.path or "").split("/") if p]
        last = unquote(parts[-1]) if parts else ""
        cleaned = re.sub(r"\.(html|htm|php|aspx)$", "", last, flags=re.I)
        cleaned = re.sub(r"[-_]+", " ", cleaned).strip()
        return (host, cleaned[:70] if len(cleaned) >= 6 else "salary page")
    except Exception:
        return ("Source", "salary page")


def host_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return (urlparse(url).hostname or "").replace("www.", "").lower()
    except Exception:
        return ""


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s-]", " ", (s or "").lower())).strip()


# ============================================================
# Parsing helpers
# ============================================================
def parse_number_like(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)) and math.isfinite(float(x)):
        return float(x)
    if not isinstance(x, str):
        return None
    s = re.sub(r"[\$€£¥₹R\$,]", "", x.strip().lower())
    m = re.search(r"(-?\d+\.?\d*)\s*([kKmM])?", s)
    if not m:
        return None
    num = float(m.group(1))
    suf = (m.group(2) or "").lower()
    if suf == "k":
        num *= 1000
    elif suf == "m":
        num *= 1000000
    return num if math.isfinite(num) else None


def clean_urls(x: Any) -> List[str]:
    if not isinstance(x, list):
        return []
    return [u.strip() for u in x if isinstance(u, str) and u.startswith("http")]


# ============================================================
# Experience helpers
# ============================================================
EXPERIENCE_LEVELS = {
    "entry": ["entry", "junior", "jr", "graduate", "fresher", "0-2", "1-2", "trainee", "intern"],
    "mid": ["mid", "intermediate", "2-5", "3-5", "associate"],
    "senior": ["senior", "sr", "5+", "5-7", "5-10", "lead", "experienced"],
    "principal": ["principal", "staff", "architect", "10+", "director", "vp", "chief", "head"]
}


def normalize_experience_level(exp: str) -> Tuple[str, str]:
    exp_lower = (exp or "").strip().lower()
    if not exp_lower:
        return ("mid", "Mid-level (default)")
    for level, keywords in EXPERIENCE_LEVELS.items():
        if any(kw in exp_lower for kw in keywords):
            return (level, {"entry": "Entry-level", "mid": "Mid-level", "senior": "Senior", "principal": "Principal"}[level])
    years_match = re.search(r'(\d+)', exp_lower)
    if years_match:
        years = int(years_match.group(1))
        if years <= 2: return ("entry", "Entry-level")
        elif years <= 5: return ("mid", "Mid-level")
        elif years <= 10: return ("senior", "Senior")
        else: return ("principal", "Principal")
    return ("mid", "Mid-level")


def extract_experience_from_job_desc(job_desc: str) -> Optional[str]:
    desc = (job_desc or "").lower()
    match = re.search(r'(\d+)\s*\+?\s*years?\s+(?:of\s+)?experience', desc)
    if match:
        return f"{match.group(1)}+ years"
    for kw in ["senior", "junior", "entry", "lead", "principal"]:
        if kw in desc:
            return kw.capitalize()
    return None


def extract_key_requirements(job_desc: str) -> List[str]:
    SKILLS = ("python", "java", "javascript", "react", "aws", "sql", "docker", "kubernetes", "node", "typescript", "angular", "vue")
    desc = (job_desc or "").lower()
    return [s for s in SKILLS if s in desc][:8]


# ============================================================
# Reliability
# ============================================================
RELIABLE_HOSTS = ["salaryexpert.com", "levels.fyi", "glassdoor", "indeed.com", "salary.com", "payscale.com", "linkedin.com", "ziprecruiter.com", "builtin.com"]
BLOCKED_HOSTS = ["pinterest", "facebook", "instagram", "tiktok", "youtube", "reddit", "quora", "wikipedia", "github"]


def is_blocked_source(url: str) -> bool:
    h = host_of(url)
    return any(b in h for b in BLOCKED_HOSTS)


def reliability_boost(url: str) -> int:
    h = host_of(url)
    return RELIABILITY_BOOST if any(r in h for r in RELIABLE_HOSTS) else 0


def geo_priority(tag: str) -> int:
    return {"Exact": 3, "Country-level": 2}.get(tag, 1)


# ============================================================
# Geo tagging
# ============================================================
def geo_tag_from_serp(url: str, title: str, snippet: str, country: str, state: str, city: str) -> str:
    meta = get_country_metadata(country)
    blob = f"{title} {snippet} {url}".lower()
    country_ok = any(a.lower() in blob for a in meta["aliases"])
    if not country_ok:
        return "Nearby/Unclear"
    if not state and not city:
        return "Country-level"
    if city and city.lower() in blob:
        return "Exact"
    if state and state.lower() in blob:
        return "Exact"
    return "Country-level"


# ============================================================
# Rate type helpers
# ============================================================
def rate_type_to_pay_type(rate_type: str) -> str:
    return "HOURLY" if (rate_type or "").lower() == "hourly" else "ANNUAL"


def pay_type_to_rate_type(pay_type: str) -> str:
    return "hourly" if (pay_type or "").upper() == "HOURLY" else "salary"


# ============================================================
# Search
# ============================================================
def serpapi_search(job_title: str, country: str, state: str, city: str, rate_type: str, job_desc: str = "", experience_level: str = "") -> List[Dict[str, Any]]:
    serp_key = require_secret_or_env("SERPAPI_API_KEY")
    pay_type = rate_type_to_pay_type(rate_type)
    meta = get_country_metadata(country)
    
    effective_exp = experience_level.strip() or extract_experience_from_job_desc(job_desc) or ""
    
    queries = [
        f'{job_title} {effective_exp} {country} {"hourly rate" if pay_type == "HOURLY" else "salary"}',
        f'{job_title} salary range "{country}"',
        f'site:salaryexpert.com "{job_title}" "{country}"',
    ]
    if meta.get("salary_sites"):
        queries.append(f'site:{meta["salary_sites"][0]} "{job_title}"')

    all_items = []
    for q in queries:
        try:
            params = {"engine": "google", "q": q, "api_key": serp_key, "num": 15}
            r = http_get("https://serpapi.com/search.json", params=params, timeout=35)
            r.raise_for_status()
            for item in (r.json().get("organic_results") or []):
                link = item.get("link", "")
                if not link.startswith("http") or is_blocked_source(link):
                    continue
                all_items.append({
                    "url": link.strip(),
                    "title": (item.get("title") or "")[:200],
                    "snippet": (item.get("snippet") or "")[:500],
                    "host": host_of(link),
                    "geo_tag": geo_tag_from_serp(link, item.get("title", ""), item.get("snippet", ""), country, state, city),
                    "rel_boost": reliability_boost(link),
                })
        except Exception:
            continue

    # Dedupe
    best = {}
    for it in all_items:
        u = it["url"]
        score = geo_priority(it["geo_tag"]) * 100 + it["rel_boost"]
        if u not in best or score > best[u].get("_score", 0):
            best[u] = {**it, "_score": score}
    
    return sorted(best.values(), key=lambda x: x.get("_score", 0), reverse=True)[:MAX_SEARCH_RESULTS]


# ============================================================
# AI Estimation
# ============================================================
def openai_estimate(job_title: str, job_desc: str, experience_level: str, country: str, state: str, city: str, rate_type: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    openai_key = require_secret_or_env("OPENAI_API_KEY")
    pay_type = rate_type_to_pay_type(rate_type)
    meta = get_country_metadata(country)
    
    location = ", ".join([x for x in [city, state, country] if x]) or country
    effective_exp = experience_level.strip() or extract_experience_from_job_desc(job_desc) or ""
    exp_norm, exp_desc = normalize_experience_level(effective_exp)
    
    # Build source list
    source_lines = []
    for c in candidates[:MAX_CANDIDATES_FOR_AI]:
        source_lines.append(f'URL: {c["url"]}\nTitle: {c.get("title","")}\nSnippet: {c.get("snippet","")}')
    sources_text = "\n\n".join(source_lines) if source_lines else "(no sources)"

    # Country-specific guidance
    if country == "Brazil":
        period_note = """BRAZIL: Salaries are typically MONTHLY. 
- If you see "R$ 5.000" or "R$ 8.000 - R$ 15.000", these are MONTHLY values
- Convert: Monthly × 13 = Annual BRL, then ÷ 5.0 = USD
- Example: R$ 10,000/month × 13 = R$ 130,000/year ÷ 5 = $26,000 USD/year
- Mid-level Software Engineer in Brazil: typically $20,000-$50,000 USD/year"""
    elif country == "India":
        period_note = """INDIA: Salaries use "LPA" (Lakhs Per Annum) = annual
- 1 Lakh = 100,000 INR. "10 LPA" = 1,000,000 INR/year
- Convert: INR ÷ 83 = USD
- Example: 15 LPA = 1,500,000 INR ÷ 83 = $18,072 USD/year"""
    elif country == "Mexico":
        period_note = """MEXICO: Salaries often MONTHLY
- Convert: Monthly × 12 = Annual MXN, then ÷ 17 = USD"""
    else:
        period_note = f"Salaries in {country} are typically annual. Convert to USD."

    output_type = "HOURLY RATE" if pay_type == "HOURLY" else "ANNUAL SALARY"
    
    prompt = f"""Extract salary data for: {job_title}
Location: {location}
Experience: {exp_norm.upper()} ({exp_desc})
Output needed: {output_type} in USD

{period_note}

CURRENCY RATES: BRL÷5, EUR×1.08, GBP×1.26, INR÷83, MXN÷17, JPY÷150, CAD×0.74, AUD×0.65

SOURCES:
{sources_text}

Return JSON only (no markdown):
{{"min_usd": <number>, "max_usd": <number>, "pay_type": "{pay_type}"}}

CRITICAL VALIDATION:
- {output_type} for {exp_norm} {job_title} in {country}
- {"Hourly: typically $5-$200/hr" if pay_type == "HOURLY" else "Annual: typically $15,000-$300,000/year"}
- Brazil mid-level engineer: {"$15-35/hr" if pay_type == "HOURLY" else "$20,000-$50,000/year"}
- US mid-level engineer: {"$40-80/hr" if pay_type == "HOURLY" else "$80,000-$150,000/year"}
- If values seem wrong, you probably have monthly data - multiply by 12-13!"""

    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 500
    }
    
    resp = http_post("https://api.openai.com/v1/chat/completions", json_body=payload, timeout=60, headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"})
    resp.raise_for_status()
    
    text_out = (resp.json().get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
    
    # Clean markdown
    text_out = re.sub(r'^```(?:json)?\s*', '', text_out)
    text_out = re.sub(r'\s*```$', '', text_out)
    
    try:
        parsed = json.loads(text_out)
    except:
        m = re.search(r'\{[^}]+\}', text_out)
        if not m:
            raise RuntimeError(f"Invalid JSON: {text_out[:200]}")
        parsed = json.loads(m.group(0))
    
    min_usd = parse_number_like(parsed.get("min_usd")) or 0
    max_usd = parse_number_like(parsed.get("max_usd")) or 0
    
    if min_usd <= 0 or max_usd <= 0:
        raise RuntimeError(f"Invalid values: {min_usd}, {max_usd}")
    
    # AGGRESSIVE SANITY CHECK FOR ANNUAL SALARIES
    if pay_type == "ANNUAL":
        # Professional roles should pay at least $10,000/year even in low-cost countries
        # If max is under $3000, it's almost certainly monthly - multiply by 13 (Brazil) or 12
        if max_usd < 3000:
            # Very low - definitely monthly values
            min_usd *= 13
            max_usd *= 13
        elif max_usd < 10000:
            # Still suspiciously low - probably monthly
            min_usd *= 12
            max_usd *= 12
    
    # SANITY CHECK FOR HOURLY RATES
    elif pay_type == "HOURLY":
        # Hourly rates should be $1-$500/hour typically
        if min_usd > 500:
            # These look like annual salaries, convert to hourly
            min_usd /= HOURS_PER_YEAR
            max_usd /= HOURS_PER_YEAR
        elif max_usd < 1:
            # Too low - maybe monthly values divided wrong, try reasonable minimum
            min_usd = max(min_usd * 100, 5)
            max_usd = max(max_usd * 100, 10)
    
    # Ensure min < max
    if min_usd > max_usd:
        min_usd, max_usd = max_usd, min_usd
    
    return {
        "min_usd": int(round(min_usd)),
        "max_usd": int(round(max_usd)),
        "pay_type": pay_type,
        "sources_used": [c["url"] for c in candidates[:5]],
        "scored_sources": [{"url": c["url"], "strength": 50 + reliability_boost(c["url"]), "range_tag": "General"} for c in candidates[:8]],
    }


# ============================================================
# UI State
# ============================================================
def init_state():
    defaults = {"job_title": "", "experience_level": "", "job_desc": "", "country": "", "state": "", "city": "", "rate_type": "salary", "currency": "USD", "last_result": None, "debug_last_error": None}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


def on_country_change():
    st.session_state["state"] = ""
    st.session_state["city"] = ""
    st.session_state["currency"] = get_country_metadata(st.session_state["country"]).get("currency", "USD")


def on_state_change():
    st.session_state["city"] = ""


# ============================================================
# Header
# ============================================================
st.markdown('<div class="jr-title">Job Rate Finder</div>', unsafe_allow_html=True)
st.markdown('<div class="jr-subtitle">Get competitive salary and hourly rate information for any position</div>', unsafe_allow_html=True)


# ============================================================
# Form
# ============================================================
with st.container(border=True):
    st.text_input("Job Title *", key="job_title", placeholder="e.g., Software Engineer")
    st.text_input("Experience Level (optional)", key="experience_level", placeholder="e.g., Senior, 5+ years")
    st.text_area("Job Description (optional)", key="job_desc", placeholder="Paste job description...", height=100)

    try:
        countries = get_country_list()
    except:
        countries = []
    
    country_options = [""] + (countries if countries else ["(unavailable)"])
    st.selectbox("Country *", options=country_options, key="country", on_change=on_country_change, format_func=lambda x: "— Select —" if x == "" else x)

    states = get_states_for_country(st.session_state["country"]) if st.session_state["country"] else []
    state_options = [""] + states
    if st.session_state["state"] not in state_options:
        st.session_state["state"] = ""

    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox("State/Province", options=state_options, key="state", on_change=on_state_change, format_func=lambda x: "— Any —" if x == "" else x)
    
    cities = get_cities(st.session_state["country"], st.session_state["state"]) if st.session_state["country"] else []
    city_options = [""] + cities
    if st.session_state["city"] not in city_options:
        st.session_state["city"] = ""
    
    with c2:
        st.selectbox("City", options=city_options, key="city", format_func=lambda x: "— Any —" if x == "" else x)
    
    with c3:
        rate_label = st.radio("Rate Type *", ["Salary (Annual)", "Hourly"], horizontal=True, key="rate_radio")
        st.session_state["rate_type"] = "hourly" if rate_label == "Hourly" else "salary"

    fx_rates = get_fx_table_usd()
    st.selectbox("Display Currency", options=sorted(fx_rates.keys()), index=sorted(fx_rates.keys()).index(st.session_state["currency"]) if st.session_state["currency"] in fx_rates else 0, key="currency")

    can_submit = bool(st.session_state["job_title"].strip() and st.session_state["country"].strip())
    submitted = st.button("Get Rates!", disabled=not can_submit)


# ============================================================
# Process
# ============================================================
if submitted:
    st.session_state["debug_last_error"] = None
    with st.spinner("Searching..."):
        try:
            candidates = serpapi_search(
                st.session_state["job_title"], st.session_state["country"],
                st.session_state["state"], st.session_state["city"],
                st.session_state["rate_type"], st.session_state["job_desc"],
                st.session_state["experience_level"]
            )
            
            if not candidates:
                st.warning("No salary sources found. Try a different job title or location.")
                st.session_state["last_result"] = None
            else:
                with st.spinner("Analyzing..."):
                    result = openai_estimate(
                        st.session_state["job_title"], st.session_state["job_desc"],
                        st.session_state["experience_level"], st.session_state["country"],
                        st.session_state["state"], st.session_state["city"],
                        st.session_state["rate_type"], candidates
                    )
                
                min_usd, max_usd = result["min_usd"], result["max_usd"]
                currency = st.session_state["currency"]
                
                min_disp = convert_from_usd(min_usd, currency) if currency != "USD" else min_usd
                max_disp = convert_from_usd(max_usd, currency) if currency != "USD" else max_usd
                
                # Build sources
                cand_map = {c["url"]: c for c in candidates}
                sources = []
                for s in result.get("scored_sources", [])[:MAX_SOURCES_TO_DISPLAY]:
                    url = s.get("url", "")
                    if url and not is_blocked_source(url):
                        host, slug = pretty_url_label(url)
                        sources.append({
                            "title": f"{host} — {slug}",
                            "url": url,
                            "strength": min(100, s.get("strength", 50)),
                            "geo": cand_map.get(url, {}).get("geo_tag", "Nearby/Unclear"),
                            "range": s.get("range_tag", "General")
                        })
                
                st.session_state["last_result"] = {
                    "min": int(round(min_disp)),
                    "max": int(round(max_disp)),
                    "currency": currency,
                    "rateType": pay_type_to_rate_type(result["pay_type"]),
                    "sources": sources,
                }
        except Exception as e:
            st.session_state["last_result"] = None
            st.session_state["debug_last_error"] = str(e)
            st.error(f"Error: {str(e)[:200]}")


# ============================================================
# Results
# ============================================================
res = st.session_state.get("last_result")
if res:
    unit = "per hour" if res["rateType"] == "hourly" else "per year"
    
    range_html = f"""
    <div class="jr-range">
      <div class="jr-range-top">
        <div style="width:28px;height:28px;border-radius:10px;background:rgba(255,255,255,.16);display:flex;align-items:center;justify-content:center;font-weight:900;">$</div>
        <div class="jr-range-title">Estimated Rate Range</div>
      </div>
      <div class="jr-range-grid">
        <div>
          <p class="jr-range-label">Minimum</p>
          <p class="jr-range-amt">{res["currency"]} {res["min"]:,}</p>
          <p class="jr-range-unit">{unit}</p>
        </div>
        <div class="jr-dash">—</div>
        <div>
          <p class="jr-range-label">Maximum</p>
          <p class="jr-range-amt">{res["currency"]} {res["max"]:,}</p>
          <p class="jr-range-unit">{unit}</p>
        </div>
      </div>
    </div>
    """
    st.markdown(range_html, unsafe_allow_html=True)

    if res.get("sources"):
        with st.container(border=True):
            st.markdown("### Sources")
            for s in res["sources"]:
                title = html.escape(s.get("title", "Source"))
                url = html.escape(s.get("url", ""), quote=True)
                strength = s.get("strength", 50)
                geo = s.get("geo", "Nearby/Unclear")
                
                st.markdown(f"""
                <a class="jr-source" href="{url}" target="_blank">
                  <div class="jr-source-ico">↗</div>
                  <div style="min-width:0;width:100%;">
                    <div class="jr-source-main">{title}</div>
                    <div class="jr-source-sub">
                      <span class="jr-geo-pill">{geo}</span>
                      <span class="jr-score-pill">
                        <span>Strength {strength}/100</span>
                        <span class="jr-score-bar"><span class="jr-score-fill" style="width:{strength}%;"></span></span>
                      </span>
                    </div>
                  </div>
                </a>
                """, unsafe_allow_html=True)

if st.session_state.get("debug_last_error"):
    with st.expander("Debug"):
        st.code(st.session_state["debug_last_error"])
