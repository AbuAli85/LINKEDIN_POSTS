"""Engagement assistant: fetch comments, assess risk, draft replies, manage approval queue."""

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests

from atomic_io import write_json

HISTORY_DIR    = Path(__file__).parent / "posts_history"
ENGAGEMENT_DIR = Path(__file__).parent / "engagement_history"
ENGAGEMENT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_RISK_SYSTEM = (
    "You are a professional LinkedIn brand manager performing comment risk assessment. "
    "Respond with valid JSON only — no markdown, no explanation outside the JSON."
)

_RISK_USER = """Assess this LinkedIn comment for reply risk on behalf of Abu Ali's professional brand.

POST TOPIC: {post_topic}
COMMENT: {comment_text}

Risk categories:
- COMPLAINT: Commenter is complaining about you, your company, or a product
- LEGAL: Involves legal threats, contracts, liability, IP, or employment disputes
- MEDICAL: Involves personal health or medical advice requests
- FINANCIAL: Involves personal financial or investment advice requests
- POLITICAL: Involves political parties, elections, or divisive political topics
- RELIGIOUS: Involves religious beliefs or practices
- SENSITIVE_PERSONAL: Involves personal loss, trauma, or sensitive personal details
- SPAM: Clearly promotional, self-promotional, or bot-like
- OFFENSIVE: Offensive, discriminatory, or hostile

Return JSON only:
{{
  "risk_level": "safe",
  "risk_categories": [],
  "reason": "one sentence"
}}

risk_level: "safe" = draft a reply, "review" = draft but flag for extra care, "block" = skip entirely."""

_REPLY_SYSTEM = """You are an elite LinkedIn ghostwriter for Abu Ali's professional personal brand.
Your replies sound like a thoughtful operator — not a brand, not a content creator.
Rules: never open with "Great question!" or "Thanks for sharing!". Never be promotional.
Keep replies concise: 1-3 sentences max. Each option must take a different angle.
Respond with valid JSON only — no markdown."""

_REPLY_USER = """Write 3 different reply options to this LinkedIn comment.

POST FIRST LINE: {post_first_line}
POST PILLAR: {pillar}
COMMENTER: {commenter_name}
COMMENT: {comment_text}

Return JSON only:
{{
  "replies": ["option 1", "option 2", "option 3"],
  "recommended": 0
}}

recommended is the index (0-2) of your strongest pick."""

# ---------------------------------------------------------------------------
# LinkedIn API helpers
# ---------------------------------------------------------------------------

def _headers() -> dict:
    token = (os.environ.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN not set.")
    return {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def _encode(urn: str) -> str:
    import urllib.parse
    return urllib.parse.quote(urn, safe="")


def fetch_post_comments(post_id: str) -> list[dict]:
    """Return raw comment elements from LinkedIn socialActions API."""
    try:
        url = f"https://api.linkedin.com/v2/socialActions/{_encode(post_id)}/comments?count=50"
        resp = requests.get(url, headers=_headers(), timeout=10)
        if resp.status_code != 200:
            print(f"WARNING: comments fetch {resp.status_code} for {post_id[:40]}", file=sys.stderr)
            return []
        return resp.json().get("elements", [])
    except Exception as exc:
        print(f"WARNING: comments fetch failed: {exc}", file=sys.stderr)
        return []


def _post_linkedin_reply(post_id: str, comment_id: str, reply_text: str) -> dict:
    author = (os.environ.get("LINKEDIN_AUTHOR_URN") or "").strip()
    if not author:
        raise RuntimeError("LINKEDIN_AUTHOR_URN not set.")
    url = f"https://api.linkedin.com/v2/socialActions/{_encode(post_id)}/comments"
    payload = {
        "actor": author,
        "message": {"text": reply_text},
        "parentComment": comment_id,
    }
    resp = requests.post(url, headers=_headers(), json=payload, timeout=15)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"LinkedIn reply API error {resp.status_code}: {resp.text[:300]}")
    return {"reply_id": resp.headers.get("x-restli-id") or resp.json().get("id", "")}


# ---------------------------------------------------------------------------
# AI helpers
# ---------------------------------------------------------------------------

def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def assess_risk(comment_text: str, post_topic: str) -> dict:
    try:
        resp = _client().messages.create(
            model=os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-4-6",
            max_tokens=300,
            system=_RISK_SYSTEM,
            messages=[{"role": "user", "content": _RISK_USER.format(
                post_topic=post_topic, comment_text=comment_text,
            )}],
        )
        return json.loads(resp.content[0].text.strip())
    except Exception as exc:
        print(f"WARNING: risk assessment failed: {exc}", file=sys.stderr)
        return {"risk_level": "review", "risk_categories": [], "reason": "Assessment failed — review manually."}


def draft_replies(comment_text: str, post_first_line: str, pillar: str, commenter_name: str) -> dict:
    try:
        resp = _client().messages.create(
            model=os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-4-6",
            max_tokens=600,
            system=_REPLY_SYSTEM,
            messages=[{"role": "user", "content": _REPLY_USER.format(
                post_first_line=post_first_line,
                pillar=pillar,
                commenter_name=commenter_name,
                comment_text=comment_text,
            )}],
        )
        return json.loads(resp.content[0].text.strip())
    except Exception as exc:
        print(f"WARNING: reply drafting failed: {exc}", file=sys.stderr)
        return {"replies": [], "recommended": 0}


# ---------------------------------------------------------------------------
# Disk helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save(path: Path, data: dict) -> None:
    write_json(path, data)


def _existing_comment_ids() -> set[str]:
    ids: set[str] = set()
    for f in ENGAGEMENT_DIR.glob("*.json"):
        try:
            if cid := _load(f).get("comment_id"):
                ids.add(cid)
        except Exception:
            continue
    return ids


def _engagement_path(comment_id: str) -> Path:
    short = hashlib.md5(comment_id.encode()).hexdigest()[:10]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return ENGAGEMENT_DIR / f"{ts}_{short}.json"


# ---------------------------------------------------------------------------
# Public commands
# ---------------------------------------------------------------------------

def fetch_all_comments() -> int:
    """Fetch new comments for all published posts, assess risk, draft replies."""
    published = []
    for f in sorted(HISTORY_DIR.glob("*.json")):
        try:
            p = _load(f)
            if p.get("published") and p.get("post_id"):
                published.append((f, p))
        except Exception:
            continue

    if not published:
        print("No published posts with post_id found.")
        return 0

    existing_ids = _existing_comment_ids()
    new_count = 0

    for post_path, post in published:
        post_id = post["post_id"]
        print(f"Fetching comments: {post_path.name} ({post_id[:50]})...")
        comments = fetch_post_comments(post_id)
        print(f"  {len(comments)} comment(s) on this post.")

        for c in comments:
            cid = c.get("id", "")
            if not cid or cid in existing_ids:
                continue

            comment_text = (c.get("message") or {}).get("text", "").strip()
            if not comment_text:
                continue

            commenter_urn  = c.get("actor", "")
            commenter_name = commenter_urn.split(":")[-1]
            created_ms     = (c.get("created") or {}).get("time", 0)
            comment_at     = (
                datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).isoformat()
                if created_ms else ""
            )

            print(f"  New comment — assessing risk...")
            risk = assess_risk(comment_text, post.get("topic", ""))
            risk_level = risk.get("risk_level", "review")
            print(f"    Risk: {risk_level} — {risk.get('reason', '')[:80]}")

            engagement: dict = {
                "post_id":        post_id,
                "post_file":      str(post_path),
                "post_pillar":    post.get("pillar", ""),
                "post_topic":     post.get("topic", ""),
                "post_first_line": post.get("post", "").split("\n", 1)[0][:120],
                "comment_id":      cid,
                "commenter_urn":   commenter_urn,
                "commenter_name":  commenter_name,
                "comment_text":    comment_text,
                "comment_at":      comment_at,
                "fetched_at":      datetime.now(timezone.utc).isoformat(),
                "risk_level":      risk_level,
                "risk_categories": risk.get("risk_categories", []),
                "risk_reason":     risk.get("reason", ""),
                "reply_drafts":    [],
                "recommended_reply": 0,
                "selected_reply":  None,
                "status":          "blocked" if risk_level == "block" else "pending",
                "approved_at":     None,
                "posted_at":       None,
                "posted_reply":    None,
            }

            if risk_level != "block":
                print("    Drafting reply options...")
                reply_data = draft_replies(
                    comment_text,
                    engagement["post_first_line"],
                    engagement["post_pillar"],
                    commenter_name,
                )
                engagement["reply_drafts"]    = reply_data.get("replies", [])
                engagement["recommended_reply"] = reply_data.get("recommended", 0)

            out = _engagement_path(cid)
            _save(out, engagement)
            existing_ids.add(cid)
            new_count += 1
            print(f"    Saved → {out.name}")

    print(f"\nDone. {new_count} new comment(s) processed.")
    return new_count


def approve_reply(path: Path, reply_index: int) -> None:
    """Mark a reply as selected and approved for posting."""
    data = _load(path)
    replies = data.get("reply_drafts", [])
    if not replies:
        raise SystemExit("No reply drafts in this file.")
    if not (0 <= reply_index < len(replies)):
        raise SystemExit(f"reply index must be 0–{len(replies) - 1}.")

    data.update({
        "selected_reply": reply_index,
        "status":         "approved",
        "approved_at":    datetime.now(timezone.utc).isoformat(),
    })
    _save(path, data)
    print(f"Approved reply [{reply_index}] for {path.name}:")
    print(f'  "{replies[reply_index]}"')
    print("Run `python engagement.py post-reply <path>` to publish it.")


def post_reply_cmd(path: Path) -> None:
    """Post the approved reply to LinkedIn."""
    data = _load(path)
    if data.get("status") != "approved":
        raise SystemExit("Reply not approved — run `approve` first.")
    if data.get("posted_at"):
        print(f"Already posted on {data['posted_at']}.")
        return

    idx        = data.get("selected_reply", 0)
    reply_text = data["reply_drafts"][idx]
    print(f"Posting reply: \"{reply_text[:80]}\"...")

    result = _post_linkedin_reply(data["post_id"], data["comment_id"], reply_text)
    data.update({
        "status":       "posted",
        "posted_at":    datetime.now(timezone.utc).isoformat(),
        "posted_reply": reply_text,
        "reply_id":     result.get("reply_id", ""),
    })
    _save(path, data)
    print(f"Posted! Reply ID: {result.get('reply_id', '(unknown)')}")


def list_pending() -> None:
    """Print all pending and approved items to stdout."""
    items = []
    for f in sorted(ENGAGEMENT_DIR.glob("*.json"), reverse=True):
        try:
            d = _load(f)
            if d.get("status") in ("pending", "approved"):
                items.append((f, d))
        except Exception:
            continue

    if not items:
        print("No pending replies.")
        return

    for path, d in items:
        rec = d.get("recommended_reply", 0)
        print(f"\n[{d.get('status','?').upper()}] [{d.get('risk_level','?')}] {path.name}")
        print(f"  Post topic : {d.get('post_topic','?')}")
        print(f"  Comment    : {d.get('comment_text','')[:100]}")
        for i, r in enumerate(d.get("reply_drafts", [])):
            marker = "★ " if i == rec else "  "
            print(f"  {marker}[{i}] {r[:90]}")


def get_repeat_engagers() -> list[dict]:
    """Return commenters who appeared on 2+ different posts (outreach leads)."""
    commenter_posts: dict[str, set] = defaultdict(set)
    commenter_info: dict[str, dict] = {}

    for f in ENGAGEMENT_DIR.glob("*.json"):
        try:
            d = _load(f)
            urn = d.get("commenter_urn", "")
            if not urn:
                continue
            commenter_posts[urn].add(d.get("post_id", ""))
            if urn not in commenter_info:
                commenter_info[urn] = {
                    "commenter_urn":  urn,
                    "commenter_name": d.get("commenter_name", urn.split(":")[-1]),
                    "comments":       [],
                }
            commenter_info[urn]["comments"].append({
                "post_topic":   d.get("post_topic", ""),
                "comment_text": d.get("comment_text", "")[:120],
                "comment_at":   d.get("comment_at", ""),
            })
        except Exception:
            continue

    leads = []
    for urn, posts in commenter_posts.items():
        if len(posts) >= 2:
            info = commenter_info[urn].copy()
            info["post_count"] = len(posts)
            leads.append(info)

    return sorted(leads, key=lambda x: -x["post_count"])


def load_all_engagement() -> list[dict]:
    """Return all engagement records sorted newest-first."""
    items = []
    for f in sorted(ENGAGEMENT_DIR.glob("*.json"), reverse=True):
        try:
            items.append(_load(f))
        except Exception:
            continue
    return items


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn engagement assistant.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch-comments", help="Fetch comments, assess risk, draft replies.")
    sub.add_parser("list",           help="List pending and approved reply items.")

    p_ap = sub.add_parser("approve", help="Approve a reply draft for posting.")
    p_ap.add_argument("path")
    p_ap.add_argument("--reply", type=int, default=0, help="Reply index (0, 1, or 2).")

    p_pr = sub.add_parser("post-reply", help="Post the approved reply to LinkedIn.")
    p_pr.add_argument("path")

    args = parser.parse_args()
    dispatch = {
        "fetch-comments": lambda: fetch_all_comments(),
        "list":           lambda: list_pending(),
        "approve":        lambda: approve_reply(Path(args.path), args.reply),
        "post-reply":     lambda: post_reply_cmd(Path(args.path)),
    }
    dispatch[args.cmd]()


if __name__ == "__main__":
    _cli()
