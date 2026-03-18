"""BLS OEWS API client for fetching official wage data by SOC code.

Flow:
1. Use Claude Haiku to map a job title → best-matching SOC code + title
2. Query the BLS Public Data API for national mean annual wage
3. Return pipeline-compatible row dicts

BLS series ID format for OEWS national mean annual wage:
    OEUS000000{SOC_no_dash}03
    e.g. SOC 11-9199 → OEUS00000011919903

The BLS public API allows 25 requests/day without a key, 500/day with a
free registration key.  We try the key from st.secrets first, then fall
back to unauthenticated.
"""

from __future__ import annotations

import json
import re
import requests
from typing import Any

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# ---------------------------------------------------------------------------
# Step 1: SOC code lookup via Haiku
# ---------------------------------------------------------------------------

def _lookup_soc_code(job_title: str, anthropic_client) -> tuple[str, str] | None:
    """Ask Haiku to map *job_title* to the best-matching SOC code and title.

    Returns (soc_code, soc_title) e.g. ("11-9199", "Managers, All Other")
    or None on failure.
    """
    prompt = (
        f'What is the best matching Bureau of Labor Statistics (BLS) '
        f'Standard Occupational Classification (SOC) code for the job title "{job_title}"?\n\n'
        f'Return ONLY a JSON object with two keys:\n'
        f'{{"soc_code": "XX-XXXX", "soc_title": "Official SOC Title"}}\n\n'
        f'Use the 6-digit SOC code format (e.g. "11-9199"). '
        f'Pick the single best match. No explanations, no markdown.'
    )
    try:
        response = anthropic_client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group())
        soc_code = data.get("soc_code", "").strip()
        soc_title = data.get("soc_title", "").strip()
        if re.match(r"^\d{2}-\d{4}$", soc_code):
            return soc_code, soc_title
    except Exception as e:
        print(f"[bls] SOC lookup error: {e}")
    return None


# ---------------------------------------------------------------------------
# Step 2: Query BLS OEWS API
# ---------------------------------------------------------------------------

def _build_series_id(soc_code: str) -> str:
    """Build the OEWS national mean annual wage series ID from a SOC code.

    Format: OEUS000000{SOC_no_dash}03
    """
    soc_stripped = soc_code.replace("-", "")
    return f"OEUS000000{soc_stripped}03"


def _query_bls_api(series_id: str, bls_api_key: str | None = None) -> dict | None:
    """Query the BLS public data API for a single series.

    Returns the most recent annual data point as a dict, or None.
    """
    payload: dict[str, Any] = {
        "seriesid": [series_id],
        "startyear": "2022",
        "endyear": "2024",
    }
    if bls_api_key:
        payload["registrationkey"] = bls_api_key

    try:
        resp = requests.post(_BLS_API_URL, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "REQUEST_SUCCEEDED":
            print(f"[bls] API status: {data.get('status')} — {data.get('message', [''])[0] if data.get('message') else ''}")
            return None

        series_list = data.get("Results", {}).get("series", [])
        if not series_list:
            return None

        series_data = series_list[0].get("data", [])
        if not series_data:
            return None

        # BLS returns data newest-first; take the most recent annual entry
        for entry in series_data:
            if entry.get("period") == "A01":  # Annual average
                return entry

        # If no annual entry, take the most recent entry available
        return series_data[0]

    except Exception as e:
        print(f"[bls] API query error: {e}")
        return None


# ---------------------------------------------------------------------------
# Step 3: Public interface
# ---------------------------------------------------------------------------

def get_bls_wage_data(
    job_title: str,
    anthropic_client,
    bls_api_key: str | None = None,
) -> list[dict]:
    """Fetch BLS OEWS wage data for a job title.

    Returns a list of pipeline-compatible row dicts (0 or 1 items).
    Each dict matches the pipeline SCHEMA fields so it can be injected
    directly into the data pool.
    """
    # Step 1: map title → SOC
    soc_result = _lookup_soc_code(job_title, anthropic_client)
    if soc_result is None:
        print(f"[bls] Could not map '{job_title}' to a SOC code")
        return []

    soc_code, soc_title = soc_result
    print(f"[bls] Mapped '{job_title}' → SOC {soc_code} ({soc_title})")

    # Step 2: query BLS
    series_id = _build_series_id(soc_code)
    bls_entry = _query_bls_api(series_id, bls_api_key)
    if bls_entry is None:
        print(f"[bls] No data returned for series {series_id}")
        return []

    # Parse the wage value
    raw_value = bls_entry.get("value", "")
    try:
        annual_pay = float(raw_value.replace(",", ""))
    except (ValueError, AttributeError):
        print(f"[bls] Could not parse wage value: {raw_value}")
        return []

    year = bls_entry.get("year", "")
    period_name = bls_entry.get("periodName", "")
    source_url = f"https://www.bls.gov/oes/current/oes{soc_code.replace('-', '')}.htm"

    row = {
        "country_specific_site_url": "bls.gov",
        "web_search_result_url": source_url,
        "job_title": soc_title,
        "found_currency": "USD",
        "found_annual_pay": annual_pay,
        "found_hourly_pay": round(annual_pay / 2080, 2),
        "found_pay_low": None,
        "found_pay_high": None,
        "display_currency": None,  # filled by pipeline
        "display_pay_rate": None,  # filled by pipeline
        "country": "United States",
        "region": "",
        "city": "",
        "remote_ok": 0,
        "source_type": "government",
        "valid": None,  # filled by pipeline validation
        "error_message": None,
        "validation_reason": None,
        "confidence": "high",
        "reasoning": f"BLS OEWS {year} {period_name} national mean annual wage for SOC {soc_code} ({soc_title})",
    }

    print(f"[bls] Got ${annual_pay:,.0f}/yr for SOC {soc_code} ({year} {period_name})")
    return [row]
