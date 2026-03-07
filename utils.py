"""
utils.py — Shared utilities for Job Rate Finder
Constants, FX conversion, currency formatting, geo helpers, statistics, parsing.
"""

from __future__ import annotations

import math
import os
import re
import statistics
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
import streamlit as st

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
MAX_SEARCH_RESULTS = 200         # cast a very wide net
MAX_SOURCES_FOR_AI = 80          # send as many as possible to Claude
MAX_DISPLAYED_SOURCES = 50
HOURS_PER_YEAR = 2080
SERPAPI_URL = "https://serpapi.com/search.json"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-opus-4-6"
COUNTRIESNOW_BASE = "https://countriesnow.space/api/v0.1"

# ─────────────────────────────────────────────
# HTTP session
# ─────────────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "JobRateFinder/3.0"})


def http_get(url: str, params: dict = None, timeout: int = 30) -> requests.Response:
    return SESSION.get(url, params=params, timeout=timeout)


def http_post(url: str, json_body: dict = None, headers: dict = None, timeout: int = 90) -> requests.Response:
    return SESSION.post(url, json=json_body, headers=headers, timeout=timeout)


def secret(name: str) -> str:
    """Retrieve a secret from env vars or Streamlit secrets."""
    v = (os.getenv(name, "") or "").strip()
    if not v:
        try:
            v = str(st.secrets.get(name, "")).strip()
        except Exception:
            pass
    if not v:
        raise RuntimeError(f"Missing secret: {name}")
    return v


# ─────────────────────────────────────────────
# URL / Source helpers
# ─────────────────────────────────────────────
GOOD_HOSTS = {
    "salaryexpert", "levels.fyi", "glassdoor", "indeed", "salary.com",
    "payscale", "linkedin", "ziprecruiter", "builtin", "simplyhired",
    "monster", "comparably", "bls.gov", "totaljobs", "reed",
    "talent.com", "careerbliss", "jobted", "adzuna", "hays",
    "roberthalf", "michaelpage", "randstad", "hired", "wellfound",
    # International salary sites
    "naukri", "ambitionbox", "stepstone", "gehalt", "cadremploi", "infojobs",
    "catho", "vagas", "salario", "occ", "computrabajo", "doda", "openwork",
    "saramin", "jobkorea", "wanted", "zhaopin", "51job", "lagou", "jobstreet",
    "kalibrr", "mycareersfuture", "seek", "nationalevacaturebank", "pracuj",
    "wynagrodzenia", "bayt", "naukrigulf", "pnet", "careers24", "lohncheck",
    "irishjobs", "drushim",
}

BAD_HOSTS = {
    "pinterest", "facebook", "instagram", "tiktok", "youtube",
    "reddit", "quora", "wikipedia", "github", "twitter", "x.com",
    "medium.com", "blog",
}


def host_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").replace("www.", "").lower()
    except Exception:
        return ""


def is_blocked(url: str) -> bool:
    h = host_of(url)
    return any(b in h for b in BAD_HOSTS)


def source_quality(url: str) -> int:
    """Score a source 0-100 based on hostname reputation."""
    h = host_of(url)
    if any(g in h for g in GOOD_HOSTS):
        return 85
    return 50


def pretty_host(url: str) -> str:
    h = host_of(url)
    return h or "source"


# ─────────────────────────────────────────────
# Country metadata
# ─────────────────────────────────────────────
COUNTRY_META = {
    "United States":  {"currency": "USD", "fx": 1.00,  "default_period": "annual"},
    "United Kingdom": {"currency": "GBP", "fx": 0.79,  "default_period": "annual"},
    "Canada":         {"currency": "CAD", "fx": 1.36,  "default_period": "annual"},
    "Australia":      {"currency": "AUD", "fx": 1.53,  "default_period": "annual"},
    "Germany":        {"currency": "EUR", "fx": 0.92,  "default_period": "annual"},
    "France":         {"currency": "EUR", "fx": 0.92,  "default_period": "annual"},
    "Spain":          {"currency": "EUR", "fx": 0.92,  "default_period": "annual"},
    "Italy":          {"currency": "EUR", "fx": 0.92,  "default_period": "annual"},
    "Brazil":         {"currency": "BRL", "fx": 5.00,  "default_period": "monthly"},
    "Mexico":         {"currency": "MXN", "fx": 17.0,  "default_period": "monthly"},
    "India":          {"currency": "INR", "fx": 83.0,  "default_period": "annual"},
    "Japan":          {"currency": "JPY", "fx": 150.0, "default_period": "monthly"},
    "Philippines":    {"currency": "PHP", "fx": 56.0,  "default_period": "monthly"},
    "Singapore":      {"currency": "SGD", "fx": 1.34,  "default_period": "annual"},
    "Netherlands":    {"currency": "EUR", "fx": 0.92,  "default_period": "annual"},
    "Sweden":         {"currency": "SEK", "fx": 10.4,  "default_period": "annual"},
    "Switzerland":    {"currency": "CHF", "fx": 0.88,  "default_period": "annual"},
    "Ireland":        {"currency": "EUR", "fx": 0.92,  "default_period": "annual"},
    "New Zealand":    {"currency": "NZD", "fx": 1.63,  "default_period": "annual"},
    "South Korea":    {"currency": "KRW", "fx": 1320,  "default_period": "annual"},
    "China":          {"currency": "CNY", "fx": 7.24,  "default_period": "monthly"},
    "UAE":            {"currency": "AED", "fx": 3.67,  "default_period": "monthly"},
    "Saudi Arabia":   {"currency": "SAR", "fx": 3.75,  "default_period": "monthly"},
    "South Africa":   {"currency": "ZAR", "fx": 18.5,  "default_period": "annual"},
    "Poland":         {"currency": "PLN", "fx": 4.05,  "default_period": "annual"},
    "Israel":         {"currency": "ILS", "fx": 3.65,  "default_period": "annual"},
}

# Maps country names to SerpAPI geo params (gl, hl)
COUNTRY_CODES: Dict[str, tuple] = {
    "United States":  ("us", "en"), "United Kingdom": ("gb", "en"), "Canada":       ("ca", "en"),
    "Australia":      ("au", "en"), "Germany":        ("de", "de"), "France":       ("fr", "fr"),
    "Spain":          ("es", "es"), "Italy":          ("it", "it"), "Brazil":       ("br", "pt"),
    "Mexico":         ("mx", "es"), "India":          ("in", "en"), "Japan":        ("jp", "ja"),
    "Philippines":    ("ph", "en"), "Singapore":      ("sg", "en"), "Netherlands":  ("nl", "nl"),
    "Sweden":         ("se", "sv"), "Switzerland":    ("ch", "de"), "Ireland":      ("ie", "en"),
    "New Zealand":    ("nz", "en"), "South Korea":    ("kr", "ko"), "China":        ("cn", "zh"),
    "UAE":            ("ae", "ar"), "Saudi Arabia":   ("sa", "ar"), "South Africa": ("za", "en"),
    "Poland":         ("pl", "pl"), "Israel":         ("il", "he"),
}


def get_country_codes(country: str) -> tuple:
    return COUNTRY_CODES.get(country, ("", "en"))


# Per-country local salary databases
COUNTRY_SALARY_SITES: Dict[str, List[str]] = {
    "Brazil":         ["catho.com.br", "vagas.com.br", "glassdoor.com.br", "salario.com.br", "infojobs.com.br"],
    "Mexico":         ["occ.com.mx", "computrabajo.com.mx", "glassdoor.com.mx", "indeed.com.mx"],
    "India":          ["naukri.com", "glassdoor.co.in", "ambitionbox.com", "shine.com"],
    "Germany":        ["stepstone.de", "gehalt.de", "glassdoor.de", "xing.com"],
    "France":         ["cadremploi.fr", "glassdoor.fr", "indeed.fr", "monster.fr"],
    "Spain":          ["infojobs.net", "glassdoor.es", "indeed.es"],
    "Italy":          ["glassdoor.it", "indeed.it", "monster.it"],
    "Japan":          ["doda.jp", "glassdoor.jp", "indeed.co.jp", "openwork.jp"],
    "South Korea":    ["saramin.co.kr", "jobkorea.co.kr", "wanted.co.kr"],
    "China":          ["zhaopin.com", "51job.com", "lagou.com"],
    "Philippines":    ["jobstreet.com.ph", "kalibrr.com", "indeed.com.ph"],
    "Singapore":      ["jobstreet.com.sg", "glassdoor.sg", "mycareersfuture.gov.sg"],
    "Australia":      ["seek.com.au", "glassdoor.com.au", "indeed.com.au"],
    "United Kingdom": ["totaljobs.com", "reed.co.uk", "glassdoor.co.uk", "adzuna.co.uk"],
    "Canada":         ["glassdoor.ca", "indeed.ca", "jobbank.gc.ca"],
    "Netherlands":    ["glassdoor.nl", "indeed.nl", "nationalevacaturebank.nl"],
    "Sweden":         ["glassdoor.se", "indeed.se", "monster.se"],
    "Poland":         ["pracuj.pl", "glassdoor.pl", "wynagrodzenia.pl"],
    "UAE":            ["bayt.com", "glassdoor.ae", "naukrigulf.com"],
    "Saudi Arabia":   ["bayt.com", "naukrigulf.com", "indeed.com.sa"],
    "South Africa":   ["pnet.co.za", "glassdoor.co.za", "careers24.com"],
    "Switzerland":    ["jobs.ch", "glassdoor.ch", "lohncheck.ch"],
    "Ireland":        ["irishjobs.ie", "glassdoor.ie", "indeed.ie"],
    "New Zealand":    ["seek.co.nz", "glassdoor.co.nz", "indeed.co.nz"],
    "Israel":         ["glassdoor.com", "indeed.co.il", "drushim.co.il"],
}

# Local-language search templates for Latin-script countries
COUNTRY_LOCAL_QUERIES: Dict[str, List[str]] = {
    "Brazil":      ["{job} salário mensal Brasil", "{job} remuneração média Brasil"],
    "Mexico":      ["{job} sueldo Mexico", "cuanto gana {job} Mexico"],
    "Germany":     ["{job} Gehalt Deutschland", "{job} Vergütung Deutschland"],
    "France":      ["{job} salaire France"],
    "Spain":       ["{job} sueldo España"],
    "Italy":       ["{job} stipendio Italia"],
    "Netherlands": ["{job} salaris Nederland"],
    "Sweden":      ["{job} lön Sverige"],
    "Poland":      ["{job} wynagrodzenie Polska"],
}


def get_meta(country: str) -> Dict[str, Any]:
    base = dict(COUNTRY_META.get(country, {"currency": "USD", "fx": 1.0, "default_period": "annual"}))
    currency = base["currency"]
    if currency == "USD":
        return base
    live_rates = get_fx()
    # Only override if we got real multi-currency data (not the {"USD":1.0} fallback)
    if len(live_rates) > 1 and currency in live_rates:
        base["fx"] = live_rates[currency]
    return base


# ─────────────────────────────────────────────
# FX
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_fx() -> Dict[str, float]:
    try:
        r = http_get("https://open.er-api.com/v6/latest/USD")
        r.raise_for_status()
        return {
            k.upper(): float(v)
            for k, v in (r.json().get("rates") or {}).items()
            if isinstance(v, (int, float)) and v > 0
        }
    except Exception:
        return {"USD": 1.0}


def to_currency(usd: float, target: str) -> float:
    if target == "USD":
        return usd
    rates = get_fx()
    return usd * rates.get(target, 1.0)


# ─────────────────────────────────────────────
# Geo data
# ─────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def get_countries() -> List[str]:
    try:
        r = http_get(f"{COUNTRIESNOW_BASE}/countries")
        r.raise_for_status()
        return sorted(
            {c["country"].strip() for c in (r.json().get("data") or []) if c.get("country")},
            key=str.lower,
        )
    except Exception:
        return [
            "United States", "United Kingdom", "Canada", "Australia",
            "Germany", "France", "India", "Netherlands", "Singapore",
            "Japan", "Brazil", "Mexico",
        ]


@st.cache_data(ttl=86400, show_spinner=False)
def get_states(country: str) -> List[str]:
    if not country:
        return []
    try:
        r = SESSION.post(f"{COUNTRIESNOW_BASE}/countries/states", json={"country": country}, timeout=20)
        if not r.ok:
            return []
        return sorted(
            {s["name"].strip() for s in ((r.json().get("data") or {}).get("states") or []) if s.get("name")},
            key=str.lower,
        )
    except Exception:
        return []


@st.cache_data(ttl=86400, show_spinner=False)
def get_cities(country: str, state: str) -> List[str]:
    if not country:
        return []
    try:
        if state:
            r = SESSION.post(
                f"{COUNTRIESNOW_BASE}/countries/state/cities",
                json={"country": country, "state": state},
                timeout=20,
            )
        else:
            r = SESSION.post(
                f"{COUNTRIESNOW_BASE}/countries/cities",
                json={"country": country},
                timeout=20,
            )
        if not r.ok:
            return []
        return sorted(
            {c.strip() for c in (r.json().get("data") or []) if isinstance(c, str) and c.strip()},
            key=str.lower,
        )
    except Exception:
        return []


# ─────────────────────────────────────────────
# Parsing helpers
# ─────────────────────────────────────────────
def parse_num(x: Any) -> Optional[float]:
    """Parse a number from various formats (int, float, string with K/M suffixes)."""
    if isinstance(x, (int, float)) and math.isfinite(x) and x > 0:
        return float(x)
    if not isinstance(x, str):
        return None
    x = x.replace(",", "").replace("$", "").replace("€", "").replace("£", "").strip()
    m = re.search(r"([\d]+(?:\.\d+)?)\s*([kKmM])?", x)
    if not m:
        return None
    n = float(m.group(1))
    suf = (m.group(2) or "").lower()
    if suf == "k":
        n *= 1_000
    elif suf == "m":
        n *= 1_000_000
    return n if math.isfinite(n) and n > 0 else None


# ─────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────
def display_money(annual_usd: float, currency: str, rate_type: str) -> str:
    val = to_currency(annual_usd, currency)
    if rate_type == "hourly":
        return f"{val / HOURS_PER_YEAR:,.2f}"
    return f"{int(round(val)):,}"


def display_unit(rate_type: str, currency: str) -> str:
    return f"{currency}/hr" if rate_type == "hourly" else f"{currency}/yr"


# ─────────────────────────────────────────────
# Statistics
# ─────────────────────────────────────────────
def _pct_idx(p: float, n: int) -> int:
    """
    Return the 0-based array index for the p-th percentile (0.0–1.0) of n values.
    Uses round(p * (n-1)) — the standard nearest-rank formula for 0-based arrays.
    Clamps to [0, n-1].
    """
    return max(0, min(n - 1, round(p * (n - 1))))


def compute_stats(
    data_table: List[Dict],
    ai_min: Optional[float] = None,
    ai_max: Optional[float] = None,
    sigma1_table: Optional[List[Dict]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Compute empirical percentile sigma ranges from a data_table (List[Dict]).

    Each row must have an "annual_usd" key. Two-pass outlier removal:
      1. Standard IQR (1.5×) to remove extreme statistical outliers.
      2. AI-range sanity check: if Claude gave a recommended range, also remove
         points that are > 3× the AI max or < 1/4 the AI min — these are almost
         certainly wrong-country or wrong-job data that slipped through.

    sigma1 (Typical, ~68%): computed from sigma1_table if provided and large enough
      (≥4 rows), otherwise falls back to the full cleaned dataset. This allows
      callers to pass location-specific data for sigma1 while sigma2 uses all data.

    sigma2 (Full Range, ~95%): always computed from the full cleaned dataset.

    Sigma boundaries are actual observed list values (percentile-indexed), NOT
    stdev-derived. Returns None if fewer than 2 values survive filtering.
    """
    values = [
        float(row["annual_usd"])
        for row in data_table
        if isinstance(row.get("annual_usd"), (int, float)) and row["annual_usd"] > 0
    ]

    if len(values) < 2:
        return None

    count_raw = len(values)
    sorted_vals = sorted(values)

    # ── Pass 1: IQR-based outlier removal (standard 1.5×) ──
    n = len(sorted_vals)
    if n >= 5:
        q1 = sorted_vals[_pct_idx(0.25, n)]
        q3 = sorted_vals[_pct_idx(0.75, n)]
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        filtered = [v for v in sorted_vals if lower_fence <= v <= upper_fence]
        if len(filtered) >= 2:
            sorted_vals = filtered

    # ── Pass 2: AI-range sanity check ──
    # Generous bounds (0.25× AI min → 3× AI max) catch wrong-country/job data
    # that IQR alone can't detect (e.g., nationwide US data in a Brazil search).
    if ai_min and ai_max and ai_min > 0 and ai_max > 0:
        sanity_lo = ai_min * 0.25
        sanity_hi = ai_max * 3.0
        sanity_filtered = [v for v in sorted_vals if sanity_lo <= v <= sanity_hi]
        if len(sanity_filtered) >= 2:
            sorted_vals = sanity_filtered

    if len(sorted_vals) < 2:
        return None

    n = len(sorted_vals)
    mean   = statistics.mean(sorted_vals)
    median = statistics.median(sorted_vals)

    # ── sigma1: use location-specific subset if available and sufficient ──
    # This makes sigma1 (Typical) represent the location the user asked for,
    # not a blend of nationwide + local data.
    s1_candidates = (
        [float(r["annual_usd"]) for r in (sigma1_table or [])
         if isinstance(r.get("annual_usd"), (int, float)) and r["annual_usd"] > 0]
    )
    # Also run the same outlier filters on the sigma1 subset for consistency
    if len(s1_candidates) >= 4:
        s1_sorted = sorted(s1_candidates)
        # Apply AI sanity bounds to sigma1 subset too
        if ai_min and ai_max and ai_min > 0 and ai_max > 0:
            s1_sorted = [v for v in s1_sorted if (ai_min * 0.25) <= v <= (ai_max * 3.0)] or s1_sorted
        s1_vals = s1_sorted if len(s1_sorted) >= 2 else sorted_vals
    else:
        s1_vals = sorted_vals

    s1_n = len(s1_vals)

    # ── Empirical percentile sigma bands (correct nearest-rank formula) ──
    sigma1_lo = s1_vals[_pct_idx(0.16, s1_n)]
    sigma1_hi = s1_vals[_pct_idx(0.84, s1_n)]

    sigma2_lo = sorted_vals[_pct_idx(0.025, n)]
    sigma2_hi = sorted_vals[_pct_idx(0.975, n)]

    sigma3_lo = sorted_vals[0]
    sigma3_hi = sorted_vals[-1]

    def _count_in(vals, lo, hi):
        return sum(1 for v in vals if lo <= v <= hi)

    return {
        "mean": mean,
        "median": median,
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
        "count": n,
        "count_raw": count_raw,
        "sigma1": (sigma1_lo, sigma1_hi),
        "sigma2": (sigma2_lo, sigma2_hi),
        "sigma3": (sigma3_lo, sigma3_hi),
        "sigma1_count": _count_in(s1_vals, sigma1_lo, sigma1_hi),
        "sigma2_count": _count_in(sorted_vals, sigma2_lo, sigma2_hi),
        "sigma3_count": n,
        # Expose whether sigma1 came from a location-specific subset
        "sigma1_location_specific": len(s1_candidates) >= 4,
    }


