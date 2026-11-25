"""Generate the synthetic demo dataset, run all detectors and score them against the planted labels.

    python scripts/make_synthetic.py            # writes data/sample/*.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orbite import detect, evaluate, store, synthetic  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figures", type=int, default=12)
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    d = synthetic.generate(a.figures, a.days, a.seed)
    posts = detect.engagement_flags(d["posts"])
    followers = detect.follower_steps(d["followers"], posts)
    patterns = detect.comment_patterns(d["comments"])
    stance = detect.stance_counts(d["comments"])
    bursts = detect.repost_bursts(d["reposts"])
    burst_flags = bursts.assign(signal=bursts["same_text_share"] >= 0.5)
    metrics = evaluate.score(d["labels"], {"engagement_spike": posts, "bought_followers": followers,
                                           "comment_pod": patterns, "coordinated_burst": burst_flags})

    for name, df in {"figures": d["figures"], "posts_scored": posts, "followers_scored": followers,
                     "comment_patterns": patterns, "stance": stance, "reposts": d["reposts"],
                     "bursts": bursts, "labels": d["labels"], "metrics": metrics}.items():
        store.write(df, name, "sample")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
