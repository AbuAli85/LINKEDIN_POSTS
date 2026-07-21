"""Post performance tracking: fetch LinkedIn engagement stats and record quality scores."""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

from atomic_io import write_json

HISTORY_DIR = Path(__file__).parent / "posts_history"

HOOK_STYLES = [
    "numbered-list",   # "5 ways X..."
    "question",        # "Why does..."
    "bold-statement",  # Direct contrarian claim
    "story",           # "Last week I..."
    "data-lead",       # Starts with a number or stat
    "observation",     # "I've noticed..."
    "contrast",        # "Everyone says X. I do Y."
]


# ---------------------------------------------------------------------------
# LinkedIn API
# ---------------------------------------------------------------------------

def fetch_linkedin_stats(post_id: str) -> dict:
    """Fetch engagement counts for a published post. Returns {} on any failure."""
    token = (os.environ.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
    if not token:
        print("WARNING: LINKEDIN_ACCESS_TOKEN not set — skipping API fetch.", file=sys.stderr)
        return {}

    import urllib.parse
    encoded = urllib.parse.quote(post_id, safe="")
    url = f"https://api.linkedin.com/v2/socialActions/{encoded}"

    try:
        resp = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"WARNING: LinkedIn socialActions returned {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
            return {}
        data = resp.json()
        # LinkedIn may use either summary objects or flat counts depending on API version
        reactions = (
            (data.get("likesSummary") or {}).get("totalLikes")
            or data.get("likedByCount")
            or 0
        )
        comments = (
            (data.get("commentsSummary") or {}).get("totalFirstLevelComments")
            or data.get("commentCount")
            or 0
        )
        shares = data.get("shareCount", 0)
        return {"reactions": reactions, "comments": comments, "shares": shares}
    except Exception as exc:
        print(f"WARNING: LinkedIn stats fetch failed: {exc}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# Disk I/O helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save(path: Path, post: dict) -> None:
    write_json(path, post)


def _merge_metrics(path: Path, updates: dict) -> dict:
    post = _load(path)
    existing = post.get("metrics") or {}
    existing.update(updates)
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    post["metrics"] = existing
    _save(path, post)
    return existing


# ---------------------------------------------------------------------------
# Public API used by main.py and generator.py
# ---------------------------------------------------------------------------

def fetch_post(path: Path) -> dict:
    """Pull LinkedIn stats for a single post file and merge them in."""
    post = _load(path)
    post_id = post.get("post_id", "")
    if not post_id:
        print(f"SKIP {path.name}: no post_id (not published yet).")
        return {}
    print(f"Fetching stats for {path.name} ({post_id})...")
    stats = fetch_linkedin_stats(post_id)
    if not stats:
        print("  No data returned from LinkedIn.")
        return {}
    merged = _merge_metrics(path, stats)
    print(f"  reactions={merged.get('reactions', 0)}  comments={merged.get('comments', 0)}  shares={merged.get('shares', 0)}")
    return merged


def fetch_all_published() -> int:
    """Fetch LinkedIn stats for every published post in posts_history/. Returns count updated."""
    published = [
        f for f in sorted(HISTORY_DIR.glob("*.json"))
        if _load(f).get("published")
    ]
    if not published:
        print("No published posts found.")
        return 0
    updated = 0
    for path in published:
        if fetch_post(path):
            updated += 1
    print(f"\nUpdated {updated}/{len(published)} posts.")
    return updated


def score_post(path: Path, score: int, hook_style: str | None, notes: str | None) -> None:
    """Write a manual quality score (1-10) and optional metadata to a post file."""
    if not (1 <= score <= 10):
        raise SystemExit("Score must be between 1 and 10.")
    updates: dict = {"manual_quality_score": score}
    if hook_style:
        if hook_style not in HOOK_STYLES:
            valid = ", ".join(HOOK_STYLES)
            raise SystemExit(f"Invalid hook style. Choose one of: {valid}")
        updates["hook_style"] = hook_style
    if notes:
        updates["review_notes"] = notes
    _merge_metrics(path, updates)
    print(f"Scored {path.name}: {score}/10" + (f"  hook={hook_style}" if hook_style else ""))


def get_performance_summary() -> dict:
    """Aggregate quality scores across all posts. Returns {} when < 3 scored posts exist."""
    posts = []
    for f in HISTORY_DIR.glob("*.json"):
        try:
            p = _load(f)
            if p.get("metrics"):
                posts.append(p)
        except Exception:
            continue

    scored = [p for p in posts if p["metrics"].get("manual_quality_score") is not None]
    if len(scored) < 3:
        return {}

    pillar_scores: dict[str, list] = defaultdict(list)
    hook_scores: dict[str, list] = defaultdict(list)

    for p in scored:
        s = p["metrics"]["manual_quality_score"]
        pillar_scores[p.get("pillar", "unknown")].append(s)
        if hs := p["metrics"].get("hook_style"):
            hook_scores[hs].append(s)

    pillar_avg = {k: round(sum(v) / len(v), 1) for k, v in pillar_scores.items()}
    hook_avg   = {k: round(sum(v) / len(v), 1) for k, v in hook_scores.items()}

    top3 = sorted(scored, key=lambda p: p["metrics"].get("manual_quality_score", 0), reverse=True)[:3]

    return {
        "total_scored": len(scored),
        "pillar_avg_score": pillar_avg,
        "hook_avg_score": hook_avg,
        "best_pillar": max(pillar_avg, key=pillar_avg.get) if pillar_avg else None,
        "best_hook_style": max(hook_avg, key=hook_avg.get) if hook_avg else None,
        "top_topics": [p.get("topic", "") for p in top3],
        "top_posts_preview": [p.get("post", "").split("\n", 1)[0][:100] for p in top3],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def check_token_scope() -> None:
    """Diagnose whether the current LinkedIn token has social read scope.

    Checks /v2/me (basic auth) then probes /v2/socialActions with a dummy URN.
    A 403 on the social probe means r_member_social is missing from the token.
    """
    import requests as _req
    token = (os.environ.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
    if not token:
        print("ERROR: LINKEDIN_ACCESS_TOKEN is not set.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    me = _req.get("https://api.linkedin.com/v2/me", headers=headers, timeout=10)
    if me.status_code == 200:
        data = me.json()
        name = f"{data.get('localizedFirstName', '')} {data.get('localizedLastName', '')}".strip()
        print(f"Token valid — authenticated as: {name or '(name unavailable)'}")
    else:
        print(f"WARNING: /v2/me returned {me.status_code}. Token may be expired or invalid.")

    # Probe social scope with a known-invalid URN — 403 = missing scope, 404 = scope present but URN unknown
    probe = _req.get(
        "https://api.linkedin.com/v2/socialActions/urn:li:share:000000000000",
        headers=headers,
        timeout=10,
    )
    if probe.status_code == 403:
        print("FAIL: r_member_social scope missing — engagement fetch will return 0 counts.")
        print("      Re-run OAuth and add 'r_member_social' to the requested scopes.")
    elif probe.status_code in (404, 200):
        print("OK: r_member_social scope confirmed (probe returned expected non-403 response).")
    else:
        print(f"UNKNOWN: social probe returned {probe.status_code} — check manually.")


def _cli() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn post performance tracking.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # fetch — pull stats for one file
    p_fetch = sub.add_parser("fetch", help="Fetch LinkedIn stats for a single post file.")
    p_fetch.add_argument("path", help="Path to the post JSON file.")

    # fetch-all — pull stats for all published posts
    sub.add_parser("fetch-all", help="Fetch LinkedIn stats for all published posts.")

    # score — write manual quality score
    p_score = sub.add_parser("score", help="Record a manual quality score for a post.")
    p_score.add_argument("path", help="Path to the post JSON file.")
    p_score.add_argument("--score", type=int, required=True, help="Quality score 1-10.")
    p_score.add_argument("--style", choices=HOOK_STYLES, help="Hook style classification.")
    p_score.add_argument("--notes", help="Short review notes.")

    # summary — print performance summary
    sub.add_parser("summary", help="Print aggregated performance summary.")

    # check-scope — diagnose LinkedIn token permissions
    sub.add_parser("check-scope", help="Check whether the token has r_member_social scope.")

    args = parser.parse_args()

    if args.cmd == "fetch":
        fetch_post(Path(args.path))
    elif args.cmd == "fetch-all":
        fetch_all_published()
    elif args.cmd == "score":
        score_post(Path(args.path), args.score, getattr(args, "style", None), getattr(args, "notes", None))
    elif args.cmd == "summary":
        summary = get_performance_summary()
        if not summary:
            print("Not enough scored posts yet (need at least 3).")
        else:
            print(json.dumps(summary, indent=2))
    elif args.cmd == "check-scope":
        check_token_scope()


if __name__ == "__main__":
    _cli()
