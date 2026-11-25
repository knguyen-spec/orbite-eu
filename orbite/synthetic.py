"""Synthetic generator with planted, labelled anomalies.

Gives the ground truth the real APIs cannot: every anomaly is known, so detectors
can be scored. It proves only that Orbite finds *this kind* of anomaly; report
synthetic and real results separately and never present synthetic scores as
evidence about a real person. All figures are fictional.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

GENERIC = ["Bravo !", "Top 🔥", "Exactement", "Enfin quelqu'un qui le dit", "100% d'accord", "Merci 👏"]
TOPICS = ["retraites", "budget", "dette", "énergie", "école", "sécurité", "Europe", "santé"]
FIRST = ["Claire", "Julien", "Nadia", "Hugo", "Léa", "Marc", "Sofia", "Paul", "Inès", "Yanis", "Chloé", "Thomas"]
LAST = ["Morel", "Faure", "Benali", "Lambert", "Roux", "Garnier", "Diallo", "Perrin", "Lefort", "Haddad", "Vidal", "Caron"]
STANCES = ["support", "criticism", "mockery", "off_topic"]


def generate(n_figures: int = 12, days: int = 120, seed: int = 7, start: str = "2026-08-01") -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    t0 = pd.Timestamp(start)
    figures, posts, followers, comments, reposts, labels = [], [], [], [], [], []

    # assign at least two of each anomaly type across figures
    kinds = ["engagement_spike", "bought_followers", "coordinated_burst", "comment_pod"]
    plan = {i: [] for i in range(n_figures)}
    for k_i, kind in enumerate(kinds):
        for j in range(2):
            plan[(k_i * 3 + j * 5) % n_figures].append(kind)

    pool = [f"acct{n:04d}" for n in range(1200)]  # anonymous ids only

    for i in range(n_figures):
        fid = f"F{i:02d}"
        platform = "YouTube" if i % 2 == 0 else "Bluesky"
        base = float(rng.choice([400, 900, 1800, 4200, 9000]))
        f0 = int(base * rng.uniform(40, 90))
        figures.append({"figure_id": fid, "name": f"{FIRST[i % 12]} {LAST[(i * 5) % 12]}",
                        "party": f"Parti {chr(65 + i % 5)}", "platform": platform, "fictional": True})

        # posts
        fig_posts = []
        for d in range(days):
            for _ in range(rng.poisson(1.4)):
                ts = t0 + pd.Timedelta(days=d, minutes=int(rng.integers(7 * 60, 23 * 60)))
                eng = float(np.exp(np.log(base) + 0.35 * rng.standard_normal()))
                topic = str(rng.choice(TOPICS))
                fig_posts.append({"post_id": f"{'YT' if platform == 'YouTube' else 'BS'}-{fid}-{len(fig_posts):04d}",
                                  "figure_id": fid, "platform": platform, "created_at": ts,
                                  "text": f"Sur {topic} : notre position est claire.", "topic": topic, "engagement": eng})
        fp = pd.DataFrame(fig_posts)
        later = fp[fp.created_at > t0 + pd.Timedelta(days=45)].index  # keep history before anomalies

        if "engagement_spike" in plan[i]:
            for idx in rng.choice(later, size=2, replace=False):
                fp.loc[idx, "engagement"] *= rng.uniform(5, 9)
                labels.append({"type": "engagement_spike", "figure_id": fid, "post_id": fp.loc[idx, "post_id"],
                               "date": fp.loc[idx, "created_at"].normalize()})
        burst_posts = []
        if "coordinated_burst" in plan[i]:
            burst_posts = list(fp.loc[rng.choice(later, size=2, replace=False), "post_id"])
            for pid in burst_posts:
                labels.append({"type": "coordinated_burst", "figure_id": fid, "post_id": pid,
                               "date": fp.loc[fp.post_id == pid, "created_at"].iloc[0].normalize()})
        pod_posts = []
        if "comment_pod" in plan[i]:
            pod_posts = list(fp.loc[rng.choice(later, size=3, replace=False), "post_id"])
            for pid in pod_posts:
                labels.append({"type": "comment_pod", "figure_id": fid, "post_id": pid,
                               "date": fp.loc[fp.post_id == pid, "created_at"].iloc[0].normalize()})

        # followers: slow trend + noise + small bump after viral posts
        viral_days = set(fp.loc[fp.engagement > 3 * base, "created_at"].dt.normalize())
        step_day = int(rng.integers(55, days - 10)) if "bought_followers" in plan[i] else None
        f = f0
        for d in range(days):
            day = t0 + pd.Timedelta(days=d)
            g = rng.normal(0.0015, 0.0012)
            if (day - pd.Timedelta(days=1)) in viral_days:
                g += rng.uniform(0.01, 0.03)
            if step_day is not None and d in (step_day, step_day + 1):
                g += rng.uniform(0.06, 0.18)
            f = max(int(f * (1 + g)), 0)
            followers.append({"figure_id": fid, "date": day, "followers": f})
        if step_day is not None:
            labels.append({"type": "bought_followers", "figure_id": fid, "post_id": None,
                           "date": t0 + pd.Timedelta(days=step_day)})
            after = fp.created_at > t0 + pd.Timedelta(days=step_day)
            fp.loc[after, "engagement"] *= 0.85  # engagement rate falls after bought followers

        fp["engagement"] = fp["engagement"].round().astype(int)
        posts.append(fp)

        # comments (sample of 30 per post) with stance; pods add copy-paste generic comments
        for _, p in fp.iterrows():
            pod = p.post_id in pod_posts
            probs = rng.dirichlet([3, 3, 2, 1])
            for c in range(30):
                if pod and rng.random() < 0.55:
                    text, stance = str(rng.choice(GENERIC[:2])), "support"
                elif rng.random() < 0.05:
                    text, stance = str(rng.choice(GENERIC)), "support"
                else:
                    stance = str(rng.choice(STANCES, p=probs))
                    text = f"{stance} {p.topic} {rng.integers(1_000_000)}"
                comments.append({"post_id": p.post_id, "text": text, "stance": stance})

        # reposts: organic spread over hours; bursts add 6-8 accounts within 60 s with identical quote text
        cluster = pool[(i % 3) * 400:(i % 3) * 400 + 400]
        for _, p in fp.iterrows():
            n = int(min(40, max(3, p.engagement / base * 12)))
            for _ in range(n):
                acct = cluster[int(rng.integers(len(cluster)))] if rng.random() < 0.8 else pool[int(rng.integers(len(pool)))]
                reposts.append({"post_id": p.post_id, "account": acct,
                                "at": p.created_at + pd.Timedelta(seconds=int(rng.exponential(3 * 3600))), "quote": ""})
            if p.post_id in burst_posts:
                at = p.created_at + pd.Timedelta(minutes=int(rng.integers(20, 120)))
                for acct in rng.choice(pool[800:], size=int(rng.integers(6, 9)), replace=False):
                    reposts.append({"post_id": p.post_id, "account": str(acct),
                                    "at": at + pd.Timedelta(seconds=int(rng.integers(0, 50))),
                                    "quote": "Il faut que tout le monde voie ça. Partagez !"})

    return {"figures": pd.DataFrame(figures), "posts": pd.concat(posts, ignore_index=True),
            "followers": pd.DataFrame(followers), "comments": pd.DataFrame(comments),
            "reposts": pd.DataFrame(reposts), "labels": pd.DataFrame(labels)}
