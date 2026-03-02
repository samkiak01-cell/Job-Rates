"""
search.py — Web search strategy for Job Rate Finder
Broad queries to maximize data points. No experience/level in search terms.
"""

from __future__ import annotations

from typing import Any, Dict, List

from utils import (
    MAX_SEARCH_RESULTS,
    SERPAPI_URL,
    host_of,
    http_get,
    is_blocked,
    secret,
    source_quality,
)


def build_queries(job: str, country: str, state: str, city: str) -> List[str]:
    """
    Build deliberately broad search queries.

    KEY DESIGN DECISIONS:
    - NO experience level or years in queries (shrinks dataset too much)
    - NO job description keywords in queries (adds noise, reduces relevance)
    - Mix of generic + site-specific queries for coverage
    - Location at varying specificity levels to capture regional + national data
    """
    loc_full = ", ".join(x for x in [city, state, country] if x)
    loc_region = ", ".join(x for x in [state, country] if x) or country

    # Core job title — strip any extra context that was appended
    core_job = job.split("|")[0].strip() if "|" in job else job.strip()

    queries = [
        # ── Broad salary queries (no site restriction) ───
        f'"{core_job}" salary {country}',
        f'"{core_job}" average salary {loc_region}',
        f'"{core_job}" salary range {country}',
        f'"{core_job}" compensation {loc_region}',
        f'"{core_job}" pay scale {country}',

        # ── Site-specific for high-quality salary DBs ────
        f'site:glassdoor.com "{core_job}" salary {country}',
        f'site:indeed.com "{core_job}" salary {country}',
        f'site:payscale.com "{core_job}" salary {country}',
        f'site:salary.com "{core_job}" salary {country}',
        f'site:levels.fyi "{core_job}" compensation',
        f'site:ziprecruiter.com "{core_job}" salary {country}',

        # ── Hourly / contract rate queries ───────────────
        f'"{core_job}" hourly rate {country}',
    ]

    # If city is specified, add city-specific queries
    if city:
        queries.insert(2, f'"{core_job}" salary {loc_full}')
        queries.insert(5, f'"{core_job}" compensation {loc_full}')

    return queries


def search_web(job: str, country: str, state: str, city: str) -> List[Dict[str, Any]]:
    """
    Execute search queries and return deduplicated, scored results.
    Returns up to MAX_SEARCH_RESULTS items sorted by source quality.
    """
    key = secret("SERPAPI_API_KEY")
    queries = build_queries(job, country, state, city)

    results: List[Dict] = []
    seen_urls: set = set()
    seen_hosts_count: Dict[str, int] = {}

    for q in queries:
        if len(results) >= MAX_SEARCH_RESULTS:
            break
        try:
            r = http_get(
                SERPAPI_URL,
                params={"engine": "google", "q": q, "api_key": key, "num": 10},
            )
            r.raise_for_status()
            data = r.json()

            for item in data.get("organic_results") or []:
                url = (item.get("link") or "").strip()
                if not url or not url.startswith("http"):
                    continue
                if is_blocked(url):
                    continue
                if url in seen_urls:
                    continue

                h = host_of(url)

                # Limit per-host to avoid one source dominating
                host_count = seen_hosts_count.get(h, 0)
                if host_count >= 5:
                    continue

                seen_urls.add(url)
                seen_hosts_count[h] = host_count + 1

                results.append({
                    "url": url,
                    "title": (item.get("title") or "")[:200],
                    "snippet": (item.get("snippet") or "")[:500],
                    "host": h,
                    "quality": source_quality(url),
                    "query": q[:80],
                })

        except Exception:
            continue

    # Sort by quality descending, then by snippet length (more content = better)
    results.sort(key=lambda x: (x["quality"], len(x.get("snippet", ""))), reverse=True)
    return results[:MAX_SEARCH_RESULTS]
