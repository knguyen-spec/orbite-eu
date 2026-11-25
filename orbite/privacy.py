"""Privacy helpers. Orbite never stores who follows, reposts or comments.

Repost networks are drawn from salted hashes, so a node can be counted and
clustered but never looked up. Rotate ORBITE_SALT to make old hashes unlinkable.
"""

from __future__ import annotations

import hashlib
import os
import re

_URL = re.compile(r"https?://\S+")
_HANDLE = re.compile(r"@[\w.\-]+")


def pseudonymise(identifier: str, salt: str | None = None) -> str:
    """Return a short salted hash. Not anonymisation under GDPR: treat outputs as personal data."""
    salt = salt if salt is not None else os.environ.get("ORBITE_SALT", "change-me")
    return hashlib.sha256(f"{salt}:{identifier}".encode()).hexdigest()[:12]


def scrub_text(text: str) -> str:
    """Remove handles and links from comment text before any processing."""
    return _HANDLE.sub("@user", _URL.sub("<url>", text or "")).strip()
