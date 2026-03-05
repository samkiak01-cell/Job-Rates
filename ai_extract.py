"""
ai_extract.py — Claude-powered salary data extraction
Sends search snippets to Claude for structured extraction and analysis.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from utils import (
    ANTHROPIC_URL,
    CLAUDE_MODEL,
    MAX_SOURCES_FOR_AI,
    get_fx,
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

RULE 1 — JOB TITLE PRECISION:
Only extract data for the EXACT job title requested, or a genuinely synonymous title. Apply strict matching:
- "Video Editor" ≠ "Videographer" (different skill set entirely)
- "Video Editor" ≠ "Cinematographer", "Film Director", "Video Producer"
- "Software Engineer" ≠ "IT Support", "Help Desk", "Systems Administrator"
- "Data Analyst" ≠ "Data Scientist", "Data Engineer"
- "Graphic Designer" ≠ "UX Designer", "Web Developer"
For EVERY source, explicitly decide: Is this data for the correct job title? If not certain, SKIP IT.

RULE 2 — COUNTRY PRECISION:
Only extract data for the target country. Watch for these wrong-country warning signs:
- Salary scale far too high for the target country (e.g., $80k+ for a Brazilian role with no USD context)
- $ symbol with no mention of the target country or currency
- .com domain with no country-specific context indicator
- Comparison articles that mention multiple countries — only extract the target country's data
If the source does not clearly confirm the correct country, SKIP IT.

RULE 3 — CURRENCY AND PAY PERIOD:
Convert everything to ANNUAL USD. Be precise about currency detection:
- R$ or BRL = Brazilian Real (Brazil, typically quoted MONTHLY)
- MXN or $ in Mexican context = Mexican Peso (typically MONTHLY)
- PHP = Philippine Peso (typically MONTHLY)
- ¥ in Japanese context = JPY (typically MONTHLY); ¥ in Chinese context = CNY (typically MONTHLY)
- AED = UAE Dirham (typically MONTHLY); SAR = Saudi Riyal (typically MONTHLY)
- $ alone near US context = USD (annually)
- £ = GBP (annually); € = EUR (annually)
Monthly-pay countries: Brazil, Mexico, Philippines, Japan, UAE, Saudi Arabia, China.
If you see "R$ 5,000" with no period stated, assume MONTHLY. Conversion: value × 12 = annual local, then ÷ exchange_rate = USD.

RULE 4 — CONFIDENCE SCORES:
- 0.85–1.0: Major salary databases with specific data for exact role+location: Glassdoor, Indeed, PayScale, Salary.com, Levels.fyi, Naukri, StepStone, Seek, Reed, Catho, Vagas, Doda, JobStreet, Saramin
- 0.6–0.84: Job postings with stated salary; regional salary sites with approximate data
- 0.3–0.59: Blog posts, forums, or tangentially related data
- Below 0.3: Do not include

RULE 5 — FINAL SANITY CHECK before submitting JSON:
Review your extracted data_points and ask:
1. Are all USD values reasonable for this country and role?
2. Did I accidentally include data from the wrong country or wrong job?
3. Did I correctly handle monthly vs annual conversion?
4. Does the ai_recommended range reflect reality for this country (not US norms)?
Fix any issues before outputting JSON.

Return ONLY valid JSON. No markdown fences. No commentary outside the JSON."""


SIMILAR_BUT_DIFFERENT: Dict[str, List[str]] = {
    "video editor":      ["videographer", "cinematographer", "film director", "video producer", "motion graphics designer"],
    "software engineer": ["it support", "systems administrator", "data entry", "help desk", "qa tester"],
    "data analyst":      ["data scientist", "data engineer", "business analyst", "database administrator"],
    "graphic designer":  ["ux designer", "ui designer", "web developer", "art director", "illustrator"],
    "accountant":        ["bookkeeper", "financial analyst", "auditor", "tax advisor"],
    "nurse":             ["doctor", "physician", "medical assistant", "pharmacist"],
    "teacher":           ["professor", "tutor", "school administrator", "curriculum developer"],
    "marketing manager": ["marketing coordinator", "digital marketing specialist", "pr manager"],
    "project manager":   ["program manager", "product manager", "scrum master", "business analyst"],
}


def _get_exclusion_examples(job: str) -> str:
    job_lower = job.lower().strip()
    for key, exclusions in SIMILAR_BUT_DIFFERENT.items():
        if key in job_lower or job_lower in key:
            excl_list = ", ".join(f'"{e}"' for e in exclusions)
            return f'\nDO NOT extract data for these similar-but-different titles: {excl_list}\n'
    return ""


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
    period_hint: str = None,
    market_notes: str = None,
) -> str:
    """Construct the full user prompt for Claude."""

    meta = get_meta(country)
    location = ", ".join(x for x in [city, state, country] if x)
    source_block = _build_source_block(sources)
    exclusion_note = _get_exclusion_examples(job)

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
        truncated = job_desc.strip()[:1500]
        jd_section = (
            f"\nJOB DESCRIPTION CONTEXT (use to understand role scope, NOT to filter):\n"
            f"{truncated}\n"
        )

    # Monthly-pay country alert — period_hint from planner overrides default if present
    effective_period = period_hint if period_hint in {"annual", "monthly"} else meta["default_period"]
    monthly_alert = ""
    if effective_period == "monthly":
        currency = meta["currency"]
        fx = meta["fx"]
        monthly_alert = (
            f"\n⚠ MONTHLY-PAY COUNTRY: In {country}, salaries are typically quoted per month.\n"
            f"Correct conversion: {currency} X/mo × 12 = {currency} (X×12)/yr ÷ {fx} = $Y USD\n"
            f"Example: {currency} 5,000/mo × 12 = {currency} 60,000/yr ÷ {fx} = ${60000/fx:,.0f} USD\n"
        )

    # Market context block from Agent 1 planner
    market_context_block = ""
    if market_notes and market_notes.strip():
        market_context_block = f"\nMARKET CONTEXT (from search planner):\n{market_notes.strip()}\n"

    return f"""Extract salary data for: **{job}** in **{location}**{market_context_block}
{exclusion_note}{exp_section}{jd_section}
COUNTRY DEFAULTS:
- Local currency: {meta['currency']}
- Exchange rate: 1 USD = {meta['fx']} {meta['currency']} [LIVE RATE — use exactly]
- Typical pay period: {meta['default_period']}
{monthly_alert}
─────────────────────────────────
SEARCH RESULTS TO ANALYZE:
─────────────────────────────────
{source_block}

─────────────────────────────────
EXTRACTION INSTRUCTIONS:
─────────────────────────────────

STEP 1 — FILTER: For each source, write in your head:
  "Source N is for [actual job title] in [actual country] → KEEP/SKIP because..."
  Then apply these checks:
  a) Is this about the correct job title (or a genuinely synonymous variant)?
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
  - Do the USD values make sense for {country}? High USD amounts for non-US countries are suspicious.
  - Are there data points from the wrong country mixed in? Remove them.
  - Did you correctly handle monthly vs annual? Check monthly-pay countries carefully.

STEP 4 — RECOMMEND a realistic range:
  - Based on ONLY the validated, high-confidence data points
  - Factor in the target experience level if provided
  - The min/max should represent a realistic offer range, NOT statistical extremes
  - The midpoint should be what a typical candidate would expect

STEP 5 — RANGES in data_points:
  - If a source gives a salary RANGE (e.g. '$60k–$90k'), put the midpoint in value_annual_usd,
    the low end (converted to annual USD) in value_min_annual_usd, and the high end in value_max_annual_usd.
  - If a source gives a SINGLE value, set both value_min_annual_usd and value_max_annual_usd to null.

Return ONLY this JSON structure:
{{
  "data_points": [
    {{
      "value_annual_usd": <number>,
      "value_min_annual_usd": <number or null>,
      "value_max_annual_usd": <number or null>,
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
    period_hint: str = None,
    market_notes: str = None,
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
        period_hint=period_hint,
        market_notes=market_notes,
    )

    resp = http_post(
        ANTHROPIC_URL,
        json_body={
            "model": CLAUDE_MODEL,
            "max_tokens": 8192,
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

    content = resp.json().get("content") or []
    raw = "".join(b.get("text", "") for b in content if b.get("type") == "text")

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
def _guard_usd(v: Any) -> Optional[float]:
    """Parse and validate a USD value: must be between $3k and $5M."""
    n = parse_num(v)
    if n is None or n < 3_000 or n > 5_000_000:
        return None
    return n


def process_extraction(
    ai_data: Dict[str, Any],
    sources: List[Dict],
) -> List[Dict]:
    """
    Process Claude extraction output into a data_table (List[Dict]).
    Each row contains annual_usd (midpoint), optional value_min_usd / value_max_usd,
    plus source metadata.
    """
    raw_points = ai_data.get("data_points") or []
    data_table: List[Dict] = []

    for dp in raw_points:
        v = _guard_usd(dp.get("value_annual_usd"))
        if v is None:
            continue

        # Parse optional range endpoints
        v_min = _guard_usd(dp.get("value_min_annual_usd"))
        v_max = _guard_usd(dp.get("value_max_annual_usd"))

        # Swap if inverted
        if v_min is not None and v_max is not None and v_min > v_max:
            v_min, v_max = v_max, v_min

        # Link back to source
        src_idx = int(dp.get("source_idx", 1)) - 1
        src = sources[src_idx] if 0 <= src_idx < len(sources) else {}

        data_table.append({
            "annual_usd": v,
            "value_min_usd": v_min,
            "value_max_usd": v_max,
            "label": dp.get("label", ""),
            "confidence": float(dp.get("confidence", 0.7)),
            "original_value": dp.get("original_value", ""),
            "conversion_note": dp.get("conversion_note", ""),
            "url": src.get("url", ""),
            "host": src.get("host", ""),
            "quality": src.get("quality", 50),
        })

    return data_table
