"""Explainable detectors. Each compares an account with its own baseline, never with other accounts.

Every function returns a DataFrame with the evidence needed to explain the flag.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

Z_THRESHOLD = 3.5      # robust z; published in the method pack
MAD_TO_SD = 0.6745     # scales MAD to a standard deviation under normality


def robust_z(x: pd.Series, window: int = 60, min_history: int = 15) -> pd.DataFrame:
    """Robust z of each value against the median/MAD of the *previous* `window` values."""
    lx = np.log1p(x.astype(float))
    prev = lx.shift(1).rolling(window, min_periods=min_history)
    med = prev.median()
    mad = prev.apply(lambda w: np.nanmedian(np.abs(w - np.nanmedian(w))), raw=True)
    z = MAD_TO_SD * (lx - med) / mad.replace(0, np.nan)
    return pd.DataFrame({"baseline": np.expm1(med), "robust_z": z})


def engagement_flags(posts: pd.DataFrame, window: int = 60, threshold: float = Z_THRESHOLD,
                     min_history: int = 30) -> pd.DataFrame:
    """Flag posts whose engagement is far above the figure's own baseline.

    No flag before `min_history` posts: a MAD from fewer posts is too noisy (z gets heavy tails).
    """
    out = []
    for _, g in posts.sort_values("created_at").groupby("figure_id"):
        g = g.copy()
        g[["baseline", "robust_z"]] = robust_z(g["engagement"], window, min_history).values
        g["ratio"] = g["engagement"] / g["baseline"]
        g["signal"] = g["robust_z"] > threshold
        out.append(g)
    return pd.concat(out, ignore_index=True) if out else posts.assign(baseline=np.nan, robust_z=np.nan, ratio=np.nan, signal=False)


def follower_steps(followers: pd.DataFrame, scored_posts: pd.DataFrame | None = None,
                   window: int = 30, threshold: float = Z_THRESHOLD, min_change: float = 0.05) -> pd.DataFrame:
    """Daily follower jumps not explained by a viral post in the previous 48 hours.

    `min_change` is a minimum effect size (5% in a day): on very steady accounts the MAD is tiny,
    so a 0.5% wobble can score z > 3.5 without meaning anything. Published in the method pack.
    """
    out = []
    for fid, g in followers.sort_values("date").groupby("figure_id"):
        g = g.copy()
        g["change"] = g["followers"].pct_change()
        prev = g["change"].shift(1).rolling(window, min_periods=10)
        med = prev.median()
        mad = prev.apply(lambda w: np.nanmedian(np.abs(w - np.nanmedian(w))), raw=True)
        g["robust_z"] = MAD_TO_SD * (g["change"] - med) / mad.replace(0, np.nan)
        viral = set()
        if scored_posts is not None:
            v = scored_posts[(scored_posts.figure_id == fid) & scored_posts.signal]
            for d in v["created_at"].dt.normalize():
                viral.update({d, d + pd.Timedelta(days=1), d + pd.Timedelta(days=2)})
        g["explained_by_viral_post"] = g["date"].isin(viral)
        g["signal"] = (g["robust_z"] > threshold) & (g["change"] >= min_change) & ~g["explained_by_viral_post"]
        out.append(g)
    res = pd.concat(out, ignore_index=True)
    # keep the first day of a multi-day step as the event
    res["event"] = res["signal"] & ~res.groupby("figure_id")["signal"].shift(1, fill_value=False)
    return res


def step_changes(series: pd.Series, penalty: float = 10.0) -> list[int]:
    """Change points (PELT) on a follower series; confirms that a jump lasts."""
    try:
        import ruptures as rpt
    except ImportError:  # optional dependency
        return []
    y = np.log(series.astype(float).clip(lower=1)).diff().fillna(0).to_numpy().reshape(-1, 1)
    return rpt.Pelt(model="l2").fit(y).predict(pen=penalty)[:-1]


def _norm(t: str) -> str:
    return " ".join(str(t).lower().split())


def comment_patterns(comments: pd.DataFrame, dup_threshold: float = 0.30, min_copies: int = 3) -> pd.DataFrame:
    """Per post: share of comments repeated verbatim >= min_copies times, and share of very short comments."""
    c = comments.assign(norm=comments["text"].map(_norm))
    counts = c.groupby(["post_id", "norm"]).size().rename("n").reset_index()
    c = c.merge(counts, on=["post_id", "norm"])
    agg = c.groupby("post_id").agg(sampled=("text", "size"),
                                   dup_share=("n", lambda s: float((s >= min_copies).mean())),
                                   short_share=("norm", lambda s: float((s.str.len() < 15).mean()))).reset_index()
    agg["signal"] = agg["dup_share"] > dup_threshold
    return agg


def stance_counts(comments: pd.DataFrame) -> pd.DataFrame:
    """Counts per post and stance. Counts only: nothing is kept per commenter."""
    return comments.pivot_table(index="post_id", columns="stance", values="text", aggfunc="size", fill_value=0).reset_index()


def repost_bursts(reposts: pd.DataFrame, window: str = "60s", min_accounts: int = 5) -> pd.DataFrame:
    """Windows where >= min_accounts distinct accounts repost the same post within `window`."""
    rows = []
    w = pd.Timedelta(window)
    for pid, g in reposts.sort_values("at").groupby("post_id"):
        times, accts, quotes = g["at"].to_numpy(), g["account"].to_numpy(), g["quote"].to_numpy()
        j = 0
        for i in range(len(times)):
            while times[i] - times[j] > w:
                j += 1
            n = len(set(accts[j:i + 1]))
            if n >= min_accounts:
                q = pd.Series(quotes[j:i + 1])
                q = q[q != ""]
                same = float(q.value_counts(normalize=True).iloc[0]) if len(q) else 0.0
                rows.append({"post_id": pid, "start": pd.Timestamp(times[j]), "accounts": n, "same_text_share": round(same, 2)})
    df = pd.DataFrame(rows, columns=["post_id", "start", "accounts", "same_text_share"])
    if not df.empty:  # keep the largest window per post and 10-minute slot
        slot = df["start"].dt.floor("10min")
        df = df.loc[df.groupby([df["post_id"], slot])["accounts"].idxmax()].reset_index(drop=True)
    return df
