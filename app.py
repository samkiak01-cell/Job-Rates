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
# Secrets/env helper
# ============================================================
def require_secret_or_env(name: str) -> str:
    v = (os.getenv(name, "") or "").strip()
    if not v:
        try:
            v = str(st.secrets.get(name, "")).strip()
        except Exception:
            v = ""
    if not v:
        raise RuntimeError(f"Missing API key/config: {name}. Set it in Streamlit Secrets or environment variables.")
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
        return sorted(set(states), key=lambda x: x.lower())
    except Exception:
        return []


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def get_cities(country: str, state: str) -> List[str]:
    try:
        if not country:
            return []

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
# Country metadata for improved international support
# ============================================================
COUNTRY_METADATA = {
    "Brazil": {
        "aliases": ["Brazil", "Brasil", "BR"],
        "local_name": "Brasil",
        "currency": "BRL",
        "language": "Portuguese",
        "salary_sites": ["vagas.com.br", "catho.com.br", "glassdoor.com.br"],
    },
    "United States": {
        "aliases": ["United States", "USA", "US", "U.S.", "U.S.A.", "America"],
        "local_name": "United States",
        "currency": "USD",
        "language": "English",
        "salary_sites": [],
    },
    "United Kingdom": {
        "aliases": ["United Kingdom", "UK", "U.K.", "Britain", "Great Britain"],
        "local_name": "United Kingdom",
        "currency": "GBP",
        "language": "English",
        "salary_sites": [],
    },
    "Germany": {
        "aliases": ["Germany", "Deutschland", "DE"],
        "local_name": "Deutschland",
        "currency": "EUR",
        "language": "German",
        "salary_sites": ["stepstone.de", "gehalt.de"],
    },
    "France": {
        "aliases": ["France", "FR"],
        "local_name": "France",
        "currency": "EUR",
        "language": "French",
        "salary_sites": [],
    },
    "Spain": {
        "aliases": ["Spain", "España", "ES"],
        "local_name": "España",
        "currency": "EUR",
        "language": "Spanish",
        "salary_sites": [],
    },
    "Mexico": {
        "aliases": ["Mexico", "México", "MX"],
        "local_name": "México",
        "currency": "MXN",
        "language": "Spanish",
        "salary_sites": ["occ.com.mx"],
    },
    "Canada": {
        "aliases": ["Canada", "CA"],
        "local_name": "Canada",
        "currency": "CAD",
        "language": "English",
        "salary_sites": [],
    },
    "Australia": {
        "aliases": ["Australia", "AU"],
        "local_name": "Australia",
        "currency": "AUD",
        "language": "English",
        "salary_sites": ["seek.com.au"],
    },
    "India": {
        "aliases": ["India", "IN"],
        "local_name": "India",
        "currency": "INR",
        "language": "English",
        "salary_sites": ["naukri.com", "ambitionbox.com"],
    },
}


def get_country_metadata(country: str) -> Dict[str, Any]:
    """Get metadata for a country, including aliases and local names."""
    for key, meta in COUNTRY_METADATA.items():
        if country in meta["aliases"] or country == key:
            return meta
    # Default metadata
    return {
        "aliases": [country],
        "local_name": country,
        "currency": "USD",
        "language": "English",
        "salary_sites": [],
    }


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
# URL helpers
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


def host_of(url: str) -> str:
    try:
        from urllib.parse import urlparse

        return (urlparse(url).hostname or "").replace("www.", "").lower()
    except Exception:
        return ""


def norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def url_contains_token(url: str, token: str) -> bool:
    if not token:
        return True
    token_norm = norm_text(token)
    token_dash = token_norm.replace(" ", "-")
    u = url.lower()
    return (token_dash in u) or (token_norm in norm_text(u))


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
        min_v = max(5.0, min(min_v, 1000.0))
        max_v = max(5.0, min(max_v, 1500.0))
    else:
        # Lower floor to catch more international salaries
        min_v = max(5_000.0, min(min_v, 10_000_000.0))
        max_v = max(5_000.0, min(max_v, 10_000_000.0))

    if min_v > max_v:
        min_v, max_v = max_v, min_v
    
    # Safety check: if both are at floor, something went wrong
    if pay_type != "HOURLY" and min_v == 5_000.0 and max_v == 5_000.0:
        # Return placeholder that indicates error
        return 0.0, 0.0
    
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
# IMPROVED: Job description and experience parsing
# ============================================================
SKILL_INDICATORS = {
    # Tech
    "python", "java", "javascript", "typescript", "react", "angular", "vue", "node",
    "aws", "azure", "gcp", "docker", "kubernetes", "sql", "nosql", "mongodb", "postgres",
    "api", "rest", "graphql", "microservices", "devops", "ci/cd", "git", "agile", "scrum",
    # Design
    "figma", "sketch", "adobe", "photoshop", "illustrator", "indesign", "xd", "after",
    "premiere", "ui", "ux", "wireframe", "prototype", "visual", "graphic",
    # Business
    "excel", "powerpoint", "tableau", "powerbi", "salesforce", "sap", "erp", "crm",
    "analytics", "reporting", "forecasting", "budgeting", "finance", "accounting",
    # Marketing
    "seo", "sem", "ppc", "google", "analytics", "adwords", "facebook", "instagram",
    "content", "copywriting", "email", "campaign", "social", "media", "brand",
    # Engineering
    "autocad", "solidworks", "revit", "cad", "civil", "mechanical", "electrical",
    # Medical
    "clinical", "patient", "medical", "healthcare", "nursing", "pharmacy", "hospital",
    # Other
    "management", "leadership", "strategy", "operations", "project", "product", "sales"
}


def extract_key_requirements(job_desc: str) -> List[str]:
    """Extract key skills, technologies, and requirements from job description."""
    desc = (job_desc or "").strip().lower()
    if not desc:
        return []
    
    found_skills: List[str] = []
    seen = set()
    
    # Extract years of experience mentions
    exp_patterns = [
        r'(\d+)\+?\s*(?:to|\-|–)?\s*\d*\s*years?(?:\s+(?:of\s+)?experience)?',
        r'(?:minimum|at least)\s+(\d+)\s*years?',
    ]
    for pattern in exp_patterns:
        matches = re.findall(pattern, desc)
        for match in matches:
            years = match if isinstance(match, str) else (match[0] if isinstance(match, tuple) else str(match))
            exp_text = f"{years}+ years"
            if exp_text not in seen:
                found_skills.append(exp_text)
                seen.add(exp_text)
                break  # Only add one experience requirement
    
    # Find skills from our dictionary
    for skill in SKILL_INDICATORS:
        if skill in desc and skill not in seen:
            found_skills.append(skill)
            seen.add(skill)
            if len(found_skills) >= 12:
                break
    
    # Find capitalized acronyms/technologies (e.g., AWS, SQL, API)
    acronyms = re.findall(r'\b[A-Z]{2,6}\b', job_desc)
    for acro in acronyms:
        acro_lower = acro.lower()
        if acro_lower not in seen and len(acro) >= 2:
            found_skills.append(acro)
            seen.add(acro_lower)
            if len(found_skills) >= 12:
                break
    
    # Find compound skills (e.g., React.js, Node.js, C++, C#)
    compounds = re.findall(r'\b\w+[\.\/\+#]\w+\b', job_desc)
    for comp in compounds:
        comp_lower = comp.lower()
        if comp_lower not in seen and len(comp) <= 20:
            found_skills.append(comp)
            seen.add(comp_lower)
            if len(found_skills) >= 12:
                break
    
    return found_skills[:10]


def build_search_hint(job_desc: str, experience_level: str) -> str:
    """Build search hint from job description and experience level."""
    bits: List[str] = []
    
    # Add experience level
    exp = (experience_level or "").strip()
    if exp:
        bits.append(exp)
    
    # Extract and add key requirements
    requirements = extract_key_requirements(job_desc)
    if requirements:
        bits.extend(requirements[:6])  # Limit to 6 most important
    
    return " ".join(bits).strip()


# ============================================================
# Reliability + blocklists
# ============================================================
RELIABLE_HOST_HINTS = [
    "salaryexpert.com",
    "levels.fyi",
    "glassdoor.com",
    "indeed.com",
    "salary.com",
    "payscale.com",
    "builtin.com",
    "ziprecruiter.com",
    "linkedin.com",
    "hays.",
    "roberthalf.",
    "randstad.",
    "michaelpage.",
    "talent.com",
    "vagas.com",  # Brazil
    "catho.com",  # Brazil
    "glassdoor.com.br",  # Brazil
    "stepstone.",  # Germany
    "gehalt.de",  # Germany
    "seek.com",  # Australia
    "naukri.com",  # India
    "ambitionbox.com",  # India
    "occ.com",  # Mexico
]

BLOCKED_HOST_HINTS = [
    "pinterest.",
    "facebook.",
    "instagram.",
    "tiktok.",
    "youtube.",
    "reddit.",
    "quora.",
    "medium.",
    "github.",
    "wikipedia.",
    "slideshare.",
]


def is_blocked_source(url: str) -> bool:
    h = host_of(url)
    return any(b in h for b in BLOCKED_HOST_HINTS)


def reliability_boost(url: str) -> int:
    h = host_of(url)
    for r in RELIABLE_HOST_HINTS:
        if r in h:
            return 28
    return 0


def geo_priority(tag: str) -> int:
    return {"Exact": 3, "Country-level": 2, "Nearby/Unclear": 1}.get(tag, 0)


# ============================================================
# SerpAPI helpers (IMPROVED geo checking)
# ============================================================
def serp_country_aliases(country: str) -> List[str]:
    """Get all possible aliases for a country."""
    meta = get_country_metadata(country)
    return meta["aliases"]


def text_contains_any(hay: str, needles: List[str]) -> bool:
    """Check if any needle appears in the haystack (case-insensitive)."""
    h = norm_text(hay)
    for n in needles:
        if not n:
            continue
        if norm_text(n) in h:
            return True
    return False


def geo_tag_from_serp(url: str, title: str, snippet: str, country: str, state: str, city: str) -> str:
    """
    Determine geographical relevance of a search result.
    Now with improved international support.
    """
    country_aliases = serp_country_aliases(country)
    blob = " ".join([title or "", snippet or "", url or ""])

    # Check for country match (including local names)
    country_ok = text_contains_any(blob, country_aliases) or url_contains_token(url, country)
    
    # For international sites, be more lenient if we see the job title + any location indicator
    if not country_ok:
        # Check if URL is from a country-specific domain
        h = host_of(url)
        meta = get_country_metadata(country)
        local_currency = meta.get("currency", "")
        
        # Check for country TLD or local salary sites
        for site in meta.get("salary_sites", []):
            if site in h:
                country_ok = True
                break
        
        # Check for currency mentions (e.g., BRL for Brazil)
        if local_currency and local_currency in blob.upper():
            country_ok = True

    if not country_ok:
        return "Nearby/Unclear"

    if not state and not city:
        return "Country-level"

    if city:
        if text_contains_any(blob, [city]) or url_contains_token(url, city):
            return "Exact"

    if state:
        if text_contains_any(blob, [state]) or url_contains_token(url, state):
            return "Exact"

    return "Country-level"


# ============================================================
# AI logic
# ============================================================
def rate_type_to_pay_type(rate_type: str) -> str:
    return "HOURLY" if (rate_type or "").strip().lower() == "hourly" else "ANNUAL"


def pay_type_to_rate_type(pay_type: str) -> str:
    return "hourly" if (pay_type or "").strip().upper() == "HOURLY" else "salary"


def serpapi_search(
    job_title: str,
    country: str,
    state: str,
    city: str,
    rate_type: str,
    job_desc: str = "",
    experience_level: str = "",
) -> List[Dict[str, Any]]:
    """
    Returns candidate results with IMPROVED international search.
    """
    serp_key = require_secret_or_env("SERPAPI_API_KEY")
    pay_type = rate_type_to_pay_type(rate_type)
    hint = build_search_hint(job_desc, experience_level)
    
    meta = get_country_metadata(country)
    local_name = meta.get("local_name", country)
    local_currency = meta.get("currency", "USD")

    # Query A: Standard English query + experience level
    q_a_parts = [job_title.strip()]
    if experience_level.strip():
        q_a_parts.append(experience_level.strip())
    q_a_parts.append(country.strip())
    if state:
        q_a_parts.append(state.strip())
    if city:
        q_a_parts.append(city.strip())
    q_a_parts.append("salary")
    q_a = " ".join([p for p in q_a_parts if p]).strip()

    # Query B: With job description hints
    q_b_parts = [job_title.strip()]
    if hint:
        q_b_parts.append(hint)
    q_b_parts.append(f'salary range "{country}"')
    q_b_parts.append("hourly rate" if pay_type == "HOURLY" else "annual salary")
    if state:
        q_b_parts.append(f'"{state}"')
    if city:
        q_b_parts.append(f'"{city}"')
    q_b = " ".join([p for p in q_b_parts if p]).strip()

    # Query C: SalaryExpert (still useful)
    q_c = f'site:salaryexpert.com "{job_title}" "{country}" salary'

    # Query D: LOCAL NAME + local currency (NEW - for Brazil, etc.)
    q_d_parts = [job_title.strip()]
    if local_name != country:
        q_d_parts.append(f'"{local_name}"')
    else:
        q_d_parts.append(f'"{country}"')
    q_d_parts.append("salário" if local_name == "Brasil" else "salary")
    if local_currency != "USD":
        q_d_parts.append(local_currency)
    q_d = " ".join([p for p in q_d_parts if p]).strip()

    # Query E: Local salary sites (NEW - for Brazil, etc.)
    q_e = None
    if meta.get("salary_sites"):
        top_site = meta["salary_sites"][0]
        q_e = f'site:{top_site} "{job_title}" salário' if local_name == "Brasil" else f'site:{top_site} "{job_title}" salary'

    queries = [q_a, q_b, q_c, q_d]
    if q_e:
        queries.append(q_e)

    all_items: List[Dict[str, Any]] = []
    for q in queries:
        try:
            params = {"engine": "google", "q": q, "api_key": serp_key, "num": 20, "tbs": "qdr:m6"}
            
            # For non-English countries, use country-specific Google
            if local_name != country and meta.get("language") != "English":
                # Use country code for gl parameter
                country_code = None
                if country == "Brazil":
                    country_code = "br"
                elif country == "Germany":
                    country_code = "de"
                elif country == "France":
                    country_code = "fr"
                elif country == "Spain":
                    country_code = "es"
                elif country == "Mexico":
                    country_code = "mx"
                
                if country_code:
                    params["gl"] = country_code
            
            r = http_get("https://serpapi.com/search.json", params=params, timeout=35)
            r.raise_for_status()
            data = r.json()

            for item in (data.get("organic_results") or []):
                link = item.get("link")
                if not (isinstance(link, str) and link.startswith(("http://", "https://"))):
                    continue
                if is_blocked_source(link):
                    continue

                title = item.get("title") if isinstance(item.get("title"), str) else ""
                snippet = item.get("snippet") if isinstance(item.get("snippet"), str) else ""
                h = host_of(link)
                geo = geo_tag_from_serp(link, title, snippet, country, state, city)
                rel = reliability_boost(link)

                all_items.append(
                    {
                        "url": link.strip(),
                        "title": title.strip(),
                        "snippet": snippet.strip(),
                        "host": h,
                        "geo_tag": geo,
                        "rel_boost": rel,
                    }
                )
        except Exception as e:
            # Continue with other queries if one fails
            continue

    # Deduplicate by URL, keep the best scoring version
    best: Dict[str, Dict[str, Any]] = {}
    for it in all_items:
        u = it["url"]
        score = geo_priority(it["geo_tag"]) * 100 + it["rel_boost"]
        if u not in best:
            best[u] = {**it, "_score": score}
        else:
            if score > int(best[u].get("_score", 0)):
                best[u] = {**it, "_score": score}

    dedup = list(best.values())
    dedup.sort(key=lambda x: int(x.get("_score", 0)), reverse=True)

    return dedup[:30]  # Increased from 24 to give more options


def openai_estimate(
    job_title: str,
    job_desc: str,
    experience_level: str,
    country: str,
    state: str,
    city: str,
    rate_type: str,
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    openai_key = require_secret_or_env("OPENAI_API_KEY")
    pay_type = rate_type_to_pay_type(rate_type)
    
    meta = get_country_metadata(country)
    local_currency = meta.get("currency", "USD")

    location_bits = [b for b in [city, state, country] if b]
    loc = ", ".join(location_bits) if location_bits else country

    exp = (experience_level or "").strip()
    exp_line = f'- Experience level: "{exp}"' if exp else '- Experience level: Not specified'
    
    # Extract key requirements for better context
    requirements = extract_key_requirements(job_desc)
    req_line = f'- Key requirements: {", ".join(requirements[:8])}' if requirements else '- Key requirements: None specified'

    # Give the model the URL + context so it can select correctly
    lines = []
    for c in candidates[:18]:  # Increased from 14
        lines.append(
            f'- {c["url"]}\n  title: {c.get("title","")}\n  snippet: {c.get("snippet","")}\n  geo: {c.get("geo_tag","")}'
        )
    url_block = "\n".join(lines) if lines else "- (no links found)"

    # IMPROVED PROMPT: Forces AI to extract actual numbers from sources
    prompt = f"""
You are a salary research analyst. Your job is to find ACTUAL salary data from the provided sources.

Job Details:
- Job title: "{job_title}"
{exp_line}
{req_line}
- Location: "{loc}"
- Local currency: {local_currency} (convert ALL estimates to USD)
- Pay type: "{pay_type}" (HOURLY = hourly rate; ANNUAL = yearly salary)

CRITICAL INSTRUCTIONS:
1. You MUST extract actual salary numbers that appear in the source content (titles/snippets)
2. DO NOT estimate or infer salaries - only use explicitly stated ranges
3. The experience level "{exp}" and requirements {requirements[:3] if requirements else []} MUST influence your range selection
4. If experience level is "senior" or "5+ years", ignore junior/entry-level sources
5. If experience level is "junior" or "entry-level", ignore senior sources
6. Weight sources that mention similar skills/requirements MORE heavily
7. RETURN ACTUAL NUMBERS - Example: if you see "$50,000 - $80,000", return min_usd: 50000, max_usd: 80000

Available candidate sources (title and snippet show actual content):
{url_block}

Output STRICT JSON (no markdown, no commentary):
{{
  "min_usd": <number (e.g., 50000)>,
  "max_usd": <number (e.g., 80000)>,
  "pay_type": "HOURLY"|"ANNUAL",
  "sources": [
    {{
      "url": <url from candidates>,
      "range_tag": "Min"|"Max"|"General",
      "strength": <0-100>,
      "extracted_range": "<what salary text you found in this source>"
    }}
  ],
  "sources_used": [<urls>, ...],
  "min_links": [<urls>, ...],
  "max_links": [<urls>, ...]
}}

Rules:
- min_usd <= max_usd, realistic for {job_title} at {exp} level in {country}
- RETURN ACTUAL NUMERIC VALUES (e.g., 50000, not "50K" or "$50,000")
- ALL VALUES IN USD (convert from {local_currency} if needed using approximate rates)
- If sources show {local_currency}, convert: BRL÷5=USD, EUR×1.1=USD, GBP×1.27=USD, INR÷83=USD
- ONLY use sources where you can see salary data in the title/snippet
- Experience level "{exp}" MUST affect the range (senior = higher, junior = lower)
- "extracted_range" field proves you found actual data (e.g., "₹50K-80K/mo" or "$90K-120K annually")
- Country-level matches are valuable for {country}
- Local salary sites MORE reliable than global aggregators
- Quality over quantity: 3-6 strong sources better than 10 weak ones
- DO NOT invent URLs - only use provided candidates
- strength = how reliable this source is (0-100)
- EXAMPLE VALID RESPONSE: {{"min_usd": 65000, "max_usd": 95000, "pay_type": "ANNUAL", ...}}
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
    
    # Debug: Show what AI returned
    if min_usd is None or max_usd is None:
        error_msg = f"OpenAI returned invalid values: min={parsed.get('min_usd')}, max={parsed.get('max_usd')}"
        raise RuntimeError(error_msg)
    
    # Debug: Check before clamping
    if min_usd == 0 or max_usd == 0:
        error_msg = f"OpenAI returned zero values: min={min_usd}, max={max_usd}. Raw response: {text_out[:500]}"
        raise RuntimeError(error_msg)
    
    min_usd, max_usd = clamp_min_max(float(min_usd), float(max_usd), pay_type_out)
    
    # Check if clamping failed
    if min_usd == 0 and max_usd == 0:
        raise RuntimeError(f"Salary range validation failed - AI may not have found valid salary data in sources")

    urls = [c["url"] for c in candidates]
    cand_set = set(urls)

    def only_candidates(xs: Any) -> List[str]:
        xs2 = clean_urls(xs)
        out: List[str] = []
        seen = set()
        for u in xs2:
            if u in cand_set and u not in seen and not is_blocked_source(u):
                seen.add(u)
                out.append(u)
        return out

    sources_used = only_candidates(parsed.get("sources_used"))
    min_links = only_candidates(parsed.get("min_links"))
    max_links = only_candidates(parsed.get("max_links"))

    scored_sources: List[Dict[str, Any]] = []
    raw_sources = parsed.get("sources")
    if isinstance(raw_sources, list):
        for item in raw_sources:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if not (isinstance(url, str) and url.startswith(("http://", "https://"))):
                continue
            url = url.strip()
            if url not in cand_set or is_blocked_source(url):
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
            strength_int = int(max(0, min(100, strength_int + reliability_boost(url))))

            scored_sources.append({"url": url, "range_tag": range_tag, "strength": strength_int})

    best_src: Dict[str, Dict[str, Any]] = {}
    for s in scored_sources:
        u = s["url"]
        if u not in best_src or int(s["strength"]) > int(best_src[u]["strength"]):
            best_src[u] = s

    dedup_scored = list(best_src.values())
    dedup_scored.sort(key=lambda x: int(x.get("strength", 0)), reverse=True)

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
# UI state init
# ============================================================
def init_state():
    defaults = {
        "job_title": "",
        "experience_level": "",
        "job_desc": "",
        "country": "",
        "state": "",
        "city": "",
        "rate_type": "salary",
        "currency": "USD",
        "last_result": None,
        "debug_last_error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


def on_country_change():
    st.session_state["state"] = ""
    st.session_state["city"] = ""
    # Auto-set currency based on country
    meta = get_country_metadata(st.session_state["country"])
    st.session_state["currency"] = meta.get("currency", "USD")


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
# Form card
# ============================================================
with st.container(border=True):
    st.text_input("Job Title *", key="job_title", placeholder="e.g., Software Engineer")
    st.text_input("Experience Level (optional)", key="experience_level", placeholder="e.g., Senior, 5+ years")
    st.text_area("Job Description (optional)", key="job_desc", placeholder="Paste job description to extract key skills...", height=130)

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
        format_func=lambda x: "— Select —" if x == "" else x,
    )

    states = []
    if st.session_state["country"] and st.session_state["country"] != "(unavailable)":
        states = get_states_for_country(st.session_state["country"]) or []
    state_options = [""] + states
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

    cities = []
    if st.session_state["country"] and st.session_state["country"] != "(unavailable)":
        cities = get_cities(st.session_state["country"], st.session_state["state"]) or []
    city_options = [""] + cities
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
            experience_level = (st.session_state["experience_level"] or "").strip()

            country = st.session_state["country"].strip()
            state = (st.session_state["state"] or "").strip()
            city = (st.session_state["city"] or "").strip()
            rate_type = st.session_state["rate_type"]
            currency = st.session_state["currency"]

            candidates = serpapi_search(
                job_title,
                country,
                state,
                city,
                rate_type,
                job_desc=job_desc,
                experience_level=experience_level,
            )
            
            if not candidates:
                st.warning(f"No salary data sources found for {job_title} in {country}. Try adjusting your search criteria.")
                st.session_state["last_result"] = None
            else:
                result = openai_estimate(
                    job_title,
                    job_desc,
                    experience_level,
                    country,
                    state,
                    city,
                    rate_type,
                    candidates,
                )

                min_usd = float(result["min_usd"])
                max_usd = float(result["max_usd"])
                pay_type = str(result.get("pay_type", rate_type_to_pay_type(rate_type))).upper()

                min_disp = min_usd
                max_disp = max_usd
                if currency.upper() != "USD":
                    min_disp = convert_from_usd(min_usd, currency)
                    max_disp = convert_from_usd(max_usd, currency)

                # Build maps from candidate metadata (geo from SERP)
                cand_map: Dict[str, Dict[str, Any]] = {c["url"]: c for c in candidates}
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
                    strength = int(max(0, min(100, strength + reliability_boost(u))))
                    geo = str(cand_map.get(u, {}).get("geo_tag", "Nearby/Unclear"))
                    sources.append({"title": title, "url": u, "range": rng, "strength": strength, "geo": geo})

                for u in min_links:
                    add_source(u, "Min (Annual)" if pay_type == "ANNUAL" else "Min (Hourly)")
                for u in max_links:
                    add_source(u, "Max (Annual)" if pay_type == "ANNUAL" else "Max (Hourly)")

                if len(sources) < 5:
                    for item in scored:
                        u = item.get("url")
                        if isinstance(u, str) and u.startswith(("http://", "https://")) and not is_blocked_source(u):
                            tag = tag_map.get(u, "General")
                            if tag == "Min":
                                rng = "Min (Annual)" if pay_type == "ANNUAL" else "Min (Hourly)"
                            elif tag == "Max":
                                rng = "Max (Annual)" if pay_type == "ANNUAL" else "Max (Hourly)"
                            else:
                                rng = "Source"
                            add_source(u, rng)
                            if len(sources) >= 12:
                                break

                if len(sources) < 3:
                    for u in sources_used:
                        if not is_blocked_source(u):
                            add_source(u, "Source")
                        if len(sources) >= 10:
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

                # Sort: geo match first, then strength
                deduped.sort(
                    key=lambda x: (geo_priority(str(x.get("geo", ""))), int(x.get("strength", 0))),
                    reverse=True,
                )

                st.session_state["last_result"] = {
                    "min": int(round(min_disp)),
                    "max": int(round(max_disp)),
                    "currency": currency.upper(),
                    "rateType": pay_type_to_rate_type(pay_type),
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
            st.error(f"Error: {str(e)[:200]}")


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
        st.caption("Sources prioritized by geo match and reliability. Range based on actual data from these sources.")

        if not sources:
            st.caption("No sources were returned confidently for this query.")
        else:
            for s in sources:
                title = (s.get("title") or "Source").replace("<", "&lt;").replace(">", "&gt;")
                url = (s.get("url") or "").replace('"', "%22")
                rng = (s.get("range") or "Source").replace("<", "&lt;").replace(">", "&gt;")
                geo = (s.get("geo") or "Nearby/Unclear").strip()
                geo_label = "Exact" if geo == "Exact" else ("Country-level" if geo == "Country-level" else "Nearby/Unclear")

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
                      <span class="jr-geo-pill">{geo_label}</span>
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
              <strong>Note:</strong> Ranges are extracted from actual salary data in source content. 
              Experience level and job requirements influence source selection and weighting.
            </div>
            """,
            unsafe_allow_html=True,
        )

if st.session_state.get("debug_last_error"):
    with st.expander("Debug details", expanded=False):
        st.code(st.session_state["debug_last_error"])
