"""
ai_extract.py — Claude-powered salary data extraction
Sends search snippets to Claude for structured extraction and analysis.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from utils import (
    ANTHROPIC_URL,
    CLAUDE_MODEL,
    MAX_SOURCES_FOR_AI,
    get_meta,
    http_post,
    parse_num,
    secret,
)


# ─────────────────────────────────────────────
# Prompt construction
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are a compensation data analyst specializing in extracting and normalizing salary data from web search snippets.

YOUR TASK: Extract every salary/compensation data point you can find and return structured JSON.

CRITICAL RULES:
1. Extract ALL data points — do not skip any salary numbers you find.
2. Convert everything to ANNUAL USD. Show your conversion logic.
3. Salary ranges like "$60k–$90k" become TWO data points (60000 and 90000).
4. "Average $75k" becomes ONE data point (75000).
5. Hourly rates → multiply by 2080 for annual.
6. Monthly rates → multiply by 12 for annual.
7. Foreign currency → divide by the exchange rate to get USD.
8. Assign confidence 0.0-1.0 based on source reputation and data specificity.
9. Do NOT invent or hallucinate numbers — only extract what's explicitly stated.
10. If a snippet is irrelevant to the job title, skip it entirely.

Return ONLY valid JSON. No markdown fences. No commentary outside the JSON."""


def _build_source_block(sources: List[Dict]) -> str:
    """Format search results into a numbered source block for the prompt."""
    lines = []
    for i, s in enumerate(sources[:MAX_SOURCES_FOR_AI], 1):
        lines.append(
            f"[SOURCE {i}] {s['host']}\n"
            f"  Title: {s['title']}\n"
            f"  Snippet: {s['snippet']}\n"
        )
    return "\n".join(lines)


def _build_user_prompt(
    job: str,
    country: str,
    state: str,
    city: str,
    exp_years: str,
    rate_type: str,
    job_desc: str,
    sources: List[Dict],
) -> str:
    """Construct the full user prompt for Claude."""

    meta = get_meta(country)
    location = ", ".join(x for x in [city, state, country] if x)
    source_block = _build_source_block(sources)

    # Experience context — informational only, does NOT filter data
    exp_section = ""
    if exp_years.strip():
        exp_section = (
            f"\nTARGET EXPERIENCE: {exp_years}\n"
            f"Use this to weight your recommended range — but still extract ALL data points regardless of level.\n"
        )

    # Job description context — helps Claude understand the role
    jd_section = ""
    if job_desc.strip():
        # Truncate to avoid overwhelming the prompt
        truncated = job_desc.strip()[:1500]
        jd_section = (
            f"\nJOB DESCRIPTION CONTEXT (use to understand role scope, NOT to filter):\n"
            f"{truncated}\n"
        )

    return f"""Extract salary data for: **{job}** in **{location}**
{exp_section}{jd_section}
COUNTRY DEFAULTS:
- Local currency: {meta['currency']}
- Exchange rate: 1 USD = {meta['fx']} {meta['currency']}
- Typical pay period: {meta['default_period']}

─────────────────────────────────
SEARCH RESULTS TO ANALYZE:
─────────────────────────────────
{source_block}

─────────────────────────────────
EXTRACTION INSTRUCTIONS:
─────────────────────────────────

For EACH salary number you find:
1. Note the raw value, its currency, and its period (annual/monthly/hourly)
2. Convert to ANNUAL USD using the exchange rate above
3. Label it with context (role level, location specifics, source type)
4. Rate confidence: 0.9+ for major salary DBs, 0.7 for job postings, 0.5 for estimates/blogs

IMPORTANT:
- Extract EVERYTHING — junior, mid, senior, all levels. The statistical model needs volume.
- Salary ranges "X to Y" → extract BOTH X and Y as separate data points
- "Base salary" and "total compensation" are BOTH valid — label them differently
- Ignore data clearly for a different profession (e.g., nurse salary on a software engineer search)
- If a source gives percentile data (10th, 25th, 50th, 75th, 90th), extract ALL percentiles

After extracting all data points, compute an AI RECOMMENDED RANGE:
- This should represent a realistic offer range for this role + location + experience level
- Weight higher-confidence sources more heavily
- Account for the target experience level if provided
- Be specific — don't just average everything

Return ONLY this JSON structure:
{{
  "data_points": [
    {{
      "value_annual_usd": <number>,
      "source_idx": <1-based source number>,
      "label": "<brief: level, location, data type e.g. 'Senior, base salary, Glassdoor'>",
      "confidence": <0.0 to 1.0>,
      "original_value": "<raw value as found e.g. '$45/hr' or '£55,000/yr'>",
      "conversion_note": "<how you converted e.g. '45 * 2080 = 93600'>"
    }}
  ],
  "ai_recommended_min_usd": <number>,
  "ai_recommended_max_usd": <number>,
  "ai_recommended_mid_usd": <number>,
  "ai_summary": "<3-4 sentence analysis: market overview, confidence level, key factors affecting pay, any notable patterns>",
  "currency_used": "{meta['currency']}",
  "warnings": ["<any data quality issues, e.g. limited data, mixed roles, stale sources>"]
}}"""


# ─────────────────────────────────────────────
# API call + response parsing
# ─────────────────────────────────────────────
def claude_extract(
    job: str,
    country: str,
    state: str,
    city: str,
    exp_years: str,
    rate_type: str,
    job_desc: str,
    sources: List[Dict],
) -> Dict[str, Any]:
    """
    Send search snippets to Claude for structured salary extraction.
    Returns parsed JSON with data_points, ai_recommended range, summary, warnings.
    """
    key = secret("ANTHROPIC_API_KEY")

    user_prompt = _build_user_prompt(
        job=job,
        country=country,
        state=state,
        city=city,
        exp_years=exp_years,
        rate_type=rate_type,
        job_desc=job_desc,
        sources=sources,
    )

    resp = http_post(
        ANTHROPIC_URL,
        json_body={
            "model": CLAUDE_MODEL,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    resp.raise_for_status()

    # Extract text from response
    content = resp.json().get("content") or [{}]
    raw = ""
    for block in content:
        if block.get("type") == "text":
            raw += block.get("text", "")

    raw = raw.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        # Try to find JSON object in the response
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            data = json.loads(match.group())
        else:
            raise RuntimeError(f"Claude returned invalid JSON: {str(e)[:200]}") from e

    return data


# ─────────────────────────────────────────────
# Post-processing
# ─────────────────────────────────────────────
def process_extraction(
    ai_data: Dict[str, Any],
    sources: List[Dict],
) -> tuple[List[float], List[Dict]]:
    """
    Process Claude's extraction output into clean data points.
    Returns (annual_values, data_points_with_source_info).
    """
    raw_points = ai_data.get("data_points") or []
    annual_values: List[float] = []
    enriched_points: List[Dict] = []

    for dp in raw_points:
        v = parse_num(dp.get("value_annual_usd"))
        if not v or v < 3_000:
            # Skip anything below $3k/year — likely a parsing error
            continue
        if v > 5_000_000:
            # Skip anything above $5M/year — likely a parsing error
            continue

        annual_values.append(v)

        # Link back to source
        src_idx = int(dp.get("source_idx", 1)) - 1
        src = sources[src_idx] if 0 <= src_idx < len(sources) else {}

        enriched_points.append({
            "annual_usd": v,
            "label": dp.get("label", ""),
            "confidence": float(dp.get("confidence", 0.7)),
            "original_value": dp.get("original_value", ""),
            "conversion_note": dp.get("conversion_note", ""),
            "url": src.get("url", ""),
            "host": src.get("host", ""),
            "quality": src.get("quality", 50),
        })

    return annual_values, enriched_points
