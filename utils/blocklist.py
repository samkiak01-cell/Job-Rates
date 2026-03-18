"""Dynamic + static domain blocklist for the salary pipeline.

Static blocklist: known-bad domains that consistently fail (Cloudflare walls,
no salary data, etc.).

Dynamic blocklist: persisted to `pipeline_blocklist.json` and grows as the
pipeline discovers domains that repeatedly wall or fail across runs.
"""

from __future__ import annotations

import json
import pathlib
from typing import Set

_BLOCKLIST_FILE = pathlib.Path("pipeline_blocklist.json")

# Domains that consistently return Cloudflare blocks, have no salary data,
# or are geographically irrelevant to most searches.
STATIC_BLOCKLIST: set[str] = {
    "reddit.com",
    "glassdoor.de",
    "glassdoor.fr",
    "ttecjobs.com",
    "indeed.com",
    "roberthalf.com",
    "monster.com",
    "jobted.com",
    "manpower.com",
}


def load_dynamic_blocklist() -> set[str]:
    """Read the dynamic blocklist from disk.  Returns an empty set if the
    file doesn't exist or is malformed."""
    if not _BLOCKLIST_FILE.exists():
        return set()
    try:
        data = json.loads(_BLOCKLIST_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {d for d in data if isinstance(d, str)}
    except Exception as e:
        print(f"[blocklist] Error loading dynamic blocklist: {e}")
    return set()


def add_to_dynamic_blocklist(domain: str) -> None:
    """Append a domain to the persistent dynamic blocklist file."""
    current = load_dynamic_blocklist()
    if domain in current:
        return
    current.add(domain)
    try:
        _BLOCKLIST_FILE.write_text(
            json.dumps(sorted(current), indent=2),
            encoding="utf-8",
        )
        print(f"[blocklist] Added '{domain}' to dynamic blocklist")
    except Exception as e:
        print(f"[blocklist] Error saving dynamic blocklist: {e}")


def get_full_blocklist() -> set[str]:
    """Return the union of the static and dynamic blocklists."""
    return STATIC_BLOCKLIST | load_dynamic_blocklist()
