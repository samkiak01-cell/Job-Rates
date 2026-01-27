# app.py
from __future__ import annotations

import os
import re
import math
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st


# ============================================================
# Page / Layout (ONLY ONCE)
# ============================================================
st.set_page_config(
    page_title="Job Rate Finder",
    page_icon="💼",
    layout="centered",
)


# ============================================================
# Styling (FIXED – single valid Python string)
# ============================================================
APP_CSS = """
<style>
  :root{
    --bg0:#0b1220;
    --bg1:#0f1b33;
    --text:#e8eefc;
    --muted:#a9b7d6;
    --border:rgba(255,255,255,.10);
    --accent:#6d5efc;
    --accent2:#9b4dff;
    --shadow:0 18px 60px rgba(0,0,0,.45);
  }

  html, body, [data-testid="stAppViewContainer"]{
    background: linear-gradient(180deg, var(--bg0), var(--bg1));
    color: var(--text);
  }

  .block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 900px;
  }

  .jr-title{
    text-align:center;
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 0.25rem;
  }

  .jr-subtitle{
    text-align:center;
    font-size: 15px;
    color: var(--muted);
    margin-bottom: 1.5rem;
  }

  .jr-card{
    background: rgba(255,255,255,.05);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px;
    box-shadow: var(--shadow);
  }

  .stTextInput input,
  .stTextArea textarea,
  .stSelectbox div[data-baseweb="select"] > div {
    background: rgba(0,0,0,.25) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
  }

  .stButton button {
    width: 100%;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    color: white;
    font-weight: 700;
    border-radius: 12px;
    padding: 0.65rem 1rem;
  }

  header, footer { visibility: hidden; }
</style>
"""

st.markdown(APP_CSS, unsafe_allow_html=True)


# ============================================================
# Data structures
# ============================================================
@dataclass
class SourceItem:
    title: str
    url: str
    range: str


# ============================================================
# Helpers
# ============================================================
def format_money(n: float) -> str:
    try:
        return f"{int(round(float(n))):,}"
    except Exception:
        return "—"


# ============================================================
# State init
# ============================================================
def init_state():
    defaults = {
        "job_title": "",
        "job_desc": "",
        "country": "",
        "state": "N/A",
        "city": "N/A",
        "rate_type": "salary",
        "currency": "USD",
        "last_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ============================================================
# Header
# ============================================================
st.markdown('<div class="jr-title">Job Rate Finder</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="jr-subtitle">Get competitive salary and hourly rate information for any position</div>',
    unsafe_allow_html=True,
)


# ============================================================
# Form
# ============================================================
st.markdown('<div class="jr-card">', unsafe_allow_html=True)

with st.form("job_rate_form"):
    job_title = st.text_input(
        "Job Title *",
        placeholder="e.g. Senior Software Engineer",
        key="job_title",
    )

    job_desc = st.text_area(
        "Job Description (optional)",
        placeholder="Paste job description here…",
        height=120,
        key="job_desc",
    )

    country = st.text_input("Country *", key="country")

    rate_type_label = st.radio(
        "Rate Type *",
        options=["Salary", "Hourly"],
        horizontal=True,
    )
    st.session_state["rate_type"] = "hourly" if rate_type_label == "Hourly" else "salary"

    currency = st.selectbox(
        "Currency *",
        options=["USD", "EUR", "GBP", "CAD", "AED"],
        key="currency",
    )

    submitted = st.form_submit_button("Get Rates")

st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# Validation
# ============================================================
def is_valid() -> Tuple[bool, str]:
    if not st.session_state["job_title"].strip():
        return False, "Job Title is required."
    if not st.session_state["country"].strip():
        return False, "Country is required."
    return True, ""


# ============================================================
# Submit handling (placeholder)
# ============================================================
if submitted:
    ok, msg = is_valid()
    if not ok:
        st.warning(msg)
    else:
        st.info(
            "UI is running correctly. "
            "Your OpenAI + SerpAPI estimation logic is intentionally not wired yet."
        )
