import json
import re
import anthropic
import pandas as pd

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

EXTRACTION_SYSTEM = """You are a salary data extractor. Your job is to extract the most relevant salary information from web page content. Return ONLY valid JSON with no additional text."""

VALIDATION_SYSTEM = """You are a job title and location matching expert. Determine if search results match search criteria using semantic matching. Return ONLY valid JSON."""

SUMMARY_SYSTEM = """You are a compensation market expert for myBasePay, a professional salary benchmarking platform. Provide accurate, helpful market intelligence."""


def _build_extraction_prompt(
    job_title: str,
    location_str: str,
    currency_hint: str,
    page_text: str,
) -> str:
    """Build the extraction prompt for a first-pass salary extraction."""
    return f"""Given this web page content from a salary data site, extract salary data matching:
- Job Title: "{job_title}"
- Location: {location_str}{currency_hint}

IMPORTANT INSTRUCTIONS:
1. The page may be in any language. Translate mentally and extract regardless of language.
2. Salary data often appears as tables, ranges, or survey results — not just single numbers.
   - If you see a salary range (e.g. min/median/max or percentile bands), use the MEDIAN or AVERAGE as found_annual_pay.
   - If only a range is present with no median, use the midpoint: (min + max) / 2 and note the range in reasoning.
3. Look for any of these patterns as salary signals:
   - Currency symbols (zł, PLN, €, £, $, ¥, kr, etc.) followed by numbers
   - Local-language salary labels: wynagrodzenie, zarobki, gehalt, salaire, salario, stipendio, fizetés, etc.
   - Columns labeled min/median/max, percentile ranges (P25/P50/P75), or survey averages
4. Job title matching: accept the closest match if an exact match is not found.
5. If the page shows salary data for multiple positions, pick the best matching one.

DO NOT EXTRACT:
- Cost-of-living indices, purchasing power indices, or similar non-salary metrics.
- Benefit values, bonus caps, signing bonuses, or equity/stock grants — only BASE SALARY figures.
- A figure if the job title on the page does not meaningfully match "{job_title}".

Return ONLY valid JSON with this exact schema:
{{
  "job_title_found": "string or null",
  "found_currency": "ISO 4217 code or null",
  "found_annual_pay": number_or_null,
  "found_hourly_pay": number_or_null,
  "found_country": "string or null",
  "found_region": "string or null",
  "found_city": "string or null",
  "confidence": "high or medium or low",
  "reasoning": "one sentence explaining why you picked these figures"
}}

Confidence guidelines:
- "high": salary figure is explicitly stated on the page for a matching job title.
- "medium": salary was inferred from a range (midpoint) or the job title was a close but not exact match.
- "low": salary is estimated, ambiguous, or the page data is unclear.

CRITICAL for numeric fields:
- found_annual_pay and found_hourly_pay MUST be plain JSON numbers (e.g. 53035, not "53,035" or "$53,035").
- Strip all currency symbols, commas, and K/M suffixes before returning (e.g. "$53,035" → 53035, "45K" → 45000).
- If no salary data is found, use JSON null (not the string "null").

If absolutely no salary data is found, return all null values with confidence "low" and reasoning explaining why.

Page content:
{page_text[:15000]}"""


def _build_critique_prompt(
    job_title: str,
    location_str: str,
    page_text: str,
    first_attempt: dict,
) -> str:
    """Build a retry-with-critique prompt for low-confidence extractions."""
    first_json = json.dumps(first_attempt, indent=2)
    return f"""Here is a first extraction attempt for salary data from a web page.
The extraction was flagged as LOW confidence. Your job is to confirm or correct the figures.

Target:
- Job Title: "{job_title}"
- Location: {location_str}

First extraction attempt:
{first_json}

Review the page content below and either:
1. Confirm the figures if they look correct, upgrading confidence if warranted.
2. Correct the figures if the first attempt was wrong — extract fresh values.

Return the same JSON schema as the first attempt. Set confidence to your own assessment.

Page content:
{page_text[:15000]}"""


def extract_salary(
    page_text: str,
    job_title: str,
    country: str,
    region: str,
    city: str,
    client: anthropic.Anthropic,
    country_currency: str | None = None,
) -> dict:
    """Extract salary data from a page using Claude Haiku.

    If the first extraction has low confidence, a second critique call is made
    (capped at 2 total calls per page).
    """

    location_parts = [p for p in [city, region, country] if p]
    location_str = ", ".join(location_parts)

    currency_hint = (
        f"\n- Expected local currency: {country_currency} "
        f"(use this if no other currency is clearly indicated on the page)"
        if country_currency
        else ""
    )

    prompt = _build_extraction_prompt(job_title, location_str, currency_hint, page_text)

    # --- First extraction call ---
    result = _call_haiku_extraction(client, prompt)
    if result is None:
        return _empty_extraction()

    result = _coerce_numeric_fields(result)

    # --- Retry-with-critique if confidence is low ---
    if result.get("confidence") == "low":
        print("[claude] low confidence — retrying with critique")
        critique_prompt = _build_critique_prompt(
            job_title, location_str, page_text, result
        )
        retry_result = _call_haiku_extraction(client, critique_prompt)
        if retry_result is not None:
            result = _coerce_numeric_fields(retry_result)

    return result


def _call_haiku_extraction(client: anthropic.Anthropic, prompt: str) -> dict | None:
    """Make a single Haiku extraction call. Returns parsed dict or None on failure."""
    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1024,
            system=EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text.strip()
        print(f"[claude] extract_salary raw: {content[:300]}")
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None

    except (json.JSONDecodeError, Exception) as e:
        print(f"[claude] extract_salary error: {e}")
        return None


def _validation_fallback(rows: list[dict]) -> list[dict]:
    """Fallback when validation API call fails: pass rows with plausible pay rates."""
    results = []
    for r in rows:
        pay = r.get("display_pay_rate")
        if pay is not None and 500 <= pay <= 10_000_000:
            results.append({"valid": 1, "validation_reason": "api_fallback_passthrough"})
        else:
            results.append({"valid": 0, "validation_reason": "api_fallback_rejected"})
    return results


def validate_rows_batch(
    rows: list[dict],
    job_title: str,
    country: str,
    region: str,
    city: str,
    client: anthropic.Anthropic,
    niche_level: str = "common",
    title_variants: list[str] | None = None,
) -> list[dict]:
    """Batch validate rows using a single Haiku call.

    Returns list of dicts with keys:
      - "valid": 0 or 1
      - "validation_reason": short explanation string

    niche_level / title_variants: passed through from classify_job_niche() to
    instruct the validator to accept related/broader titles for niche searches.
    """

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
            "confidence": r.get("confidence", "medium"),
            "reasoning": r.get("reasoning", ""),
        }
        for i, r in enumerate(rows)
    ], indent=2)

    location_parts = [p for p in [city, region, country] if p]
    location_str = ", ".join(location_parts)

    # Build niche-awareness note for the validator
    if niche_level == "niche" and title_variants:
        niche_note = (
            f'\n⚠️ NICHE TITLE NOTE: "{job_title}" is a niche/specialised role. '
            f"The search intentionally retrieved pages for related titles: {title_variants}. "
            "Accept rows whose job_title_found matches ANY of these variants, or is a "
            "reasonable functional equivalent (e.g. 'Account Analyst' for 'Account Management Analyst'). "
            "Do NOT reject a row solely because the title is not an exact match to the primary title.\n"
        )
    elif niche_level == "specialized":
        niche_note = (
            f'\nNOTE: "{job_title}" is a specialised title — accept close functional equivalents.\n'
        )
    else:
        niche_note = ""

    prompt = f"""For each result below, determine if it is a valid salary data point for the search criteria. Use semantic matching for job titles (related titles count as valid).

Search criteria:
- Job Title: "{job_title}"
- Location: {location_str}
{niche_note}
Results to validate:
{rows_json}

Each result includes:
- display_pay_rate: the extracted salary figure
- confidence: how confident the extraction was ("high", "medium", or "low")
- reasoning: why the extraction chose those figures

Return ONLY a JSON array of objects with "idx", "valid" (1=match, 0=no match), and "validation_reason" (short string explaining why):
[{{"idx": 0, "valid": 1, "validation_reason": "plausible range"}}, {{"idx": 1, "valid": 0, "validation_reason": "mismatched job title"}}, ...]

Validation rules:

TWO-TIER THRESHOLD based on extraction confidence:

For HIGH confidence rows:
- valid=1 if job title is semantically related AND location roughly matches (or location is empty/null) AND display_pay_rate is not null and looks plausible for the role
- valid=0 if display_pay_rate is null, or job title is completely unrelated

For LOW confidence rows (apply stricter checks):
- Apply all the high-confidence rules above, PLUS:
- Check cross-row consistency: if the figure is an obvious outlier compared to the other figures in this batch, mark it invalid with validation_reason="outlier"
- If the extraction reasoning is vague or unconvincing, mark invalid with validation_reason="low confidence unverified"
- Low confidence rows need stronger corroborating evidence (e.g. the pay figure should be in a similar range to other rows in the batch)

For MEDIUM confidence rows:
- Apply the same rules as high confidence, but flag if the figure seems unusual compared to the batch

General rules:
- valid=0 if display_pay_rate is null
- valid=0 if job title is completely unrelated
- Use validation_reason values like: "plausible range", "mismatched job title", "outlier", "currency ambiguous", "low confidence unverified", "null pay rate", "location mismatch"
"""

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=2048,
            system=VALIDATION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text.strip()
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            results = json.loads(json_match.group())
            result_map = {
                r["idx"]: {
                    "valid": r.get("valid", 0),
                    "validation_reason": r.get("validation_reason", "unknown"),
                }
                for r in results
            }
            return [
                result_map.get(i, {"valid": 0, "validation_reason": "missing from response"})
                for i in range(len(rows))
            ]

        return [{"valid": 0, "validation_reason": "no valid response"} for _ in rows]

    except Exception as e:
        print(f"[claude] validate_rows_batch error: {e}")
        return _validation_fallback(rows)


def generate_summary(
    job_title: str,
    country: str,
    region: str,
    city: str,
    display_pref: str,
    display_currency: str,
    valid_rows_df: pd.DataFrame,
    client: anthropic.Anthropic,
    moderate_confidence: bool = False,
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

    confidence_note = (
        "\n⚠️ IMPORTANT: Only a small number of data points were collected for this query. "
        "Explicitly caveat your summary by noting that the data is limited and the range is indicative only.\n"
        if moderate_confidence else ""
    )

    prompt = f"""Job: {job_title}
Location: {location_str}
Display preference: {display_pref} in {display_currency}
{confidence_note}
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


# Maps common currency names / symbols → ISO 4217 codes
_CURRENCY_NAME_MAP = {
    "złoty": "PLN", "zloty": "PLN", "zł": "PLN", "zl": "PLN",
    "euro": "EUR", "€": "EUR",
    "dollar": "USD", "dollars": "USD", "usd": "USD", "$": "USD",
    "pound": "GBP", "pounds": "GBP", "sterling": "GBP", "£": "GBP",
    "franc": "CHF", "francs": "CHF", "chf": "CHF",
    "forint": "HUF", "ft": "HUF",
    "koruna": "CZK", "kč": "CZK", "czk": "CZK",
    "leu": "RON", "lei": "RON", "ron": "RON",
    "kuna": "HRK", "hrk": "HRK",
    "ruble": "RUB", "rubles": "RUB", "руб": "RUB",
    "hryvnia": "UAH", "₴": "UAH",
    "krona": "SEK", "kronor": "SEK", "sek": "SEK",
    "krone": "NOK", "nok": "NOK",
    "krone": "DKK", "dkk": "DKK",
    "yen": "JPY", "¥": "JPY",
    "yuan": "CNY", "renminbi": "CNY", "rmb": "CNY",
    "rupee": "INR", "rupees": "INR", "₹": "INR",
    "real": "BRL", "reais": "BRL", "brl": "BRL",
    "peso": "MXN", "mxn": "MXN",
    "won": "KRW", "₩": "KRW",
    "ringgit": "MYR", "myr": "MYR",
    "baht": "THB", "thb": "THB",
    "lira": "TRY", "try": "TRY",
    "dirham": "AED", "aed": "AED",
    "riyal": "SAR", "sar": "SAR",
}


def _coerce_numeric_fields(data: dict) -> dict:
    """
    Ensure found_annual_pay and found_hourly_pay are floats (or None).
    Claude occasionally returns formatted strings like "$53,035" or "45K"
    even when instructed not to — this strips those artefacts defensively.

    Also strips implausibly small (< 1,000) or large (> 10,000,000) values,
    logging extraction errors via an '_error' key on the dict.
    """
    # Normalize found_currency: map common names/symbols to ISO 4217
    currency = data.get("found_currency")
    if currency and isinstance(currency, str):
        normalized = _CURRENCY_NAME_MAP.get(currency.strip().lower())
        if normalized:
            data["found_currency"] = normalized
        else:
            # Already looks like an ISO code — just uppercase and strip
            data["found_currency"] = currency.strip().upper()

    for field in ("found_annual_pay", "found_hourly_pay"):
        val = data.get(field)
        if val is None:
            continue
        if isinstance(val, (int, float)):
            data[field] = float(val)
        elif isinstance(val, str):
            # Handle K / M suffixes before stripping (e.g. "45K" → "45000")
            val_upper = val.upper().strip()
            if val_upper.endswith("K"):
                cleaned = re.sub(r"[^\d.]", "", val_upper[:-1])
                try:
                    data[field] = float(cleaned) * 1_000
                except ValueError:
                    data[field] = None
                    continue
            elif val_upper.endswith("M"):
                cleaned = re.sub(r"[^\d.]", "", val_upper[:-1])
                try:
                    data[field] = float(cleaned) * 1_000_000
                except ValueError:
                    data[field] = None
                    continue
            else:
                # Strip currency symbols, spaces, commas
                cleaned = re.sub(r"[^\d.]", "", val.replace(",", ""))
                try:
                    data[field] = float(cleaned) if cleaned else None
                except ValueError:
                    data[field] = None
                    continue

        # Plausibility check on the final numeric value (field-aware thresholds)
        numeric_val = data.get(field)
        is_hourly = field == "found_hourly_pay"
        min_val, max_val = (1.0, 10_000) if is_hourly else (1_000, 10_000_000)
        if numeric_val is not None and (numeric_val < min_val or numeric_val > max_val):
            range_str = f"[{min_val} – {max_val:,}]"
            error_msg = (
                f"{field} value {numeric_val} is outside plausible range "
                f"{range_str}; stripped to null"
            )
            print(f"[claude] extraction error: {error_msg}")
            data[field] = None
            # Append to _error key
            existing_error = data.get("_error", "")
            data["_error"] = (existing_error + "; " + error_msg).lstrip("; ")

    return data


def _empty_extraction() -> dict:
    return {
        "job_title_found": None,
        "found_currency": None,
        "found_annual_pay": None,
        "found_hourly_pay": None,
        "found_country": None,
        "found_region": None,
        "found_city": None,
        "confidence": None,
        "reasoning": None,
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
