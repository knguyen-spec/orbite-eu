"""Collectors parsed against recorded-shape fake responses (no network in CI)."""

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orbite.collectors import bluesky, wikipedia, youtube  # noqa: E402


class FakeResp:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    def __init__(self, payloads):
        self.payloads, self.calls = list(payloads), []

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append((url, params))
        return FakeResp(self.payloads.pop(0))


def test_wikipedia_parses_items():
    s = FakeSession([{"items": [{"timestamp": "2026112000", "views": 1234}, {"timestamp": "2026112100", "views": 99}]}])
    df = wikipedia.pageviews("Marine Le Pen", dt.date(2026, 11, 20), dt.date(2026, 11, 21), session=s)
    assert list(df.views) == [1234, 99] and "Marine_Le_Pen" in s.calls[0][0]


def test_bluesky_feed_skips_reposts_and_sums_engagement():
    post = {"uri": "at://did:plc:x/app.bsky.feed.post/abc", "likeCount": 10, "repostCount": 2, "replyCount": 3, "quoteCount": 1,
            "record": {"text": "hello", "createdAt": "2026-11-20T10:00:00Z"}}
    s = FakeSession([{"feed": [{"post": post}, {"post": post, "reason": {"$type": "repost"}}]}])
    df = bluesky.author_feed("example.bsky.social", session=s)
    assert len(df) == 1 and df.iloc[0]["engagement"] == 16 and df.iloc[0]["post_id"] == "BS-abc"


def test_bluesky_reposters_are_hashed():
    s = FakeSession([{"repostedBy": [{"did": "did:plc:alice"}, {"did": "did:plc:bob"}]}])
    out = bluesky.reposters("at://x", session=s)
    assert len(out) == 2 and all("did:" not in h for h in out)


def test_youtube_quota_meter_stops_before_cap():
    m = youtube.QuotaMeter(budget=1)
    s = FakeSession([{"items": [{"statistics": {"subscriberCount": "1000"}, "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]}])
    youtube.channel_stats("UC1", "key", s, m)
    with pytest.raises(RuntimeError):
        youtube.channel_stats("UC1", "key", s, m)


def test_youtube_comments_are_scrubbed():
    s = FakeSession([{"items": [{"snippet": {"topLevelComment": {"snippet": {"textDisplay": "@bob voir https://x.co ici"}}}}]}])
    out = youtube.comment_texts("YT-abc", "key", 10, s)
    assert out == ["@user voir <url> ici"]
