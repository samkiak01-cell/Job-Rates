import time
import requests

JINA_BASE = "https://r.jina.ai/"

# Strings that indicate the page is a bot/auth wall, not real content
_BLOCK_SIGNALS = [
    "403: Forbidden",
    "Just a moment",
    "Additional Verification Required",
    "Enable JavaScript and cookies",
    "cf-browser-verification",
    "Cloudflare",
    "Access denied",
    "Robot or human?",
    "Please verify you are a human",
]

_LOGIN_SIGNALS = [
    "Sign in to continue",
    "Log in to view",
    "Create a free account",
    "Register to see",
    "Please sign in",
]


def fetch_page(url: str) -> tuple[str | None, str | None]:
    """
    Fetch a page via Jina Reader.
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
            msg = f"Page fetch failed (HTTP {resp.status_code})"
            print(f"[jina] {msg}: {url}")
            return None, msg

        text = resp.text.strip()
        if not text:
            msg = "Empty page content returned"
            print(f"[jina] {msg}: {url}")
            return None, msg

        # Check for bot/Cloudflare block even when Jina returns HTTP 200
        text_sample = text[:2000].lower()
        for signal in _BLOCK_SIGNALS:
            if signal.lower() in text_sample:
                msg = "Blocked by bot/Cloudflare protection — page content unavailable"
                print(f"[jina] {msg}: {url}")
                return None, msg

        # Check for login walls
        for signal in _LOGIN_SIGNALS:
            if signal.lower() in text_sample:
                msg = "Login wall — sign-in required to view this page"
                print(f"[jina] {msg}: {url}")
                return None, msg

        # Also catch Jina's inline warning for blocked targets
        if "Target URL returned error 403" in text or "Target URL returned error 401" in text:
            msg = "Blocked by bot/Cloudflare protection — page content unavailable"
            print(f"[jina] {msg}: {url}")
            return None, msg

        return text[:20000], None

    except requests.exceptions.Timeout:
        msg = "Request timed out (>15s)"
        print(f"[jina] {msg}: {url}")
        return None, msg
    except Exception as e:
        msg = f"Page fetch error: {e}"
        print(f"[jina] {msg}: {url}")
        return None, msg
    finally:
        time.sleep(1)
