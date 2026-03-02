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

YOUR TASK: Extract salary data points and return structured JSON.

CRITICAL ACCURACY RULES:
1. ONLY extract data for the EXACT job title requested (or very close variants). "Video Editor" and "Film Director" are NOT the same job. "Software Engineer" and "IT Support" are NOT the same job.
2. ONLY extract data for the CORRECT COUNTRY/LOCATION. If the search is for Brazil, ignore any US/UK/etc salary data that crept into results. Pay close attention to currency symbols and context clues.
3. Convert everything to ANNUAL USD. Be precise about currency detection:
   - R$ or BRL = Brazilian Real
   - $ alone near US context = USD
   - £ = GBP
   - € = EUR
   - ¥ = JPY or CNY (determine from context)
4. Salary ranges like "$60k–$90k" → TWO data points (low end and high end).
5. Hourly rates → multiply by 2080 for annual.
6. Monthly rates → multiply by 12 for annual, THEN convert currency to USD.
7. Assign confidence scores honestly:
   - 0.85-1.0: Major salary databases (Glassdoor, Indeed, PayScale, Salary.com, Levels.fyi) with specific data for this exact role+location
   - 0.6-0.84: Job postings with stated salary, or salary sites with approximate/estimated data
   - 0.3-0.59: Blog posts, forums, or data that's tangentially related
   - Below 0.3: Don't include it at all
8. Do NOT extract data that is clearly for a different profession, different country, or a different seniority level disguised as the target role.
9. When in doubt about a conversion or whether data is relevant, SKIP IT. Precision > volume.

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

STEP 1 — FILTER: For each source, determine:
  a) Is this about the correct job title (or a very close variant)?
  b) Is this about the correct country/region?
  c) Does it contain actual salary numbers?
  If ANY answer is NO, skip the entire source.

STEP 2 — EXTRACT: For each valid salary number:
  1. Identify the currency from context (symbols, country mentions, site domain)
  2. Identify the pay period (annual, monthly, hourly, weekly)
  3. Convert to ANNUAL amount in the local currency first
  4. Then convert to USD: divide by {meta['fx']}
  5. Label with context (role variant, data type, source name)

STEP 3 — VALIDATE your extractions:
  - Do the USD values make sense for {country}? A video editor in Brazil earning $100k+ USD is suspicious.
  - Are there data points from the wrong country mixed in? Remove them.
  - Did you accidentally use the wrong exchange rate or pay period? Double-check.

STEP 4 — RECOMMEND a realistic range:
  - Based on ONLY the validated, high-confidence data points
  - Factor in the target experience level if provided
  - The min/max should represent a realistic offer range, NOT statistical extremes
  - The midpoint should be what a typical candidate would expect

Return ONLY this JSON structure:
{{
  "data_points": [
    {{
      "value_annual_usd": <number>,
      "source_idx": <1-based source number>,
      "label": "<brief: level, location, data type e.g. 'Senior, base salary, Glassdoor'>",
      "confidence": <0.3 to 1.0>,
      "original_value": "<raw value as found e.g. 'R$ 5,000/month' or '$45/hr'>",
      "conversion_note": "<step by step: 'R$ 5000/mo × 12 = R$ 60000/yr ÷ 5.0 = $12,000 USD'>"
    }}
  ],
  "ai_recommended_min_usd": <number>,
  "ai_recommended_max_usd": <number>,
  "ai_recommended_mid_usd": <number>,
  "ai_summary": "<3-4 sentences: market overview for this role in {location}, confidence level, key pay factors, patterns noticed>",
  "currency_used": "{meta['currency']}",
  "warnings": ["<any data quality issues, e.g. 'Limited data specific to this city', 'Mixed seniority levels in results'>"]
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
    Process Claude extraction output into clean data points.
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
