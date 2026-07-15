"""Link liveness check — fail if any canonical SmartPRO URL is dead.

Iterates every key in links.PATHS, requests the canonical URL (following
redirects), and fails on any non-200. Wired into the GitHub Actions workflow
before the publish step and exposed via `python panel.py doctor`, so a route
that 404s (the /careers class of bug) can never ship into a published post.

Usage:
    python check_links.py            # exit 0 if all live, 1 if any dead
    python check_links.py --json     # machine-readable report on stdout
"""
from __future__ import annotations

import json
import sys

import requests

import links

TIMEOUT = 15
# One retry smooths over transient 5xx / network blips so a single hiccup in CI
# doesn't block the day's post. A genuinely dead route fails both attempts.
RETRIES = 2


def check_url(u: str) -> tuple[bool, int | None, str]:
    """Return (ok, status_code, note) for a single URL after following redirects."""
    last_err = ""
    for attempt in range(RETRIES):
        try:
            resp = requests.get(u, timeout=TIMEOUT, allow_redirects=True)
            note = f"{resp.status_code}"
            if resp.history:
                note += f" (redirected from {resp.history[0].status_code})"
            return resp.status_code == 200, resp.status_code, note
        except requests.RequestException as e:
            last_err = str(e)
    return False, None, f"request failed: {last_err}"


def check_all() -> list[dict]:
    """Check every canonical URL in links.PATHS. Returns a list of result dicts."""
    results = []
    for key in links.PATHS:
        u = links.url(key)
        ok, status, note = check_url(u)
        results.append({"key": key, "url": u, "ok": ok, "status": status, "note": note})
    return results


def main(argv: list[str]) -> int:
    results = check_all()
    as_json = "--json" in argv

    if as_json:
        print(json.dumps(results, indent=2))
    else:
        print("Link liveness check (canonical URLs from links.PATHS):\n")
        for r in results:
            mark = "OK  " if r["ok"] else "DEAD"
            print(f"  [{mark}] {r['key']:<12} {r['url']}  -> {r['note']}")

    dead = [r for r in results if not r["ok"]]
    if dead:
        if not as_json:
            print(f"\nFAIL: {len(dead)} dead link(s): {', '.join(r['key'] for r in dead)}")
        return 1
    if not as_json:
        print(f"\nOK: all {len(results)} links live.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
