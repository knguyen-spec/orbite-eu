"""Score detectors against the synthetic generator's labels.

Targets fixed before testing (POC plan): recall >= 0.80 and precision >= 0.70 per anomaly type.
"""

from __future__ import annotations

import pandas as pd

TARGETS = {"recall": 0.80, "precision": 0.70}


def _pr(pred: set, truth: set) -> dict:
    tp = len(pred & truth)
    precision = tp / len(pred) if pred else float("nan")
    recall = tp / len(truth) if truth else float("nan")
    return {"predicted": len(pred), "labelled": len(truth), "true_pos": tp,
            "precision": round(precision, 3), "recall": round(recall, 3)}


def score(labels: pd.DataFrame, flags: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """flags: {'engagement_spike': posts_df, 'bought_followers': followers_df, 'comment_pod': ..., 'coordinated_burst': ...}"""
    rows = []
    for kind in ["engagement_spike", "comment_pod", "coordinated_burst"]:
        truth = set(labels.loc[labels.type == kind, "post_id"])
        f = flags.get(kind)
        pred = set(f.loc[f["signal"], "post_id"]) if f is not None and "signal" in f else set(f["post_id"]) if f is not None else set()
        rows.append({"detector": kind, **_pr(pred, truth)})
    # day-level: a predicted step counts if within 1 day of the labelled start
    truth = labels[labels.type == "bought_followers"][["figure_id", "date"]]
    f = flags.get("bought_followers")
    pred = f.loc[f["event"], ["figure_id", "date"]] if f is not None else pd.DataFrame(columns=["figure_id", "date"])
    hit_truth = {(r.figure_id, r.date) for r in truth.itertuples()
                 if ((pred.figure_id == r.figure_id) & ((pred.date - r.date).abs() <= pd.Timedelta(days=1))).any()}
    hit_pred = sum(((truth.figure_id == r.figure_id) & ((truth.date - r.date).abs() <= pd.Timedelta(days=1))).any()
                   for r in pred.itertuples())
    rows.append({"detector": "bought_followers", "predicted": len(pred), "labelled": len(truth), "true_pos": len(hit_truth),
                 "precision": round(hit_pred / len(pred), 3) if len(pred) else float("nan"),
                 "recall": round(len(hit_truth) / len(truth), 3) if len(truth) else float("nan")})
    out = pd.DataFrame(rows)
    out["meets_target"] = (out["recall"] >= TARGETS["recall"]) & (out["precision"] >= TARGETS["precision"])
    return out
