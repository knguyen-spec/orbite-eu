"""Wikipedia page views: free, no key, daily history back to mid-2015.

Used as Orbite's long public-attention baseline from day one.
Endpoint: https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/
"""

from __future__ import annotations

import datetime as dt
import urllib.parse

import pandas as pd

from . import DEFAULT_TIMEOUT, make_session

BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"


def pageviews(title: str, start: dt.date, end: dt.date, project: str = "fr.wikipedia",
              agent: str = "user", session=None) -> pd.DataFrame:
    """Daily views for one article. `agent='user'` excludes known bots and spiders."""
    s = session or make_session()
    article = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"{BASE}/{project}/all-access/{agent}/{article}/daily/{start:%Y%m%d}00/{end:%Y%m%d}00"
    r = s.get(url, timeout=DEFAULT_TIMEOUT)
    if r.status_code == 404:  # article has no views in range, or wrong title
        return pd.DataFrame(columns=["date", "article", "views"])
    r.raise_for_status()
    rows = [{"date": pd.Timestamp(i["timestamp"][:8]), "article": title, "views": int(i["views"])}
            for i in r.json().get("items", [])]
    return pd.DataFrame(rows, columns=["date", "article", "views"])
