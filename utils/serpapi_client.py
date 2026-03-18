import json
import re
import requests
from typing import Optional

SALARY_SITE_WHITELIST: dict[str, list[str]] = {
    "US": [
        "salary.com", "payscale.com", "glassdoor.com", "comparably.com",
        "careerbliss.com", "salaryexpert.com", "levels.fyi", "talent.com",
        "bls.gov", "onetonline.org", "zippia.com", "flexjobs.com",
        "simplyhired.com", "ziprecruiter.com", "indeed.com",
    ],
    "UK": [
        "glassdoor.co.uk", "reed.co.uk", "totaljobs.com", "cwjobs.co.uk",
        "itjobswatch.co.uk", "glassdoor.com", "salary.com", "payscale.com",
        "talent.com", "adzuna.com",
    ],
    "DE": [
        "stepstone.de", "gehalt.de", "kununu.com", "xing.com",
        "glassdoor.com", "payscale.com", "talent.com", "paylab.com",
    ],
    "AU": [
        "seek.com.au", "glassdoor.com.au", "payscale.com", "talent.com",
        "salary.com", "adzuna.com.au",
    ],
    "CA": [
        "glassdoor.ca", "payscale.com", "salary.com", "talent.com",
        "adzuna.ca", "workopolis.com",
    ],
    "GLOBAL": [
        "glassdoor.com", "salary.com", "payscale.com", "talent.com",
        "comparably.com", "salaryexpert.com", "careerbliss.com", "adzuna.com",
    ],
}

_COUNTRY_TO_KEY: dict[str, str] = {
    "United States": "US", "USA": "US", "US": "US",
    "United Kingdom": "UK", "UK": "UK", "Britain": "UK", "England": "UK",
    "Germany": "DE", "Deutschland": "DE",
    "Australia": "AU",
    "Canada": "CA",
}


def _get_country_key(country: str) -> str:
    return _COUNTRY_TO_KEY.get(country, "GLOBAL")


INDUSTRY_VERTICAL_SOURCES: dict[str, list[str]] = {
    "healthcare": [
        "nursesalaryguide.com", "nurse.com", "allnurses.com",
        "bls.gov", "onetonline.org", "salary.com", "payscale.com",
        "glassdoor.com",
    ],
    "tech": [
        "levels.fyi", "glassdoor.com", "payscale.com",
        "salary.com", "teamblind.com", "comparably.com",
    ],
    "legal": [
        "nalp.org", "glassdoor.com", "salary.com", "payscale.com",
    ],
    "finance": [
        "efinancialcareers.com", "glassdoor.com", "salary.com", "payscale.com",
    ],
    "government": [
        "bls.gov", "onetonline.org", "usajobs.gov", "salary.com",
    ],
}

_VERTICAL_KEYWORDS: dict[str, list[str]] = {
    "healthcare": [
        "nurse", "nursing", "rn", "lpn", "physician", "doctor", "md",
        "therapist", "medical", "clinical", "health", "pharmacy", "pharmacist",
        "dental", "dentist", "surgeon", "surgical", "icu", "er", "coordinator",
        "case manager", "patient", "care coordinator", "health coordinator",
    ],
    "tech": [
        "engineer", "developer", "programmer", "devops", "sre", "architect",
        "data scientist", "machine learning", "ml", "ai", "software",
        "backend", "frontend", "fullstack", "cloud", "cybersecurity",
    ],
    "legal": ["attorney", "lawyer", "paralegal", "counsel", "legal", "solicitor"],
    "finance": [
        "accountant", "analyst", "banker", "trader", "portfolio",
        "financial", "cpa", "actuary", "controller", "cfo",
    ],
    "government": ["government", "federal", "public sector", "civil service", "municipal"],
}


def detect_job_vertical(job_title: str) -> str | None:
    title_lower = job_title.lower()
    # Healthcare check is first because "coordinator" alone shouldn't trigger it
    # but "nursing coordinator" or "care coordinator" should
    for vertical, keywords in _VERTICAL_KEYWORDS.items():
        for kw in keywords:
            if kw in title_lower:
                return vertical
    return None


_DOMAIN_SOURCE_TYPE: dict[str, str] = {
    "bls.gov": "government",
    "onetonline.org": "government",
    "usajobs.gov": "government",
    "dol.gov": "government",
    "salary.com": "salary_database",
    "payscale.com": "salary_database",
    "salaryexpert.com": "salary_database",
    "levels.fyi": "salary_database",
    "erieri.com": "salary_database",
    "zippia.com": "salary_database",
    "comparably.com": "aggregator",
    "glassdoor.com": "aggregator",
    "glassdoor.co.uk": "aggregator",
    "careerbliss.com": "aggregator",
    "talent.com": "aggregator",
    "flexjobs.com": "job_board",
    "indeed.com": "job_board",
    "linkedin.com": "job_board",
    "ziprecruiter.com": "job_board",
    "simplyhired.com": "job_board",
    "monster.com": "job_board",
}


def get_source_type(domain: str) -> str:
    domain_lower = domain.lower()
    for key, stype in _DOMAIN_SOURCE_TYPE.items():
        if key in domain_lower:
            return stype
    return "aggregator"


_URL_QUALITY_BOOST = ["/salary", "/pay", "/compensation", "/wages", "/wage"]
_URL_QUALITY_PENALTY = ["/blog/", "/category/", "/tag/", "/author/", "/news/", "?q=", "/search?", "/about/"]


def _score_url_quality(url: str) -> int:
    score = 0
    url_lower = url.lower()
    for pat in _URL_QUALITY_BOOST:
        if pat in url_lower:
            score += 2
    for pat in _URL_QUALITY_PENALTY:
        if pat in url_lower:
            score -= 3
    return score


_US_EXCLUDED_TLDS = [".co.uk", ".de", ".fr", ".pl", ".nl", ".es", ".it", ".com.au", ".ca", ".in"]
_UK_EXCLUDED_TLDS = [".de", ".fr", ".pl", ".nl", ".es", ".it", ".com.au", ".in"]


def _is_wrong_tld(domain: str, country_key: str) -> bool:
    if country_key == "US":
        return any(domain.endswith(tld) for tld in _US_EXCLUDED_TLDS)
    elif country_key == "UK":
        return any(domain.endswith(tld) for tld in _UK_EXCLUDED_TLDS)
    return False


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

_HAIKU_MODEL = "claude-haiku-4-5-20251001"


def ai_suggest_salary_sources(job_title: str, country: str, anthropic_client) -> list[str]:
    """Ask Claude Haiku to suggest the best salary data websites for any job title and country.

    Returns a deduplicated list of domain names, most relevant first.
    Falls back to [] silently on any failure.
    """
    try:
        prompt = (
            f'What are the best websites to find accurate salary data for a "{job_title}" in {country}? '
            f"Include industry-specific sites, government labor statistics, and general salary databases. "
            f'Return ONLY a JSON array of domain names, e.g. ["salary.com", "bls.gov"]. '
            f"Return 6-10 domains, most relevant first. No explanations, no markdown."
        )
        response = anthropic_client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        domains = json.loads(raw)
        if isinstance(domains, list):
            return [d.strip().lower() for d in domains if isinstance(d, str) and d.strip()]
    except Exception:
        pass
    return []


def classify_job_niche(
    job_title: str,
    anthropic_client=None,
) -> tuple[str, list[str], str | None]:
    """Classify a job title as 'common', 'specialized', or 'niche'.

    Returns:
        (niche_level, title_variants, job_vertical)
        - niche_level: 'common' | 'specialized' | 'niche'
        - title_variants: list of alternative/broader titles to also search for
          (empty for common titles)
        - job_vertical: detected industry vertical or None
    """
    raw_words = job_title.strip().split()
    # Strip stop words and seniority words for classification only
    content_words = [
        w.lower().rstrip("s")
        for w in raw_words
        if w.lower() not in _SENIORITY_WORDS and w.lower() not in _TITLE_STOP_WORDS
    ]
    n_content = len(content_words)

    # Detect job vertical for all titles
    job_vertical = detect_job_vertical(job_title)

    if n_content <= 2:
        # Short meaningful content — almost always a common role
        return "common", [], job_vertical

    # Count how many content words are well-known role/function tokens
    known = sum(1 for w in content_words if w in _COMMON_ROLE_TOKENS)
    if known >= n_content - 1:
        # Most content words are recognisable — "specialized" (may still need synonyms
        # for less-searched variants but doesn't need target reduction)
        return "specialized", [], job_vertical

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

    # If an Anthropic client is provided and the title is niche, enrich variants via Haiku
    if anthropic_client is not None:
        try:
            prompt = (
                f'For the job title "{job_title}", return a JSON array of 3-5 semantically '
                f"equivalent or broader titles that commonly appear on salary data websites. "
                f"Include alternate phrasings, common abbreviations, and related specialty titles. "
                f"Return ONLY a JSON array of strings, no explanation."
            )
            response = anthropic_client.messages.create(
                model=_HAIKU_MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            ai_text = response.content[0].text.strip()
            ai_variants: list[str] = json.loads(ai_text)
            if isinstance(ai_variants, list):
                for av in ai_variants:
                    if not isinstance(av, str):
                        continue
                    if av.lower() not in seen_set and len(av.split()) >= 2:
                        seen_set.add(av.lower())
                        unique_variants.append(av)
                    if len(unique_variants) >= 5:
                        break
        except Exception:
            # Haiku call failed — silently continue with static-only variants
            pass

    return "niche", unique_variants, job_vertical


def discover_top_sites(
    country: str,
    api_key: str,
    job_title: str | None = None,
    job_vertical: str | None = None,
    anthropic_client=None,
) -> list[str]:
    """Discover top salary data sites for the given country using SerpAPI.

    When job_title and anthropic_client are provided, Claude Haiku is called to
    suggest the most relevant salary sources for that specific role — covering any
    job title regardless of industry vertical.
    """
    country_key = _get_country_key(country)
    base_sites = list(SALARY_SITE_WHITELIST.get(country_key, SALARY_SITE_WHITELIST["GLOBAL"]))

    # Priority order: AI suggestions → vertical sources → country whitelist
    seen_sites: set[str] = set()
    merged: list[str] = []

    # 1. AI-suggested sources (most relevant for this specific job title)
    if anthropic_client and job_title:
        ai_sites = ai_suggest_salary_sources(job_title, country, anthropic_client)
        for s in ai_sites:
            if not _is_wrong_tld(s, country_key) and s not in seen_sites:
                seen_sites.add(s)
                merged.append(s)

    # 2. Hardcoded vertical sources as supplemental fallback
    if job_vertical:
        for s in INDUSTRY_VERTICAL_SOURCES.get(job_vertical, []):
            if s not in seen_sites:
                seen_sites.add(s)
                merged.append(s)

    # 3. Country whitelist
    for s in base_sites:
        if s not in seen_sites:
            seen_sites.add(s)
            merged.append(s)

    base_sites = merged

    local_terms = COUNTRY_SALARY_TERMS.get(country, [])
    extra = f" {local_terms[0]}" if local_terms else ""
    query = f"top salary data job sites {country}{extra} site:salary jobs pay"

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
        # Fall back to base_sites defaults
        return [s for s in base_sites if not _is_wrong_tld(s, country_key)][:20]

    organic = data.get("organic_results", [])

    # Score domains
    domain_scores: dict[str, int] = {}

    for result in organic:
        link = result.get("link", "")
        domain = _extract_domain(link)
        if not domain:
            continue

        # Skip wrong-TLD domains entirely
        if _is_wrong_tld(domain, country_key):
            continue

        if domain not in domain_scores:
            domain_scores[domain] = 0

        # +3 if in whitelist
        if _matches_whitelist(domain, country_key):
            domain_scores[domain] += 3

        # +1 per organic result appearance
        domain_scores[domain] += 1

    # Sort by score descending, take top 20 unique domains
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    top_domains = [d for d, _ in sorted_domains[:20]]

    # If we got fewer than 20, pad with base_sites defaults (filtering wrong TLDs)
    if len(top_domains) < 20:
        top_domains_set = set(top_domains)
        for wl_domain in base_sites:
            if _is_wrong_tld(wl_domain, country_key):
                continue
            if wl_domain not in top_domains_set:
                top_domains.append(wl_domain)
                top_domains_set.add(wl_domain)
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

    # Score and sort URLs by quality
    urls = sorted(urls, key=_score_url_quality, reverse=True)

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


def _matches_whitelist(domain: str, country_key: str = "GLOBAL") -> bool:
    """Check if domain matches any whitelist entry."""
    sites = SALARY_SITE_WHITELIST.get(country_key, SALARY_SITE_WHITELIST["GLOBAL"])
    all_sites = set(sites) | set(SALARY_SITE_WHITELIST["GLOBAL"])
    for wl in all_sites:
        if domain == wl or domain.endswith("." + wl) or wl.endswith("." + domain):
            return True
    return False
