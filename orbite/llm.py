"""Minimal Mistral client (EU-hosted API). Optional: without MISTRAL_API_KEY, callers fall back to templates.

Freeze the model version for a campaign (MISTRAL_MODEL) and log every prompt for audit.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

URL = "https://api.mistral.ai/v1/chat/completions"
LOG = Path(__file__).resolve().parents[1] / "data" / "llm_log.jsonl"


def available() -> bool:
    return bool(os.environ.get("MISTRAL_API_KEY"))


def chat_json(system: str, user: str, temperature: float = 0.0, timeout: int = 60) -> dict:
    model = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
    r = requests.post(URL, timeout=timeout, headers={"Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}"},
                      json={"model": model, "temperature": temperature, "response_format": {"type": "json_object"},
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": time.time(), "model": model, "system": system, "user": user, "output": content},
                                ensure_ascii=False) + "\n")
    except OSError:
        pass
    return json.loads(content)
