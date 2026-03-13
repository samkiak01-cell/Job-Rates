import json
import re
import anthropic
import pandas as pd

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

EXTRACTION_SYSTEM = """You are a salary data extractor. Your job is to extract the most relevant salary information from web page content. Return ONLY valid JSON with no additional text."""

VALIDATION_SYSTEM = """You are a job title and location matching expert. Determine if search results match search criteria using semantic matching. Return ONLY valid JSON."""

SUMMARY_SYSTEM = """You are a compensation market expert for myBasePay, a professional salary benchmarking platform. Provide accurate, helpful market intelligence."""


def extract_salary(
    page_text: str,
    job_title: str,
    country: str,
    region: str,
    city: str,
    client: anthropic.Anthropic,
) -> dict:
    """Extract salary data from a page using Claude Haiku."""

    location_parts = [p for p in [city, region, country] if p]
    location_str = ", ".join(location_parts)

    prompt = f"""Given this web page content from a salary data site, if the content is not in English, first translate it to English internally, then extract the MOST RELEVANT salary entry matching:
- Job Title: "{job_title}"
- Location: {location_str}

Return ONLY valid JSON with this exact schema:
{{
  "job_title_found": "string or null",
  "found_currency": "ISO 4217 code or null",
  "found_annual_pay": "number or null",
  "found_hourly_pay": "number or null",
  "found_country": "string or null",
  "found_region": "string or null",
  "found_city": "string or null"
}}

If no salary data is found or the content is not salary-related, return all null values.

Page content:
{page_text[:10000]}"""

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=512,
            system=EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text.strip()
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return _empty_extraction()

    except (json.JSONDecodeError, Exception) as e:
        print(f"[claude] extract_salary error: {e}")
        return _empty_extraction()


def validate_rows_batch(
    rows: list[dict],
    job_title: str,
    country: str,
    region: str,
    city: str,
    client: anthropic.Anthropic,
) -> list[int]:
    """Batch validate rows using a single Haiku call. Returns list of 0/1 values."""

    if not rows:
        return []

    rows_json = json.dumps([
        {
            "idx": i,
            "job_title_found": r.get("job_title", ""),
            "found_country": r.get("country", ""),
            "found_region": r.get("region", ""),
            "found_city": r.get("city", ""),
            "display_pay_rate": r.get("display_pay_rate"),
        }
        for i, r in enumerate(rows)
    ], indent=2)

    location_parts = [p for p in [city, region, country] if p]
    location_str = ", ".join(location_parts)

    prompt = f"""For each result below, determine if it matches the search criteria using semantic matching for job titles (related titles count as valid).

Search criteria:
- Job Title: "{job_title}"
- Location: {location_str}

Results to validate:
{rows_json}

Return ONLY a JSON array of objects with "idx" and "valid" (1=match, 0=no match):
[{{"idx": 0, "valid": 1}}, {{"idx": 1, "valid": 0}}, ...]

Rules:
- valid=1 if job title is semantically related AND location roughly matches (or location is empty/null)
- valid=0 if display_pay_rate is null
- valid=0 if job title is completely unrelated
"""

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1024,
            system=VALIDATION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text.strip()
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            results = json.loads(json_match.group())
            # Build a mapping idx -> valid
            valid_map = {r["idx"]: r.get("valid", 0) for r in results}
            return [valid_map.get(i, 0) for i in range(len(rows))]

        return [0] * len(rows)

    except Exception as e:
        print(f"[claude] validate_rows_batch error: {e}")
        return [0] * len(rows)


def generate_summary(
    job_title: str,
    country: str,
    region: str,
    city: str,
    display_pref: str,
    display_currency: str,
    valid_rows_df: pd.DataFrame,
    client: anthropic.Anthropic,
) -> dict:
    """Generate AI market summary using Claude Sonnet."""

    location_parts = [p for p in [city, region, country] if p]
    location_str = ", ".join(location_parts) if location_parts else country

    # Format valid rows as markdown table (supplementary context only)
    if valid_rows_df is not None and len(valid_rows_df) > 0:
        cols = ["job_title", "found_currency", "display_pay_rate", "country", "region", "city"]
        available_cols = [c for c in cols if c in valid_rows_df.columns]
        table_df = valid_rows_df[available_cols].head(20)
        supplementary_data = table_df.to_markdown(index=False)
    else:
        supplementary_data = "No valid data found"

    prompt = f"""Job: {job_title}
Location: {location_str}
Display preference: {display_pref} in {display_currency}

Supplementary data from web (use as context only, do not anchor your analysis to it):
{supplementary_data}

Based primarily on your own training knowledge about compensation for this role in this market:

Provide your response as JSON with this exact schema:
{{
  "summary": "3-5 sentence market summary covering expected pay range and current market conditions",
  "bullets": ["1-3 ultra-short insight chips, each max 6 words, punchy and specific — e.g. 'FAANG pays 30% above median', 'Remote roles add ~15%', 'High demand, low supply'. Only include a chip if you have a genuine insight — return 1 to 3 items, never 0."],
  "market_analytics": {{
    "market_min": number,
    "median": number,
    "mean": number,
    "market_max": number
  }},
  "recommended_range": {{
    "min": number,
    "max": number,
    "justification": "brief justification"
  }}
}}

All monetary values should be in {display_currency} as {display_pref.lower()} figures.
Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=1500,
            system=SUMMARY_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text.strip()
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return _empty_summary()

    except Exception as e:
        print(f"[claude] generate_summary error: {e}")
        return _empty_summary()


def _empty_extraction() -> dict:
    return {
        "job_title_found": None,
        "found_currency": None,
        "found_annual_pay": None,
        "found_hourly_pay": None,
        "found_country": None,
        "found_region": None,
        "found_city": None,
    }


def _empty_summary() -> dict:
    return {
        "summary": "Unable to generate market summary at this time.",
        "bullets": ["Data unavailable"],
        "market_analytics": {
            "market_min": None,
            "median": None,
            "mean": None,
            "market_max": None,
        },
        "recommended_range": {
            "min": None,
            "max": None,
            "justification": "Insufficient data to provide recommendation.",
        },
    }
