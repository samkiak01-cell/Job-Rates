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
    try:
        if not country:
            return []
        r = http_post(
            f"{COUNTRIESNOW_BASE}/countries/states",
            json_body={"country": country},
            timeout=25,
        )
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
            r = http_post(
                f"{COUNTRIESNOW_BASE}/countries/cities",
                json_body={"country": country},
                timeout=25,
            )
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


def get_host(url: str) -> str:
    try:
        from urllib.parse import urlparse

        return (urlparse(url).hostname or "").replace("www.", "").lower()
    except Exception:
        return ""


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
# Job description: short hint for search + ranking
# ============================================================
def make_desc_hint(job_desc: str, *, max_chars: int = 90) -> str:
    if not job_desc:
        return ""
    t = job_desc.strip()
    if len(t) < 8:
        return ""
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s\-/&+]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    boiler = {
        "responsibilities", "requirements", "qualification", "qualifications",
        "about", "company", "role", "position", "job", "summary", "overview",
        "benefits", "equal", "opportunity", "employer", "apply", "applying",
    }

    snippet = t[: max_chars * 2]
    words = [w for w in re.split(r"\s+", snippet) if w]
    cleaned_words: List[str] = []
    for w in words:
        lw = w.lower()
        if lw in boiler:
            continue
        if len(w) > 28:
            continue
        cleaned_words.append(w)
        if sum(len(x) + 1 for x in cleaned_words) >= max_chars:
            break

    hint = " ".join(cleaned_words).strip()
    if len(hint) < 8:
        hint = t[:max_chars].strip()

    return hint[:max_chars].strip()


# ============================================================
# Source quality gates (stops irrelevant sources from showing)
# ============================================================
GOOD_DOMAIN_HINTS = [
    "levels.fyi",
    "glassdoor.",
    "indeed.",
    "salary.com",
    "payscale.",
    "builtin.com",
    "ziprecruiter.",
    "linkedin.",
    "monster.",
    "talent.com",
    "hays.",
    "roberthalf.",
    "randstad.",
    "michaelpage.",
]

BAD_DOMAIN_HINTS = [
    "pinterest.",
    "facebook.",
    "instagram.",
    "tiktok.",
    "youtube.",
    "reddit.",          # can be useful, but very often messy for comp justification
    "quora.",
    "medium.",          # too noisy
    "github.",          # not salary
    "wikipedia.",       # not salary
    "slideshare.",
]


def domain_quality_score(url: str) -> int:
    host = get_host(url)
    if not host:
        return 40

    for b in BAD_DOMAIN_HINTS:
        if b in host:
            return 20

    for g in GOOD_DOMAIN_HINTS:
        if g in host:
            return 85

    # default, unknown host
    return 55


def overlaps_range(a_min: float, a_max: float, b_min: float, b_max: float, tol: float = 0.12) -> bool:
    """
    Returns True if ranges overlap with tolerance.
    tol=0.12 means we allow ~12% wiggle room.
    """
    if a_min > a_max:
        a_min, a_max = a_max, a_min
    if b_min > b_max:
        b_min, b_max = b_max, b_min

    # widen the "b" range a bit to avoid over-filtering
    widen = max(1.0, (b_max - b_min) * tol)
    b_min2 = b_min - widen
    b_max2 = b_max + widen

    return not (a_max < b_min2 or a_min > b_max2)


# ============================================================
# AI logic
# ============================================================
def rate_type_to_pay_type(rate_type: str) -> str:
    return "HOURLY" if (rate_type or "").strip().lower() == "hourly" else "ANNUAL"


def pay_type_to_rate_type(pay_type: str) -> str:
    return "hourly" if (pay_type or "").strip().upper() == "HOURLY" else "salary"


def serpapi_search(
    job_title: str,
    job_desc: str,
    country: str,
    state: str,
    city: str,
    rate_type: str,
) -> List[str]:
    serp_key = require_secret_or_env("SERPAPI_API_KEY")

    location_bits = [b for b in [city, state, country] if b]
    loc = ", ".join(location_bits) if location_bits else country

    pay_type = rate_type_to_pay_type(rate_type)
    desc_hint = make_desc_hint(job_desc, max_chars=80)

    hint_block = f' "{desc_hint}"' if desc_hint else ""

    # Bias query toward well-known comp sources without hard restricting.
    # Also add "compensation add-ons" to pull pages that include ranges.
    quality_bias = " (site:levels.fyi OR site:glassdoor.com OR site:salary.com OR site:payscale.com OR site:indeed.com OR site:builtin.com)"
    query = (
        f'{job_title}{hint_block} salary range {loc} '
        f'{"hourly rate" if pay_type=="HOURLY" else "annual salary"}'
        f'{quality_bias}'
    )

    params = {
        "engine": "google",
        "q": query,
        "api_key": serp_key,
        "num": 25,
        # last ~3 months
        "tbs": "qdr:m3",
    }

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

    return out[:22]


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

    url_block = "\n".join(f"- {u}" for u in urls[:20]) if urls else "- (no links found)"

    prompt = f"""
You are estimating compensation ranges from recent job postings/listings and reputable salary pages.

Task:
- Job title: "{job_title}"
- Job description (optional): "{job_desc or ""}"
- Location: "{loc}"
- Pay type: "{pay_type}" (HOURLY means hourly rate; ANNUAL means yearly salary)
- Consider only postings/pages that appear updated/valid within the last ~3 months (best effort).

Use these candidate links ONLY (do not invent new URLs):
{url_block}

Output STRICT JSON only (no markdown, no commentary) in this exact shape:
{{
  "pay_type": "HOURLY"|"ANNUAL",
  "sources": [
    {{
      "url": <one of the candidate urls>,
      "scope": "local"|"national"|"unknown",
      "quoted_min_usd": <number or null>,
      "quoted_max_usd": <number or null>,
      "quoted_point_usd": <number or null>,
      "strength": <integer 0-100>,
      "notes": <short string>
    }}
  ]
}}

Rules:
- Prefer returning 5–8 strong sources if (and only if) 5–8 clearly relevant, reputable sources exist in the candidates.
- Do NOT force a minimum number of sources.
- Only include sources that mention an actual numeric compensation figure/range for this role (or very close title) and this location or clearly-labeled scope.
- If a page only gives a single estimate, put it in quoted_point_usd and leave min/max null.
- If you can’t reliably extract numbers, do not include that source.
- strength is how strong the page is as a compensation source (0-100).
""".strip()

    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
    payload = {"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "input": prompt, "temperature": 0}

    resp = http_post("https://api.openai.com/v1/responses", json_body=payload, timeout=70, headers=headers)
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

    cand_set = set(urls)

    raw_sources = parsed.get("sources")
    if not isinstance(raw_sources, list):
        raw_sources = []

    cleaned_sources: List[Dict[str, Any]] = []
    for item in raw_sources:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not (isinstance(url, str) and url.startswith(("http://", "https://"))):
            continue
        url = url.strip()
        if url not in cand_set:
            # hard block invented URLs
            continue

        scope = str(item.get("scope") or "unknown").strip().lower()
        if scope not in ("local", "national", "unknown"):
            scope = "unknown"

        qmin = parse_number_like(item.get("quoted_min_usd"))
        qmax = parse_number_like(item.get("quoted_max_usd"))
        qpt = parse_number_like(item.get("quoted_point_usd"))

        # Require numeric
        if qmin is None and qmax is None and qpt is None:
            continue

        # Convert point into a narrow range for later overlap checks
        if qpt is not None and (qmin is None and qmax is None):
            qmin = float(qpt) * 0.92
            qmax = float(qpt) * 1.08

        if qmin is None:
            qmin = qmax
        if qmax is None:
            qmax = qmin
        if qmin is None or qmax is None:
            continue

        qmin, qmax = clamp_min_max(float(qmin), float(qmax), pay_type_out)

        strength_raw = item.get("strength")
        strength_num = (
            float(strength_raw)
            if isinstance(strength_raw, (int, float))
            else (parse_number_like(str(strength_raw)) or 55.0)
        )
        strength_i = int(max(0, min(100, round(strength_num))))

        # combine with domain heuristic to reduce random sites
        dq = domain_quality_score(url)
        strength_i = int(round(0.7 * strength_i + 0.3 * dq))

        notes = str(item.get("notes") or "").strip()[:140]

        cleaned_sources.append(
            {
                "url": url,
                "scope": scope,
                "quoted_min_usd": float(qmin),
                "quoted_max_usd": float(qmax),
                "strength": strength_i,
                "notes": notes,
            }
        )

    # dedupe (keep strongest)
    by_url: Dict[str, Dict[str, Any]] = {}
    for s in cleaned_sources:
        u = s["url"]
        if u not in by_url or int(s["strength"]) > int(by_url[u]["strength"]):
            by_url[u] = s
    cleaned_sources = list(by_url.values())

    # Sort: strongest first, prefer local
    cleaned_sources.sort(key=lambda x: (0 if x["scope"] == "local" else 1, -int(x["strength"])))

    # Recompute final range from sources to ensure consistency.
    # Use top 3-8 sources with numbers.
    usable = cleaned_sources[:8]
    mins = [float(s["quoted_min_usd"]) for s in usable]
    maxs = [float(s["quoted_max_usd"]) for s in usable]
    if not mins or not maxs:
        raise RuntimeError("No usable sources with numeric ranges were returned.")

    min_usd = min(mins)
    max_usd = max(maxs)
    min_usd, max_usd = clamp_min_max(min_usd, max_usd, pay_type_out)

    # Enforce: drop sources that do not overlap the computed final range
    filtered: List[Dict[str, Any]] = []
    for s in cleaned_sources:
        if overlaps_range(float(s["quoted_min_usd"]), float(s["quoted_max_usd"]), min_usd, max_usd, tol=0.10):
            filtered.append(s)

    # keep up to 12, but prefer 5-8 if available
    filtered = filtered[:12]

    return {
        "min_usd": int(round(min_usd)),
        "max_usd": int(round(max_usd)),
        "pay_type": pay_type_out,
        "sources": filtered,
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
# Form card
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
        format_func=lambda x: "— Select —" if x == "" else x,
    )

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
            state = (st.session_state["state"] or "").strip()
            city = (st.session_state["city"] or "").strip()
            rate_type = st.session_state["rate_type"]
            currency = st.session_state["currency"]

            urls = serpapi_search(job_title, job_desc, country, state, city, rate_type)
            result = openai_estimate(job_title, job_desc, country, state, city, rate_type, urls)

            min_usd = float(result["min_usd"])
            max_usd = float(result["max_usd"])
            pay_type = str(result.get("pay_type", rate_type_to_pay_type(rate_type))).upper()

            min_disp = min_usd
            max_disp = max_usd
            if currency.upper() != "USD":
                min_disp = convert_from_usd(min_usd, currency)
                max_disp = convert_from_usd(max_usd, currency)

            sources_in = result.get("sources") or []

            # Build UI sources; always consistent with computed min/max.
            sources_ui: List[Dict[str, Any]] = []
            for s in sources_in:
                u = s.get("url") or ""
                if not u:
                    continue
                host, slug = pretty_url_label(u)
                title = f"{host} — {slug}" if slug else host

                strength = int(s.get("strength", domain_quality_score(u)))
                strength = int(max(0, min(100, strength)))

                # Tag what the page supports relative to final range (informational)
                qmin = float(s.get("quoted_min_usd", min_usd))
                qmax = float(s.get("quoted_max_usd", max_usd))
                tag = "Source"
                if abs(qmin - min_usd) <= max(1.0, (max_usd - min_usd) * 0.10):
                    tag = "Min-ish"
                if abs(qmax - max_usd) <= max(1.0, (max_usd - min_usd) * 0.10):
                    tag = "Max-ish"

                sources_ui.append(
                    {
                        "title": title,
                        "url": u,
                        "range": tag,
                        "strength": strength,
                    }
                )

            st.session_state["last_result"] = {
                "min": int(round(min_disp)),
                "max": int(round(max_disp)),
                "currency": currency.upper(),
                "rateType": pay_type_to_rate_type(pay_type),
                "sources": sources_ui[:12],
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
        st.caption("These sources are filtered to ensure they align with the estimated range.")

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
                      <span>Supports: {rng}</span>
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
              <strong>Note:</strong> The range is computed from the returned sources (not independently),
              and sources are filtered to match the range.
            </div>
            """,
            unsafe_allow_html=True,
        )

if st.session_state.get("debug_last_error"):
    with st.expander("Debug details", expanded=False):
        st.code(st.session_state["debug_last_error"])
