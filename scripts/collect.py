"""Daily collector for live, public, aggregate data. Run by .github/workflows/collect.yml.

    python scripts/collect.py --check          # can each API be reached from here?
    python scripts/collect.py --wikipedia      # free, no key: public-attention index
    python scripts/collect.py --all            # + YouTube (needs YOUTUBE_API_KEY) + Bluesky

Writes data/live/*.parquet and data/live/run_log.json. Data cost: 0 €.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orbite import detect, store  # noqa: E402
from orbite.collectors import bluesky, make_session, wikipedia, youtube  # noqa: E402


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config" / "figures.yaml").read_text(encoding="utf-8"))


def check(session) -> None:
    tests = {"wikipedia": lambda: wikipedia.pageviews("Assemblée nationale (France)", dt.date.today() - dt.timedelta(days=3),
                                                      dt.date.today() - dt.timedelta(days=1), session=session),
             "bluesky": lambda: bluesky.profile("bsky.app", session=session)}
    if os.environ.get("YOUTUBE_API_KEY"):
        tests["youtube"] = lambda: youtube.channel_stats("UC_x5XG1OV2P6uZZ5FSM9Ttw", os.environ["YOUTUBE_API_KEY"], session=session)
    for name, fn in tests.items():
        try:
            fn()
            print(f"OK    {name}")
        except Exception as e:  # report and continue
            print(f"FAIL  {name}: {e}")


def collect_wikipedia(cfg: dict, session, log: dict) -> None:
    days = cfg["settings"]["attention_days"]
    end = dt.date.today() - dt.timedelta(days=1)
    frames = []
    for f in cfg["figures"]:
        df = wikipedia.pageviews(f["wikipedia_fr"], end - dt.timedelta(days=days), end, session=session)
        frames.append(df.assign(figure_id=f["id"], name=f["name"]))
    pv = pd.concat(frames, ignore_index=True)
    scored = []
    for _, g in pv.sort_values("date").groupby("figure_id"):
        g = g.copy()
        g[["baseline", "robust_z"]] = detect.robust_z(g["views"], window=60, min_history=20).values
        g["signal"] = g["robust_z"] > detect.Z_THRESHOLD
        scored.append(g)
    store.write(pd.concat(scored, ignore_index=True), "attention", "live")
    log["wikipedia_rows"] = len(pv)


def collect_youtube(cfg: dict, session, log: dict) -> list[pd.DataFrame]:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        log["youtube"] = "skipped: no YOUTUBE_API_KEY"
        return []
    meter = youtube.QuotaMeter(cfg["settings"]["youtube_quota_budget"])
    frames, today = [], pd.Timestamp(dt.date.today())
    for f in cfg["figures"]:
        if not f.get("youtube_channel_id"):
            continue
        ch = youtube.channel_stats(f["youtube_channel_id"], key, session, meter)
        store.append(pd.DataFrame([{"figure_id": f["id"], "date": today, "followers": ch["subscribers"], "platform": "YouTube"}]),
                     "followers", ["figure_id", "date", "platform"])
        vids = youtube.recent_videos(ch["uploads_playlist"], key, cfg["settings"]["youtube_videos_per_figure"], session, meter)
        if not vids.empty:
            frames.append(vids.assign(figure_id=f["id"], collected_at=today))
    log["youtube_units"] = meter.spent
    return frames


def collect_bluesky(cfg: dict, session, log: dict) -> list[pd.DataFrame]:
    frames, today = [], pd.Timestamp(dt.date.today())
    for f in cfg["figures"]:
        h = f.get("bluesky_handle")
        if not h:
            continue
        p = bluesky.profile(h, session)
        store.append(pd.DataFrame([{"figure_id": f["id"], "date": today, "followers": p["followers"], "platform": "Bluesky"}]),
                     "followers", ["figure_id", "date", "platform"])
        feed = bluesky.author_feed(h, cfg["settings"]["bluesky_posts_per_figure"], session)
        if not feed.empty:
            frames.append(feed.assign(figure_id=f["id"], collected_at=today))
    log["bluesky_figures"] = sum(bool(f.get("bluesky_handle")) for f in cfg["figures"])
    return frames


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--wikipedia", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    s, cfg = make_session(), load_config()
    if a.check:
        check(s)
        return
    log = {"started": dt.datetime.now(dt.timezone.utc).isoformat()}
    if a.wikipedia or a.all:
        collect_wikipedia(cfg, s, log)
    if a.all:
        frames = collect_youtube(cfg, s, log) + collect_bluesky(cfg, s, log)
        if frames:
            # counts change after publication: keep the latest snapshot per post
            posts = store.append(pd.concat(frames, ignore_index=True), "posts", ["post_id"])
            all_posts = pd.read_parquet(posts)
            store.write(detect.engagement_flags(all_posts), "posts_scored", "live")
            fol = store.read("followers", "live")
            if fol is not None:
                store.write(detect.follower_steps(fol, store.read("posts_scored", "live")), "followers_scored", "live")
    log["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (store.DATA / "live").mkdir(parents=True, exist_ok=True)
    (store.DATA / "live" / "run_log.json").write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
