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
MAX_SEARCH_RESULTS = 50          # cast a wide net
MAX_SOURCES_FOR_AI = 30          # send plenty to Claude
MAX_DISPLAYED_SOURCES = 12
HOURS_PER_YEAR = 2080
SERPAPI_URL = "https://serpapi.com/search.json"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-opus-4-20250514"
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


def get_meta(country: str) -> Dict[str, Any]:
    return COUNTRY_META.get(country, {"currency": "USD", "fx": 1.0, "default_period": "annual"})


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


def fmt_money(n: float, currency: str = "USD", rate_type: str = "salary") -> str:
    if rate_type == "hourly":
        return f"{currency} {n:,.2f}/hr"
    return f"{currency} {int(round(n)):,}/yr"


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
def compute_stats(values: List[float]) -> Optional[Dict[str, Any]]:
    """
    Compute mean, stdev, and sigma ranges from annual USD values.
    Uses IQR-based outlier removal for robustness before computing stats.
    Returns None if fewer than 2 values.
    """
    if len(values) < 2:
        return None

    # Sort for percentile calculations
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    # IQR-based outlier filtering (only if we have enough data)
    if n >= 5:
        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1
        lower_fence = q1 - 2.0 * iqr  # generous 2x IQR to keep more data
        upper_fence = q3 + 2.0 * iqr
        filtered = [v for v in sorted_vals if lower_fence <= v <= upper_fence]
        if len(filtered) >= 2:
            sorted_vals = filtered

    mean = statistics.mean(sorted_vals)

    if len(sorted_vals) >= 3:
        stdev = statistics.stdev(sorted_vals)
    else:
        stdev = abs(sorted_vals[-1] - sorted_vals[0]) / 2

    # Prevent stdev from being 0 (all identical values)
    if stdev < 1:
        stdev = mean * 0.05  # assume 5% spread as minimum

    def clamp_range(lo, hi):
        return max(0, lo), max(0, hi)

    # Median
    if len(sorted_vals) % 2 == 0:
        median = (sorted_vals[len(sorted_vals) // 2 - 1] + sorted_vals[len(sorted_vals) // 2]) / 2
    else:
        median = sorted_vals[len(sorted_vals) // 2]

    return {
        "mean": mean,
        "median": median,
        "stdev": stdev,
        "min": min(sorted_vals),
        "max": max(sorted_vals),
        "count": len(sorted_vals),
        "count_raw": len(values),
        "sigma1": clamp_range(mean - stdev, mean + stdev),
        "sigma2": clamp_range(mean - 2 * stdev, mean + 2 * stdev),
        "sigma3": clamp_range(mean - 3 * stdev, mean + 3 * stdev),
    }


def find_evidence_for_range(lo: float, hi: float, data_points: List[Dict], max_evidence: int = 3) -> List[Dict]:
    """Return up to `max_evidence` data points whose annual_usd falls within [lo, hi]."""
    hits = [dp for dp in data_points if dp.get("annual_usd") and lo <= dp["annual_usd"] <= hi]
    # Sort by confidence descending, then by source quality
    hits.sort(key=lambda d: (d.get("confidence", 0), d.get("quality", 0)), reverse=True)
    return hits[:max_evidence]
