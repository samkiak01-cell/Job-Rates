"""
search.py -- Web search strategy for Job Rate Finder
Runs SerpAPI queries and direct scraping in parallel for maximum source coverage.
"""

from __future__ import annotations

import datetime
from concurrent.futures import ThreadPoolExecutor
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
from scraper import run_scraper

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
        ]

    # -- State/region queries (if state provided) --
    if state and state != country:
        queries += [
            f'"{core_job}" salary {state}',
            f'"{core_job}" average pay {state} {country}',
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


def _search_serpapi(job: str, country: str, state: str, city: str) -> List[Dict[str, Any]]:
    """
    Execute all SerpAPI queries and return deduplicated, quality-scored results.
    Collects up to MAX_SEARCH_RESULTS unique sources.
    """
    key = secret("SERPAPI_API_KEY")
    queries = build_queries(job, country, state, city)
    gl, hl = get_country_codes(country)

    results: List[Dict] = []
    seen_urls: set = set()
    seen_hosts_count: Dict[str, int] = {}
    failed_queries = 0

    for q in queries:
        if len(results) >= MAX_SEARCH_RESULTS:
            break
        if failed_queries > 5:
            break
        try:
            params = {"engine": "google", "q": q, "api_key": key, "num": 10}
            if gl:
                params["gl"] = gl
                params["hl"] = hl
            r = http_get(SERPAPI_URL, params=params)
            r.raise_for_status()
            data = r.json()

            found_any = False
            for item in data.get("organic_results") or []:
                url = (item.get("link") or "").strip()
                if not url or not url.startswith("http"):
                    continue
                if is_blocked(url):
                    continue
                if url in seen_urls:
                    continue

                h = host_of(url)
                host_count = seen_hosts_count.get(h, 0)
                if host_count >= 6:
                    continue

                seen_urls.add(url)
                seen_hosts_count[h] = host_count + 1
                found_any = True

                results.append({
                    "url": url,
                    "title": (item.get("title") or "")[:200],
                    "snippet": (item.get("snippet") or "")[:500],
                    "host": h,
                    "quality": source_quality(url),
                    "query": q[:80],
                })

            if not found_any:
                failed_queries += 1

        except Exception:
            failed_queries += 1
            continue

    results.sort(key=lambda x: (x["quality"], len(x.get("snippet", ""))), reverse=True)
    return results


def _merge_sources(serp: List[Dict], scraped: List[Dict]) -> List[Dict]:
    """Combine SerpAPI + scraped results, deduplicate by URL, re-sort by quality."""
    combined: List[Dict] = list(serp)
    seen_urls = {r["url"] for r in serp}

    for r in scraped:
        if r.get("url") and r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            combined.append(r)

    combined.sort(key=lambda x: (x.get("quality", 0), len(x.get("snippet", ""))), reverse=True)
    return combined[:MAX_SEARCH_RESULTS]


def search_web(job: str, country: str, state: str, city: str) -> List[Dict[str, Any]]:
    """
    Run SerpAPI queries and direct scraper in parallel, then merge results.
    Aims to collect 80–150 unique sources before sending to Claude.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        serp_future    = pool.submit(_search_serpapi, job, country, state, city)
        scraper_future = pool.submit(run_scraper,     job, country, state, city)

        serp_results    = serp_future.result(timeout=180)
        scraper_results = scraper_future.result(timeout=40)

    return _merge_sources(serp_results, scraper_results)
