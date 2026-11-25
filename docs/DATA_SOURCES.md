# Data sources (checked November 2026; reconfirm before launch)

| Source | Endpoint(s) | Key | Cost / limit | Used for | Plan |
|---|---|---|---|---|---|
| LCP candidate list | Article, snapshot in `data/census_2026-11-25.csv` | No | Free | Who is running | Public |
| Wikipedia page views | `wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/all-access/user/{article}/daily/{start}/{end}` | No (send a descriptive User-Agent) | Free; history from mid-2015 | Attention index, long baseline | Public, Signal |
| Wikidata | `query.wikidata.org/sparql`; P2397 YouTube channel ID, P12361 Bluesky handle (confirm) | No | Free | Suggest official accounts for human confirmation | All |
| YouTube Data API v3 | `channels.list`, `playlistItems.list`, `videos.list`, `commentThreads.list` | Yes (free) | 10,000 units/day default; these calls cost 1 unit each; avoid `search.list` | Subscribers (rounded), views, likes, comment counts, comment sample | Signal, Expert |
| Bluesky AppView | `public.api.bsky.app/xrpc/app.bsky.actor.getProfile`, `app.bsky.feed.getAuthorFeed`, `app.bsky.feed.getRepostedBy` | Reported not needed for these reads; `searchPosts` needs an app password | Free | Posts, counts, repost network (hashed) | Signal, Expert |
| Mistral API | `api.mistral.ai/v1/chat/completions` | Yes | ≈ $0.10 in / $0.30 out per million tokens (Mistral Small, Oct 2026) | Briefs, stance counts | Signal, Expert |
| X API | pay-per-use | — | $0.005 per post read, $0.010 per user read | **Not used** | — |

Not included yet (see the Data Source Map doc): Community Notes daily download, Google Fact Check Claim Search, Arcom speaking-time CSVs, Assemblée nationale open data, OpenAlex.

TikTok's Research API and Meta's Content Library are limited to academic and non-profit researchers, so they are out of scope for the commercial product.
