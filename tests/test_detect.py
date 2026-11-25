import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orbite import brief, detect, evaluate, synthetic  # noqa: E402


def _posts(values):
    t = pd.date_range("2026-09-01", periods=len(values), freq="D")
    return pd.DataFrame({"figure_id": "F", "post_id": [f"P{i}" for i in range(len(values))],
                         "platform": "YouTube", "created_at": t, "engagement": values})


def test_spike_flagged_and_baseline_ignores_current_post():
    rng = np.random.default_rng(0)
    vals = list(np.exp(np.log(1000) + 0.3 * rng.standard_normal(40)).round())
    vals.append(9000)
    out = detect.engagement_flags(_posts(vals))
    assert bool(out.iloc[-1]["signal"])
    assert out.iloc[:-1]["signal"].sum() <= 1


def test_no_flags_without_history():
    out = detect.engagement_flags(_posts([100, 5000, 100]))
    assert not out["signal"].any()


def test_burst_detection():
    t0 = pd.Timestamp("2026-11-01 21:04")
    rows = [{"post_id": "P", "account": f"a{i}", "at": t0 + pd.Timedelta(seconds=5 * i), "quote": "same"} for i in range(7)]
    rows += [{"post_id": "P", "account": f"b{i}", "at": t0 + pd.Timedelta(hours=i + 1), "quote": ""} for i in range(5)]
    b = detect.repost_bursts(pd.DataFrame(rows))
    assert len(b) == 1 and b.iloc[0]["accounts"] == 7 and b.iloc[0]["same_text_share"] == 1.0


def test_comment_pod():
    c = pd.DataFrame({"post_id": ["P"] * 10 + ["Q"] * 10,
                      "text": ["Top 🔥"] * 6 + [f"avis {i}" for i in range(4)] + [f"x {i}" for i in range(10)]})
    out = detect.comment_patterns(c).set_index("post_id")
    assert out.loc["P", "signal"] and not out.loc["Q", "signal"]


def test_synthetic_end_to_end_meets_recall():
    d = synthetic.generate(n_figures=12, days=120, seed=7)
    posts = detect.engagement_flags(d["posts"])
    fol = detect.follower_steps(d["followers"], posts)
    m = evaluate.score(d["labels"], {"engagement_spike": posts, "bought_followers": fol,
                                     "comment_pod": detect.comment_patterns(d["comments"]),
                                     "coordinated_burst": detect.repost_bursts(d["reposts"]).assign(signal=True)})
    assert (m["recall"] >= 0.8).all(), m


def test_brief_template_is_valid_and_validator_rejects_uncited():
    f = {"figure": "X", "platform": "YouTube", "post_id": "YT-1", "engagement": 900, "baseline": 100,
         "ratio": 9.0, "robust_z": 5.1, "ids": ["YT-1"]}
    assert brief.validate(brief.template(f), f["ids"])
    assert not brief.validate(["Uncited claim."], f["ids"])
    assert not brief.validate(["Wrong id. [YT-2]"], f["ids"])
