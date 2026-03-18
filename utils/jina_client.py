import time
import requests
from bs4 import BeautifulSoup

JINA_BASE = "https://r.jina.ai/"

# Strings that indicate the page is a bot/auth wall, not real content
_BLOCK_SIGNALS = [
    "403: Forbidden",
    "Just a moment...",        # Cloudflare spinner — always includes the ellipsis
    "Additional Verification Required",
    "Enable JavaScript and cookies",
    "cf-browser-verification",
    "Robot or human?",
    "Please verify you are a human",
    # "Cloudflare" removed — too broad, appears in legitimate site footers
    # "Access denied" removed — too broad, appears in legitimate content
]

_LOGIN_SIGNALS = [
    "Sign in to continue",
    "Log in to view",
    "Create a free account",
    "Register to see",
    "Please sign in",
]

_SALARY_SIGNALS = [
    "$", "£", "€", "per hour", "per year", "/hr", "/yr",
    "salary", "compensation", "pay rate", "wage", "hourly",
    "annual", "base pay",
]


def _extract_salary_focused_lines(text: str) -> str:
    """
    Filter text to lines containing salary-relevant content, with a 2-line
    context window before and after each matching line. Output capped at 8,000 chars.
    """
    salary_keywords = [
        "$", "£", "€", "/hr", "/yr", "per hour", "per year",
        "salary", "compensation", "pay", "annually", "wage", "hourly",
        "usd", "gbp", "eur", "cad", "aud", "inr", "jpy",
    ]
    lines = text.splitlines()
    matched_indices = set()

    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in salary_keywords):
            # Add 2-line context window before and after
            for j in range(max(0, i - 2), min(len(lines), i + 3)):
                matched_indices.add(j)

    # Preserve order and deduplicate
    kept_lines = []
    seen = set()
    for i in sorted(matched_indices):
        line = lines[i]
        if line not in seen:
            seen.add(line)
            kept_lines.append(line)

    result = "\n".join(kept_lines)
    return result[:8000]


def _parse_salary_html(html: str) -> str:
    """
    Parse raw HTML, targeting salary-relevant structured content first,
    falling back to full text extraction with salary-focused filtering.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise tags
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        # Preserve ld+json script tags before removing scripts
        if tag.name == "script" and tag.get("type") == "application/ld+json":
            continue
        tag.decompose()

    collected_lines = []

    # 1. Find tags with salary/pay/compensation/wage in class attribute
    salary_class_keywords = ["salary", "pay", "compensation", "wage"]
    for tag in soup.find_all(True):
        tag_classes = tag.get("class", [])
        if isinstance(tag_classes, list):
            tag_classes_str = " ".join(tag_classes).lower()
        else:
            tag_classes_str = str(tag_classes).lower()
        if any(kw in tag_classes_str for kw in salary_class_keywords):
            text = tag.get_text(separator=" ", strip=True)
            if text:
                collected_lines.append(text)

    # 2. Find tags with data-testid containing "salary" or "pay"
    for tag in soup.find_all(True, attrs={"data-testid": True}):
        testid = tag.get("data-testid", "").lower()
        if "salary" in testid or "pay" in testid:
            text = tag.get_text(separator=" ", strip=True)
            if text:
                collected_lines.append(text)

    # 3. Extract ld+json script content
    import json
    for script_tag in soup.find_all("script", type="application/ld+json"):
        raw = script_tag.string or ""
        if raw.strip():
            collected_lines.append(raw.strip())

    # Deduplicate lines
    seen = set()
    deduped = []
    for line in collected_lines:
        if line not in seen:
            seen.add(line)
            deduped.append(line)

    structured_result = "\n".join(deduped)

    if len(structured_result) >= 100:
        return structured_result[:8000]

    # Fallback: full text extraction with salary-focused filtering
    full_text = soup.get_text(separator="\n", strip=True)
    return _extract_salary_focused_lines(full_text)


def _fetch_direct_http(url: str) -> tuple[str | None, str | None]:
    """
    Attempt to fetch the URL directly using a browser-like User-Agent,
    then parse salary-relevant content from the HTML.
    Returns (content, error_message).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        if resp.status_code != 200:
            return None, f"NETWORK:Direct HTTP failed (HTTP {resp.status_code})"
        content = _parse_salary_html(resp.text)
        if not content or len(content) < 50:
            return None, "NETWORK:Direct HTTP returned insufficient content"
        print(f"[jina] Direct HTTP fallback succeeded: {url}")
        return content, None
    except requests.exceptions.Timeout:
        return None, "NETWORK:Direct HTTP timed out"
    except Exception as e:
        return None, f"NETWORK:Direct HTTP error: {e}"


def fetch_page(url: str) -> tuple[str | None, str | None]:
    """
    Fetch a page via Jina Reader, with direct HTTP fallback on failure.
    Returns (content, error_message).
    content is None on failure; error_message describes what went wrong.
    """
    jina_url = JINA_BASE + url
    headers = {
        "Accept": "text/plain",
        "User-Agent": "Mozilla/5.0 (compatible; myBasePay-JobRateAgent/1.0)",
        # Allow up to 30 s for JS-rendered salary pages to fully load
        "X-Timeout": "30",
        # Return clean markdown so tables are preserved
        "X-Return-Format": "markdown",
        # Skip image alt-text to save token budget for actual salary content
        "X-With-Images-Summary": "false",
    }

    try:
        resp = requests.get(jina_url, headers=headers, timeout=15)
        if resp.status_code == 429:
            print(f"[jina] HTTP 429 rate limit — waiting 10s and retrying: {url}")
            time.sleep(10)
            resp = requests.get(jina_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            msg = f"NETWORK:Page fetch failed (HTTP {resp.status_code})"
            print(f"[jina] {msg}: {url}")
            print(f"[jina] Jina failed ({msg}), trying direct HTTP fallback: {url}")
            direct_content, direct_error = _fetch_direct_http(url)
            if direct_content:
                return direct_content, None
            return None, msg

        text = resp.text.strip()
        if not text:
            msg = "NETWORK:Empty page content returned"
            print(f"[jina] {msg}: {url}")
            # Empty content — direct HTTP unlikely to help, return as-is
            return None, msg

        # Scoring-based wall detection on first 3000 chars
        text_sample = text[:3000].lower()
        wall_score = sum(3 for signal in _BLOCK_SIGNALS if signal.lower() in text_sample)
        salary_score = sum(1 for signal in _SALARY_SIGNALS if signal in text_sample)

        if wall_score - salary_score >= 3:
            msg = "WALL:Blocked by bot/Cloudflare protection — page content unavailable"
            print(f"[jina] {msg}: {url}")
            print(f"[jina] Jina failed ({msg}), trying direct HTTP fallback: {url}")
            direct_content, direct_error = _fetch_direct_http(url)
            if direct_content:
                return direct_content, None
            return None, msg

        # Scoring-based login wall detection
        login_signals_found = any(signal.lower() in text_sample for signal in _LOGIN_SIGNALS)
        if login_signals_found and salary_score < 2:
            msg = "WALL:Login wall — sign-in required to view this page"
            print(f"[jina] {msg}: {url}")
            print(f"[jina] Jina failed ({msg}), trying direct HTTP fallback: {url}")
            direct_content, direct_error = _fetch_direct_http(url)
            if direct_content:
                return direct_content, None
            return None, msg

        # Also catch Jina's inline warning for blocked targets
        if "Target URL returned error 403" in text or "Target URL returned error 401" in text:
            msg = "WALL:Blocked by bot/Cloudflare protection — page content unavailable"
            print(f"[jina] {msg}: {url}")
            print(f"[jina] Jina failed ({msg}), trying direct HTTP fallback: {url}")
            direct_content, direct_error = _fetch_direct_http(url)
            if direct_content:
                return direct_content, None
            return None, msg

        # Salary-focused preprocessing for longer texts
        if len(text) > 4000:
            return _extract_salary_focused_lines(text), None
        return text, None

    except requests.exceptions.Timeout:
        msg = "NETWORK:Request timed out (>15s)"
        print(f"[jina] {msg}: {url}")
        print(f"[jina] Jina failed ({msg}), trying direct HTTP fallback: {url}")
        direct_content, direct_error = _fetch_direct_http(url)
        if direct_content:
            return direct_content, None
        return None, msg
    except Exception as e:
        msg = f"NETWORK:Page fetch error: {e}"
        print(f"[jina] {msg}: {url}")
        print(f"[jina] Jina failed ({msg}), trying direct HTTP fallback: {url}")
        direct_content, direct_error = _fetch_direct_http(url)
        if direct_content:
            return direct_content, None
        return None, msg
    finally:
        time.sleep(1)
