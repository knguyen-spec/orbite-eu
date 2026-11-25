"""Resolve official accounts of public figures from Wikidata (free SPARQL endpoint).

Only official accounts listed on Wikidata are proposed, and a human must confirm
each one in config/figures.yaml. Orbite never matches ordinary users across platforms.
"""

from __future__ import annotations

from . import DEFAULT_TIMEOUT, make_session

SPARQL = "https://query.wikidata.org/sparql"
P_YOUTUBE_CHANNEL = "P2397"   # YouTube channel ID
P_BLUESKY_HANDLE = "P12361"   # Bluesky handle: confirm on wikidata.org before first use

QUERY = """
SELECT ?item ?yt ?bsky WHERE {{
  ?article schema:about ?item ; schema:isPartOf <https://fr.wikipedia.org/> ; schema:name "{title}"@fr .
  OPTIONAL {{ ?item wdt:{p_yt} ?yt . }}
  OPTIONAL {{ ?item wdt:{p_bs} ?bsky . }}
}} LIMIT 5
"""


def official_accounts(wikipedia_title: str, session=None) -> dict:
    s = session or make_session()
    q = QUERY.format(title=wikipedia_title.replace("_", " ").replace('"', ""), p_yt=P_YOUTUBE_CHANNEL, p_bs=P_BLUESKY_HANDLE)
    r = s.get(SPARQL, params={"query": q, "format": "json"}, timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    rows = r.json()["results"]["bindings"]
    pick = lambda k: sorted({b[k]["value"] for b in rows if k in b})
    return {"wikidata": pick("item")[0].rsplit("/", 1)[-1] if pick("item") else "",
            "youtube_channel_ids": pick("yt"), "bluesky_handles": pick("bsky")}
