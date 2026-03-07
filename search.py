"""
search.py -- Web search strategy for Job Rate Finder
Runs SerpAPI queries in parallel for maximum source coverage with minimal latency.
"""

from __future__ import annotations

import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from utils import (
    COUNTRY_LOCAL_QUERIES,
    COUNTRY_SALARY_SITES,
    MAX_SEARCH_RESULTS,
    SERPAPI_URL,
    get_country_codes,
    host_of,
    http_get,
    is_blocked,
    secret,
    source_quality,
)

_CURRENT_YEAR = datetime.date.today().year

# Salary-specific sites to query individually
SALARY_SITES = [
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

# Max parallel SerpAPI workers — balances speed vs rate limits
_SERP_WORKERS = 8


def build_queries(job: str, country: str, state: str, city: str) -> List[str]:
    """
    Build an aggressive set of search queries to maximize unique sources.

    Strategy:
    - 12 generic queries with varying keywords
    - 12 site-specific queries hitting every major salary database
    - Country-specific local salary site queries
    - Local-language templates
    - 5 alternate phrasing queries
    """
    core_job = job.split("|")[0].strip() if "|" in job else job.strip()
    loc_full   = ", ".join(x for x in [city, state, country] if x)
    loc_region = ", ".join(x for x in [state, country] if x) or country

    queries = []

    # -- Broad queries (no site restriction) --
    queries += [
        f'"{core_job}" salary {country}',
        f'"{core_job}" average salary {loc_region}',
        f'"{core_job}" salary range {country}',
        f'"{core_job}" compensation {country}',
        f'"{core_job}" pay {country}',
        f'"{core_job}" wage {country}',
        f'"{core_job}" earnings {country}',
        f'"{core_job}" salary survey {country}',
        f'"{core_job}" total compensation {country}',
        f'"{core_job}" hourly rate {country}',
        f'how much does a {core_job} make in {country}',
        f'{core_job} salary guide {country}',
    ]

    # -- City-specific queries (if city provided) --
    if city:
        queries += [
            f'"{core_job}" salary {loc_full}',
            f'"{core_job}" pay {loc_full}',
            f'"{core_job}" compensation {loc_full}',
            f'how much does a {core_job} make in {city}',
            f'"{core_job}" salary {city} {state}',
            f'site:glassdoor.com "{core_job}" salary {city}',
            f'site:indeed.com "{core_job}" salary {city}',
        ]

    # -- State/region queries (if state provided) --
    if state and state != country:
        queries += [
            f'"{core_job}" salary {state}',
            f'"{core_job}" average pay {state} {country}',
            f'"{core_job}" salary range {state}',
            f'site:glassdoor.com "{core_job}" salary {state}',
            f'site:indeed.com "{core_job}" salary {state}',
        ]

    # -- Site-specific queries for every major salary DB --
    for site in SALARY_SITES:
        queries.append(f'site:{site} "{core_job}" salary {country}')

    # -- Country-specific local salary site queries --
    for site in COUNTRY_SALARY_SITES.get(country, []):
        queries.append(f'site:{site} "{core_job}" salary')
        queries.append(f'site:{site} {core_job}')

    # -- Local-language queries --
    for tmpl in COUNTRY_LOCAL_QUERIES.get(country, []):
        queries.append(tmpl.format(job=core_job))

    # -- Alternate phrasing queries --
    queries += [
        f'{core_job} salary range {country} {_CURRENT_YEAR - 1} {_CURRENT_YEAR}',
        f'{core_job} salary percentile {country}',
        f'{core_job} entry level salary {country}',
        f'{core_job} senior salary {country}',
        f'{core_job} median salary {country}',
    ]

    return queries


def _location_relevance_score(text: str, city: str, state: str) -> int:
    """
    Return a bonus score (0–15) if the text mentions the target city or state.
    Used to up-rank sources that are clearly location-specific.
    """
    if not text:
        return 0
    tl = text.lower()
    score = 0
    if city and city.lower() in tl:
        score += 15
    elif state and state.lower() in tl:
        score += 8
    return score


def _fetch_one(q: str, key: str, gl: str, hl: str) -> tuple[str, list]:
    """Fetch one SerpAPI query. Returns (query, organic_results)."""
    try:
        params = {"engine": "google", "q": q, "api_key": key, "num": 10}
        if gl:
            params["gl"] = gl
            params["hl"] = hl
        r = http_get(SERPAPI_URL, params=params, timeout=20)
        r.raise_for_status()
        return q, (r.json().get("organic_results") or [])
    except Exception:
        return q, []


def _search_serpapi(job: str, country: str, state: str, city: str, plan: dict = {}) -> List[Dict[str, Any]]:
    """
    Execute all SerpAPI queries in parallel and return deduplicated, quality-scored results.
    Collects up to MAX_SEARCH_RESULTS unique sources.
    """
    key = secret("SERPAPI_API_KEY")
    queries = build_queries(job, country, state, city)
    gl, hl = get_country_codes(country)

    # ── Append planner query strategies ──
    location = ", ".join(x for x in [city, state, country] if x) or country
    for tmpl in (plan.get("query_strategies") or []):
        try:
            queries.append(tmpl.format(job=job, location=location))
        except KeyError:
            pass

    # ── Append planner target sites not already in SALARY_SITES ──
    existing_site_set = set(SALARY_SITES)
    for site in (plan.get("target_sites") or []):
        if site not in existing_site_set:
            queries.append(f'site:{site} "{job}" salary')

    # Deduplicate queries while preserving order
    seen_q: set = set()
    unique_queries: List[str] = []
    for q in queries:
        if q not in seen_q:
            seen_q.add(q)
            unique_queries.append(q)

    # ── Parallel fetch — all queries fire concurrently ──
    all_items: List[tuple[str, dict]] = []  # (query, item)
    with ThreadPoolExecutor(max_workers=_SERP_WORKERS) as pool:
        futures = {pool.submit(_fetch_one, q, key, gl, hl): q for q in unique_queries}
        for future in as_completed(futures, timeout=90):
            try:
                q, items = future.result(timeout=25)
                for item in items:
                    all_items.append((q, item))
            except Exception:
                continue

    # ── Serial deduplication + scoring ──
    results: List[Dict] = []
    seen_urls: set = set()
    seen_hosts_count: Dict[str, int] = {}

    for q, item in all_items:
        if len(results) >= MAX_SEARCH_RESULTS:
            break

        url = (item.get("link") or "").strip()
        if not url or not url.startswith("http"):
            continue
        if is_blocked(url):
            continue
        if url in seen_urls:
            continue

        h = host_of(url)
        if seen_hosts_count.get(h, 0) >= 6:
            continue

        seen_urls.add(url)
        seen_hosts_count[h] = seen_hosts_count.get(h, 0) + 1

        snippet = (item.get("snippet") or "")[:500]
        title   = (item.get("title") or "")[:200]

        # Location-relevance bonus — boosts city/state-specific sources
        loc_bonus = _location_relevance_score(snippet + " " + title, city, state)
        base_quality = source_quality(url)

        results.append({
            "url": url,
            "title": title,
            "snippet": snippet,
            "host": h,
            "quality": base_quality + loc_bonus,
            "query": q[:80],
        })

    # Sort: quality desc, then snippet length (more text = more data for Claude)
    results.sort(key=lambda x: (x["quality"], len(x.get("snippet", ""))), reverse=True)
    return results


def search_web(job: str, country: str, state: str, city: str, plan: dict = {}) -> List[Dict[str, Any]]:
    """
    Run SerpAPI queries in parallel and return deduplicated, quality-sorted results.
    Accepts an optional SearchPlan dict from site_planner to enrich queries.
    """
    return _search_serpapi(job, country, state, city, plan)
