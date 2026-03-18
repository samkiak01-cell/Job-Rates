from __future__ import annotations

import hashlib
import json
import pathlib
import time
import uuid
import pandas as pd
import numpy as np
from typing import Generator, Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import anthropic

from utils.serpapi_client import discover_top_sites, search_site, classify_job_niche, get_source_type, SALARY_SITE_WHITELIST, INDUSTRY_VERTICAL_SOURCES
from utils.jina_client import fetch_page
from utils.claude_client import extract_salary, validate_rows_batch, generate_summary
from utils.currency import convert_currency
from utils.countries import get_country_currency

HOURS_PER_YEAR = 2080
FETCH_BATCH_SIZE = 3
URL_FETCH_TIMEOUT = 35       # seconds per individual URL fetch
DOMAIN_WALL_CLOCK_TIMEOUT = 90  # seconds for the entire domain block

# Domains that consistently return Cloudflare blocks, have no salary data,
# or are geographically irrelevant to most searches — skip entirely.
FETCH_BLOCKLIST = {
    "reddit.com",         # Cloudflare-walled for Jina
    "glassdoor.de",       # Cloudflare-walled for Jina
    "glassdoor.fr",       # Cloudflare-walled for Jina
    "ttecjobs.com",       # Job listings, never contains salary figures
    "indeed.com",         # Cloudflare-walled globally for Jina
    "roberthalf.com",     # Consistent timeouts with Jina
    "monster.com",        # Consistent timeouts/blocks with Jina
    "jobted.com",         # Job listings only, no salary figures
    "manpower.com",       # Company site, not salary data
}

# Adaptive target data-point counts by job niche level
TARGET_BY_NICHE = {
    "common": 80,       # Plenty of pages exist — aim high
    "specialized": 50,  # Fewer dedicated pages — moderate target
    "niche": 25,        # Very few exact matches — lower bar to avoid padding with garbage
}

SCHEMA = [
    "country_specific_site_url",
    "web_search_result_url",
    "job_title",
    "found_currency",
    "found_annual_pay",
    "found_hourly_pay",
    "found_pay_low",
    "found_pay_high",
    "display_currency",
    "display_pay_rate",
    "country",
    "region",
    "city",
    "remote_ok",
    "source_type",
    "valid",
    "error_message",
    "validation_reason",
]

# File-based result cache
CACHE_DIR = pathlib.Path("pipeline_cache")
CACHE_TTL_HOURS = 24
MAX_LOG_ENTRIES = 50
LOG_FILE = "pipeline_run_log.json"

# Bail-out limits differentiated by failure type
BAIL_LIMITS = {
    "wall": 2,      # Stop domain quickly on confirmed walls
    "network": 3,   # Moderate patience for network issues
    "no_data": 4,   # Current default for pages with no salary data
    "default": 4,
}

# Minimum valid data points floor (raised from 14 to 20)
MINIMUM_VALID_FLOOR = 20
MINIMUM_VALID_FLOOR_DOMAINS = 15

# Quality strategy switch: if less than 30% of extracted rows are valid after 10 domains, expand
QUALITY_SWITCH_DOMAINS = 10
QUALITY_SWITCH_THRESHOLD = 0.30


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _make_error(stage: str, reason: str, recoverable: bool = False) -> str:
    """Return a JSON-encoded structured error string."""
    return json.dumps({"stage": stage, "reason": reason, "recoverable": recoverable})


def _reorder_domains_by_yield(remaining: list[str], yield_rates: dict) -> list[str]:
    """Reorder domains: high-yield first, 0%-yield-after-3-URLs last, unknown in middle."""
    def sort_key(d: str) -> int:
        info = yield_rates.get(d, {})
        fetched = info.get("urls_fetched", 0)
        valid = info.get("valid_rows", 0)
        if fetched == 0:
            return 1  # unknown — keep in middle
        rate = valid / fetched
        if rate == 0 and fetched >= 3:
            return 2  # deprioritise (0% yield after ≥3 URLs)
        return 0 if rate > 0 else 1
    return sorted(remaining, key=sort_key)


def _build_summary_stub(valid_count: int, rejection_reasons: list[str]) -> dict:
    """Build an insufficient-data stub summary dict."""
    return {
        "summary": (
            f"Insufficient data: only {valid_count} valid data point(s) collected. "
            "More data is needed for a reliable market analysis."
        ),
        "bullets": [
            f"{valid_count} valid rows collected",
            "Increase search scope",
            "Try broader job title",
        ],
        "insufficient_data": True,
        "rejection_reasons": rejection_reasons,
        "market_analytics": {"market_min": None, "median": None, "mean": None, "market_max": None},
        "recommended_range": {"min": None, "max": None, "justification": "Insufficient data"},
    }


def _get_cache_key(job_title: str, country: str, region: str) -> str:
    normalized = f"{job_title.lower().strip()}|{country.lower()}|{region.lower()}"
    return hashlib.md5(normalized.encode()).hexdigest()


def _load_cache(cache_key: str) -> list[dict] | None:
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / f"{cache_key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        age_hours = (time.time() - data.get("timestamp", 0)) / 3600
        if age_hours > CACHE_TTL_HOURS:
            print(f"[pipeline] Cache expired ({age_hours:.1f}h > {CACHE_TTL_HOURS}h): {cache_key}")
            return None
        print(f"[pipeline] Cache hit ({age_hours:.1f}h old): {cache_key}")
        return data.get("rows", [])
    except Exception as e:
        print(f"[pipeline] Cache load error: {e}")
        return None


def _save_cache(cache_key: str, rows: list[dict]) -> None:
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        path = CACHE_DIR / f"{cache_key}.json"
        path.write_text(
            json.dumps({"timestamp": time.time(), "rows": rows}, default=str),
            encoding="utf-8",
        )
        print(f"[pipeline] Cache saved: {cache_key} ({len(rows)} rows)")
    except Exception as e:
        print(f"[pipeline] Cache save error: {e}")


def _append_log(log_entry: dict) -> None:
    try:
        path = pathlib.Path(LOG_FILE)
        entries: list = []
        if path.exists():
            try:
                entries = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(entries, list):
                    entries = []
            except Exception:
                entries = []
        entries.append(log_entry)
        entries = entries[-MAX_LOG_ENTRIES:]
        path.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")
    except Exception as e:
        print(f"[pipeline] Log append error: {e}")


def _classify_fetch_error(error_msg: str | None) -> str:
    """Classify a fetch error message into wall / network / default."""
    if not error_msg:
        return "default"
    if "WALL:" in error_msg:
        return "wall"
    if "NETWORK:" in error_msg:
        return "network"
    return "default"


def _country_to_key(country: str) -> str:
    mapping = {
        "United States": "US", "USA": "US", "US": "US",
        "United Kingdom": "UK", "UK": "UK", "Britain": "UK", "England": "UK",
        "Germany": "DE", "Australia": "AU", "Canada": "CA",
    }
    return mapping.get(country, "GLOBAL")


def _pre_sort_domains(domains: list[str], country: str, job_vertical: str | None) -> list[str]:
    """Pre-sort domains before the main loop: high-priority sources first."""
    country_key = _country_to_key(country)
    high_priority = set(SALARY_SITE_WHITELIST.get(country_key, []))
    vertical_priority = set(INDUSTRY_VERTICAL_SOURCES.get(job_vertical, [])) if job_vertical else set()
    blocked = FETCH_BLOCKLIST

    def domain_priority(d: str) -> int:
        if d in blocked:
            return 999
        score = 50
        if d in vertical_priority:
            score -= 20
        if d in high_priority:
            score -= 10
        stype = get_source_type(d)
        if stype == "government":
            score -= 8
        elif stype == "salary_database":
            score -= 5
        return score

    return sorted(domains, key=domain_priority)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

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
    pipeline_start_time = time.time()
    urls_fetched = 0
    domains_processed = 0

    # Classify job title niche before anything else — drives TARGET and search strategy
    niche_level, title_variants, job_vertical = classify_job_niche(job_title, anthropic_client=client)
    TARGET_SOURCE_PAY_COUNT = TARGET_BY_NICHE[niche_level]
    print(f"[pipeline] Job niche: {niche_level} | TARGET={TARGET_SOURCE_PAY_COUNT} | variants={title_variants} | vertical={job_vertical}")

    # Cache check — if we have fresh results, skip discovery + fetch entirely
    cache_key = _get_cache_key(job_title, country, region)
    cached_rows = _load_cache(cache_key)
    _from_cache = False
    if cached_rows:
        rows = [dict(r) for r in cached_rows]
        _from_cache = True
        yield {
            "type": "progress",
            "value": 0.80,
            "text": f"Loaded {len(rows)} cached results (< {CACHE_TTL_HOURS}h old) — recalculating...",
        }

    if not _from_cache:
        # Step 1: Discover top sites (5%)
        yield {
            "type": "progress",
            "value": 0.05,
            "text": (
                f"Discovering top salary sites for {country} "
                f"[{niche_level} title, target {TARGET_SOURCE_PAY_COUNT} data points]..."
            ),
        }

        try:
            sites = discover_top_sites(country, serpapi_key, job_vertical=job_vertical)
        except Exception as e:
            yield {"type": "error", "message": f"Site discovery failed: {e}"}
            return

        if not sites:
            yield {"type": "error", "message": "No salary sites discovered. Check your SerpAPI key."}
            return

        # Resolve the country's native currency once — used as a fallback when Claude
        # extracts a pay number but fails to identify the currency code.
        country_currency = get_country_currency(country)

        # Steps 2 & 3: Search + fetch per site (10%–80%)
        source_pay_count = 0
        # TARGET_SOURCE_PAY_COUNT is already set adaptively above based on niche_level

        domain_yield: dict[str, dict] = {}  # domain -> {"valid_rows": int, "urls_fetched": int}
        _force_continue = False  # overrides TARGET check when floor condition fires
        seen_urls: set[str] = set()  # dedup — never fetch the same URL twice

        def _fetch_and_extract(url: str, src_type: str | None = None) -> tuple:
            """Fetch a single URL and run extraction. Returns (url, page_text, fetch_error, extracted)."""
            page_text, fetch_error = fetch_page(url)
            if not page_text:
                return url, None, fetch_error, None
            extracted = extract_salary(page_text, job_title, country, region, city, client, country_currency, source_type=src_type)
            return url, page_text, None, extracted

        # Pre-sort domains before the main loop: high-priority sources first.
        sites_queue = _pre_sort_domains(list(sites), country, job_vertical)
        i = 0

        while i < len(sites_queue):
            domain = sites_queue[i]

            # Skip permanently blocked domains
            if domain in FETCH_BLOCKLIST:
                i += 1
                continue

            if (source_pay_count >= TARGET_SOURCE_PAY_COUNT) and not _force_continue:
                break

            progress = 0.10 + (min(i, len(sites)) / max(len(sites), 1)) * 0.70
            yield {
                "type": "progress",
                "value": progress,
                "text": f"Searching {domain} ({i+1}/{len(sites_queue)}, {source_pay_count}/{TARGET_SOURCE_PAY_COUNT} data points)...",
            }

            try:
                urls = search_site(domain, job_title, country, region, city, description, serpapi_key, title_variants or None)
            except Exception as e:
                print(f"[pipeline] search_site({domain}) error: {e}")
                i += 1
                domains_processed += 1
                continue

            if not urls:
                i += 1
                domains_processed += 1
                continue

            # Deduplicate URLs — skip any already fetched this session
            urls = [u for u in urls if u not in seen_urls]

            # Per-domain state
            domain_had_valid = domain_yield.get(domain, {}).get("valid_rows", 0) > 0
            bail_limit = 5 if domain_had_valid else 4  # stricter bail-out for untested domains
            consecutive_wall = 0
            consecutive_network = 0
            consecutive_no_data = 0
            domain_valid_rows = 0
            domain_urls_fetched = 0
            domain_wall_hits = 0
            domain_network_errors = 0
            domain_start_time = time.time()

            # Get source type for this domain
            current_source_type = get_source_type(domain)

            # Process URLs in concurrent batches
            url_idx = 0
            while url_idx < len(urls):
                if (source_pay_count >= TARGET_SOURCE_PAY_COUNT) and not _force_continue:
                    break

                should_bail = (
                    consecutive_wall >= BAIL_LIMITS["wall"] or
                    consecutive_network >= BAIL_LIMITS["network"] or
                    consecutive_no_data >= bail_limit
                )
                if should_bail:
                    print(f"[pipeline] Bailing on {domain}: wall={consecutive_wall}, network={consecutive_network}, no_data={consecutive_no_data}")
                    break

                # 90-second wall-clock timeout per domain
                if time.time() - domain_start_time > DOMAIN_WALL_CLOCK_TIMEOUT:
                    yield {
                        "type": "progress",
                        "value": progress,
                        "text": f"{domain} timed out (90s wall-clock), moving on",
                    }
                    break

                batch = urls[url_idx:url_idx + FETCH_BATCH_SIZE]
                url_idx += FETCH_BATCH_SIZE
                batch_results: list = [None] * len(batch)

                with ThreadPoolExecutor(max_workers=FETCH_BATCH_SIZE) as executor:
                    future_to_idx = {
                        executor.submit(_fetch_and_extract, url, current_source_type): idx
                        for idx, url in enumerate(batch)
                    }
                    for future, idx in future_to_idx.items():
                        try:
                            batch_results[idx] = future.result(timeout=URL_FETCH_TIMEOUT)
                        except FuturesTimeoutError:
                            batch_results[idx] = (
                                batch[idx], None,
                                _make_error("fetch", "URL fetch timed out (35s)"),
                                None,
                            )
                        except Exception as e:
                            batch_results[idx] = (
                                batch[idx], None,
                                _make_error("fetch", str(e)),
                                None,
                            )

                # Yield results in original URL order
                for result in batch_results:
                    if result is None:
                        continue
                    url, page_text, fetch_error, extracted = result
                    seen_urls.add(url)
                    urls_fetched += 1
                    domain_urls_fetched += 1

                    if page_text is None:
                        row = _empty_row(domain, url, display_currency, fetch_error)
                        rows.append(row)
                        yield {"type": "row", "row": row}
                        error_class = _classify_fetch_error(fetch_error)
                        if error_class == "wall":
                            consecutive_wall += 1
                            consecutive_network = 0
                            consecutive_no_data = 0
                            domain_wall_hits += 1
                        elif error_class == "network":
                            consecutive_network += 1
                            consecutive_wall = 0
                            consecutive_no_data = 0
                            domain_network_errors += 1
                        else:
                            consecutive_no_data += 1
                            consecutive_wall = 0
                            consecutive_network = 0
                    else:
                        row = _build_row(domain, url, extracted, job_title, country, region, city, display_currency, current_source_type)
                        rows.append(row)
                        yield {"type": "row", "row": row}
                        if _has_data(row):
                            source_pay_count += 1
                            consecutive_wall = 0
                            consecutive_network = 0
                            consecutive_no_data = 0
                            domain_valid_rows += 1
                        else:
                            consecutive_no_data += 1
                            consecutive_wall = 0
                            consecutive_network = 0

                    # Check bail-out after each individual result (not just per batch)
                    should_bail = (
                        consecutive_wall >= BAIL_LIMITS["wall"] or
                        consecutive_network >= BAIL_LIMITS["network"] or
                        consecutive_no_data >= bail_limit
                    )
                    if should_bail:
                        break

            # Record domain yield stats
            domain_yield[domain] = {
                "valid_rows": domain_valid_rows,
                "urls_fetched": domain_urls_fetched,
            }

            # Emit health event for this domain
            yield {
                "type": "health",
                "domain": domain,
                "urls_fetched": domain_urls_fetched,
                "valid_rows": domain_valid_rows,
                "wall_hits": domain_wall_hits,
                "network_errors": domain_network_errors,
                "source_type": get_source_type(domain),
            }

            i += 1
            domains_processed += 1

            # Quality strategy switch at domain 10
            if domains_processed == QUALITY_SWITCH_DOMAINS:
                total_with_data_so_far = sum(1 for r in rows if _has_data(r))
                if total_with_data_so_far > 0 and source_pay_count / total_with_data_so_far < QUALITY_SWITCH_THRESHOLD:
                    old_niche = niche_level
                    if niche_level == "niche":
                        niche_level = "specialized"
                    elif niche_level == "specialized":
                        niche_level = "common"
                    if niche_level != old_niche:
                        print(f"[pipeline] Quality switch: {old_niche} → {niche_level} (only {source_pay_count}/{total_with_data_so_far} rows valid)")
                        yield {"type": "progress", "value": progress, "text": f"Low data quality detected — expanding search scope..."}

            # Minimum floor: if fewer than 20 data points after 15 domains, force continuation
            if domains_processed == MINIMUM_VALID_FLOOR_DOMAINS and source_pay_count < MINIMUM_VALID_FLOOR:
                _force_continue = True
                print(f"[pipeline] Floor triggered: only {source_pay_count} data points after {MINIMUM_VALID_FLOOR_DOMAINS} domains, forcing continuation")

            # Reorder remaining domains by yield rate
            if i < len(sites_queue):
                remaining = sites_queue[i:]
                sites_queue[i:] = _reorder_domains_by_yield(remaining, domain_yield)

    else:
        # When loaded from cache, resolve country_currency and seen_urls for second-pass use
        country_currency = get_country_currency(country)
        seen_urls: set[str] = set(r.get("web_search_result_url", "") for r in rows if r.get("web_search_result_url"))
        source_pay_count = sum(1 for r in rows if _has_data(r))
        sites = []

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

    # Cache exchange rates — one API call per unique currency pair per pipeline run
    rate_cache: dict[tuple[str, str], float | None] = {}

    def _get_rate(from_code: str, to_code: str) -> float | None:
        if from_code == to_code:
            return 1.0
        key = (from_code.upper(), to_code.upper())
        if key not in rate_cache:
            rate_cache[key] = convert_currency(1.0, from_code, to_code)
        return rate_cache[key]

    for row in rows:
        found_currency = row.get("found_currency")

        if display_pref == "Annual Salary":
            source_amount = row.get("found_annual_pay")
        else:
            source_amount = row.get("found_hourly_pay")

        if source_amount is None:
            row["display_pay_rate"] = None
            continue

        if not found_currency:
            inferred = country_currency
            if inferred:
                found_currency = inferred
                row["found_currency"] = inferred
                if not row.get("error_message"):
                    row["error_message"] = _make_error(
                        "currency", f"Currency inferred from country ({inferred})", recoverable=True
                    )
            else:
                row["display_pay_rate"] = None
                row["error_message"] = _make_error("currency", "Currency code missing — cannot convert")
                continue

        rate = _get_rate(found_currency, display_currency)
        if rate is not None:
            row["display_pay_rate"] = source_amount * rate
        else:
            row["display_pay_rate"] = None
            row["error_message"] = _make_error(
                "currency", f"Currency conversion failed ({found_currency} → {display_currency})"
            )

    # Step 6: Validation (90%)
    yield {"type": "progress", "value": 0.90, "text": "Validating results..."}

    # Deduplicate rows with identical (domain, found_annual_pay) before validation
    # to avoid the same data point being counted multiple times (e.g. levels.fyi)
    seen_pay_keys: set[tuple] = set()
    for row in rows:
        if row.get("display_pay_rate") is not None:
            key = (row.get("country_specific_site_url"), row.get("found_annual_pay"))
            if key in seen_pay_keys:
                row["display_pay_rate"] = None
                row["valid"] = 0
                row["validation_reason"] = "duplicate data point"
            else:
                seen_pay_keys.add(key)

    rows_with_data = [r for r in rows if r.get("display_pay_rate") is not None]

    if rows_with_data:
        validation_results = validate_rows_batch(
            rows_with_data, job_title, country, region, city, client,
            niche_level=niche_level, title_variants=title_variants,
        )

        valid_idx = 0
        for row in rows:
            if row.get("display_pay_rate") is not None:
                if valid_idx < len(validation_results):
                    vr = validation_results[valid_idx]
                    row["valid"] = vr.get("valid", 0)
                    row["validation_reason"] = vr.get("validation_reason")
                    if row["valid"] == 0 and vr.get("validation_reason"):
                        row["error_message"] = vr["validation_reason"]
                else:
                    row["valid"] = 0
                    row["validation_reason"] = "missing from response"
                valid_idx += 1
            else:
                row["valid"] = 0
                row["validation_reason"] = "null pay rate"
    else:
        for row in rows:
            row["valid"] = 0
            row["validation_reason"] = "null pay rate"

    valid_df = pd.DataFrame(rows, columns=SCHEMA)
    valid_df = valid_df[valid_df["valid"] == 1].copy()
    valid_count = len(valid_df)

    # Second pass: if insufficient valid data, retry with title variants + relaxed geo
    if valid_count < 7 and not _from_cache and title_variants:
        yield {
            "type": "progress",
            "value": 0.92,
            "text": f"Only {valid_count} valid rows — running second pass with expanded search...",
        }
        print(f"[pipeline] Second pass triggered: {valid_count} valid rows, trying {len(title_variants)} title variants")

        second_pass_domains = _pre_sort_domains(list(sites)[:10], country, job_vertical)

        for variant_title in title_variants[:3]:
            for sp_domain in second_pass_domains[:5]:
                if sp_domain in FETCH_BLOCKLIST:
                    continue
                try:
                    sp_urls = search_site(
                        sp_domain, variant_title, country, "", "",
                        description, serpapi_key, title_variants=None,
                    )
                except Exception:
                    continue
                for sp_url in sp_urls[:2]:
                    if sp_url in seen_urls:
                        continue
                    page_text, fetch_error = fetch_page(sp_url)
                    seen_urls.add(sp_url)
                    if page_text:
                        sp_source_type = get_source_type(sp_domain)
                        sp_extracted = extract_salary(
                            page_text, variant_title, country, "", "", client,
                            country_currency, source_type=sp_source_type,
                        )
                        sp_row = _build_row(sp_domain, sp_url, sp_extracted, variant_title, country, "", "", display_currency, sp_source_type)
                        rows.append(sp_row)
                        yield {"type": "row", "row": sp_row}

        # Re-run normalization and currency conversion on new rows only
        for row in rows:
            if row.get("display_pay_rate") is not None:
                continue  # already processed
            annual = row.get("found_annual_pay")
            hourly = row.get("found_hourly_pay")
            if hourly and not annual:
                row["found_annual_pay"] = hourly * HOURS_PER_YEAR
            elif annual and not hourly:
                row["found_hourly_pay"] = annual / HOURS_PER_YEAR

            found_currency = row.get("found_currency") or country_currency
            if found_currency:
                row["found_currency"] = found_currency

            if display_pref == "Annual Salary":
                source_amount = row.get("found_annual_pay")
            else:
                source_amount = row.get("found_hourly_pay")

            if source_amount is not None and found_currency:
                rate = _get_rate(found_currency, display_currency)
                if rate is not None:
                    row["display_pay_rate"] = source_amount * rate

        # Re-validate all rows with data (including new ones)
        all_rows_with_data = [r for r in rows if r.get("display_pay_rate") is not None and r.get("valid") is None]
        if all_rows_with_data:
            sp_validation = validate_rows_batch(
                all_rows_with_data, job_title, country, region, city, client,
                niche_level=niche_level, title_variants=title_variants,
            )
            vsp_idx = 0
            for row in rows:
                if row.get("display_pay_rate") is not None and row.get("valid") is None:
                    if vsp_idx < len(sp_validation):
                        vr = sp_validation[vsp_idx]
                        row["valid"] = vr.get("valid", 0)
                        row["validation_reason"] = vr.get("validation_reason")
                    vsp_idx += 1

        # Recount valid rows
        valid_df = pd.DataFrame(rows, columns=SCHEMA)
        valid_df = valid_df[valid_df["valid"] == 1].copy()
        valid_count = len(valid_df)
        print(f"[pipeline] Second pass complete: {valid_count} total valid rows")

    # Save to cache after validation if valid_count >= 5
    if valid_count >= 5 and not _from_cache:
        valid_rows_for_cache = [r for r in rows if r.get("valid") == 1]
        _save_cache(cache_key, valid_rows_for_cache)

    # Build DataFrame (after all second pass processing)
    df = pd.DataFrame(rows, columns=SCHEMA)
    yield {"type": "stats", "df": df}

    # Step 7: Generate AI Summary with quality gate (95%)
    yield {"type": "progress", "value": 0.95, "text": "Generating AI summary..."}

    valid_df = df[df["valid"] == 1].copy() if len(df) > 0 else pd.DataFrame()
    valid_count = len(valid_df)

    if valid_count < 5:
        # Insufficient data — return a stub instead of calling the model
        rejection_reasons = list({
            r.get("validation_reason") or r.get("error_message") or "unknown"
            for r in rows
            if r.get("valid") != 1 and (r.get("validation_reason") or r.get("error_message"))
        })[:10]
        summary_data = _build_summary_stub(valid_count, rejection_reasons)
    elif valid_count < 10:
        # Moderate confidence — instruct Sonnet to caveat its output
        try:
            summary_data = generate_summary(
                job_title=job_title, country=country, region=region, city=city,
                display_pref=display_pref, display_currency=display_currency,
                valid_rows_df=valid_df, client=client, moderate_confidence=True,
            )
        except Exception as e:
            print(f"[pipeline] generate_summary error: {e}")
            summary_data = None
    else:
        try:
            summary_data = generate_summary(
                job_title=job_title, country=country, region=region, city=city,
                display_pref=display_pref, display_currency=display_currency,
                valid_rows_df=valid_df, client=client,
            )
        except Exception as e:
            print(f"[pipeline] generate_summary error: {e}")
            summary_data = None

    yield {"type": "summary", "data": summary_data}

    # Write session log
    rows_with_data = [r for r in rows if r.get("display_pay_rate") is not None]
    try:
        log = {
            "run_id": str(uuid.uuid4()),
            "job_title": job_title,
            "country": country,
            "niche_level": niche_level,
            "title_variants": title_variants,
            "job_vertical": job_vertical,
            "domains_tried": domains_processed,
            "urls_fetched": urls_fetched,
            "rows_extracted": len(rows),
            "rows_validated": len(rows_with_data),
            "rows_valid": valid_count,
            "from_cache": _from_cache,
            "duration_seconds": round(time.time() - pipeline_start_time, 2),
            "confidence_level": "High" if valid_count >= 10 else "Moderate" if valid_count >= 5 else "Limited",
        }
        _append_log(log)
        print(f"[pipeline] Session log appended: {log['run_id']}")
    except Exception as e:
        print(f"[pipeline] Failed to write session log: {e}")

    # Complete
    yield {"type": "progress", "value": 1.0, "text": "Complete"}
    yield {"type": "complete"}


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def _build_row(
    domain: str,
    url: str,
    extracted: dict,
    job_title: str,
    country: str,
    region: str,
    city: str,
    display_currency: str,
    source_type: str | None = None,    # NEW
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
        "found_pay_low": extracted.get("found_pay_low"),
        "found_pay_high": extracted.get("found_pay_high"),
        "display_currency": display_currency,
        "display_pay_rate": None,
        "country": extracted.get("found_country") or country,
        "region": extracted.get("found_region") or region,
        "city": extracted.get("found_city") or city,
        "remote_ok": extracted.get("remote_ok", 0),
        "source_type": source_type,
        "valid": None,
        "error_message": _make_error("extract", extraction_error) if extraction_error else None,
        "validation_reason": None,
        "confidence": extracted.get("confidence"),
        "reasoning": extracted.get("reasoning"),
    }


def _has_data(row: dict) -> bool:
    """
    Count a source URL as one data point if it has a usable pay rate.
    A source with both annual AND hourly counts as ONE — not two.
    Do NOT evaluate this after Step 4 normalization (which derives the missing
    rate for every row, making every row appear to have both).
    """
    return (
        row.get("found_annual_pay") is not None or
        row.get("found_hourly_pay") is not None
    )


def _empty_row(domain: str, url: str, display_currency: str, error_message: str | None = None) -> dict:
    return {
        "country_specific_site_url": domain,
        "web_search_result_url": url,
        "job_title": None,
        "found_currency": None,
        "found_annual_pay": None,
        "found_hourly_pay": None,
        "found_pay_low": None,
        "found_pay_high": None,
        "display_currency": display_currency,
        "display_pay_rate": None,
        "country": None,
        "region": None,
        "city": None,
        "remote_ok": 0,
        "source_type": None,
        "valid": 0,
        "error_message": _make_error("fetch", error_message or "Page fetch failed") if error_message else None,
        "validation_reason": None,
    }
