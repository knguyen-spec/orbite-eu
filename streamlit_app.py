"""Orbite demo app: Public (free), Signal (55 €/month), Expert (≈ 490 €/month per team).

    streamlit run app/streamlit_app.py

Demo mode reads data/sample (synthetic, fictional figures). Live mode appears once
scripts/collect.py has written data/live. Access codes for paid plans come from
st.secrets["access_codes"]; without secrets the demo codes in README.md apply.
"""

from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orbite import METHOD_VERSION, brief, detect, store  # noqa: E402

st.set_page_config(page_title="Orbite", page_icon="🪐", layout="wide")

INK, IA, REGLE, HUMAIN, OK = "#121833", "#6B3FD6", "#3F57D9", "#8F5308", "#11795A"
PLANS = {"Public": 0, "Signal": 1, "Expert": 2}
DEMO_CODES = {"Signal": "signal-demo", "Expert": "expert-demo"}


# ---------- data ----------
@st.cache_data(ttl=3600)
def load(mode: str) -> dict:
    names = ["figures", "posts_scored", "followers_scored", "comment_patterns", "stance", "reposts", "bursts", "metrics", "attention"]
    return {n: store.read(n, mode) for n in names}


@st.cache_data
def census() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "census_2026-11-25.csv").fillna("")


def codes() -> dict:
    try:
        return dict(st.secrets["access_codes"])
    except Exception:
        return DEMO_CODES


# ---------- sidebar: plan and data mode ----------
with st.sidebar:
    st.markdown("### 🪐 Orbite\n*Measure, never judge.*")
    plan = st.radio("Plan", list(PLANS), captions=["Free · no account", "55 €/month · 30-day trial", "≈ 490 €/month per team"])
    unlocked = plan == "Public"
    if plan != "Public":
        code = st.text_input(f"{plan} access code", type="password", help="Demo codes are in README.md")
        unlocked = code == codes().get(plan)
        if code and not unlocked:
            st.error("That code doesn't match. Check README.md for the demo codes.")
    level = PLANS[plan] if unlocked else 0
    live_ok = store.path("posts_scored", "live").exists() or store.path("attention", "live").exists()
    mode = "live" if st.toggle("Live data", value=False, disabled=not live_ok,
                               help="Runs on data/live once scripts/collect.py has run") else "sample"
    st.caption(f"Method {METHOD_VERSION} · data: {'live public aggregates' if mode == 'live' else 'synthetic, fictional figures'}")

D = load(mode)
demo = load("sample")  # Expert method pack always shows synthetic scores, labelled as such
attention_live = load("live").get("attention")


def locked(need: str) -> None:
    st.info(f"**Part of Orbite {need}.** Choose {need} in the sidebar and enter its access code to open this view.")


def fig_name(fid: str) -> str:
    f = D.get("figures")
    if f is not None and fid in set(f.figure_id):
        r = f.set_index("figure_id").loc[fid]
        return f"{r['name']} · {r['party']} (fictional)" if r.get("fictional", False) else str(r["name"])
    return fid


tabs = st.tabs(["Public", "Signal", "Expert", "Data sources", "Method & trust"])

# ---------- Public ----------
with tabs[0]:
    st.subheader("Who is running in 2027")
    st.caption("Real data. Source: LCP list of declared and potential candidates, read 25 Nov 2026. Order follows the source, not the polls. Orbite recommends no one.")
    c = census()
    for grp, g in c.groupby("group", sort=False):
        st.markdown(f"**{grp}** · {len(g)}")
        st.dataframe(g[["name", "party", "note"]], hide_index=True, width="stretch")
    st.subheader("Public attention: Wikipedia page views")
    if attention_live is not None and not attention_live.empty:
        a = attention_live
        pick = st.multiselect("Figures", sorted(a["name"].unique()), default=sorted(a["name"].unique())[:4])
        figp = go.Figure()
        for n in pick:
            g = a[a.name == n]
            figp.add_scatter(x=g.date, y=g.views, mode="lines", name=n)
            s = g[g.signal]
            figp.add_scatter(x=s.date, y=s.views, mode="markers", marker=dict(color=HUMAIN, size=9), showlegend=False,
                             hovertemplate="%{x|%d %b}: %{y:,} views (signal)<extra>" + n + "</extra>")
        figp.update_layout(yaxis_type="log", yaxis_title="Daily views (log)", height=380, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(figp, width="stretch")
        st.caption("Amber dots: days above robust z 3.5 against each figure's own 60-day baseline. Attention is not support.")
    else:
        st.info("Run `python scripts/collect.py --wikipedia` (free, no key) to load real daily page views for the figures in config/figures.yaml.")

# ---------- Signal ----------
with tabs[1]:
    posts = D.get("posts_scored")
    if level < 1:
        locked("Signal")
    elif posts is None or posts.empty:
        st.info("No scored posts yet in this mode. Run `python scripts/make_synthetic.py` or the live collector.")
    else:
        k1, k2, k3, k4 = st.columns(4)
        week = posts.created_at.max() - pd.Timedelta(days=7)
        k1.metric("Figures watched", posts.figure_id.nunique())
        k2.metric("Signals this week", int(posts[(posts.created_at > week) & posts.signal].shape[0]))
        k3.metric("Data cost", "0 €")
        k4.metric("Threshold", f"robust z > {detect.Z_THRESHOLD}")
        fids = sorted(posts.figure_id.unique())
        fid = st.selectbox("Figure", fids, format_func=fig_name)
        g = posts[posts.figure_id == fid].sort_values("created_at")
        fg = go.Figure()
        fg.add_scatter(x=g.created_at, y=g.baseline, mode="lines", line=dict(color=IA, dash="dash"), name="Baseline (median of previous 60 posts)")
        n = g[~g.signal]
        fg.add_scatter(x=n.created_at, y=n.engagement, mode="markers", marker=dict(color=REGLE, size=6), name="Post",
                       customdata=n.post_id, hovertemplate="%{customdata}<br>%{y:,}<extra></extra>")
        s = g[g.signal]
        fg.add_scatter(x=s.created_at, y=s.engagement, mode="markers", marker=dict(color=HUMAIN, size=12), name="Signal",
                       customdata=s.post_id, hovertemplate="%{customdata}<br>%{y:,}<extra></extra>")
        fg.update_layout(yaxis_type="log", yaxis_title="Engagement per post (log)", height=380, margin=dict(l=10, r=10, t=10, b=10),
                         legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fg, width="stretch")
        if s.empty:
            st.success("No signal for this figure in the period.")
        else:
            pid = st.selectbox("Flagged post", list(s.post_id[::-1]))
            p = s.set_index("post_id").loc[pid]
            a, b = st.columns(2)
            with a:
                st.markdown(f"**{pid}** · {p.platform} · {p.created_at:%d %b %Y %H:%M}")
                st.markdown(f"> {p.text}")
                st.markdown(f"Engagement **{int(p.engagement):,}** · **{p.ratio:.1f}×** baseline · robust z **{p.robust_z:.1f}**")
                st.caption("A signal, not proof of manipulation or bias.")
            stance_df = D.get("stance")
            st_row = None
            if stance_df is not None and pid in set(stance_df.post_id):
                st_row = stance_df.set_index("post_id").loc[pid].to_dict()
            with b:
                if st_row:
                    st.markdown("**Comment stance** (counts only, sample)")
                    sc = pd.Series(st_row).reindex(["support", "criticism", "mockery", "off_topic"]).fillna(0)
                    fb = go.Figure(go.Bar(x=sc.values, y=sc.index, orientation="h", marker_color=REGLE,
                                          text=[f"{v:.0f}" for v in sc.values], textposition="outside"))
                    fb.update_layout(height=200, margin=dict(l=10, r=30, t=5, b=5), xaxis_title="Comments")
                    st.plotly_chart(fb, width="stretch")
                else:
                    st.caption("No comment sample for this post.")
            bursts = D.get("bursts")
            bl = bursts[bursts.post_id == pid].to_dict("records") if (level >= 2 and bursts is not None) else []
            facts = brief.facts_for(p.to_dict() | {"post_id": pid}, {"name": fig_name(fid)}, st_row, bl)
            lang = st.radio("Brief language", ["en", "fr"], horizontal=True)
            out = brief.write_brief(facts, lang)
            st.markdown(f"**Sourced brief** · {out['source']} · *{out['status']}*")
            txt = "\n".join(out["sentences"])
            st.text_area("Brief", txt, height=140, label_visibility="collapsed")
            st.download_button("Download brief (.txt)", txt, file_name=f"brief_{pid}.txt")

# ---------- Expert ----------
with tabs[2]:
    if level < 2:
        locked("Expert")
    else:
        bursts, reposts, posts = D.get("bursts"), D.get("reposts"), D.get("posts_scored")
        st.subheader("Coordination bursts")
        st.caption("Windows where 5+ distinct accounts reposted the same post within 60 seconds. Accounts are pseudonymous; private people are never named.")
        if bursts is not None and not bursts.empty:
            st.dataframe(bursts.sort_values("accounts", ascending=False), hide_index=True, width="stretch")
            pid = st.selectbox("Repost network around post", list(bursts.post_id.unique()))
            r = reposts[reposts.post_id == pid]
            bset = set(r[r.quote != ""].account)
            G = nx.Graph()
            for acct in r.account.unique():
                G.add_edge(pid, acct)
            pos = nx.spring_layout(G, seed=3)
            ex, ey = [], []
            for u, v in G.edges():
                ex += [pos[u][0], pos[v][0], None]
                ey += [pos[u][1], pos[v][1], None]
            gn = go.Figure()
            gn.add_scatter(x=ex, y=ey, mode="lines", line=dict(color="#D3D8EA", width=1), hoverinfo="skip", showlegend=False)
            nodes = [n for n in G.nodes if n != pid]
            gn.add_scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode="markers", showlegend=False,
                           marker=dict(size=8, color=[HUMAIN if n in bset else REGLE for n in nodes]), hoverinfo="skip")
            gn.add_scatter(x=[pos[pid][0]], y=[pos[pid][1]], mode="markers+text", text=[pid], textposition="top center",
                           marker=dict(size=16, color=IA), showlegend=False)
            gn.update_layout(height=380, xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(gn, width="stretch")
            st.caption("Amber: accounts in the burst with identical quote text. Blue: other reposters.")
        elif reposts is None:
            st.info("Repost data is collected on Bluesky only, and only after scripts/collect.py --all has run.")
        else:
            st.success("No bursts found.")
        st.subheader("Method pack")
        m = demo.get("metrics")
        if m is not None:
            st.caption("Scored on the SYNTHETIC generator's planted labels. This proves the detectors find these planted patterns, not that they are right on real data.")
            st.dataframe(m, hide_index=True, width="stretch")
        st.subheader("Export")
        if posts is not None:
            agg = posts[["figure_id", "platform", "post_id", "created_at", "engagement", "baseline", "robust_z", "signal"]]
            st.download_button("Download scored aggregates (.csv)", agg.to_csv(index=False), file_name=f"orbite_{mode}_{METHOD_VERSION}.csv")
        st.code(f"GET /v1/signals?figure=<id>&from=2026-10-01   # planned API (method {METHOD_VERSION})", language="text")

# ---------- Data sources ----------
with tabs[3]:
    st.subheader("Where every number comes from")
    st.dataframe(pd.DataFrame([
        ["LCP census", "Article (snapshot CSV)", "Who is running", "Public", "Free", "Weekly", "Real snapshot 25 Nov 2026"],
        ["Wikipedia page views", "wikimedia.org/api/rest_v1/metrics/pageviews", "Attention index", "Public", "Free, no key", "Daily", "Collector ready"],
        ["Wikidata", "query.wikidata.org/sparql", "Official accounts (human-confirmed)", "All", "Free", "Weekly", "Script ready"],
        ["YouTube Data API v3", "channels · playlistItems · videos · commentThreads", "Reception, comment sample", "Signal, Expert", "Free key, 10,000 units/day", "Daily", "Collector ready"],
        ["Bluesky AppView", "getProfile · getAuthorFeed · getRepostedBy", "Posts, repost network", "Signal, Expert", "Free", "Daily", "Collector ready"],
        ["Mistral API", "chat/completions (EU)", "Briefs, stance counts", "Signal, Expert", "≈ $0.10 / $0.30 per M tokens", "Per brief", "Optional; template fallback"],
        ["X API", "pay-per-use", "Not used", "—", "$0.005 per post read", "—", "Dropped: cost"],
    ], columns=["Source", "Endpoint", "Feeds", "Plan", "Cost", "Refresh", "Status"]), hide_index=True, width="stretch")
    log = store.DATA / "live" / "run_log.json"
    if log.exists():
        st.caption("Last live collection run")
        st.code(log.read_text(), language="json")

# ---------- Method ----------
with tabs[4]:
    st.subheader("Principles")
    st.markdown("""
- Measure, never judge character or recommend a vote.
- Same method for every figure and every political side, published in full.
- Each account is compared with its own baseline: robust z > 3.5 on log engagement against the median and MAD of its previous 60 posts.
- Aggregates over individuals. No follower, reposter or commenter identity is stored; repost networks use salted hashes.
- Every brief sentence cites a source ID; briefs stay *awaiting review* until a named person checks them.
- Anyone, candidates included, can contest a status; corrections are logged.
- No per-account views for parties, candidates or campaigns. Pause new outputs on the eve and day of each vote.
""")
