"""Suggest official YouTube and Bluesky accounts from Wikidata, for HUMAN confirmation.

    python scripts/resolve_accounts.py   # writes config/accounts_suggested.yaml

Copy only accounts you have checked by hand into config/figures.yaml.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orbite.collectors import make_session, wikidata  # noqa: E402


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config" / "figures.yaml").read_text(encoding="utf-8"))
    s, out = make_session(), {}
    for f in cfg["figures"]:
        try:
            out[f["id"]] = wikidata.official_accounts(f["wikipedia_fr"], s)
        except Exception as e:
            out[f["id"]] = {"error": str(e)}
        print(f["id"], out[f["id"]])
    (ROOT / "config" / "accounts_suggested.yaml").write_text(
        "# Suggestions from Wikidata. Confirm each by hand before copying to figures.yaml.\n"
        + yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
