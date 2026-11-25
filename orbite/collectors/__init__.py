"""Collectors for free, public APIs. Each returns pandas DataFrames of aggregates.

All collectors accept an optional `session` (requests.Session-like) so tests can
inject fake responses and production can share retries and timeouts.
"""

import os

import requests

DEFAULT_TIMEOUT = 30


def user_agent() -> str:
    """Wikimedia and others ask for a descriptive User-Agent with a contact."""
    contact = os.environ.get("ORBITE_CONTACT", "https://github.com/your-org/orbite")
    return f"OrbiteResearch/0.3 ({contact})"


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent()})
    adapter = requests.adapters.HTTPAdapter(max_retries=requests.adapters.Retry(
        total=3, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504)))
    s.mount("https://", adapter)
    return s
