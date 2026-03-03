"""
site_planner.py — Agent 1: Search plan generator
Uses Claude Haiku to analyse job+location and produce a targeted SearchPlan dict.
Falls back to _default_plan() on any failure.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

from utils import (
    ANTHROPIC_URL,
    COUNTRY_META,
    COUNTRY_SALARY_SITES,
    http_post,
    secret,
)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Fallback salary sites used when Haiku call fails (mirrors SALARY_SITES in search.py,
# kept here explicitly to avoid a circular import)
PLANNER_DEFAULT_SITES: List[str] = [
    "glassdoor.com",
    "indeed.com",
    "payscale.com",
    "salary.com",
    "levels.fyi",
    "ziprecruiter.com",
    "builtin.com",
    "comparably.com",
    "talent.com",
    "simplyhired.com",
    "careerbliss.com",
    "salaryexpert.com",
]

_PLANNER_SYSTEM = (
    "You are a compensation research strategist. "
    "Return ONLY valid JSON — no markdown, no commentary."
)


def _build_planner_prompt(
    job: str, country: str, state: str, city: str, exp_years: str
) -> str:
    location = ", ".join(x for x in [city, state, country] if x)
    exp_note = f" with {exp_years} experience" if exp_years.strip() else ""
    return f"""Analyse this salary research task and return a JSON search plan.

Job: {job}{exp_note}
Location: {location}

Return ONLY this JSON (no markdown, no extra keys):
{{
  "target_sites": [<15 to 30 ranked domain strings most useful for {country} salary data>],
  "query_strategies": [<5 to 10 query template strings using {{job}} and {{location}} placeholders>],
  "period_hint": "<'annual' or 'monthly' — typical pay reporting period in {country}>",
  "currency": "<ISO currency code for {country}>",
  "market_notes": "<1-2 sentences about data quality / what to watch for when extracting {job} salaries in {country}>"
}}

Rules:
- target_sites: rank highest-quality local salary databases for {country} first
- query_strategies: templates MUST use {{job}} and/or {{location}} placeholders
- period_hint: 'monthly' for Brazil, Mexico, Philippines, Japan, UAE, Saudi Arabia, China; 'annual' otherwise
- currency: correct ISO code (e.g. INR for India, BRL for Brazil, USD for United States)
- market_notes: focus on common pitfalls (currency confusion, monthly vs annual, data freshness)"""


def _default_plan(country: str) -> Dict:
    """Fallback plan built from utils constants — never fails."""
    meta = COUNTRY_META.get(country, {"currency": "USD", "default_period": "annual"})
    period_hint = meta.get("default_period", "annual")
    currency = meta.get("currency", "USD")

    # Combine generic sites + country-specific salary sites
    country_sites = COUNTRY_SALARY_SITES.get(country, [])
    sites = list(dict.fromkeys(PLANNER_DEFAULT_SITES + country_sites))[:30]

    location_placeholder = country
    queries = [
        f'"{{{job}}}" salary {location_placeholder}',
        f'"{{{job}}}" average salary {location_placeholder}',
        f'"{{{job}}}" salary range {location_placeholder}',
        f'"{{{job}}}" compensation {location_placeholder}',
        f'how much does a {{{job}}} make in {location_placeholder}',
    ]
    # Use actual country name in templates
    queries = [
        f'"{{job}}" salary {country}',
        f'"{{job}}" average salary {country}',
        f'"{{job}}" salary range {country}',
        f'"{{job}}" compensation {country}',
        f'how much does a {{job}} make in {country}',
    ]

    return {
        "target_sites": sites,
        "query_strategies": queries,
        "period_hint": period_hint,
        "currency": currency,
        "market_notes": "",
    }


def plan_search(
    job: str,
    country: str,
    state: str = "",
    city: str = "",
    exp_years: str = "",
) -> Dict:
    """
    Call Claude Haiku to generate a targeted search plan for the given job+location.
    Returns a valid SearchPlan dict. NEVER raises — falls back to _default_plan() on any error.
    """
    try:
        key = secret("ANTHROPIC_API_KEY")
        prompt = _build_planner_prompt(job, country, state, city, exp_years)

        resp = http_post(
            ANTHROPIC_URL,
            json_body={
                "model": HAIKU_MODEL,
                "max_tokens": 1024,
                "system": _PLANNER_SYSTEM,
                "messages": [{"role": "user", "content": prompt}],
            },
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=20,
        )
        resp.raise_for_status()

        content = resp.json().get("content") or [{}]
        raw = ""
        for block in content:
            if block.get("type") == "text":
                raw += block.get("text", "")
        raw = raw.strip()

        # Strip markdown fences if model added them despite instructions
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        plan = json.loads(raw)

        # ── Validate required keys ──
        required = {"target_sites", "query_strategies", "period_hint", "currency", "market_notes"}
        if not required.issubset(plan.keys()):
            raise ValueError(f"Missing keys: {required - plan.keys()}")

        # ── Clamp list lengths ──
        plan["target_sites"]     = list(plan["target_sites"])[:30]
        plan["query_strategies"] = list(plan["query_strategies"])[:10]

        # ── Validate period_hint ──
        if plan["period_hint"] not in {"annual", "monthly"}:
            plan["period_hint"] = _default_plan(country)["period_hint"]

        # ── Validate currency ──
        if not isinstance(plan["currency"], str) or not plan["currency"].strip():
            plan["currency"] = _default_plan(country)["currency"]
        else:
            plan["currency"] = plan["currency"].strip().upper()

        return plan

    except Exception:
        return _default_plan(country)
