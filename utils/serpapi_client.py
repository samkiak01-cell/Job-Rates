import re
import requests
from typing import Optional

SALARY_SITE_WHITELIST = {
    # English-language / global salary data sites
    "indeed.com", "glassdoor.com", "salary.com", "payscale.com",
    "linkedin.com", "monster.com", "totaljobs.com", "reed.co.uk",
    "levels.fyi", "comparably.com", "careerbliss.com",
    "stepstone.de", "talent.com", "salaryexpert.com", "erieri.com",
    "michaelpage.com", "roberthalf.com", "glassdoor.co.uk",
    # Poland-specific
    "pracuj.pl", "wynagrodzenia.pl", "nofluffjobs.com", "justjoin.it",
    "praca.pl", "bulldogjob.pl", "pensjometr.pl",
    # Broader Europe
    "stepstone.com", "jobijoba.com", "loonwijzer.nl", "jobted.com",
    # Staffing / recruiters with salary guides
    "adecco.com", "randstad.com", "manpower.com",
}

# Local-language salary keywords keyed by country name.
# Used to build richer search queries for non-English markets.
COUNTRY_SALARY_TERMS: dict[str, list[str]] = {
    "Poland": ["wynagrodzenie", "zarobki"],
    "Germany": ["gehalt", "lohn"],
    "Austria": ["gehalt"],
    "Switzerland": ["gehalt", "lohn"],
    "France": ["salaire"],
    "Belgium": ["salaire", "loon"],
    "Netherlands": ["salaris", "loon"],
    "Spain": ["salario", "sueldo"],
    "Italy": ["stipendio"],
    "Portugal": ["salário"],
    "Brazil": ["salário"],
    "Mexico": ["salario"],
    "Czech Republic": ["plat", "mzda"],
    "Slovakia": ["plat", "mzda"],
    "Hungary": ["fizetés", "bér"],
    "Romania": ["salariu"],
    "Bulgaria": ["zaplate"],
    "Ukraine": ["зарплата"],
    "Russia": ["зарплата", "оклад"],
    "Japan": ["給料", "年収"],
    "China": ["薪资", "工资"],
    "South Korea": ["연봉", "급여"],
    "Turkey": ["maaş", "ücret"],
    "Sweden": ["lön"],
    "Norway": ["lønn"],
    "Denmark": ["løn"],
    "Finland": ["palkka"],
}

SERPAPI_BASE = "https://serpapi.com/search"

# ---------------------------------------------------------------------------
# Niche job title classification
# ---------------------------------------------------------------------------

# Role/function tokens — words common enough in job titles that their presence
# signals a well-understood role.  Titles whose content words are *mostly*
# drawn from this set are classified as "common" or "specialized".
_COMMON_ROLE_TOKENS = {
    # Core role words
    "engineer", "developer", "programmer", "designer", "architect",
    "manager", "director", "executive", "president", "vp",
    "analyst", "consultant", "specialist", "coordinator",
    "administrator", "assistant", "associate", "officer",
    "accountant", "recruiter", "strategist", "marketer",
    "scientist", "researcher", "physician", "nurse", "therapist",
    "representative", "rep", "advisor", "agent", "broker",
    # Common domain/function words that appear in well-known multi-word titles
    "customer", "success", "business", "sales", "marketing", "product",
    "data", "technical", "operations", "software", "cloud", "digital",
    "finance", "financial", "legal", "human", "resources",
    "security", "quality", "project", "program", "supply", "chain",
    "content", "growth", "revenue", "enterprise", "corporate",
    "information", "technology", "it", "devop", "sre", "ml", "ai",
    "ux", "ui", "frontend", "backend", "fullstack",
}

# Seniority/qualifier prefixes that alone don't make a title niche.
_SENIORITY_WORDS = {
    "senior", "junior", "lead", "principal", "staff", "chief",
    "head", "entry", "mid", "level", "sr", "jr",
}

# Stop words that appear in job titles but carry no role signal (e.g. "VP of Product")
_TITLE_STOP_WORDS = {"of", "the", "and", "for", "in", "at", "to", "a", "an", "&"}


def classify_job_niche(job_title: str) -> tuple[str, list[str]]:
    """Classify a job title as 'common', 'specialized', or 'niche'.

    Returns:
        (niche_level, title_variants)
        - niche_level: 'common' | 'specialized' | 'niche'
        - title_variants: list of alternative/broader titles to also search for
          (empty for common titles)
    """
    raw_words = job_title.strip().split()
    # Strip stop words and seniority words for classification only
    content_words = [
        w.lower().rstrip("s")
        for w in raw_words
        if w.lower() not in _SENIORITY_WORDS and w.lower() not in _TITLE_STOP_WORDS
    ]
    n_content = len(content_words)

    if n_content <= 2:
        # Short meaningful content — almost always a common role
        return "common", []

    # Count how many content words are well-known role/function tokens
    known = sum(1 for w in content_words if w in _COMMON_ROLE_TOKENS)
    if known >= n_content - 1:
        # Most content words are recognisable — "specialized" (may still need synonyms
        # for less-searched variants but doesn't need target reduction)
        return "specialized", []

    # Otherwise genuinely niche — generate title variants for broader search coverage
    # Work on the original raw_words (stripped of stop words only, keep seniority)
    sig_words = [w for w in raw_words if w.lower() not in _TITLE_STOP_WORDS]
    n = len(sig_words)
    variants: list[str] = []

    if n == 3:
        # e.g. "Account Management Analyst" → "Account Analyst", "Management Analyst"
        variants.append(sig_words[0] + " " + sig_words[2])
        variants.append(sig_words[1] + " " + sig_words[2])
        # If last word is a known role token, try swapping last word → "Manager"
        last_lower = sig_words[2].lower().rstrip("s")
        if last_lower in _COMMON_ROLE_TOKENS and last_lower != "manager":
            variants.append(sig_words[0] + " Manager")
    elif n >= 4:
        variants.append(sig_words[0] + " " + sig_words[-1])
        variants.append(" ".join(sig_words[:-1]))
        variants.append(" ".join(sig_words[1:]))

    # Deduplicate and cap at 3
    seen_set: set[str] = {job_title.lower()}
    unique_variants: list[str] = []
    for v in variants:
        if v.lower() not in seen_set and len(v.split()) >= 2:
            seen_set.add(v.lower())
            unique_variants.append(v)
        if len(unique_variants) >= 3:
            break

    return "niche", unique_variants


def discover_top_sites(country: str, api_key: str) -> list[str]:
    """Discover top salary data sites for the given country using SerpAPI."""
    local_terms = COUNTRY_SALARY_TERMS.get(country, [])
    extra = f" {local_terms[0]}" if local_terms else ""
    query = f"top salary data job sites {country}{extra}"

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
    title_variants: list[str] | None = None,
) -> list[str]:
    """Search a specific site for salary pages matching the job criteria.

    title_variants: optional list of alternative/broader titles to include in
    the query via OR (used for niche titles to widen the search net).
    """
    location_parts = [p for p in [city, region, country] if p]
    location_str = " ".join(location_parts)

    # Build salary term clause: always include English plus any local-language terms
    local_terms = COUNTRY_SALARY_TERMS.get(country, [])
    all_salary_terms = ["salary"] + local_terms
    if len(all_salary_terms) == 1:
        salary_clause = "salary"
    else:
        salary_clause = "(" + " OR ".join(all_salary_terms) + ")"

    # Build title clause: for niche titles, OR in up to 2 variants
    if title_variants:
        all_titles = [job_title] + title_variants[:2]
        title_clause = "(" + " OR ".join(f'"{t}"' for t in all_titles) + ")"
    else:
        title_clause = f'"{job_title}"'

    query = f"site:{domain} {title_clause} {location_str} {salary_clause}"

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
