from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Generator, Any
import anthropic

from utils.serpapi_client import discover_top_sites, search_site
from utils.jina_client import fetch_page
from utils.claude_client import extract_salary, validate_rows_batch, generate_summary
from utils.currency import convert_currency

HOURS_PER_YEAR = 2080

SCHEMA = [
    "country_specific_site_url",
    "web_search_result_url",
    "job_title",
    "found_currency",
    "found_annual_pay",
    "found_hourly_pay",
    "display_currency",
    "display_pay_rate",
    "country",
    "region",
    "city",
    "valid",
    "error_message",
]


def run_pipeline(
    job_title: str,
    country: str,
    region: str,
    city: str,
    description: str,
    display_pref: str,
    display_currency: str,
    serpapi_key: str,
    anthropic_key: str,
    exchangerate_key: str,
) -> Generator[dict[str, Any], None, None]:
    """
    Orchestrates the full pipeline. Yields progress events as dicts:
    {"type": "progress", "value": float (0-1), "text": str}
    {"type": "row", "row": dict}
    {"type": "stats", "df": pd.DataFrame}
    {"type": "summary", "data": dict}
    {"type": "error", "message": str}
    {"type": "complete"}
    """

    client = anthropic.Anthropic(api_key=anthropic_key)
    rows: list[dict] = []

    # Step 1: Discover top sites (5%)
    yield {"type": "progress", "value": 0.05, "text": f"Discovering top salary sites for {country}..."}

    try:
        sites = discover_top_sites(country, serpapi_key)
    except Exception as e:
        yield {"type": "error", "message": f"Site discovery failed: {e}"}
        return

    if not sites:
        yield {"type": "error", "message": "No salary sites discovered. Check your SerpAPI key."}
        return

    # Steps 2 & 3: Search + fetch per site, fast-fail if first URL blocked (10%-80%)
    source_pay_count = 0
    TARGET_SOURCE_PAY_COUNT = 50

    def _has_data(row: dict) -> bool:
        """
        Count a source URL as one data point if it has a usable pay rate.
        A source with both annual AND hourly counts as ONE — not two.
        Do NOT evaluate this after Step 4 normalization (which derives the missing
        rate for every row, making every row appear to have both).
        """
        return (
            row["found_annual_pay"] is not None or
            row["found_hourly_pay"] is not None
        )

    for i, domain in enumerate(sites):
        if source_pay_count >= TARGET_SOURCE_PAY_COUNT:
            break

        progress = 0.10 + (i / len(sites)) * 0.70
        yield {
            "type": "progress",
            "value": progress,
            "text": f"Searching {domain} ({i+1}/{len(sites)}, {source_pay_count}/{TARGET_SOURCE_PAY_COUNT} data points)...",
        }

        try:
            urls = search_site(domain, job_title, country, region, city, description, serpapi_key)
        except Exception as e:
            print(f"[pipeline] search_site({domain}) error: {e}")
            continue
        if not urls:
            continue

        consecutive_no_data = 0
        for url in urls:
            if source_pay_count >= TARGET_SOURCE_PAY_COUNT:
                break
            if consecutive_no_data >= 5:
                print(f"[pipeline] Skipping {domain}: 5 consecutive pulls with no pay data")
                break

            page_text, fetch_error = fetch_page(url)
            if not page_text:
                rows.append(_empty_row(domain, url, display_currency, fetch_error))
                yield {"type": "row", "row": rows[-1]}
                consecutive_no_data += 1
                continue

            extracted = extract_salary(page_text, job_title, country, region, city, client)
            row = _build_row(domain, url, extracted, job_title, country, region, city, display_currency)
            rows.append(row)
            yield {"type": "row", "row": row}

            if _has_data(row):
                source_pay_count += 1
                consecutive_no_data = 0
            else:
                consecutive_no_data += 1

    if not rows:
        yield {"type": "error", "message": "No search results found. Try a different job title or location."}
        return

    # Step 4: Normalize hourly <-> annual (82%)
    yield {"type": "progress", "value": 0.82, "text": "Calculating hourly \u2194 annual equivalents..."}

    for row in rows:
        annual = row.get("found_annual_pay")
        hourly = row.get("found_hourly_pay")

        if hourly and not annual:
            row["found_annual_pay"] = hourly * HOURS_PER_YEAR
        elif annual and not hourly:
            row["found_hourly_pay"] = annual / HOURS_PER_YEAR

    # Step 5: Currency conversion (86%)
    yield {"type": "progress", "value": 0.86, "text": "Converting currencies..."}

    for row in rows:
        found_currency = row.get("found_currency")

        if display_pref == "Annual Salary":
            source_amount = row.get("found_annual_pay")
        else:
            source_amount = row.get("found_hourly_pay")

        if source_amount is None or not found_currency:
            row["display_pay_rate"] = None
            if not row.get("error_message") and not found_currency and source_amount is not None:
                row["error_message"] = "Currency code missing — cannot convert"
            continue

        if found_currency == display_currency:
            row["display_pay_rate"] = source_amount
        else:
            converted = convert_currency(source_amount, found_currency, display_currency, exchangerate_key)
            row["display_pay_rate"] = converted
            if converted is None:
                row["error_message"] = f"Currency conversion failed ({found_currency} → {display_currency})"

    # Step 6: Validation (90%)
    yield {"type": "progress", "value": 0.90, "text": "Validating results..."}

    rows_with_data = [r for r in rows if r.get("display_pay_rate") is not None]

    if rows_with_data:
        valid_flags = validate_rows_batch(
            rows_with_data, job_title, country, region, city, client
        )

        valid_idx = 0
        for row in rows:
            if row.get("display_pay_rate") is not None:
                row["valid"] = valid_flags[valid_idx] if valid_idx < len(valid_flags) else 0
                valid_idx += 1
            else:
                row["valid"] = 0
    else:
        for row in rows:
            row["valid"] = 0

    # Build DataFrame
    df = pd.DataFrame(rows, columns=SCHEMA)
    yield {"type": "stats", "df": df}

    # Step 7: Generate AI Summary (95%)
    yield {"type": "progress", "value": 0.95, "text": "Generating AI summary..."}

    valid_df = df[df["valid"] == 1].copy() if len(df) > 0 else pd.DataFrame()

    try:
        summary_data = generate_summary(
            job_title=job_title,
            country=country,
            region=region,
            city=city,
            display_pref=display_pref,
            display_currency=display_currency,
            valid_rows_df=valid_df,
            client=client,
        )
    except Exception as e:
        print(f"[pipeline] generate_summary error: {e}")
        summary_data = None

    yield {"type": "summary", "data": summary_data}

    # Complete
    yield {"type": "progress", "value": 1.0, "text": "Complete"}
    yield {"type": "complete"}


def compute_sigma_stats(df: pd.DataFrame) -> dict | None:
    """Compute 1-sigma and 2-sigma statistics from valid rows."""
    valid = df[(df["valid"] == 1) & (df["display_pay_rate"].notna())]

    if len(valid) < 7:
        return None

    rates = valid["display_pay_rate"].values
    mean = float(np.mean(rates))
    std = float(np.std(rates))

    def band_stats(n_sigma):
        mask = np.abs(rates - mean) <= n_sigma * std
        band = rates[mask]
        if len(band) == 0:
            return None
        return {
            "min": float(np.min(band)),
            "mean": float(np.mean(band)),
            "max": float(np.max(band)),
            "count": int(len(band)),
        }

    return {
        "mean": mean,
        "std": std,
        "sigma1": band_stats(1),
        "sigma2": band_stats(2),
    }


def _build_row(
    domain: str,
    url: str,
    extracted: dict,
    job_title: str,
    country: str,
    region: str,
    city: str,
    display_currency: str,
) -> dict:
    all_null = (
        extracted.get("found_annual_pay") is None
        and extracted.get("found_hourly_pay") is None
    )
    extraction_error = extracted.get("_error") if all_null else None
    if all_null and not extraction_error:
        extraction_error = "No salary data found on page"
    return {
        "country_specific_site_url": domain,
        "web_search_result_url": url,
        "job_title": extracted.get("job_title_found") or job_title,
        "found_currency": extracted.get("found_currency"),
        "found_annual_pay": extracted.get("found_annual_pay"),
        "found_hourly_pay": extracted.get("found_hourly_pay"),
        "display_currency": display_currency,
        "display_pay_rate": None,
        "country": extracted.get("found_country") or country,
        "region": extracted.get("found_region") or region,
        "city": extracted.get("found_city") or city,
        "valid": None,
        "error_message": extraction_error,
    }


def _empty_row(domain: str, url: str, display_currency: str, error_message: str | None = None) -> dict:
    return {
        "country_specific_site_url": domain,
        "web_search_result_url": url,
        "job_title": None,
        "found_currency": None,
        "found_annual_pay": None,
        "found_hourly_pay": None,
        "display_currency": display_currency,
        "display_pay_rate": None,
        "country": None,
        "region": None,
        "city": None,
        "valid": 0,
        "error_message": error_message,
    }
