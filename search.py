"""
search.py -- Web search strategy for Job Rate Finder
Aggressive multi-query approach to maximize unique sources and data points.
"""

from __future__ import annotations

import datetime
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


def build_queries(job: str, country: str, state: str, city: str) -> List[str]:
    """
    Build an aggressive set of search queries to maximize unique sources.

    Strategy:
    - 6+ generic queries with varying keywords (salary, pay, compensation, wage, earnings)
    - 12 site-specific queries hitting every major salary database
    - Location at multiple granularity levels
    - Variant phrasings to catch different page types
    - NO experience/level in queries (shrinks results)
    - NO job description text (adds noise)
    """
    core_job = job.split("|")[0].strip() if "|" in job else job.strip()
    loc_full = ", ".join(x for x in [city, state, country] if x)
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

    # -- State/region queries (if state provided but different from country) --
    if state and state != country:
        queries += [
            f'"{core_job}" salary {state}',
            f'"{core_job}" average pay {state} {country}',
        ]

    # -- Site-specific queries for every major salary DB --
    for site in SALARY_SITES:
        queries.append(f'site:{site} "{core_job}" salary {country}')

    # -- Country-specific local salary site queries --
    country_sites = COUNTRY_SALARY_SITES.get(country, [])
    for site in country_sites:
        queries.append(f'site:{site} "{core_job}" salary')
        queries.append(f'site:{site} {core_job}')

    # -- Local-language queries --
    local_templates = COUNTRY_LOCAL_QUERIES.get(country, [])
    for tmpl in local_templates:
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


def search_web(job: str, country: str, state: str, city: str) -> List[Dict[str, Any]]:
    """
    Execute all queries and return deduplicated, quality-scored results.
    Aims to collect as many unique sources as possible up to MAX_SEARCH_RESULTS.
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
        # If too many queries are failing, stop early
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

                # Allow up to 6 results per host (increased for more data)
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

    # Sort: high-quality salary sites first, then by snippet richness
    results.sort(key=lambda x: (x["quality"], len(x.get("snippet", ""))), reverse=True)
    return results[:MAX_SEARCH_RESULTS]
