"""Comment stance on live data: an LLM labels a batch of scrubbed comment texts; only counts are kept.

Zero-shot is weak on French irony. Validate on 300-500 hand-labelled comments and report
F1 per class before showing stance publicly; replace with a fine-tuned French model if needed.
"""

from __future__ import annotations

import json
from collections import Counter

from . import llm

LABELS = ["support", "criticism", "mockery", "off_topic"]
SYSTEM = ("Classify each comment's stance toward the post's author: support, criticism, mockery or off_topic. "
          'Return JSON {"labels": [...]} with exactly one label per comment, in order.')


def count_stance(post_text: str, comments: list[str], batch: int = 50) -> dict[str, int] | None:
    if not llm.available() or not comments:
        return None
    counts: Counter = Counter()
    for i in range(0, len(comments), batch):
        chunk = comments[i:i + batch]
        j = llm.chat_json(SYSTEM, json.dumps({"post": post_text, "comments": chunk}, ensure_ascii=False))
        counts.update(l for l in j.get("labels", [])[:len(chunk)] if l in LABELS)
    return {k: counts.get(k, 0) for k in LABELS}
