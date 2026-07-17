"""Lead detection and outreach pipeline for SmartPro LinkedIn automation.

Commands:
  python outreach.py fetch            # fetch all new comments from LinkedIn
  python outreach.py qualify          # run Claude qualification on unscored comments
  python outreach.py enrich           # enrich qualified leads via Bright Data + Apollo
  python outreach.py draft-replies    # draft replies for qualified leads
  python outreach.py draft-dms        # draft DM sequences for high-intent replied leads
  python outreach.py export           # export leads.csv
  python outreach.py send-sequences   # send due sequence steps to all tracker leads
  python outreach.py run-all          # run all steps in sequence (incl. enrich)
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import anthropic
import requests

HISTORY_DIR     = Path(__file__).parent / "posts_history"
OUTREACH_DIR    = Path(__file__).parent / "outreach_history"
LEADS_CSV       = Path(__file__).parent / "leads.csv"
TRACKER_FILE    = Path(__file__).parent / "outreach_tracker.json"
TEMPLATES_FILE  = Path(__file__).parent / "sequence_templates.json"

OUTREACH_DIR.mkdir(exist_ok=True)

CLAUDE_MODEL     = "claude-sonnet-4-6"
LI_BASE          = "https://api.linkedin.com/v2"
MAX_RETRIES      = 3
RETRY_BASE_DELAY = 60  # seconds


# ---------------------------------------------------------------------------
# LinkedIn API helpers
# ---------------------------------------------------------------------------

def _li_headers() -> dict:
    """LinkedIn auth headers — prefers the dedicated read token if present.

    The Community Management API can't co-exist with Share on LinkedIn on the same app
    (LinkedIn policy), so reads use a separate app + token. We prefer LINKEDIN_READ_TOKEN
    when set, falling back to LINKEDIN_ACCESS_TOKEN so single-app setups still work.
    """
    token = (
        os.environ.get("LINKEDIN_READ_TOKEN")
        or os.environ.get("LINKEDIN_ACCESS_TOKEN")
        or ""
    ).strip()
    if not token:
        raise RuntimeError(
            "Neither LINKEDIN_READ_TOKEN nor LINKEDIN_ACCESS_TOKEN is set. "
            "See LINKEDIN_SETUP.md."
        )
    return {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def _encode(urn: str) -> str:
    return urllib.parse.quote(urn, safe="")


def _li_get(url: str) -> dict | None:
    """GET with exponential backoff on 429/5xx. Returns None on 401/403 (logs and continues)."""
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
            print("  WARNING: LinkedIn token expired (401) — re-run LINKEDIN_SETUP.md OAuth.",
                  file=sys.stderr)
            return None
        if resp.status_code == 403:
            # Most common cause: token is missing `r_member_social` scope, which is
            # gated behind the Community Management API product approval. See
            # LINKEDIN_SETUP.md — without this scope, /v2/socialActions/.../comments
            # returns 403 on every call and outreach silently produces zero leads.
            print(
                "  WARNING: LinkedIn returned 403 — token is missing `r_member_social` scope.\n"
                "  Apply for the Community Management API product in the LinkedIn Developer\n"
                "  Console, then re-OAuth with that scope added. See LINKEDIN_SETUP.md.",
                file=sys.stderr,
            )
            return None
        if resp.status_code == 429 or resp.status_code >= 500:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"  Rate limit/server error ({resp.status_code}), retrying in {delay}s...",
                  file=sys.stderr)
            time.sleep(delay)
            continue
        print(f"  WARNING: LinkedIn API returned {resp.status_code} — skipping. "
              f"Body: {resp.text[:200]}", file=sys.stderr)
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
    return json.loads(path.read_text(encoding="utf-8-sig"))


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

def _preflight_scope_check() -> bool:
    """Verify the token has `r_member_social` before iterating 20 posts.

    Hits a single sample socialActions endpoint. 403 here means the token is missing
    the Community Management API scope — known silent-failure mode. Returns True
    if comment-reading appears to work, False otherwise (with a clear message).
    """
    # Pick the most recent published post to probe with.
    for f in sorted(HISTORY_DIR.glob("*.json"), reverse=True):
        try:
            p = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not p.get("post_id"):
            continue
        url = f"{LI_BASE}/socialActions/{_encode(p['post_id'])}/comments?count=1"
        try:
            resp = requests.get(url, headers=_li_headers(), timeout=15)
        except Exception as exc:
            print(f"  Preflight network error: {exc}", file=sys.stderr)
            return True  # don't block on transient network — let the real loop log it
        if resp.status_code == 200:
            return True
        if resp.status_code == 403:
            print(
                "\n  ⚠ PREFLIGHT FAILED — token cannot read comments (HTTP 403).\n"
                "    Cause: missing `r_member_social` scope (Community Management API).\n"
                "    Fix:   Apply for the product in LinkedIn Developer Console, then\n"
                "           re-OAuth with `r_member_social` in the scope string. See\n"
                "           LINKEDIN_SETUP.md. Until then, outreach.fetch will produce\n"
                "           0 results regardless of how many posts are published.\n",
                file=sys.stderr,
            )
            return False
        if resp.status_code == 401:
            print("\n  ⚠ PREFLIGHT FAILED — LinkedIn token expired (401).\n", file=sys.stderr)
            return False
        # Any other status — let the main loop handle it normally.
        return True
    return True  # no published posts to probe; nothing to do anyway


def cmd_fetch() -> None:
    """Fetch all new comments from all published posts."""
    if not _preflight_scope_check():
        return

    published = []
    for f in sorted(HISTORY_DIR.glob("*.json")):
        try:
            p = json.loads(f.read_text(encoding="utf-8-sig"))
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


def cmd_enrich() -> None:
    """Enrich high/medium-intent qualified leads via Bright Data + Apollo.

    Runs after qualify, before draft-replies. Idempotent — leads.csv dedup by
    linkedin_url means re-running is safe. Silently skips if API keys missing,
    so the rest of the pipeline keeps working.
    """
    if not os.environ.get("BRIGHTDATA_API_KEY") and not os.environ.get("APOLLO_API_KEY"):
        print("  Skipped — neither BRIGHTDATA_API_KEY nor APOLLO_API_KEY set.")
        print("  See ENRICH_LEADS.md for setup. (Pipeline continues.)")
        return

    try:
        from enrich_leads import enrich_one  # local module
    except ImportError as exc:
        print(f"  enrich_leads module unavailable: {exc}", file=sys.stderr)
        return

    enriched = 0
    skipped  = 0
    failed   = 0

    for f in _all_comment_files():
        try:
            data = _load_json(f)
        except Exception:
            continue

        modified = False
        for comment in data.get("comments", []):
            qual = comment.get("qualification") or {}
            if qual.get("intent", "low") not in ("high", "medium"):
                continue
            if comment.get("enriched"):
                skipped += 1
                continue
            li_url = comment.get("commenter_linkedin_url", "").strip()
            if not li_url:
                continue

            name = comment.get("commenter_name", "Unknown")
            print(f"  Enriching: {name} — {li_url}")
            try:
                enrich_one(li_url, dry_run=False)
                comment["enriched"]    = True
                comment["enriched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                enriched += 1
                modified = True
            except Exception as exc:
                print(f"    ERROR: {exc}", file=sys.stderr)
                failed += 1

        if modified:
            _save_json(f, data)

    print(f"\nEnriched {enriched}, skipped {skipped} (already done), failed {failed}.")


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
        ("Fetch comments",    cmd_fetch),
        ("Qualify leads",     cmd_qualify),
        ("Enrich leads",      cmd_enrich),
        ("Draft replies",     cmd_draft_replies),
        ("Export leads.csv",  cmd_export),
        ("Send sequences",    cmd_send_sequences),
    ]
    for label, fn in steps:
        print(f"\n=== {label} ===")
        try:
            fn()
        except Exception as exc:
            print(f"  ERROR in {label}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Manual capture — workaround for missing r_member_social scope
# ---------------------------------------------------------------------------

def cmd_manual_capture(urls: list[str]) -> None:
    """Add leads manually by LinkedIn profile URL — no r_member_social needed.

    Usage:
        python outreach.py manual-capture https://linkedin.com/in/name-here
        python outreach.py manual-capture url1 url2 url3

    Each URL is looked up via the public LinkedIn API (basic profile only).
    Falls back to name extraction from the URL slug if the API is inaccessible.
    Leads are written to outreach_tracker.json and leads.csv via import_leads.py logic.
    """
    import re
    import csv
    from datetime import date

    TRACKER = Path(__file__).parent / "outreach_tracker.json"
    LEADS   = Path(__file__).parent / "leads.csv"
    TODAY   = date.today().isoformat()

    SEG_B = ["investor","investment","fund","venture","capital","vc","angel"]
    SEG_C = ["cto","tech","developer","engineer","saas","digital","software"]

    PAIN_MAP = {
        "sanad":             "Multi-client work permit tracking",
        "pro":               "MOL submissions manual 15+ clients",
        "hr manager":        "WPS payroll file 2+ days every month",
        "hr director":       "Omanisation ratios no real-time data",
        "hr specialist":     "HR and PRO hats too much manual admin",
        "ceo":               "3+ hrs Monday HR admin",
        "cfo":               "Payroll errors employee disputes",
        "managing director": "HR PRO across multiple companies no unified view",
        "owner":             "Single HR person single point of failure",
        "founder":           "Client updates via WhatsApp, clients feel abandoned",
        "investor":          "Oman HR tech market pitch Vision 2040",
        "cto":               "Multi-tenant GCC compliance peer angle",
        "default":           "Manual HR/payroll admin taking too long",
    }

    def slug_to_name(url: str) -> str:
        slug = url.rstrip("/").split("/in/")[-1].split("?")[0]
        parts = re.sub(r"-\w{4,}$", "", slug).replace("-", " ").title()
        return parts

    def detect_segment(title: str) -> str:
        t = title.lower()
        if any(k in t for k in SEG_B): return "B"
        if any(k in t for k in SEG_C): return "C"
        return "A"

    def detect_pain(title: str) -> str:
        t = title.lower()
        for k, v in PAIN_MAP.items():
            if k in t: return v
        return PAIN_MAP["default"]

    def next_id(tracker: list) -> str:
        nums = [int(m.group(1)) for p in tracker
                for m in [re.match(r"OA-(\d+)", p.get("id",""))] if m]
        return f"OA-{(max(nums)+1 if nums else 21):03d}"

    TRACKER = Path(__file__).parent / "outreach_tracker.json"
    LEADS   = Path(__file__).parent / "leads.csv"
    TODAY   = date.today().isoformat()

    tracker = json.loads(TRACKER.read_text(encoding="utf-8-sig")) if TRACKER.exists() else []
    existing_urls = {p.get("linkedin_url","").rstrip("/") for p in tracker}

    csv_urls: set = set()
    if LEADS.exists():
        with open(LEADS, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                u = row.get("linkedin_url","").rstrip("/")
                if u: csv_urls.add(u)

    added = []
    skipped = []

    for raw_url in urls:
        url = raw_url.strip().rstrip("/")
        if not url.startswith("https://www.linkedin.com/in/"):
            if "/in/" in url:
                url = "https://www.linkedin.com" + url[url.index("/in/"):]
            else:
                print(f"  WARNING: Skipping (not a /in/ profile URL): {url}")
                continue

        if url in existing_urls or url in csv_urls:
            print(f"  Duplicate, skipping: {url}")
            skipped.append(url)
            continue

        name    = slug_to_name(url)
        title   = "HR Manager"
        company = "Unknown Company"
        city    = "Muscat"

        seg    = detect_segment(title)
        pain   = detect_pain(title)
        new_id = next_id(tracker)

        entry = {
            "id": new_id,
            "name": name,
            "linkedin_url": url,
            "company": company,
            "segment": seg,
            "started_at": TODAY,
            "status": "active",
            "current_step": 1,
            "notes": f"Manually captured | Title: {title} | Location: {city} | Pain: {pain}",
            "tags": ["manual-capture", city.lower(), "priority-1"],
            "converted_at": "",
        }
        tracker.append(entry)
        existing_urls.add(url)

        csv_row = {
            "name": name, "linkedin_url": url, "company": company,
            "title_guess": title, "intent": "high" if seg == "A" else "medium",
            "post_topic": "", "comment_text": "", "reply_status": "pending",
            "dm_status": "step_1", "first_seen": TODAY, "last_touchpoint": TODAY,
            "demo_requested": "", "demo_date": "", "demo_outcome": "",
            "deal_value": "", "notes": entry["notes"],
        }
        added.append((entry, csv_row))
        seg_label = {"A": "Buyer (Seg A)", "B": "Investor (Seg B)", "C": "Tech Peer (Seg C)"}[seg]
        print(f"  Added  {new_id}  {name}  |  {seg_label}")
        print(f"         {url}")

    if not added:
        print(f"\n  Nothing added. {len(skipped)} duplicate(s) skipped.")
        return

    TRACKER.write_text(json.dumps(tracker, indent=2, ensure_ascii=False), encoding="utf-8")

    fieldnames = ["name","linkedin_url","company","title_guess","intent","post_topic",
                  "comment_text","reply_status","dm_status","first_seen","last_touchpoint",
                  "demo_requested","demo_date","demo_outcome","deal_value","notes"]
    with open(LEADS, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        for _, row in added:
            w.writerow(row)

    print(f"\nAdded {len(added)} lead(s) to outreach_tracker.json + leads.csv")
    print("  Note: name/title/company guessed from URL slug.")
    print("  Edit outreach_tracker.json to correct details before the sequence fires.")


# ---------------------------------------------------------------------------
# Sequence send — outreach_tracker.json → LinkedIn DMs
# ---------------------------------------------------------------------------

def _load_tracker() -> list[dict]:
    """Load outreach_tracker.json; return [] if missing."""
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text(encoding="utf-8-sig"))
    return []


def _save_tracker(tracker: list[dict]) -> None:
    TRACKER_FILE.write_text(json.dumps(tracker, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_templates() -> dict:
    if not TEMPLATES_FILE.exists():
        raise RuntimeError(
            "sequence_templates.json not found — run from repo root or check path."
        )
    return json.loads(TEMPLATES_FILE.read_text(encoding="utf-8-sig"))


def _render_template(template: str, lead: dict) -> str:
    """Replace {{first_name}} and {{company}} placeholders."""
    first_name = (lead.get("name") or "").split()[0] or "there"
    company    = lead.get("company") or "your company"
    return template.replace("{{first_name}}", first_name).replace("{{company}}", company)



def _is_due(lead: dict, step_data: dict) -> bool:
    """Return True if this lead is due for the given step today or overdue."""
    today      = date.today()
    last_sent  = (lead.get("last_sent_at") or "").strip()
    days_after = int(step_data.get("days_after_prev", 0))

    if not last_sent:
        started_raw = (lead.get("started_at") or today.isoformat()).strip()
        try:
            started = date.fromisoformat(started_raw)
        except ValueError:
            started = today
        return today >= started + timedelta(days=days_after)

    try:
        last_date = date.fromisoformat(last_sent)
    except ValueError:
        return True
    return today >= last_date + timedelta(days=days_after)


def _li_post_json(url: str, payload: dict) -> dict | None:
    """POST JSON to LinkedIn API with exponential backoff. Returns parsed body or None."""
    token = (os.environ.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN is not set.")
    headers = {
        "Authorization":             f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type":              "application/json",
    }
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
        except Exception as exc:
            print(f"  Network error: {exc}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
            continue
        if resp.status_code in (200, 201):
            try:
                return resp.json()
            except Exception:
                return {"status": "ok"}
        if resp.status_code == 401:
            print("  WARNING: LinkedIn token expired (401) — re-run OAuth.", file=sys.stderr)
            return None
        if resp.status_code == 403:
            print(
                f"  WARNING: LinkedIn returned 403 — missing scope or API not approved.\n"
                f"  Body: {resp.text[:300]}",
                file=sys.stderr,
            )
            return None
        if resp.status_code == 429 or resp.status_code >= 500:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"  Rate limit ({resp.status_code}), retrying in {delay}s...", file=sys.stderr)
            time.sleep(delay)
            continue
        print(f"  WARNING: POST {url} -> {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return None
    return None


def _li_resolve_urn(linkedin_url: str) -> str | None:
    """Resolve a LinkedIn profile URL to a person URN (urn:li:person:<id>).

    Requires r_liteprofile or r_basicprofile scope.
    Returns None on failure.
    """
    vanity = linkedin_url.rstrip("/").split("/in/")[-1].split("?")[0]
    url    = f"{LI_BASE}/people/(vanityName:{urllib.parse.quote(vanity)})?projection=(id)"
    data   = _li_get(url)
    if data and data.get("id"):
        return f"urn:li:person:{data['id']}"
    return None


def _li_send_connection(lead: dict, message: str, dry_run: bool = False) -> bool:
    """Send a LinkedIn connection request with personalised note (step 1).

    Returns True on success or in dry-run mode.
    Requires w_member_social scope.
    """
    if dry_run:
        return True
    person_urn = _li_resolve_urn(lead.get("linkedin_url", ""))
    if not person_urn:
        print(
            f"  WARNING: Could not resolve URN for {lead.get('name')} "
            f"({lead.get('linkedin_url')}) — skipping.",
            file=sys.stderr,
        )
        return False
    payload = {
        "invitee": {
            "com.linkedin.relationships.invitation.InviteeProfile": {
                "profileUrn": person_urn
            }
        },
        "message": message[:300],
    }
    return _li_post_json(f"{LI_BASE}/invitations", payload) is not None


def _li_send_message(lead: dict, message: str, dry_run: bool = False) -> bool:
    """Send a LinkedIn DM to an existing connection (steps 2-5).

    Returns True on success or in dry-run mode.
    Requires w_member_messaging scope (Member Data Portability API product).
    """
    if dry_run:
        return True
    person_urn = _li_resolve_urn(lead.get("linkedin_url", ""))
    if not person_urn:
        print(
            f"  WARNING: Could not resolve URN for {lead.get('name')} — skipping.",
            file=sys.stderr,
        )
        return False
    payload = {
        "recipients":  [person_urn],
        "subject":     "",
        "body":        message,
        "messageType": "MEMBER_TO_MEMBER",
    }
    return _li_post_json(f"{LI_BASE}/messages", payload) is not None


def cmd_send_sequences() -> int:
    """Send due outreach sequence steps to all active leads in outreach_tracker.json.

    For each active lead:
      1. Checks whether current_step is due based on last_sent_at + per-step interval.
      2. Renders the template ({{first_name}}, {{company}} substitution).
      3. Sends via LinkedIn API:
           step 1    -> connection request  (POST /v2/invitations, w_member_social)
           steps 2-5 -> direct message      (POST /v2/messages, w_member_messaging)
      4. On success: advances current_step and records last_sent_at in tracker.
      5. Saves an audit record to outreach_history/ regardless of outcome.

    Dry-run mode (tracker advances, nothing sent):
        LINKEDIN_DRY_RUN=true python outreach.py send-sequences

    Returns the number of messages successfully sent/simulated.
    """
    dry_run = os.environ.get("LINKEDIN_DRY_RUN", "").lower() in ("1", "true", "yes")
    if dry_run:
        print("  [DRY RUN -- messages will NOT be sent, but tracker WILL advance]")

    daily_limit = int(os.environ.get("OUTREACH_DAILY_LIMIT", "15"))
    print(f"  Daily cap: {daily_limit} messages")

    templates = _load_templates()
    step_map  = {s["step"]: s for s in templates["steps"]}
    max_step  = max(step_map.keys())

    tracker   = _load_tracker()
    today_str = date.today().isoformat()

    sent = skipped = errors = 0

    for lead in tracker:
        if lead.get("status") != "active" or lead.get("converted_at"):
            skipped += 1
            continue

        step_num = int(lead.get("current_step", 1))
        if step_num > max_step:
            if lead.get("status") == "active":
                lead["status"] = "sequence_complete"
            skipped += 1
            continue

        step_data = step_map.get(step_num)
        if not step_data:
            print(f"  WARNING: No template for step {step_num} -- skipping {lead.get('id')}",
                  file=sys.stderr)
            skipped += 1
            continue

        if not _is_due(lead, step_data):
            skipped += 1
            continue

        rendered  = _render_template(step_data["template"], lead)
        lead_id   = lead.get("id", "?")
        name      = lead.get("name", "?")
        step_type = step_data.get("type", "message")

        print(f"  {lead_id}  {name}  ->  Step {step_num} [{step_type}]")
        if dry_run:
            print(f"    Preview: {rendered[:120].replace(chr(10), ' ')}...")

        # Audit record saved regardless of send outcome
        audit_path = OUTREACH_DIR / f"{lead_id}_step{step_num}_{today_str}.json"
        _save_json(audit_path, {
            "lead_id":      lead_id,
            "name":         name,
            "company":      lead.get("company", ""),
            "linkedin_url": lead.get("linkedin_url", ""),
            "step":         step_num,
            "step_type":    step_type,
            "sent_at":      today_str,
            "dry_run":      dry_run,
            "message":      rendered,
        })

        if step_type == "connection_request":
            success = _li_send_connection(lead, rendered, dry_run=dry_run)
        else:
            success = _li_send_message(lead, rendered, dry_run=dry_run)

        if success:
            lead["last_sent_at"] = today_str
            lead["current_step"] = step_num + 1
            if step_num == max_step:
                lead["status"] = "sequence_complete"
            sent += 1
            print(f"    OK {'[DRY RUN] ' if dry_run else ''}Step {step_num} sent")
            if sent >= daily_limit:
                print(f"\n  Daily cap of {daily_limit} reached — stopping. "
                      f"Remaining leads will be picked up on the next run.")
                break
        else:
            errors += 1
            print(f"    FAIL Step {step_num} -- tracker NOT advanced", file=sys.stderr)

    if sent > 0 or dry_run:
        _save_tracker(tracker)

    print(f"\nDone -- {sent} sent, {skipped} not due / skipped, {errors} error(s).")
    return sent


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Lead detection and outreach pipeline for SmartPro LinkedIn automation."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch",           help="Fetch all new comments from LinkedIn")
    sub.add_parser("qualify",         help="Run Claude qualification on unscored comments")
    sub.add_parser("enrich",          help="Enrich qualified leads via Bright Data + Apollo")
    sub.add_parser("draft-replies",   help="Draft replies for qualified leads")
    sub.add_parser("draft-dms",       help="Draft DM sequences for high-intent replied leads")
    sub.add_parser("export",          help="Export leads.csv")
    p_seq = sub.add_parser("send-sequences",
                           help="Send due sequence steps (LINKEDIN_DRY_RUN=true to preview)")
    p_seq.add_argument("--limit", type=int, default=None,
                       help="Max messages to send this run (overrides OUTREACH_DAILY_LIMIT env var, default 15)")
    sub.add_parser("run-all",         help="Run all pipeline steps in sequence")
    p_manual = sub.add_parser("manual-capture",
        help="Add leads by LinkedIn profile URL (no r_member_social needed)")
    p_manual.add_argument("urls", nargs="+", help="One or more LinkedIn profile URLs")

    args = parser.parse_args()

    if args.cmd == "manual-capture":
        cmd_manual_capture(args.urls)
        return

    dispatch = {
        "fetch":          cmd_fetch,
        "qualify":        cmd_qualify,
        "enrich":         cmd_enrich,
        "draft-replies":  cmd_draft_replies,
        "draft-dms":      cmd_draft_dms,
        "export":         cmd_export,
        "run-all":        cmd_run_all,
    }
    if args.cmd == "send-sequences":
        if getattr(args, "limit", None) is not None:
            os.environ["OUTREACH_DAILY_LIMIT"] = str(args.limit)
        cmd_send_sequences()
    else:
        dispatch[args.cmd]()


if __name__ == "__main__":
    _cli()
