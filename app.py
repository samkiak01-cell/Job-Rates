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

# Hours per year (for hourly <-> annual conversion)
HOURS_PER_YEAR = 2080  # 40 hours/week × 52 weeks


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
# Country metadata for international support
# ============================================================
COUNTRY_METADATA = {
    "Brazil": {
        "aliases": ["Brazil", "Brasil", "BR"],
        "local_name": "Brasil",
        "currency": "BRL",
        "language": "Portuguese",
        "salary_sites": ["vagas.com.br", "catho.com.br", "glassdoor.com.br"],
        "salary_period": "monthly",  # Default salary period in this country
        "months_per_year": 13,  # 13th month bonus
    },
    "United States": {
        "aliases": ["United States", "USA", "US", "U.S.", "U.S.A.", "America"],
        "local_name": "United States",
        "currency": "USD",
        "language": "English",
        "salary_sites": [],
        "salary_period": "annual",
        "months_per_year": 12,
    },
    "United Kingdom": {
        "aliases": ["United Kingdom", "UK", "U.K.", "Britain", "Great Britain"],
        "local_name": "United Kingdom",
        "currency": "GBP",
        "language": "English",
        "salary_sites": [],
        "salary_period": "annual",
        "months_per_year": 12,
    },
    "Germany": {
        "aliases": ["Germany", "Deutschland", "DE"],
        "local_name": "Deutschland",
        "currency": "EUR",
        "language": "German",
        "salary_sites": ["stepstone.de", "gehalt.de"],
        "salary_period": "annual",
        "months_per_year": 12,
    },
    "France": {
        "aliases": ["France", "FR"],
        "local_name": "France",
        "currency": "EUR",
        "language": "French",
        "salary_sites": [],
        "salary_period": "annual",
        "months_per_year": 12,
    },
    "Spain": {
        "aliases": ["Spain", "España", "ES"],
        "local_name": "España",
        "currency": "EUR",
        "language": "Spanish",
        "salary_sites": [],
        "salary_period": "annual",
        "months_per_year": 14,  # 14 payments common in Spain
    },
    "Mexico": {
        "aliases": ["Mexico", "México", "MX"],
        "local_name": "México",
        "currency": "MXN",
        "language": "Spanish",
        "salary_sites": ["occ.com.mx"],
        "salary_period": "monthly",
        "months_per_year": 12,
    },
    "Canada": {
        "aliases": ["Canada", "CA"],
        "local_name": "Canada",
        "currency": "CAD",
        "language": "English",
        "salary_sites": [],
        "salary_period": "annual",
        "months_per_year": 12,
    },
    "Australia": {
        "aliases": ["Australia", "AU"],
        "local_name": "Australia",
        "currency": "AUD",
        "language": "English",
        "salary_sites": ["seek.com.au"],
        "salary_period": "annual",
        "months_per_year": 12,
    },
    "India": {
        "aliases": ["India", "IN"],
        "local_name": "India",
        "currency": "INR",
        "language": "English",
        "salary_sites": ["naukri.com", "ambitionbox.com"],
        "salary_period": "annual",  # Usually LPA (Lakhs Per Annum)
        "months_per_year": 12,
    },
    "Japan": {
        "aliases": ["Japan", "JP", "日本"],
        "local_name": "Japan",
        "currency": "JPY",
        "language": "Japanese",
        "salary_sites": [],
        "salary_period": "monthly",
        "months_per_year": 12,
    },
    "Philippines": {
        "aliases": ["Philippines", "PH"],
        "local_name": "Philippines",
        "currency": "PHP",
        "language": "English",
        "salary_sites": [],
        "salary_period": "monthly",
        "months_per_year": 13,
    },
}


def get_country_metadata(country: str) -> Dict[str, Any]:
    """Get metadata for a country, including aliases and local names."""
    for key, meta in COUNTRY_METADATA.items():
        if country in meta["aliases"] or country == key:
            return meta
    return {
        "aliases": [country],
        "local_name": country,
        "currency": "USD",
        "language": "English",
        "salary_sites": [],
        "salary_period": "annual",
        "months_per_year": 12,
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
    """Convert USD to another currency."""
    to_ccy = (to_ccy or "USD").upper()
    rate = get_fx_table_usd().get(to_ccy)
    return amount if not rate else amount * rate


def convert_to_usd(amount: float, from_ccy: str) -> float:
    """Convert from a currency to USD."""
    from_ccy = (from_ccy or "USD").upper()
    if from_ccy == "USD":
        return amount
    rate = get_fx_table_usd().get(from_ccy)
    if not rate or rate <= 0:
        return amount
    return amount / rate


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
    s = re.sub(r"[\$€£¥₹R\$]", "", s).strip()

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
    """Validate salary range."""
    if min_v <= 0 or max_v <= 0:
        return 0.0, 0.0

    if not math.isfinite(min_v) or not math.isfinite(max_v):
        return 0.0, 0.0

    if min_v > max_v:
        min_v, max_v = max_v, min_v

    if pay_type == "HOURLY":
        # Hourly: $1 to $1000/hour is reasonable range
        if min_v > 1000 or max_v > 1000:
            return 0.0, 0.0
        if min_v < 1:
            min_v = 1  # Minimum $1/hour
    else:
        # Annual: $1,000 to $10M/year is reasonable
        if min_v > 10_000_000 or max_v > 10_000_000:
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
# Experience level normalization
# ============================================================
EXPERIENCE_LEVELS = {
    "entry": ["entry", "entry-level", "entry level", "junior", "jr", "graduate", "grad", "fresher", "0-2 years", "1-2 years", "0-1 years", "trainee", "intern"],
    "mid": ["mid", "mid-level", "mid level", "intermediate", "2-5 years", "3-5 years", "2-4 years", "3-4 years", "associate"],
    "senior": ["senior", "sr", "experienced", "5+ years", "5-7 years", "5-10 years", "6+ years", "7+ years", "lead", "team lead"],
    "principal": ["principal", "staff", "architect", "10+ years", "8+ years", "director", "vp", "executive", "chief", "head of", "manager"]
}


def normalize_experience_level(exp: str) -> Tuple[str, str]:
    """Normalize experience level to a standard category."""
    exp_lower = (exp or "").strip().lower()
    if not exp_lower:
        return ("mid", "Mid-level (default)")

    for level, keywords in EXPERIENCE_LEVELS.items():
        for kw in keywords:
            if kw in exp_lower:
                descriptions = {
                    "entry": "Entry-level/Junior (0-2 years)",
                    "mid": "Mid-level (2-5 years)",
                    "senior": "Senior (5+ years)",
                    "principal": "Principal/Staff (10+ years)"
                }
                return (level, descriptions[level])

    years_match = re.search(r'(\d+)\s*\+?\s*years?', exp_lower)
    if years_match:
        years = int(years_match.group(1))
        if years <= 2:
            return ("entry", f"Entry-level ({years} years)")
        elif years <= 5:
            return ("mid", f"Mid-level ({years} years)")
        elif years <= 10:
            return ("senior", f"Senior ({years} years)")
        else:
            return ("principal", f"Principal ({years}+ years)")

    return ("mid", f"Mid-level (inferred from: {exp})")


def extract_experience_from_job_desc(job_desc: str) -> Optional[str]:
    """Extract experience level from job description if present."""
    desc = (job_desc or "").strip().lower()
    if not desc:
        return None

    exp_patterns = [
        r'(\d+)\s*\+?\s*years?\s+(?:of\s+)?experience',
        r'(?:minimum|at least|requires?)\s+(\d+)\s*\+?\s*years?',
        r'(\d+)\s*-\s*(\d+)\s*years?\s+(?:of\s+)?experience',
    ]

    for pattern in exp_patterns:
        match = re.search(pattern, desc)
        if match:
            if match.lastindex == 2:
                return f"{match.group(1)}-{match.group(2)} years"
            else:
                return f"{match.group(1)}+ years"

    level_keywords = {
        "entry level": "Entry-level",
        "entry-level": "Entry-level",
        "junior": "Junior",
        "senior": "Senior",
        "lead": "Lead",
        "principal": "Principal",
        "staff": "Staff",
        "mid-level": "Mid-level",
        "mid level": "Mid-level",
    }

    for keyword, level in level_keywords.items():
        if keyword in desc:
            return level

    return None


# ============================================================
# Skills extraction
# ============================================================
SKILL_INDICATORS = (
    "python", "java", "javascript", "typescript", "react", "angular", "vue", "node",
    "aws", "azure", "gcp", "docker", "kubernetes", "sql", "nosql", "mongodb", "postgres",
    "api", "rest", "graphql", "microservices", "devops", "ci/cd", "git", "agile", "scrum",
    "figma", "sketch", "adobe", "photoshop", "illustrator", "indesign", "xd",
    "premiere", "ui", "ux", "wireframe", "prototype", "visual", "graphic",
    "excel", "powerpoint", "tableau", "powerbi", "salesforce", "sap", "erp", "crm",
    "analytics", "reporting", "forecasting", "budgeting", "finance", "accounting",
    "seo", "sem", "ppc", "adwords", "content", "copywriting", "campaign", "brand",
    "autocad", "solidworks", "revit", "cad", "civil", "mechanical", "electrical",
    "clinical", "patient", "medical", "healthcare", "nursing", "pharmacy", "hospital",
    "management", "leadership", "strategy", "operations", "project", "product", "sales"
)

SKIP_ACRONYMS = {"HTTP", "WWW", "COM", "ORG", "NET", "HTML", "CSS", "URL", "PDF", "THE", "AND", "FOR", "USD", "BRL", "EUR", "GBP"}


def extract_key_requirements(job_desc: str) -> List[str]:
    """Extract key skills from job description."""
    desc = (job_desc or "").strip().lower()
    if not desc:
        return []

    found_skills: List[str] = []
    seen: set = set()

    for skill in SKILL_INDICATORS:
        if skill in desc and skill not in seen:
            found_skills.append(skill)
            seen.add(skill)
            if len(found_skills) >= MAX_SKILLS_TO_EXTRACT:
                break

    acronyms = re.findall(r'\b[A-Z]{2,6}\b', job_desc)
    for acro in acronyms:
        acro_lower = acro.lower()
        if acro not in SKIP_ACRONYMS and acro_lower not in seen:
            found_skills.append(acro)
            seen.add(acro_lower)
            if len(found_skills) >= MAX_SKILLS_TO_EXTRACT:
                break

    return found_skills[:10]


def build_search_hint(job_desc: str, experience_level: str) -> str:
    """Build search hint from job description and experience level."""
    bits: List[str] = []
    exp = (experience_level or "").strip()
    if exp:
        bits.append(exp)
    requirements = extract_key_requirements(job_desc)
    if requirements:
        bits.extend(requirements[:6])
    return " ".join(bits).strip()


# ============================================================
# Reliability + blocklists
# ============================================================
RELIABLE_HOST_HINTS = [
    "salaryexpert.com", "levels.fyi", "glassdoor.com", "indeed.com", "salary.com",
    "payscale.com", "builtin.com", "ziprecruiter.com", "linkedin.com",
    "hays.", "roberthalf.", "randstad.", "michaelpage.", "talent.com",
    "vagas.com", "catho.com", "glassdoor.com.br", "stepstone.", "gehalt.de",
    "seek.com", "naukri.com", "ambitionbox.com", "occ.com",
]

BLOCKED_HOST_HINTS = [
    "pinterest.", "facebook.", "instagram.", "tiktok.", "youtube.",
    "reddit.", "quora.", "medium.", "github.", "wikipedia.", "slideshare.",
]


def is_blocked_source(url: str) -> bool:
    h = host_of(url)
    return any(b in h for b in BLOCKED_HOST_HINTS)


def reliability_boost(url: str) -> int:
    h = host_of(url)
    for r in RELIABLE_HOST_HINTS:
        if r in h:
            return RELIABILITY_BOOST
    return 0


def geo_priority(tag: str) -> int:
    return {"Exact": 3, "Country-level": 2, "Nearby/Unclear": 1}.get(tag, 0)


# ============================================================
# SerpAPI geo helpers
# ============================================================
def serp_country_aliases(country: str) -> List[str]:
    meta = get_country_metadata(country)
    return meta["aliases"]


def text_contains_any(hay: str, needles: List[str]) -> bool:
    h = norm_text(hay)
    for n in needles:
        if not n:
            continue
        if norm_text(n) in h:
            return True
    return False


def geo_tag_from_serp(url: str, title: str, snippet: str, country: str, state: str, city: str) -> str:
    country_aliases = serp_country_aliases(country)
    blob = " ".join([title or "", snippet or "", url or ""])

    country_ok = text_contains_any(blob, country_aliases) or url_contains_token(url, country)

    if not country_ok:
        h = host_of(url)
        meta = get_country_metadata(country)
        local_currency = meta.get("currency", "")

        for site in meta.get("salary_sites", []):
            if site in h:
                country_ok = True
                break

        if local_currency and local_currency in blob.upper():
            country_ok = True

    if not country_ok:
        return "Nearby/Unclear"

    if not state and not city:
        return "Country-level"

    if city and (text_contains_any(blob, [city]) or url_contains_token(url, city)):
        return "Exact"

    if state and (text_contains_any(blob, [state]) or url_contains_token(url, state)):
        return "Exact"

    return "Country-level"


# ============================================================
# Rate type helpers
# ============================================================
def rate_type_to_pay_type(rate_type: str) -> str:
    return "HOURLY" if (rate_type or "").strip().lower() == "hourly" else "ANNUAL"


def pay_type_to_rate_type(pay_type: str) -> str:
    return "hourly" if (pay_type or "").strip().upper() == "HOURLY" else "salary"


def convert_hourly_to_annual(hourly: float) -> float:
    """Convert hourly rate to annual salary."""
    return hourly * HOURS_PER_YEAR


def convert_annual_to_hourly(annual: float) -> float:
    """Convert annual salary to hourly rate."""
    return annual / HOURS_PER_YEAR

def serpapi_search(
    job_title: str,
    country: str,
    state: str,
    city: str,
    rate_type: str,
    job_desc: str = "",
    experience_level: str = "",
) -> List[Dict[str, Any]]:
    """Returns candidate results with international search support."""
    serp_key = require_secret_or_env("SERPAPI_API_KEY")
    pay_type = rate_type_to_pay_type(rate_type)

    effective_exp = experience_level.strip()
    if not effective_exp:
        effective_exp = extract_experience_from_job_desc(job_desc) or ""

    hint = build_search_hint(job_desc, effective_exp)

    meta = get_country_metadata(country)
    local_name = meta.get("local_name", country)
    local_currency = meta.get("currency", "USD")

    # Build multiple search queries
    q_a_parts = [job_title.strip()]
    if effective_exp:
        q_a_parts.append(effective_exp)
    q_a_parts.append(country.strip())
    if state:
        q_a_parts.append(state.strip())
    if city:
        q_a_parts.append(city.strip())
    q_a_parts.append("hourly rate" if pay_type == "HOURLY" else "salary")
    q_a = " ".join([p for p in q_a_parts if p]).strip()

    q_b_parts = [job_title.strip()]
    if hint:
        q_b_parts.append(hint)
    q_b_parts.append(f'"{country}"')
    q_b_parts.append("hourly rate" if pay_type == "HOURLY" else "annual salary")
    if state:
        q_b_parts.append(f'"{state}"')
    q_b = " ".join([p for p in q_b_parts if p]).strip()

    q_c = f'site:salaryexpert.com "{job_title}" "{country}"'

    q_d_parts = [job_title.strip()]
    if local_name != country:
        q_d_parts.append(f'"{local_name}"')
    else:
        q_d_parts.append(f'"{country}"')
    if local_name == "Brasil":
        q_d_parts.append("salário" if pay_type == "ANNUAL" else "valor hora")
    else:
        q_d_parts.append("salary" if pay_type == "ANNUAL" else "hourly rate")
    q_d = " ".join([p for p in q_d_parts if p]).strip()

    q_e = None
    if meta.get("salary_sites"):
        top_site = meta["salary_sites"][0]
        q_e = f'site:{top_site} "{job_title}"'

    queries = [q_a, q_b, q_c, q_d]
    if q_e:
        queries.append(q_e)

    all_items: List[Dict[str, Any]] = []
    for q in queries:
        try:
            params = {"engine": "google", "q": q, "api_key": serp_key, "num": 20, "tbs": "qdr:m6"}

            if local_name != country and meta.get("language") != "English":
                country_codes = {
                    "Brazil": "br", "Germany": "de", "France": "fr",
                    "Spain": "es", "Mexico": "mx", "Japan": "jp"
                }
                if country in country_codes:
                    params["gl"] = country_codes[country]

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

                all_items.append({
                    "url": link.strip(),
                    "title": title.strip(),
                    "snippet": snippet.strip(),
                    "host": h,
                    "geo_tag": geo,
                    "rel_boost": rel,
                })
        except Exception:
            continue

    # Deduplicate
    best: Dict[str, Dict[str, Any]] = {}
    for it in all_items:
        u = it["url"]
        score = geo_priority(it["geo_tag"]) * 100 + it["rel_boost"]
        if u not in best or score > int(best[u].get("_score", 0)):
            best[u] = {**it, "_score": score}

    dedup = list(best.values())
    dedup.sort(key=lambda x: int(x.get("_score", 0)), reverse=True)

    return dedup[:MAX_SEARCH_RESULTS]


def get_salary_period_guidance(country: str, pay_type: str) -> str:
    """Get country-specific guidance on salary periods."""
    meta = get_country_metadata(country)
    default_period = meta.get("salary_period", "annual")
    months = meta.get("months_per_year", 12)
    currency = meta.get("currency", "USD")

    if pay_type == "HOURLY":
        return f"""
HOURLY RATE HANDLING:
- User wants HOURLY rate in USD
- Look for "/hour", "/hr", "per hour", "hourly", "an hour" indicators
- If you only find annual salary, divide by {HOURS_PER_YEAR} to get hourly
- If you only find monthly salary, divide by 173 (average hours/month) to get hourly
- Return the HOURLY rate in min_usd and max_usd fields
- Example: $80,000/year ÷ 2080 = $38.46/hour
"""

    # Annual salary guidance
    if country == "Brazil":
        return f"""
BRAZIL SALARY HANDLING (CRITICAL):
- Brazilian salaries are typically quoted as MONTHLY (mensal), not annual
- Common format: "R$ 5.000" or "R$ 8.000 - R$ 15.000" - these are MONTHLY
- Brazil has 13th month salary (décimo terceiro)
- CONVERSION: Monthly × 13 = Annual in BRL, then ÷ 5 = USD
- Example: R$ 8.000/month × 13 = R$ 104.000/year ÷ 5 = $20,800 USD/year
- If source says "por mês", "mensal", "CLT" without "/year", it's MONTHLY
- Typical Software Engineer range: R$ 5.000-25.000/month = $13,000-65,000 USD/year
"""
    elif country == "India":
        return f"""
INDIA SALARY HANDLING (CRITICAL):
- Indian salaries often use "LPA" (Lakhs Per Annum) - this IS annual
- 1 Lakh = 100,000 INR
- "10 LPA" = 10,00,000 INR/year = ~$12,000 USD/year
- If monthly, multiply by 12
- Current rate: ~83 INR = 1 USD
- Typical Software Engineer range: 5-30 LPA = $6,000-36,000 USD/year
"""
    elif country == "Mexico":
        return f"""
MEXICO SALARY HANDLING (CRITICAL):
- Mexican salaries are often quoted MONTHLY
- Look for "mensual", "al mes", "/mes" = MONTHLY
- Look for "anual", "al año" = ANNUAL
- If unclear, assume MONTHLY and multiply by 12
- Current rate: ~17 MXN = 1 USD
- Example: MXN 30,000/month × 12 = MXN 360,000/year ÷ 17 = $21,176 USD/year
"""
    elif country == "Japan":
        return f"""
JAPAN SALARY HANDLING:
- Japanese salaries can be monthly (月給) or annual (年収)
- Look for 万 (man) = 10,000 yen
- "月給30万" = 300,000 yen/month × 12 = 3,600,000 yen/year
- Current rate: ~150 JPY = 1 USD
- Example: ¥5,000,000/year ÷ 150 = $33,333 USD/year
"""
    elif country in ["Germany", "France", "Spain", "United Kingdom"]:
        return f"""
EUROPEAN SALARY HANDLING:
- Most European salaries are quoted ANNUALLY (gross)
- Look for "pro Jahr", "per year", "annual", "brutto" = ANNUAL
- Look for "pro Monat", "monthly" = MONTHLY (multiply by 12)
- Spain often has 14 payments/year (multiply monthly by 14)
- EUR to USD: multiply by ~1.08
- GBP to USD: multiply by ~1.26
"""
    else:
        return f"""
SALARY PERIOD HANDLING:
- Default assumption for {country}: {default_period} salary
- If monthly: multiply by {months} to get annual
- Convert to USD using current exchange rates
- Look for period indicators: "/year", "annual", "p.a." vs "/month", "monthly"
"""


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
    """Use AI to extract and normalize salary data from search results."""
    openai_key = require_secret_or_env("OPENAI_API_KEY")
    pay_type = rate_type_to_pay_type(rate_type)

    meta = get_country_metadata(country)
    local_currency = meta.get("currency", "USD")

    location_bits = [b for b in [city, state, country] if b]
    loc = ", ".join(location_bits) if location_bits else country

    # Get experience level
    effective_exp = experience_level.strip()
    if not effective_exp:
        effective_exp = extract_experience_from_job_desc(job_desc) or ""

    exp_normalized, exp_description = normalize_experience_level(effective_exp)

    # Experience section
    if effective_exp:
        exp_section = f"""
EXPERIENCE LEVEL (MUST ADJUST SALARY):
- Specified: "{effective_exp}"
- Category: {exp_normalized.upper()} - {exp_description}

ADJUSTMENT RULES:
- ENTRY/JUNIOR: Use lower 25th percentile
- MID-LEVEL: Use median/middle
- SENIOR: Use upper 75th percentile  
- PRINCIPAL/STAFF: Use top of range + 15-25%
"""
    else:
        exp_section = """
EXPERIENCE LEVEL: Not specified - use MID-LEVEL (median values)
"""

    # Requirements
    requirements = extract_key_requirements(job_desc)
    req_line = f'- Skills: {", ".join(requirements[:8])}' if requirements else ''

    # Source list
    lines = []
    for c in candidates[:MAX_CANDIDATES_FOR_AI]:
        lines.append(f'- {c["url"]}\n  title: {c.get("title","")}\n  snippet: {c.get("snippet","")}')
    url_block = "\n".join(lines) if lines else "- (no sources found)"

    # Get salary period guidance
    period_guidance = get_salary_period_guidance(country, pay_type)

    # Build the prompt
    output_unit = "HOURLY rate" if pay_type == "HOURLY" else "ANNUAL salary"
    
    prompt = f"""You are a salary analyst. Extract salary data from web search results.

JOB: "{job_title}"
LOCATION: "{loc}"
LOCAL CURRENCY: {local_currency}
REQUESTED OUTPUT: {output_unit} in USD
{req_line}

{exp_section}

{period_guidance}

CURRENCY CONVERSION (to USD):
- BRL: ÷ 5.0
- EUR: × 1.08
- GBP: × 1.26
- INR: ÷ 83
- MXN: ÷ 17
- JPY: ÷ 150
- AUD: × 0.65
- CAD: × 0.74
- PHP: ÷ 56

SOURCES:
{url_block}

TASK:
1. Find salary numbers in the sources above
2. Determine if each is hourly, monthly, or annual
3. Convert everything to {output_unit} in USD
4. Adjust for {exp_normalized} experience level

OUTPUT JSON (no markdown):
{{
  "min_usd": <number - {output_unit} in USD>,
  "max_usd": <number - {output_unit} in USD>,
  "pay_type": "{pay_type}",
  "conversion_notes": "<explain what you found and how you converted>",
  "sources": [
    {{
      "url": "<url>",
      "range_tag": "Min"|"Max"|"General",
      "strength": <0-100>,
      "original_value": "<exact value found, e.g. 'R$ 8.000/month'>",
      "converted_usd": <final {output_unit} USD>
    }}
  ],
  "sources_used": ["<urls>"],
  "min_links": ["<urls for minimum>"],
  "max_links": ["<urls for maximum>"]
}}

SANITY CHECK:
- {"Hourly rates typically: $10-$300/hour for professional roles" if pay_type == "HOURLY" else "Annual salaries typically: $15,000-$500,000 for professional roles"}
- If your result seems too low, you probably have monthly values - convert to annual first!
- Brazil mid-level engineer: {"$10-40/hour" if pay_type == "HOURLY" else "$20,000-50,000/year"}
- USA mid-level engineer: {"$40-80/hour" if pay_type == "HOURLY" else "$80,000-150,000/year"}
""".strip()

    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}

    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 2500
    }

    resp = http_post("https://api.openai.com/v1/chat/completions", json_body=payload, timeout=60, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    text_out = ""
    choices = data.get("choices", [])
    if choices:
        text_out = choices[0].get("message", {}).get("content", "")

    text_out = (text_out or "").strip()
    if not text_out:
        raise RuntimeError("OpenAI returned an empty response.")

    raw_ai_response = text_out

    # Clean markdown formatting
    if text_out.startswith("```"):
        text_out = re.sub(r'^```(?:json)?\s*', '', text_out)
        text_out = re.sub(r'\s*```$', '', text_out)

    try:
        parsed = json.loads(text_out)
    except Exception:
        m = re.search(r"\{.*\}", text_out, re.S)
        if not m:
            raise RuntimeError(f"Invalid JSON from AI: {text_out[:500]}")
        parsed = json.loads(m.group(0))

    pay_type_out = str(parsed.get("pay_type") or pay_type).upper()
    if pay_type_out not in ("HOURLY", "ANNUAL"):
        pay_type_out = pay_type

    min_usd = parse_number_like(parsed.get("min_usd"))
    max_usd = parse_number_like(parsed.get("max_usd"))

    if min_usd is None or max_usd is None:
        raise RuntimeError(f"Invalid values from AI: min={parsed.get('min_usd')}, max={parsed.get('max_usd')}")

    if min_usd <= 0 or max_usd <= 0:
        raise RuntimeError(f"Zero/negative values: min={min_usd}, max={max_usd}")

    # Sanity check and auto-correct
    if pay_type_out == "ANNUAL":
        # Annual salary sanity check
        if max_usd < 10000:
            # Suspiciously low - probably monthly values, multiply by 12
            min_usd = min_usd * 12
            max_usd = max_usd * 12
        elif max_usd < 15000 and country in ["United States", "United Kingdom", "Germany", "Canada", "Australia"]:
            # Still too low for developed countries
            min_usd = min_usd * 12
            max_usd = max_usd * 12
    elif pay_type_out == "HOURLY":
        # Hourly rate sanity check
        if max_usd > 500:
            # Probably annual values, convert to hourly
            min_usd = min_usd / HOURS_PER_YEAR
            max_usd = max_usd / HOURS_PER_YEAR
        elif max_usd < 1 and min_usd < 1:
            # Probably some weird format, try multiplying
            min_usd = min_usd * 100
            max_usd = max_usd * 100

    original_min = min_usd
    original_max = max_usd

    min_usd, max_usd = clamp_min_max(float(min_usd), float(max_usd), pay_type_out)

    if min_usd == 0 and max_usd == 0:
        raise RuntimeError(f"Invalid final values (min={original_min}, max={original_max})")

    # Process sources
    urls = [c["url"] for c in candidates]
    cand_set = set(urls)

    def only_candidates(xs: Any) -> List[str]:
        xs2 = clean_urls(xs)
        return [u for u in xs2 if u in cand_set and not is_blocked_source(u)]

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
            strength_num = float(strength_raw) if isinstance(strength_raw, (int, float)) else DEFAULT_STRENGTH_SCORE
            strength_int = int(max(0, min(100, round(strength_num) + reliability_boost(url))))

            scored_sources.append({"url": url, "range_tag": range_tag, "strength": strength_int})

    # Dedupe sources
    best_src: Dict[str, Dict[str, Any]] = {}
    for s in scored_sources:
        u = s["url"]
        if u not in best_src or s["strength"] > best_src[u]["strength"]:
            best_src[u] = s

    dedup_scored = sorted(best_src.values(), key=lambda x: x.get("strength", 0), reverse=True)

    return {
        "min_usd": int(round(min_usd)),
        "max_usd": int(round(max_usd)),
        "pay_type": pay_type_out,
        "sources_used": sources_used,
        "min_links": min_links,
        "max_links": max_links,
        "scored_sources": dedup_scored,
        "conversion_notes": parsed.get("conversion_notes", ""),
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
        "uploaded_file_key": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


def on_country_change():
    st.session_state["state"] = ""
    st.session_state["city"] = ""
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
    st.text_input(
        "Experience Level (optional)",
        key="experience_level",
        placeholder="e.g., Senior, 5+ years, Entry-level, Junior"
    )
    st.text_area(
        "Job Description (optional)",
        key="job_desc",
        placeholder="Paste job description to extract skills and experience requirements...",
        height=130
    )

    uploaded = st.file_uploader("Upload Job Description (optional)", type=["txt"], accept_multiple_files=False)
    if uploaded is not None:
        file_key = f"uploaded_{uploaded.name}_{uploaded.size}"
        if st.session_state.get("uploaded_file_key") != file_key:
            try:
                text = uploaded.read().decode("utf-8", errors="ignore")
                st.session_state["job_desc"] = text
                st.session_state["uploaded_file_key"] = file_key
            except Exception:
                pass

    try:
        countries = get_country_list()
    except Exception:
        countries = []

    if not countries:
        st.error("Could not load country list. Check your internet connection.")
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
            options=["Salary (Annual)", "Hourly"],
            index=0 if st.session_state["rate_type"] == "salary" else 1,
            horizontal=True,
            key="rate_type_radio",
        )
        st.session_state["rate_type"] = "hourly" if rate_type_label == "Hourly" else "salary"

    fx_rates = get_fx_table_usd()
    currency_codes = sorted(fx_rates.keys())
    st.selectbox(
        "Display Currency *",
        options=currency_codes,
        index=currency_codes.index(st.session_state["currency"]) if st.session_state["currency"] in currency_codes else currency_codes.index("USD"),
        key="currency",
    )

    def is_valid() -> Tuple[bool, str]:
        if not (st.session_state["job_title"] or "").strip():
            return False, "Job Title is required."
        if not (st.session_state["country"] or "").strip():
            return False, "Country is required."
        if st.session_state["country"] == "(unavailable)":
            return False, "Country list is unavailable."
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
    candidates = []

    with st.spinner("Searching salary data sources..."):
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
                job_title, country, state, city, rate_type,
                job_desc=job_desc, experience_level=experience_level,
            )

            if not candidates:
                st.warning(f"No salary sources found for {job_title} in {country}. Try adjusting your search.")
                st.session_state["last_result"] = None
            else:
                with st.spinner(f"Analyzing {len(candidates)} sources..."):
                    result = openai_estimate(
                        job_title, job_desc, experience_level,
                        country, state, city, rate_type, candidates,
                    )

                min_usd = float(result["min_usd"])
                max_usd = float(result["max_usd"])
                pay_type = str(result.get("pay_type", rate_type_to_pay_type(rate_type))).upper()

                # Convert to display currency
                min_disp = min_usd
                max_disp = max_usd
                if currency.upper() != "USD":
                    min_disp = convert_from_usd(min_usd, currency)
                    max_disp = convert_from_usd(max_usd, currency)

                # Build source display data
                cand_map: Dict[str, Dict[str, Any]] = {c["url"]: c for c in candidates}
                scored = result.get("scored_sources") or []
                score_map: Dict[str, int] = {}
                tag_map: Dict[str, str] = {}
                for item in scored:
                    if isinstance(item, dict) and isinstance(item.get("url"), str):
                        u = item["url"].strip()
                        if u:
                            score_map[u] = int(item.get("strength", DEFAULT_STRENGTH_SCORE))
                            tag_map[u] = str(item.get("range_tag", "General"))

                sources: List[Dict[str, Any]] = []
                min_links = result.get("min_links") or []
                max_links = result.get("max_links") or []
                sources_used = result.get("sources_used") or []

                def add_source(u: str, rng: str):
                    if any(s["url"] == u for s in sources):
                        return
                    host, slug = pretty_url_label(u)
                    title = f"{host} — {slug}" if slug else host
                    strength = int(score_map.get(u, DEFAULT_STRENGTH_SCORE))
                    strength = int(max(0, min(100, strength + reliability_boost(u))))
                    geo = str(cand_map.get(u, {}).get("geo_tag", "Nearby/Unclear"))
                    sources.append({"title": title, "url": u, "range": rng, "strength": strength, "geo": geo})

                rate_label = "Hourly" if pay_type == "HOURLY" else "Annual"
                for u in min_links:
                    add_source(u, f"Min ({rate_label})")
                for u in max_links:
                    add_source(u, f"Max ({rate_label})")

                # Add more sources if needed
                if len(sources) < 5:
                    for item in scored:
                        u = item.get("url")
                        if isinstance(u, str) and u.startswith("http") and not is_blocked_source(u):
                            tag = tag_map.get(u, "General")
                            rng = f"Min ({rate_label})" if tag == "Min" else f"Max ({rate_label})" if tag == "Max" else "Source"
                            add_source(u, rng)
                            if len(sources) >= MAX_SOURCES_TO_DISPLAY:
                                break

                if len(sources) < 3:
                    for u in sources_used:
                        if not is_blocked_source(u):
                            add_source(u, "Source")
                        if len(sources) >= 10:
                            break

                # Sort by geo match then strength
                sources.sort(
                    key=lambda x: (geo_priority(str(x.get("geo", ""))), int(x.get("strength", 0))),
                    reverse=True,
                )

                st.session_state["last_result"] = {
                    "min": int(round(min_disp)),
                    "max": int(round(max_disp)),
                    "currency": currency.upper(),
                    "rateType": pay_type_to_rate_type(pay_type),
                    "sources": sources[:MAX_SOURCES_TO_DISPLAY],
                    "conversion_notes": result.get("conversion_notes", ""),
                }

        except requests.HTTPError as e:
            st.session_state["last_result"] = None
            st.session_state["debug_last_error"] = repr(e)

            status = None
            try:
                status = e.response.status_code if e.response is not None else None
            except Exception:
                pass

            if status == 401:
                st.error("API authentication failed. Check your OPENAI_API_KEY.")
            else:
                st.error("Something went wrong. Please try again.")

        except Exception as e:
            st.session_state["last_result"] = None
            st.session_state["debug_last_error"] = repr(e)

            error_str = str(e)
            if "zero" in error_str.lower() or "invalid" in error_str.lower():
                st.error("❌ Could not extract valid salary data from search results.")
                st.warning(
                    f"**Suggestions:**\n"
                    f"- Simplify the job title (e.g., 'Software Engineer' instead of 'Senior Full-Stack Engineer III')\n"
                    f"- Try a different location\n"
                    f"- Remove state/city filters"
                )

                if candidates:
                    with st.expander("🔍 Sources found (but no salary data extracted)", expanded=False):
                        for i, c in enumerate(candidates[:10], 1):
                            st.markdown(f"**{i}.** [{c.get('host', 'Unknown')}]({c.get('url', '#')})")
                            st.caption(f"Title: {c.get('title', 'N/A')[:100]}")
                            st.caption(f"Snippet: {c.get('snippet', 'N/A')[:200]}")
                            st.divider()
            else:
                st.error(f"Error: {error_str[:300]}")


# ============================================================
# Render results
# ============================================================
res = st.session_state.get("last_result")
if res:
    unit = "per hour" if res["rateType"] == "hourly" else "per year"
    cur = res["currency"]
    min_v = res["min"]
    max_v = res["max"]

    # Format numbers appropriately
    if res["rateType"] == "hourly":
        min_formatted = f"{min_v:,}"
        max_formatted = f"{max_v:,}"
    else:
        min_formatted = f"{min_v:,}"
        max_formatted = f"{max_v:,}"

    range_html = f"""
    <div class="jr-range">
      <div class="jr-range-top">
        <div style="width:28px;height:28px;border-radius:10px;background:rgba(255,255,255,.16);display:flex;align-items:center;justify-content:center;font-weight:900;">$</div>
        <div class="jr-range-title">Estimated Rate Range</div>
      </div>
      <div class="jr-range-grid">
        <div>
          <p class="jr-range-label">Minimum</p>
          <p class="jr-range-amt">{cur} {min_formatted}</p>
          <p class="jr-range-unit">{unit}</p>
        </div>
        <div class="jr-dash">—</div>
        <div>
          <p class="jr-range-label">Maximum</p>
          <p class="jr-range-amt">{cur} {max_formatted}</p>
          <p class="jr-range-unit">{unit}</p>
        </div>
      </div>
    </div>
    """
    st.markdown(range_html, unsafe_allow_html=True)

    # Show conversion notes if available
    notes = res.get("conversion_notes", "")
    if notes:
        st.caption(f"📊 {notes}")

    sources: List[Dict[str, Any]] = res.get("sources") or []

    with st.container(border=True):
        st.markdown("### Rate Justification Sources")
        st.caption("Sources sorted by location match and reliability.")

        if not sources:
            st.caption("No sources returned for this query.")
        else:
            for s in sources:
                title = html.escape(s.get("title") or "Source")
                url = html.escape(s.get("url") or "", quote=True)
                rng = html.escape(s.get("range") or "Source")
                geo = (s.get("geo") or "Nearby/Unclear").strip()
                geo_label = {"Exact": "Exact", "Country-level": "Country-level"}.get(geo, "Nearby/Unclear")

                try:
                    strength_i = int(max(0, min(100, int(s.get("strength", DEFAULT_STRENGTH_SCORE)))))
                except Exception:
                    strength_i = DEFAULT_STRENGTH_SCORE

                row_html = f"""
                <a class="jr-source" href="{url}" target="_blank" rel="noopener noreferrer">
                  <div class="jr-source-ico">↗</div>
                  <div style="min-width:0; width:100%;">
                    <div class="jr-source-main">{title}</div>
                    <div class="jr-source-sub">
                      <span>Range: {rng}</span>
                      <span class="jr-geo-pill">{geo_label}</span>
                      <span class="jr-score-pill">
                        <span>Strength</span>
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
              <strong>Note:</strong> Salary ranges are estimated from available online data.
              Actual compensation may vary based on company, skills, and negotiation.
            </div>
            """,
            unsafe_allow_html=True,
        )

# Debug section
if st.session_state.get("debug_last_error"):
    with st.expander("Debug details", expanded=False):
        st.code(st.session_state["debug_last_error"])
