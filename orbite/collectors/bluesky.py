"""Bluesky public AppView (AT Protocol). Free; the read endpoints below are reported to work without a key.

Test from your network before relying on it: `python scripts/collect.py --check`.
Reposters are stored only as salted hashes (see orbite.privacy).
"""

from __future__ import annotations

import pandas as pd

from ..privacy import pseudonymise
from . import DEFAULT_TIMEOUT, make_session

APPVIEW = "https://public.api.bsky.app/xrpc"


def _get(method: str, params: dict, session) -> dict:
    r = session.get(f"{APPVIEW}/{method}", params=params, timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    return r.json()


def profile(handle: str, session=None) -> dict:
    s = session or make_session()
    j = _get("app.bsky.actor.getProfile", {"actor": handle}, s)
    return {"handle": handle, "followers": j.get("followersCount", 0), "posts": j.get("postsCount", 0)}


def author_feed(handle: str, limit: int = 100, session=None) -> pd.DataFrame:
    """Original posts (no replies) with public counts."""
    s = session or make_session()
    j = _get("app.bsky.feed.getAuthorFeed", {"actor": handle, "limit": min(limit, 100),
                                             "filter": "posts_no_replies"}, s)
    rows = []
    for item in j.get("feed", []):
        if "reason" in item:  # skip reposts of other people's posts
            continue
        p = item["post"]
        likes, reposts = p.get("likeCount", 0), p.get("repostCount", 0)
        replies, quotes = p.get("replyCount", 0), p.get("quoteCount", 0)
        rows.append({"post_id": "BS-" + p["uri"].rsplit("/", 1)[-1], "uri": p["uri"], "platform": "Bluesky",
                     "created_at": pd.Timestamp(p["record"].get("createdAt", p.get("indexedAt"))),
                     "text": p["record"].get("text", ""), "likes": likes, "reposts": reposts,
                     "comments": replies, "quotes": quotes, "engagement": likes + reposts + replies + quotes})
    return pd.DataFrame(rows)


def reposters(uri: str, limit: int = 100, session=None) -> list[str]:
    """Hashed identities of accounts that reposted a post (one page, up to 100)."""
    s = session or make_session()
    j = _get("app.bsky.feed.getRepostedBy", {"uri": uri, "limit": min(limit, 100)}, s)
    return [pseudonymise(a["did"]) for a in j.get("repostedBy", [])]
