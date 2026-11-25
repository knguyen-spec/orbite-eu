# Ethics and legal red lines

These rules are enforced in code where possible; the rest are product rules.

| Rule | Where it is enforced |
|---|---|
| Official accounts of public figures only; never private individuals | `config/figures.yaml` (human-confirmed); `resolve_accounts.py` only suggests |
| No follower, reposter or commenter identity stored | `privacy.pseudonymise` (salted hash), `privacy.scrub_text`; comments reduced to counts |
| No inferred political belief stored per person | Stance kept as counts per post (`detect.stance_counts`, `stance.count_stance`) |
| Every brief sentence cites a source ID | `brief.validate` rejects uncited output; template fallback |
| "Signal" and "to check", never "fraud" or "fake" | LLM system prompt + human review status |
| Same method for every figure and side | One code path; thresholds are constants in `detect.py` |
| No per-account views for parties, candidates or campaigns | Contract rule; aggregates only for PR and public-affairs firms |
| Pause outputs on the eve and day of each vote | Ops rule (production) |

Legal notes (not legal advice; validate with the DPO):
- Political opinions are special-category data under GDPR Article 9. Pseudonymisation is not anonymisation.
- France's journalism exemption covers press work, not every paying user of the 55 € tier; the product is designed not to need it.
- YouTube API Services terms restrict storing and redistributing data: keep derived aggregates, refresh rather than archive raw content.
- Synthetic results are never presented as evidence about a real person.
