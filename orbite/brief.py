"""Grounded brief: every sentence must cite a source ID from the facts, or the brief is rejected.

The LLM only rephrases facts Orbite computed; it never adds numbers. Without an API key,
a deterministic template produces the same structure (used in the demo and in tests).
"""

from __future__ import annotations

import json
import re

from . import llm

SYSTEM = ("You write short, neutral briefs for journalists. Use ONLY the facts given. "
          "Every sentence ends with one or more source IDs in square brackets, taken from the facts' 'ids'. "
          "Never say fraud, fake, manipulation or bias; say 'signal' and 'to check'. "
          'Return JSON: {"sentences": ["...[ID]", ...]} with 3 to 5 sentences.')

CITE = re.compile(r"\[([A-Za-z0-9_\-:, ]+)\]\s*$")


def facts_for(post: dict, figure: dict, stance: dict | None = None, bursts: list[dict] | None = None) -> dict:
    f = {"figure": figure["name"], "platform": post["platform"], "post_id": post["post_id"],
         "engagement": int(post["engagement"]), "baseline": round(float(post["baseline"])),
         "ratio": round(float(post["ratio"]), 1), "robust_z": round(float(post["robust_z"]), 1),
         "ids": [post["post_id"]]}
    if stance:
        sid = f"RS-{post['post_id']}"
        total = sum(stance.values()) or 1
        f["comment_stance_pct"] = {k: round(100 * v / total) for k, v in stance.items()}
        f["ids"].append(sid)
    for b in bursts or []:
        bid = f"BURST-{post['post_id']}-{b['start']:%H%M}"
        f.setdefault("bursts", []).append({"id": bid, "time": f"{b['start']:%H:%M}", "accounts": int(b["accounts"]),
                                           "same_text_share": b["same_text_share"]})
        f["ids"].append(bid)
    return f


def validate(sentences: list[str], allowed_ids: list[str]) -> bool:
    for s in sentences:
        m = CITE.search(s.strip())
        if not m:
            return False
        ids = [i.strip() for i in m.group(1).split(",")]
        if not ids or any(i not in allowed_ids for i in ids):
            return False
    return bool(sentences)


def template(f: dict, lang: str = "en") -> list[str]:
    pid = f["post_id"]
    if lang == "fr":
        out = [f"La publication {pid} de {f['figure']} ({f['platform']}) a reçu {f['ratio']} fois son engagement habituel (z robuste {f['robust_z']}). [{pid}]"]
        if "comment_stance_pct" in f:
            s = f["comment_stance_pct"]
            out.append(f"Dans l'échantillon de commentaires, {s.get('support', 0)} % expriment un soutien et {s.get('criticism', 0)} % une critique. [RS-{pid}]")
        for b in f.get("bursts", []):
            out.append(f"À {b['time']}, {b['accounts']} comptes l'ont republiée en moins d'une minute. [{b['id']}]")
        out.append(f"C'est un signal à vérifier, pas une preuve. [{pid}]")
        return out
    out = [f"Post {pid} by {f['figure']} ({f['platform']}) drew {f['ratio']} times its usual engagement (robust z {f['robust_z']}). [{pid}]"]
    if "comment_stance_pct" in f:
        s = f["comment_stance_pct"]
        out.append(f"In the comment sample, {s.get('support', 0)}% express support and {s.get('criticism', 0)}% criticism. [RS-{pid}]")
    for b in f.get("bursts", []):
        out.append(f"At {b['time']}, {b['accounts']} accounts reposted it within one minute. [{b['id']}]")
    out.append(f"This is a signal to check, not proof. [{pid}]")
    return out


def write_brief(f: dict, lang: str = "en") -> dict:
    """Returns {'sentences', 'source': 'llm'|'template', 'status': 'awaiting review'}."""
    if llm.available():
        try:
            j = llm.chat_json(SYSTEM, f"Language: {lang}\nFacts:\n{json.dumps(f, ensure_ascii=False, default=str)}")
            sents = j.get("sentences", [])
            if validate(sents, f["ids"]):
                return {"sentences": sents, "source": "llm", "status": "awaiting review"}
        except Exception:  # network, quota or format error: fall back, never block the analyst
            pass
    return {"sentences": template(f, lang), "source": "template", "status": "awaiting review"}
