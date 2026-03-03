"""
scraper.py — Direct salary page scraper for Job Rate Finder
Supplements SerpAPI by visiting salary sites directly and extracting snippets.
Returns results in the same shape as SerpAPI results so they feed the same pipeline.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus

from utils import host_of, source_quality

# Browser-like headers to reduce bot detection
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Regex patterns to find salary figures in page text
_SALARY_PATTERNS = [
    # "$72,000" or "$72k" or "USD 72,000"
    r"\$\s?[\d,]+(?:\.\d+)?(?:\s?[Kk])?",
    r"USD\s?[\d,]+(?:\.\d+)?(?:\s?[Kk])?",
    # "72,000 USD" or "72K USD"
    r"[\d,]+(?:\.\d+)?(?:\s?[Kk])?\s?USD",
    # Local currency with numbers: "R$ 5,000" "€ 45,000" "£ 38,000"
    r"(?:R\$|€|£|¥|₹|S\$|A\$|C\$)\s?[\d,]+(?:\.\d+)?(?:\s?[Kk])?",
    # "5,000 per month" "45,000 per year" (context gives us the figure)
    r"[\d,]+(?:\.\d+)?\s?(?:per|/)\s?(?:month|year|yr|mo|hr|hour)",
]

_SALARY_RE = re.compile("|".join(_SALARY_PATTERNS), re.IGNORECASE)


def _job_slug(job: str) -> str:
    """'Software Engineer' → 'software-engineer'"""
    return re.sub(r"\s+", "-", job.strip().lower())


def _job_slug_title(job: str) -> str:
    """'Software Engineer' → 'Software-Engineer'"""
    return "-".join(w.capitalize() for w in job.strip().split())


def _loc_slug(text: str) -> str:
    return re.sub(r"\s+", "-", text.strip().lower())


def _country_code_2(country: str) -> str:
    _MAP = {
        "United States": "US", "United Kingdom": "GB", "Canada": "CA",
        "Australia": "AU", "Germany": "DE", "France": "FR", "Spain": "ES",
        "Italy": "IT", "Brazil": "BR", "Mexico": "MX", "India": "IN",
        "Japan": "JP", "Philippines": "PH", "Singapore": "SG",
        "Netherlands": "NL", "Sweden": "SE", "Switzerland": "CH",
        "Ireland": "IE", "New Zealand": "NZ", "South Korea": "KR",
        "China": "CN", "UAE": "AE", "Saudi Arabia": "SA",
        "South Africa": "ZA", "Poland": "PL", "Israel": "IL",
    }
    return _MAP.get(country, "US")


def _build_scraper_urls(job: str, country: str, state: str, city: str) -> List[Tuple[str, str]]:
    """Return list of (url, host_label) tuples to scrape."""
    slug    = _job_slug(job)
    slug2   = _job_slug_title(job)
    enc     = quote_plus(job)
    c2      = _country_code_2(country)
    c_lower = country.lower().replace(" ", "-")

    loc_parts = [p for p in [city, state, country] if p]
    loc_enc   = quote_plus(", ".join(loc_parts)) if loc_parts else quote_plus(country)
    city_slug = _loc_slug(city) if city else _loc_slug(country)

    targets: List[Tuple[str, str]] = [
        (f"https://www.talent.com/salary?job={enc}&location={loc_enc}", "talent.com"),
        (f"https://www.salaryexpert.com/salary/{city_slug}/{slug}", "salaryexpert.com"),
        (f"https://www.ziprecruiter.com/Salaries/{slug2}-Salary", "ziprecruiter.com"),
        (f"https://www.careerbliss.com/facts-and-figures/careerbliss-salary-information/{slug}/", "careerbliss.com"),
        (f"https://www.simplyhired.com/{slug}-salaries", "simplyhired.com"),
        (f"https://www.comparably.com/salaries/{slug}-salary", "comparably.com"),
        (f"https://www.payscale.com/research/{c2}/Job={slug2}/Salary", "payscale.com"),
        (f"https://jobted.com/{c_lower}/jobs/{slug}/salary", "jobted.com"),
    ]
    return targets


def _extract_jsonld_snippet(soup) -> str:
    """Try to extract a salary snippet from JSON-LD structured data."""
    try:
        from bs4 import BeautifulSoup  # local import to keep module-level clean
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    t = (item.get("@type") or "").lower()
                    if "occupation" in t or "joboffer" in t or "jobposting" in t:
                        est = item.get("estimatedSalary") or item.get("baseSalary") or {}
                        if est:
                            val = est.get("value") or {}
                            lo  = val.get("minValue") or est.get("minValue") or ""
                            hi  = val.get("maxValue") or est.get("maxValue") or ""
                            cur = est.get("currency") or val.get("currency") or "USD"
                            unit = val.get("unitText") or est.get("unitText") or "YEAR"
                            if lo or hi:
                                return f"Salary: {cur} {lo}–{hi} per {unit.lower()}"
            except Exception:
                continue
    except Exception:
        pass
    return ""


def _extract_meta_snippet(soup) -> str:
    """Extract salary info from meta description tags."""
    try:
        for name in ["description", "og:description", "twitter:description"]:
            tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
            if tag:
                content = (tag.get("content") or "").strip()
                if content and _SALARY_RE.search(content):
                    return content[:500]
    except Exception:
        pass
    return ""


def _extract_text_snippet(soup) -> str:
    """Regex scan on visible page text for salary patterns."""
    try:
        # Remove script/style to keep clean text
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Find salary mentions
        matches = _SALARY_RE.findall(text)
        if matches:
            # Return first 3 unique matches as a snippet
            seen = []
            for m in matches:
                m = m.strip()
                if m and m not in seen:
                    seen.append(m)
                if len(seen) >= 3:
                    break
            return " | ".join(seen)
    except Exception:
        pass
    return ""


def _scrape_one(url: str, host: str) -> Optional[Dict]:
    """Fetch one salary page and return a result dict, or None on failure."""
    import requests
    try:
        r = requests.get(url, headers=_HEADERS, timeout=10, allow_redirects=True)
        if r.status_code not in (200, 203):
            return None
        ct = r.headers.get("content-type", "")
        if "html" not in ct:
            return None
        html = r.text
        if len(html) < 500:
            return None

        # Parse with BeautifulSoup (lxml preferred, html.parser fallback)
        try:
            from bs4 import BeautifulSoup
            try:
                soup = BeautifulSoup(html, "lxml")
            except Exception:
                soup = BeautifulSoup(html, "html.parser")
        except ImportError:
            return None

        # Extract title
        title_tag = soup.find("title")
        title = (title_tag.get_text(strip=True) if title_tag else host)[:200]

        # Try extraction methods in priority order
        snippet = _extract_jsonld_snippet(soup)
        if not snippet:
            snippet = _extract_meta_snippet(soup)
        if not snippet:
            snippet = _extract_text_snippet(soup)

        if not snippet:
            return None

        return {
            "url": url,
            "title": title,
            "snippet": snippet[:500],
            "host": host,
            "quality": source_quality(url),
        }
    except Exception:
        return None


def run_scraper(job: str, country: str, state: str, city: str) -> List[Dict]:
    """
    Directly scrape salary pages for the given job+location.
    Returns results in the same shape as SerpAPI organic results.
    Hard cap: 30 seconds total, 10 seconds per page.
    Failures are silently skipped — scraper is supplemental, not critical.
    """
    targets = _build_scraper_urls(job, country, state, city)
    results: List[Dict] = []

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(_scrape_one, url, host): (url, host)
            for url, host in targets
        }
        for future in as_completed(futures, timeout=30):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception:
                pass

    return results
