# Orbite

**Measure, never judge.** Orbite checks how public figures' posts are received against each account's own baseline, using free public data only, and turns each signal into a sourced brief a person reviews before anything is published.

| Plan | For | Price (hypothesis) | In the app |
|---|---|---|---|
| **Public** | Voters, students, anyone curious | Free, no account | Candidate census, Wikipedia attention index |
| **Signal** | Journalists, fact-checkers, engaged citizens | 55 €/month, 30-day trial | Baseline chart, flagged posts, comment stance (counts), sourced brief |
| **Expert** | Researchers, think tanks, NGOs | ≈ 490 €/month per team; studies on quote | Coordination bursts, repost network, method pack, CSV export |

Data cost: **0 €**. X is not used (pay-per-use was too expensive for follower-level work).

---

## 1. Run the demo locally (5 minutes)

```bash
git clone https://github.com/<your-org>/orbite.git && cd orbite
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/make_synthetic.py                        # synthetic demo data + detector scores
streamlit run app/streamlit_app.py
```

Demo access codes (change them before sharing; see section 3): Signal `signal-demo`, Expert `expert-demo`.

Add real public data at any time, no key needed:

```bash
python scripts/collect.py --check        # which APIs can this machine reach?
python scripts/collect.py --wikipedia    # real daily page views for config/figures.yaml
```

Then switch on **Live data** in the app's sidebar.

## 2. Put it on GitHub

```bash
git init && git add . && git commit -m "Orbite v0.3"
gh repo create <your-org>/orbite --private --source . --push     # or create the repo on github.com
```

- **Actions → tests** runs on every push (`pytest` + synthetic scoring).
- **Actions → daily collection** runs at 05:23 UTC and commits `data/live/`. Trigger it by hand with *Run workflow* (`scope: wikipedia` needs no key).
- Repository secrets (Settings → Secrets and variables → Actions): `YOUTUBE_API_KEY`, `MISTRAL_API_KEY` (optional), `ORBITE_SALT` (any long random string). Variable: `ORBITE_CONTACT` (a project URL or team inbox for the User-Agent).

## 3. Host the demo on Streamlit Community Cloud

1. Go to share.streamlit.io → **Create app** → pick the repo, branch `main`, file `app/streamlit_app.py`.
2. **Advanced settings → Secrets**: paste `.streamlit/secrets.toml.example` with your own access codes (and `MISTRAL_API_KEY` if you want LLM briefs).
3. Deploy. Each push from the daily workflow redeploys the app with fresh data.

Limits to know: Community Cloud apps sleep when unused and wake on the next visit, and hosting is not in the EU. Fine for a demo with synthetic and public aggregates; for production use an EU host (section 5).

## 4. From demo to real time

| Stage | Freshness | How |
|---|---|---|
| Demo (now) | Daily | GitHub Actions cron → parquet in repo → Streamlit Cloud |
| Pilot (Dec–Jan) | Hourly | Cron every hour for Bluesky; YouTube stays daily (quota); move data from git to object storage (S3-compatible, EU) |
| Production (spring 2027) | Near real time | Bluesky firehose consumer (Jetstream) on a small EU VM; YouTube polling within quota; alerts by email; app on an EU container host (e.g. Scaleway) with a managed database |

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 5. What the numbers mean (read before the demo)

Detectors scored on **synthetic** planted labels, pooled over 8 seeds (12 fictional figures × 120 days each):

| Detector | Precision | Recall | Worst seed precision | Target (P ≥ 0.70, R ≥ 0.80) |
|---|---|---|---|---|
| Engagement spike (robust z > 3.5) | 0.65 | 1.00 | 0.33 | Precision **missed** |
| Bought followers (step + no viral post) | 1.00 | 1.00 | 1.00 | Met |
| Comment pod (copy-paste share > 30%) | 1.00 | 1.00 | 1.00 | Met |
| Coordinated burst (5+ accounts in 60 s, same text) | 1.00 | 1.00 | 1.00 | Met |

- The perfect scores mean the planted patterns are easy, not that the detectors are right on real data. Report synthetic and real results separately.
- Spike false alarms come from multiple testing: about 1,700 posts are tested, and a MAD estimated from 60 posts gives z-scores heavier tails than a normal curve. Next step: estimate the false-alarm rate on quiet real weeks and consider Benjamini–Hochberg.
- Two method choices are published in the code: no spike flag before 30 posts of history, and a 5% minimum daily change for follower jumps.

## 6. Repository map

```
app/streamlit_app.py        the demo app (Public / Signal / Expert, plan gating, live toggle)
orbite/collectors/          wikipedia.py · youtube.py · bluesky.py · wikidata.py (free APIs)
orbite/detect.py            robust z, follower steps (+ PELT), comment patterns, repost bursts
orbite/synthetic.py         generator with planted, labelled anomalies (fictional figures)
orbite/evaluate.py          precision / recall against labels
orbite/brief.py             grounded brief: every sentence cites a source ID or is rejected
orbite/stance.py, llm.py    optional Mistral calls (counts only; prompts logged)
orbite/privacy.py           salted hashes, comment scrubbing
orbite/store.py             parquet + DuckDB, no server
scripts/                    make_synthetic.py · collect.py · resolve_accounts.py
config/figures.yaml         who is followed (official accounts only, human-confirmed)
data/census_2026-11-25.csv  real candidate list (LCP, read 25 Nov 2026)
docs/                       ARCHITECTURE · DATA_SOURCES · ETHICS
```

## 7. Before any public launch

- Read the YouTube API Services terms and Bluesky's developer guidelines; store derived aggregates only.
- DPO review (GDPR Art. 9: political opinions). See [docs/ETHICS.md](docs/ETHICS.md).
- Validate stance on 300–500 hand-labelled French comments; run the name-swap bias test on briefs.
