"""Lead detection and outreach pipeline for SmartPro LinkedIn automation.

Commands:
  python outreach.py fetch          # fetch all new comments from LinkedIn
  python outreach.py qualify        # run Claude qualification on unscored comments
  python outreach.py draft-replies  # draft replies for qualified leads
  python outreach.py draft-dms      # draft DM sequences for high-intent replied leads
  python outreach.py export         # export leads.csv
  python outreach.py run-all        # run all steps in sequence
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests

HISTORY_DIR  = Path(__file__).parent / "posts_history"
OUTREACH_DIR = Path(__file__).parent / "outreach_history"
LEADS_CSV    = Path(__file__).parent / "leads.csv"

OUTREACH_DIR.mkdir(exist_ok=True)

CLAUDE_MODEL     = "claude-sonnet-4-6"
LI_BASE          = "https://api.linkedin.com/v2"
MAX_RETRIES      = 3
RETRY_BASE_DELAY = 60  # seconds


# ---------------------------------------------------------------------------
# LinkedIn API helpers
# ---------------------------------------------------------------------------

def _li_headers() -> dict:
    token = (os.environ.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN not set.")
    return {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def _encode(urn: str) -> str:
    return urllib.parse.quote(urn, safe="")


def _li_get(url: str) -> dict | None:
    """GET with exponential backoff on 429/5xx. Returns None on 401 (logs and continues)."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=_li_headers(), timeout=15)
        except Exception as exc:
            print(f"  Network error: {exc}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
            continue

        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 401:
            print("  WARNING: LinkedIn token expired (401) — skipping.", file=sys.stderr)
            return None
        if resp.status_code == 429 or resp.status_code >= 500:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"  Rate limit/server error ({resp.status_code}), retrying in {delay}s...",
                  file=sys.stderr)
            time.sleep(delay)
            continue
        print(f"  WARNING: LinkedIn API returned {resp.status_code} — skipping.", file=sys.stderr)
        return None
    return None


def fetch_comments_for_post(post_id: str) -> list[dict]:
    """Fetch all comments for a published post. Returns [] on any failure."""
    url = f"{LI_BASE}/socialActions/{_encode(post_id)}/comments?count=50"
    data = _li_get(url)
    if data is None:
        return []

    comments = []
    for el in data.get("elements", []):
        actor = el.get("actor", "")
        # Actor is typically a URN string
        commenter_id = actor if isinstance(actor, str) else str(actor)

        # Name resolution: LinkedIn social actions API returns URNs, not names.
        # We store the URN; display name can be enriched later.
        commenter_name = ""
        if isinstance(actor, dict):
            fn = actor.get("localizedFirstName", "")
            ln = actor.get("localizedLastName", "")
            commenter_name = f"{fn} {ln}".strip()

        message = el.get("message", {})
        text = message.get("text", "") if isinstance(message, dict) else str(message)

        created = el.get("created", {})
        ts = created.get("time", 0) if isinstance(created, dict) else 0
        try:
            comment_date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat() if ts else ""
        except Exception:
            comment_date = ""

        # Build LinkedIn profile URL from URN
        safe_commenter = commenter_id.replace("urn:li:person:", "")
        li_url = (f"https://www.linkedin.com/in/{safe_commenter}"
                  if commenter_id.startswith("urn:li:person:") else "")

        comments.append({
            "comment_id":           el.get("id", ""),
            "commenter_id":         commenter_id,
            "commenter_name":       commenter_name,
            "commenter_title":      "",
            "commenter_linkedin_url": li_url,
            "comment_text":         text,
            "comment_date":         comment_date,
            "qualification":        None,
            "reply_drafts":         [],
            "recommended_reply":    0,
            "replied":              False,
            "replied_at":           None,
            "dm_sequence_drafted":  False,
        })
    return comments


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _all_comment_files() -> list[Path]:
    return sorted(OUTREACH_DIR.glob("*_comments.json"))


def _all_dm_files() -> list[Path]:
    return sorted(OUTREACH_DIR.glob("*_dm_sequence.json"))


def _existing_comment_ids() -> set[str]:
    ids: set[str] = set()
    for f in _all_comment_files():
        try:
            for c in _load_json(f).get("comments", []):
                if cid := c.get("comment_id"):
                    ids.add(cid)
        except Exception:
            continue
    return ids


# ---------------------------------------------------------------------------
# Claude helpers
# ---------------------------------------------------------------------------

def _claude() -> anthropic.Anthropic:
    return anthropic.Anthropic()


_QUALIFY_SYSTEM = (
    "You are a lead qualifier for SmartPro, an HR/payroll SaaS for Oman businesses. "
    "Score this LinkedIn comment 1-10 for sales intent. High score (7+): commenter has a "
    "real HR/payroll/WPS problem, is likely a decision maker, comment shows genuine pain or "
    "curiosity. Low score (1-3): generic praise, competitor, recruiter, unrelated. "
    "Return JSON only — no markdown, no explanation outside the JSON."
)

_QUALIFY_USER = """Score this LinkedIn comment for sales intent.

POST TOPIC: {post_topic}
POST PILLAR: {post_pillar}
COMMENTER NAME: {commenter_name}
COMMENT: {comment_text}

Return JSON only:
{{
  "score": <int 1-10>,
  "reason": "<one sentence>",
  "title_guess": "<likely job title>",
  "company_guess": "<likely company or industry>",
  "intent": "high" | "medium" | "low",
  "recommended_action": "reply" | "dm" | "ignore"
}}"""

_REPLY_SYSTEM = (
    "You are Fahad Alamri (Abu Ali), founder of SmartPro. You're replying to a LinkedIn comment. "
    "Rules: Never pitch directly. Continue the conversation. Add one specific insight the "
    "commenter didn't mention. End with a soft open question or 'happy to share more — DM me.' "
    "Max 3 sentences. Sound human, not corporate. Context: SmartPro automates HR/WPS/payroll "
    "for Oman businesses. WhatsApp +96879665522. thesmartpro.io"
)

_REPLY_USER = """Draft 2 reply options for this LinkedIn comment.

POST TOPIC: {post_topic}
COMMENT BY {commenter_name}: {comment_text}

Return JSON only:
{{
  "replies": ["option 1 (max 3 sentences)", "option 2 (different angle, max 3 sentences)"],
  "recommended": 0
}}"""

_DM_SYSTEM = (
    "You are Fahad Alamri (Abu Ali), founder of SmartPro — HR/WPS/payroll SaaS for Oman businesses. "
    "Draft a 3-message DM sequence for a LinkedIn lead who engaged with one of your posts. "
    "Rules: No pitching in message 1. Be genuinely helpful. Reference the original post topic. "
    "Message 3 is the only one with a direct demo ask. Sound like a founder, not a salesperson. "
    "Keep each message under 120 words. Return JSON only."
)

_DM_USER = """Draft a 3-message DM sequence for this lead.

ORIGINAL POST TOPIC: {post_topic}
COMMENTER NAME: {commenter_name}
THEIR COMMENT: {comment_text}
INTENT SCORE: {score}/10 — {intent}

Message guidelines:
- Message 1 (send immediately): deliver value, reference original post, no pitch
- Message 2 (day 3): share the most relevant SmartPro use case / outcome as a mini case study
- Message 3 (day 7): ask if a 20-min no-pitch WPS demo would be useful

Return JSON only:
{{
  "messages": [
    {{"day": 0, "message": "..."}},
    {{"day": 3, "message": "..."}},
    {{"day": 7, "message": "..."}}
  ]
}}"""


def qualify_comment(comment: dict, post_topic: str, post_pillar: str) -> dict:
    """Run Claude qualification on a single comment. Returns qualification dict."""
    try:
        resp = _claude().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system=_QUALIFY_SYSTEM,
            messages=[{"role": "user", "content": _QUALIFY_USER.format(
                post_topic=post_topic,
                post_pillar=post_pillar,
                commenter_name=comment.get("commenter_name", "Unknown"),
                comment_text=comment.get("comment_text", ""),
            )}],
        )
        return json.loads(resp.content[0].text.strip())
    except Exception as exc:
        print(f"  WARNING: qualification failed: {exc}", file=sys.stderr)
        return {
            "score": 0, "reason": "Qualification failed — review manually.",
            "title_guess": "", "company_guess": "",
            "intent": "low", "recommended_action": "ignore",
        }


def draft_replies_for_comment(comment: dict, post_topic: str) -> tuple[list[str], int]:
    """Draft 2 reply options. Returns (replies_list, recommended_index)."""
    try:
        resp = _claude().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            system=_REPLY_SYSTEM,
            messages=[{"role": "user", "content": _REPLY_USER.format(
                post_topic=post_topic,
                commenter_name=comment.get("commenter_name", "them"),
                comment_text=comment.get("comment_text", ""),
            )}],
        )
        data = json.loads(resp.content[0].text.strip())
        return data.get("replies", []), data.get("recommended", 0)
    except Exception as exc:
        print(f"  WARNING: reply drafting failed: {exc}", file=sys.stderr)
        return [], 0


def draft_dm_sequence(comment: dict, post_topic: str, qualification: dict) -> list[dict]:
    """Draft a 3-message DM sequence for a high-intent lead."""
    try:
        resp = _claude().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=_DM_SYSTEM,
            messages=[{"role": "user", "content": _DM_USER.format(
                post_topic=post_topic,
                commenter_name=comment.get("commenter_name", "them"),
                comment_text=comment.get("comment_text", ""),
                score=qualification.get("score", 0),
                intent=qualification.get("intent", "medium"),
            )}],
        )
        data = json.loads(resp.content[0].text.strip())
        return data.get("messages", [])
    except Exception as exc:
        print(f"  WARNING: DM drafting failed: {exc}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_fetch() -> None:
    """Fetch all new comments from all published posts."""
    published = []
    for f in sorted(HISTORY_DIR.glob("*.json")):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            if p.get("post_id"):
                published.append((f, p))
        except Exception:
            continue

    if not published:
        print("No published posts with post_id found.")
        return

    existing_ids = _existing_comment_ids()
    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    for f, post in published:
        post_id = post["post_id"]
        print(f"Fetching comments for {f.name} ({post_id[:40]})...")
        try:
            raw_comments = fetch_comments_for_post(post_id)
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            continue

        new_comments = [c for c in raw_comments if c["comment_id"] not in existing_ids]
        if not new_comments:
            print("  No new comments.")
            continue

        safe_id = post_id.replace("urn:li:share:", "").replace(":", "_")[:20]
        out_path = OUTREACH_DIR / f"{today}_{safe_id}_comments.json"

        # Merge with existing file for this post/day if it exists
        if out_path.exists():
            try:
                data = _load_json(out_path)
            except Exception:
                data = {"post_id": post_id, "post_topic": post.get("topic", ""),
                        "post_pillar": post.get("pillar", ""), "fetched_at": "", "comments": []}
        else:
            data = {"post_id": post_id, "post_topic": post.get("topic", ""),
                    "post_pillar": post.get("pillar", ""), "fetched_at": "", "comments": []}

        data["fetched_at"] = datetime.now(timezone.utc).isoformat()
        data["comments"].extend(new_comments)
        for c in new_comments:
            existing_ids.add(c["comment_id"])

        _save_json(out_path, data)
        print(f"  Saved {len(new_comments)} new comment(s) to {out_path.name}")


def cmd_qualify() -> None:
    """Run Claude qualification on all unscored comments."""
    comment_files = _all_comment_files()
    if not comment_files:
        print("No comment files found. Run: python outreach.py fetch")
        return

    total = 0
    for f in comment_files:
        try:
            data = _load_json(f)
        except Exception as exc:
            print(f"  Error reading {f.name}: {exc}", file=sys.stderr)
            continue

        post_topic  = data.get("post_topic", "")
        post_pillar = data.get("post_pillar", "")
        modified    = False

        for comment in data.get("comments", []):
            if comment.get("qualification") is not None:
                continue
            if not comment.get("comment_text", "").strip():
                continue

            name = comment.get("commenter_name", "Unknown")
            print(f"  Qualifying: {name} — {comment['comment_text'][:60]}...")
            comment["qualification"] = qualify_comment(comment, post_topic, post_pillar)
            intent = comment["qualification"].get("intent", "low")
            score  = comment["qualification"].get("score", 0)
            print(f"    → intent={intent}, score={score}/10")
            modified = True
            total += 1

        if modified:
            _save_json(f, data)

    print(f"\nQualified {total} comment(s).")


def cmd_draft_replies() -> None:
    """Draft 2 reply options for all high/medium-intent unhandled comments."""
    total = 0
    for f in _all_comment_files():
        try:
            data = _load_json(f)
        except Exception as exc:
            print(f"  Error reading {f.name}: {exc}", file=sys.stderr)
            continue

        post_topic = data.get("post_topic", "")
        modified   = False

        for comment in data.get("comments", []):
            qual = comment.get("qualification")
            if not qual or qual.get("intent", "low") not in ("high", "medium"):
                continue
            if comment.get("reply_drafts"):
                continue

            name = comment.get("commenter_name", "Unknown")
            print(f"  Drafting replies for {name}...")
            replies, rec = draft_replies_for_comment(comment, post_topic)
            comment["reply_drafts"]    = replies
            comment["recommended_reply"] = rec
            modified = True
            total += 1
            print(f"    → {len(replies)} option(s)")

        if modified:
            _save_json(f, data)

    print(f"\nDrafted replies for {total} comment(s).")


def cmd_draft_dms() -> None:
    """Draft 3-message DM sequences for high-intent leads who have been replied to."""
    existing_dm_ids = {f.stem.replace("_dm_sequence", "") for f in _all_dm_files()}
    total = 0

    for f in _all_comment_files():
        try:
            data = _load_json(f)
        except Exception as exc:
            print(f"  Error reading {f.name}: {exc}", file=sys.stderr)
            continue

        post_topic = data.get("post_topic", "")
        post_id    = data.get("post_id", "")
        modified   = False

        for comment in data.get("comments", []):
            qual = comment.get("qualification")
            if not qual or qual.get("intent") != "high":
                continue
            if not comment.get("replied"):
                continue

            commenter_id = comment.get("commenter_id", "")
            safe_id      = commenter_id.replace("urn:li:person:", "").replace(":", "_")[:20]
            if safe_id in existing_dm_ids:
                continue

            name = comment.get("commenter_name", "Unknown")
            print(f"  Drafting DM sequence for {name}...")
            messages = draft_dm_sequence(comment, post_topic, qual)
            if not messages:
                continue

            dm_path = OUTREACH_DIR / f"{safe_id}_dm_sequence.json"
            _save_json(dm_path, {
                "commenter_id":   commenter_id,
                "commenter_name": name,
                "linkedin_url":   comment.get("commenter_linkedin_url", ""),
                "post_id":        post_id,
                "post_topic":     post_topic,
                "qualification":  qual,
                "dm_sequence":    messages,
                "created_at":     datetime.now(timezone.utc).isoformat(),
                "status":         "queued",
            })
            comment["dm_sequence_drafted"] = True
            existing_dm_ids.add(safe_id)
            modified = True
            total += 1
            print(f"    → saved to {dm_path.name}")

        if modified:
            _save_json(f, data)

    print(f"\nDrafted DM sequences for {total} lead(s).")


def cmd_export() -> None:
    """Export/upsert leads.csv from all outreach_history data.

    Demo-tracking columns (demo_requested, demo_date, demo_outcome, deal_value)
    are initialised empty for new leads and NEVER overwritten on upsert — fill
    them manually in Excel/Sheets and they will survive every subsequent run.
    """
    FIELDNAMES = [
        "name", "linkedin_url", "company", "title_guess", "intent",
        "post_topic", "comment_text", "reply_status", "dm_status",
        "first_seen", "last_touchpoint",
        # Demo-tracking — fill manually; never auto-overwritten
        "demo_requested", "demo_date", "demo_outcome", "deal_value",
        "notes",
    ]
    DEMO_FIELDS = {"demo_requested", "demo_date", "demo_outcome", "deal_value", "notes"}

    # Load existing leads keyed by linkedin_url (or name fallback)
    existing: dict[str, dict] = {}
    if LEADS_CSV.exists():
        try:
            with LEADS_CSV.open(encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    key = row.get("linkedin_url") or row.get("name", "")
                    if key:
                        existing[key] = row
        except Exception as exc:
            print(f"  WARNING: could not read existing leads.csv: {exc}", file=sys.stderr)

    for f in _all_comment_files():
        try:
            data = _load_json(f)
        except Exception:
            continue

        post_topic = data.get("post_topic", "")
        for comment in data.get("comments", []):
            qual = comment.get("qualification")
            if not qual or qual.get("intent", "low") == "low":
                continue

            url  = comment.get("commenter_linkedin_url", "")
            name = comment.get("commenter_name", "")
            key  = url or name
            if not key:
                continue

            reply_status = (
                "replied"  if comment.get("replied")      else
                "drafted"  if comment.get("reply_drafts") else
                "none"
            )
            dm_status       = "queued" if comment.get("dm_sequence_drafted") else "none"
            first_seen      = (comment.get("comment_date") or data.get("fetched_at", ""))[:10]
            last_touchpoint = (comment.get("replied_at") or first_seen)[:10]

            if key in existing:
                # Update pipeline state; preserve all manually-filled demo/notes fields
                existing[key]["last_touchpoint"] = last_touchpoint
                existing[key]["reply_status"]    = reply_status
                existing[key]["dm_status"]        = dm_status
            else:
                existing[key] = {
                    "name":            name,
                    "linkedin_url":    url,
                    "company":         qual.get("company_guess", ""),
                    "title_guess":     qual.get("title_guess", ""),
                    "intent":          qual.get("intent", ""),
                    "post_topic":      post_topic,
                    "comment_text":    comment.get("comment_text", "")[:200],
                    "reply_status":    reply_status,
                    "dm_status":       dm_status,
                    "first_seen":      first_seen,
                    "last_touchpoint": last_touchpoint,
                    # Demo tracking — empty until you fill them in
                    "demo_requested":  "",
                    "demo_date":       "",
                    "demo_outcome":    "",
                    "deal_value":      "",
                    "notes":           "",
                }

    with LEADS_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing.values())

    print(f"Exported {len(existing)} lead(s) to {LEADS_CSV}")


def cmd_run_all() -> None:
    """Run all pipeline steps in sequence (DM drafting skipped if no replied comments)."""
    steps = [
        ("Fetch comments",   cmd_fetch),
        ("Qualify leads",    cmd_qualify),
        ("Draft replies",    cmd_draft_replies),
        ("Export leads.csv", cmd_export),
    ]
    for label, fn in steps:
        print(f"\n=== {label} ===")
        try:
            fn()
        except Exception as exc:
            print(f"  ERROR in {label}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Lead detection and outreach pipeline for SmartPro LinkedIn automation."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch",         help="Fetch all new comments from LinkedIn")
    sub.add_parser("qualify",       help="Run Claude qualification on unscored comments")
    sub.add_parser("draft-replies", help="Draft replies for qualified leads")
    sub.add_parser("draft-dms",     help="Draft DM sequences for high-intent replied leads")
    sub.add_parser("export",        help="Export leads.csv")
    sub.add_parser("run-all",       help="Run all pipeline steps in sequence")

    args = parser.parse_args()

    dispatch = {
        "fetch":         cmd_fetch,
        "qualify":       cmd_qualify,
        "draft-replies": cmd_draft_replies,
        "draft-dms":     cmd_draft_dms,
        "export":        cmd_export,
        "run-all":       cmd_run_all,
    }
    dispatch[args.cmd]()


if __name__ == "__main__":
    _cli()
