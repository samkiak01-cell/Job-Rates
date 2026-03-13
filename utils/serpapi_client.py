import requests
from typing import Optional

SALARY_SITE_WHITELIST = {
    "indeed.com", "glassdoor.com", "salary.com", "payscale.com",
    "dice.com", "ziprecruiter.com", "linkedin.com", "monster.com",
    "totaljobs.com", "reed.co.uk", "seek.com.au", "levels.fyi",
    "builtin.com", "comparably.com", "simplyhired.com", "careerbliss.com",
    "jobstreet.com", "naukri.com", "stepstone.de", "jobs.ch",
    "michaelpage.com", "roberthalf.com", "hays.com", "ambitionbox.com",
    "talent.com", "salaryexpert.com", "erieri.com", "jobsora.com",
}

SERPAPI_BASE = "https://serpapi.com/search"


def discover_top_sites(country: str, api_key: str) -> list[str]:
    """Discover top salary data sites for the given country using SerpAPI."""
    query = f"top salary data job sites {country}"

    params = {
        "engine": "google",
        "q": query,
        "num": 30,
        "api_key": api_key,
    }

    try:
        resp = requests.get(SERPAPI_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[serpapi] discover_top_sites error: {e}")
        # Fall back to whitelist defaults
        return list(SALARY_SITE_WHITELIST)[:20]

    organic = data.get("organic_results", [])

    # Score domains
    domain_scores: dict[str, int] = {}

    for result in organic:
        link = result.get("link", "")
        domain = _extract_domain(link)
        if not domain:
            continue

        if domain not in domain_scores:
            domain_scores[domain] = 0

        # +3 if in whitelist
        if _matches_whitelist(domain):
            domain_scores[domain] += 3

        # +1 per organic result appearance
        domain_scores[domain] += 1

    # Sort by score descending, take top 20 unique domains
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    top_domains = [d for d, _ in sorted_domains[:20]]

    # If we got fewer than 20, pad with whitelist defaults
    if len(top_domains) < 20:
        for wl_domain in SALARY_SITE_WHITELIST:
            if wl_domain not in top_domains:
                top_domains.append(wl_domain)
            if len(top_domains) >= 20:
                break

    return top_domains[:20]


def search_site(
    domain: str,
    job_title: str,
    country: str,
    region: str,
    city: str,
    description: str,
    api_key: str,
) -> list[str]:
    """Search a specific site for salary pages matching the job criteria."""
    location_parts = [p for p in [city, region, country] if p]
    location_str = " ".join(location_parts)
    query = f"site:{domain} {job_title} {location_str} salary"

    params = {
        "engine": "google",
        "q": query,
        "num": 10,
        "api_key": api_key,
    }

    try:
        resp = requests.get(SERPAPI_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[serpapi] search_site({domain}) error: {e}")
        return []

    organic = data.get("organic_results", [])
    urls = [r.get("link", "") for r in organic if r.get("link")]
    return urls[:10]


def _extract_domain(url: str) -> str:
    """Extract root domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        # Remove www. prefix
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def _matches_whitelist(domain: str) -> bool:
    """Check if domain matches any whitelist entry."""
    for wl in SALARY_SITE_WHITELIST:
        if domain == wl or domain.endswith("." + wl) or wl.endswith("." + domain):
            return True
    return False
