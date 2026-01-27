import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st


# =========================
# Page + Theme
# =========================
st.set_page_config(
    page_title="Job Rate Finder",
    page_icon="💲",
    layout="centered",
)

CSS = """
<style>
/* Page background */
.stApp {
  background: radial-gradient(1200px 800px at 20% 0%, rgba(124, 58, 237, 0.35), transparent 60%),
              radial-gradient(1200px 800px at 80% 10%, rgba(99, 102, 241, 0.30), transparent 55%),
              linear-gradient(180deg, #070A12 0%, #0B1020 100%);
  color: #E5E7EB;
}

/* Center container spacing */
.block-container {
  padding-top: 2.2rem;
  padding-bottom: 3rem;
  max-width: 860px;
}

/* Headings */
h1, h2, h3 {
  color: #E5E7EB !important;
}
p, label, div, span {
  color: #CBD5E1;
}

/* Form card */
.jr-card {
  background: rgba(17, 24, 39, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  padding: 18px 18px 6px 18px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.35);
  backdrop-filter: blur(10px);
}

/* Result gradient card */
.jr-gradient {
  background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 50%, #A855F7 100%);
  border-radius: 16px;
  padding: 18px;
  color: white;
  box-shadow: 0 18px 50px rgba(0,0,0,0.35);
  border: 1px solid rgba(255,255,255,0.14);
}

/* Result layout */
.jr-range {
  display: flex;
  gap: 24px;
  align-items: baseline;
}
.jr-range .jr-sep {
  font-size: 26px;
  opacity: 0.6;
  margin: 0 4px;
}
.jr-label {
  font-size: 12px;
  opacity: 0.78;
  margin-bottom: 2px;
}
.jr-money {
  font-size: 34px;
  font-weight: 700;
  line-height: 1.2;
}
.jr-unit {
  font-size: 12px;
  opacity: 0.78;
  margin-top: 4px;
}

/* Sources card */
.jr-sources {
  background: rgba(17, 24, 39, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.35);
  backdrop-filter: blur(10px);
}

/* Source row card */
.jr-source {
  display: flex;
  gap: 12px;
  padding: 12px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(2, 6, 23, 0.35);
  transition: all 0.15s ease;
  text-decoration: none !important;
}
.jr-source:hover {
  border-color: rgba(99, 102, 241, 0.55);
  background: rgba(2, 6, 23, 0.55);
  transform: translateY(-1px);
}
.jr-ico {
  width: 22px;
  height: 22px;
  border-radius: 7px;
  background: rgba(99, 102, 241, 0.22);
  display: grid;
  place-items: center;
  flex: 0 0 22px;
  margin-top: 2px;
}
.jr-source-main {
  color: #E5E7EB !important;
  font-weight: 600;
  font-size: 13px;
  line-height: 1.2;
}
.jr-source-sub {
  color: #9CA3AF !important;
  font-size: 12px;
  margin-top: 4px;
}

/* Note box */
.jr-note {
  margin-top: 14px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(251, 191, 36, 0.35);
  background: rgba(251, 191, 36, 0.10);
  color: #FDE68A;
  font-size: 12px;
}

/* Make Streamlit inputs darker */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
  background: rgba(2, 6, 23, 0.35) !important;
  color: #E5E7EB !important;
  border-color: rgba(148, 163, 184, 0.18) !important;
}
.stTextArea textarea::placeholder, .stTextInput input::placeholder {
  color: rgba(203, 213, 225, 0.55) !important;
}

/* Buttons */
.stButton button {
  background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 60%, #A855F7 100%) !important;
  color: white !important;
  border: 0 !important;
  border-radius: 12px !important;
  padding: 0.65rem 1rem !important;
  font-weight: 700 !important;
  width: 100% !important;
}
.stButton button:hover {
  filter: brightness(1.05);
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =========================
# Types + helpers
# =========================
@dataclass
class SourceItem:
    title: str
    url: str
    range: str


def format_money(n: float) -> str:
    try:
        return f"{int(round(float(n))):,}"
    except Exception:
        return "—"


def safe_host(url: str) -> str:
    try:
        host = re.sub(r"^https?://", "", url.strip(), flags=re.I)
        host = host.split("/")[0]
        host = re.sub(r"^www\.", "", host, flags=re.I)
        return host or "source"
    except Exception:
        return "source"


def prettify_url_label(url: str) -> str:
    """
    Turn a URL into a readable label like:
    "salary.com — marketing director salary (los angeles ca)"
    """
    host = safe_host(url)
    # make a readable tail from path
    tail = url
    try:
        tail = re.sub(r"^https?://", "", url.strip(), flags=re.I)
        tail = tail.split("/", 1)[1] if "/" in tail else ""
        tail = re.sub(r"[?#].*$", "", tail)
        tail = re.sub(r"\.(html|htm|php|aspx)$", "", tail, flags=re.I)
        tail = tail.replace("-", " ").replace("_", " ")
        tail = re.sub(r"\s+", " ", tail).strip()
        if len(tail) > 58:
            tail = tail[:58].rstrip() + "…"
    except Exception:
        tail = ""
    if tail:
        return f"{host} — {tail}"
    return host


def parse_source_blob(blob: Any, default_range: str = "Source") -> Optional[SourceItem]:
    """
    The current app sometimes receives sources as HTML blocks like:
      <a class="jr-source" href="https://..."> ... Reported Range: Min ... </a>

    This parses:
      - href="..."
      - some meaningful text inside
      - "Reported Range: X" if present

    If it's already a dict with url/title/range, it passes through.
    """
    if blob is None:
        return None

    # Already structured
    if isinstance(blob, dict):
        url = str(blob.get("url", "")).strip()
        if not url:
            return None
        title = str(blob.get("title", "")).strip() or prettify_url_label(url)
        rng = str(blob.get("range", "")).strip() or default_range
        return SourceItem(title=title, url=url, range=rng)

    # Plain URL string
    if isinstance(blob, str) and blob.strip().lower().startswith(("http://", "https://")):
        url = blob.strip()
        return SourceItem(title=prettify_url_label(url), url=url, range=default_range)

    # HTML string
    if isinstance(blob, str) and "<a" in blob and "href=" in blob:
        s = blob

        href_match = re.search(r'href\s*=\s*"([^"]+)"', s, flags=re.I)
        if not href_match:
            href_match = re.search(r"href\s*=\s*'([^']+)'", s, flags=re.I)
        url = href_match.group(1).strip() if href_match else ""
        if not url:
            return None

        # Try to find a "Reported Range:" line
        rr_match = re.search(r"Reported\s*Range:\s*([^<]+)", s, flags=re.I)
        rng = rr_match.group(1).strip() if rr_match else default_range

        # Try to find a “main” text chunk
        main_match = re.search(r'jr-source-main"\s*>\s*([^<]+)\s*<', s, flags=re.I)
        if main_match:
            title = main_match.group(1).strip()
        else:
            # fallback to URL-based label
            title = prettify_url_label(url)

        return SourceItem(title=title, url=url, range=rng)

    # Unknown
    return None


def normalize_sources(raw_sources: Any) -> List[SourceItem]:
    """
    raw_sources could be:
      - list[str]
      - list[dict]
      - list[html-string]
      - None
    """
    out: List[SourceItem] = []
    if not raw_sources:
        return out
    if not isinstance(raw_sources, list):
        raw_sources = [raw_sources]

    for item in raw_sources:
        parsed = parse_source_blob(item)
        if parsed and parsed.url:
            out.append(parsed)

    # De-dupe by URL
    seen = set()
    deduped: List[SourceItem] = []
    for s in out:
        if s.url in seen:
            continue
        seen.add(s.url)
        deduped.append(s)
    return deduped


# =========================
# Your business logic hook
# =========================
def estimate_job_rate(
    job_title: str,
    job_description: str,
    country: str,
    state: str,
    city: str,
    rate_type: str,
    currency: str,
) -> Dict[str, Any]:
    """
    IMPORTANT:
    This function is a placeholder wrapper.

    In your current project you already have working logic that returns something like:
      {
        "min": ... or "min_usd": ...,
        "max": ... or "max_usd": ...,
        "currency": "USD",
        "rateType"/"pay_type": ...,
        "sources": [...]
      }

    Replace the body of this function with your existing working call.
    """
    raise NotImplementedError("Hook estimate_job_rate() to your existing OpenAI + SerpAPI code.")


# =========================
# UI
# =========================
st.markdown("<h1 style='text-align:center; margin-bottom: 4px;'>Job Rate Finder</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; margin-top: 0; color: rgba(203,213,225,0.75);'>"
    "Get competitive salary and hourly rate information for any position"
    "</p>",
    unsafe_allow_html=True,
)

st.markdown("<div class='jr-card'>", unsafe_allow_html=True)

with st.form("job_rate_form", clear_on_submit=False):
    # No prefills / no hardcoding
    job_title = st.text_input("Job Title *", value="", placeholder="e.g., Senior Software Engineer")

    job_description = st.text_area(
        "Job Description (optional)",
        value="",
        placeholder="Paste job description here...",
        height=120,
    )

    c1, c2, c3 = st.columns(3)

    # NOTE:
    # Use your existing country/state/city lists in your app.py right now.
    # Here we keep them as selectboxes without hardcoding values in the UI.
    # If you currently store the lists in variables, plug them in below.
    #
    # For now we provide safe defaults to avoid crashes.
    ALL_COUNTRIES = st.session_state.get("ALL_COUNTRIES", ["United States"])
    states_for_country = st.session_state.get("STATES_FOR_COUNTRY", {})
    cities_for_state = st.session_state.get("CITIES_FOR_STATE", {})

    with c1:
        country = st.selectbox("Country *", options=ALL_COUNTRIES, index=0)

    with c2:
        state_options = states_for_country.get(country, [])
        if not state_options:
            state_options = ["N/A"]
        state = st.selectbox("State/Province (optional)", options=state_options, index=0)

    with c3:
        # city list can depend on country+state; if not available, still allow N/A
        city_key = (country, state)
        city_options = cities_for_state.get(city_key, [])
        if not city_options:
            city_options = ["N/A"]
        city = st.selectbox("City (optional)", options=city_options, index=0)

    rate_type = st.radio("Rate Type *", options=["Hourly", "Salaried"], horizontal=True, index=1)
    currency = st.selectbox("Currency *", options=["USD", "EUR", "GBP", "AED", "CAD"], index=0)

    submitted = st.form_submit_button("Get Rates!")

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# Run estimation + render
# =========================
if submitted:
    if not job_title.strip() or not country.strip():
        st.error("Please fill in the required fields: Job Title and Country.")
    else:
        with st.spinner("Analyzing…"):
            try:
                # Hook to your existing logic.
                # IMPORTANT: Keep state/city optional.
                # If the user selected N/A, send empty strings.
                state_send = "" if state == "N/A" else state
                city_send = "" if city == "N/A" else city

                # This must be replaced with your existing function call.
                result = estimate_job_rate(
                    job_title=job_title.strip(),
                    job_description=job_description.strip(),
                    country=country.strip(),
                    state=state_send.strip(),
                    city=city_send.strip(),
                    rate_type="hourly" if rate_type == "Hourly" else "salary",
                    currency=currency.strip(),
                )

                # Normalize fields across possible shapes
                min_val = result.get("min_usd", result.get("min"))
                max_val = result.get("max_usd", result.get("max"))
                pay_type = result.get("pay_type", result.get("rateType", "salary"))
                curr = result.get("currency", currency)

                sources_raw = result.get("sources")
                if sources_raw is None:
                    sources_raw = result.get("sources_used", [])

                sources = normalize_sources(sources_raw)

                # Render rate card
                unit = "per hour" if str(pay_type).lower() == "hourly" else "per year"

                st.markdown(
                    f"""
                    <div class="jr-gradient">
                      <div style="display:flex; align-items:center; gap:10px; margin-bottom: 8px;">
                        <div style="width:22px;height:22px;border-radius:7px;background:rgba(255,255,255,0.18);display:grid;place-items:center;">$</div>
                        <div style="font-weight:700;">Estimated Rate Range</div>
                      </div>

                      <div class="jr-range">
                        <div>
                          <div class="jr-label">Minimum</div>
                          <div class="jr-money">{curr} {format_money(min_val)}</div>
                          <div class="jr-unit">{unit}</div>
                        </div>

                        <div class="jr-sep">—</div>

                        <div>
                          <div class="jr-label">Maximum</div>
                          <div class="jr-money">{curr} {format_money(max_val)}</div>
                          <div class="jr-unit">{unit}</div>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Render sources card (NO raw HTML blobs)
                st.markdown("<div class='jr-sources'>", unsafe_allow_html=True)
                st.markdown("<h3 style='margin-top:0;'>Rate Justification Sources</h3>", unsafe_allow_html=True)
                st.markdown(
                    "<p style='margin-top:0; color: rgba(203,213,225,0.75);'>"
                    "The above rate range is based on data from the following industry sources:"
                    "</p>",
                    unsafe_allow_html=True,
                )

                if not sources:
                    st.markdown(
                        "<p style='color: rgba(203,213,225,0.75);'>No sources were returned confidently for this query.</p>",
                        unsafe_allow_html=True,
                    )
                else:
                    for s in sources:
                        # Clean label: do NOT show a raw URL
                        title = s.title.strip() if s.title else prettify_url_label(s.url)
                        # Escape quotes minimally
                        href = s.url.replace('"', "%22")
                        st.markdown(
                            f"""
                            <a class="jr-source" href="{href}" target="_blank" rel="noopener noreferrer">
                              <div class="jr-ico">↗</div>
                              <div style="min-width:0;">
                                <div class="jr-source-main">{title}</div>
                                <div class="jr-source-sub">Reported Range: {s.range}</div>
                              </div>
                            </a>
                            """,
                            unsafe_allow_html=True,
                        )

                st.markdown(
                    """
                    <div class="jr-note">
                      <strong>Note:</strong> These rates are estimates based on aggregated market data.
                      Actual compensation may vary based on experience, skills, company size, and other factors.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

            except NotImplementedError:
                st.error(
                    "Your UI is working, but estimate_job_rate() is not wired to your existing OpenAI + SerpAPI logic yet. "
                    "Paste your existing working estimation function into estimate_job_rate()."
                )
            except Exception as e:
                st.error(f"Error: {e}")
