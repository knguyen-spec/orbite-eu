"""YouTube Data API v3. Free key, default quota 10,000 units/day; each list call below costs 1 unit.

Needs YOUTUBE_API_KEY. Avoid search.list (separate, small daily bucket).
Comment text is scrubbed and only used to build per-video aggregates; author names are never kept.
Check the YouTube API Services terms before storing anything beyond derived aggregates.
"""

from __future__ import annotations

import pandas as pd

from ..privacy import scrub_text
from . import DEFAULT_TIMEOUT, make_session

API = "https://www.googleapis.com/youtube/v3"


class QuotaMeter:
    """Counts units spent in this run so the job can stop before the daily cap."""

    def __init__(self, budget: int = 9000):
        self.budget, self.spent = budget, 0

    def charge(self, units: int = 1) -> None:
        if self.spent + units > self.budget:
            raise RuntimeError(f"YouTube quota budget reached ({self.spent}/{self.budget} units)")
        self.spent += units


def _get(path: str, params: dict, key: str, session, meter: QuotaMeter | None) -> dict:
    if meter:
        meter.charge(1)
    r = session.get(f"{API}/{path}", params={**params, "key": key}, timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    return r.json()


def channel_stats(channel_id: str, key: str, session=None, meter=None) -> dict:
    s = session or make_session()
    items = _get("channels", {"part": "statistics,contentDetails", "id": channel_id}, key, s, meter).get("items", [])
    if not items:
        raise ValueError(f"Channel not found: {channel_id}")
    st, cd = items[0]["statistics"], items[0]["contentDetails"]
    return {"channel_id": channel_id,
            "subscribers": int(st.get("subscriberCount", 0)),  # rounded by YouTube
            "views": int(st.get("viewCount", 0)), "videos": int(st.get("videoCount", 0)),
            "uploads_playlist": cd["relatedPlaylists"]["uploads"]}


def recent_videos(uploads_playlist: str, key: str, max_results: int = 50, session=None, meter=None) -> pd.DataFrame:
    """Latest uploads with their public counts (2 units for up to 50 videos)."""
    s = session or make_session()
    pl = _get("playlistItems", {"part": "contentDetails", "playlistId": uploads_playlist,
                                "maxResults": min(max_results, 50)}, key, s, meter)
    ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    if not ids:
        return pd.DataFrame()
    vids = _get("videos", {"part": "statistics,snippet", "id": ",".join(ids)}, key, s, meter)
    rows = []
    for v in vids.get("items", []):
        st, sn = v.get("statistics", {}), v["snippet"]
        likes, comments = int(st.get("likeCount", 0)), int(st.get("commentCount", 0))
        rows.append({"post_id": "YT-" + v["id"], "platform": "YouTube", "created_at": pd.Timestamp(sn["publishedAt"]),
                     "text": sn.get("title", ""), "views": int(st.get("viewCount", 0)),
                     "likes": likes, "comments": comments, "engagement": likes + comments})
    return pd.DataFrame(rows)


def comment_texts(video_id: str, key: str, max_comments: int = 300, session=None, meter=None) -> list[str]:
    """Top-level comment texts only, scrubbed of handles and links. 1 unit per 100 comments."""
    s = session or make_session()
    out, token = [], None
    while len(out) < max_comments:
        params = {"part": "snippet", "videoId": video_id.removeprefix("YT-"), "maxResults": 100,
                  "textFormat": "plainText", "order": "relevance"}
        if token:
            params["pageToken"] = token
        j = _get("commentThreads", params, key, s, meter)
        for it in j.get("items", []):
            out.append(scrub_text(it["snippet"]["topLevelComment"]["snippet"].get("textDisplay", "")))
        token = j.get("nextPageToken")
        if not token:
            break
    return out[:max_comments]
