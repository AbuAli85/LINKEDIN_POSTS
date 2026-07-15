#!/usr/bin/env python3
"""panel.py — the one friendly control panel for the LinkedIn auto-poster.

Everything an owner does day-to-day, in one command:

    python panel.py            # status overview — what needs you right now
    python panel.py review     # list drafts waiting for review (with previews)
    python panel.py show 1     # read draft #1 in full
    python panel.py approve 1  # approve draft #1 (publishes on its next cron)
    python panel.py publish 1  # publish draft #1 to LinkedIn right now
    python panel.py reject 1   # remove draft #1 from the queue
    python panel.py doctor     # health check — live links + stale-price/CTA scan
    python panel.py help

Drafts can be addressed by their review number (from `review`/`status`) or by
any unique part of their filename, e.g. `python panel.py show pain`.

This panel never changes anything without an explicit verb (approve / publish /
reject). Plain `panel.py` only reads. It reuses main.py's approve/publish logic
so the result is identical to the GitHub Actions workflow.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HISTORY_DIR = ROOT / "posts_history"

# Muscat is UTC+4 (no DST).
MUSCAT = timezone(timedelta(hours=4))
PUBLISH_HOUR_UTC = 6
GENERATE_HOUR_UTC = 5

# ---------------------------------------------------------------------------
# Loading & classification (kept in lockstep with dashboard.py)
# ---------------------------------------------------------------------------


def load_posts() -> list[dict]:
    """Every post JSON, newest first. BOM-tolerant and skips unreadable files."""
    posts: list[dict] = []
    for f in sorted(HISTORY_DIR.glob("*.json"), reverse=True):
        try:
            p = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        p["_filename"] = f.name
        p["_path"] = f
        posts.append(p)
    return posts


def needs_review(post: dict) -> bool:
    """Exactly the dashboard's 'Needs review' predicate (dashboard.py)."""
    status = post.get("status")
    return (
        (status == "draft" or post.get("approval_required"))
        and not post.get("published")
        and not post.get("approved", False)
        and not (post.get("dry_run", False) and not post.get("approval_required", False))
        and status not in ("superseded", "deleted", "approved")
        and not post.get("is_variant", False)
    )


def is_queued(post: dict) -> bool:
    """Approved and waiting for its scheduled publish cron."""
    return (
        (post.get("approved") or post.get("status") == "approved")
        and not post.get("published")
        and post.get("status") not in ("superseded", "deleted")
    )


def is_published(post: dict) -> bool:
    return bool(post.get("published"))


def pending_drafts() -> list[dict]:
    """Review queue, oldest first so the most urgent draft is #1."""
    drafts = [p for p in load_posts() if needs_review(p)]
    drafts.sort(key=lambda p: p["_filename"])  # chronological by timestamp prefix
    return drafts


# ---------------------------------------------------------------------------
# Selection: by review-number or by filename fragment
# ---------------------------------------------------------------------------


def resolve(selector: str, pool: list[dict] | None = None) -> dict:
    """Return one post from `selector` (a 1-based index into the review queue,
    or any unique substring of a filename across all posts)."""
    queue = pending_drafts()
    if selector.isdigit():
        i = int(selector)
        if 1 <= i <= len(queue):
            return queue[i - 1]
        _die(f"No draft #{i} in the review queue (there are {len(queue)}). "
             f"Run `python panel.py review` to see the list.")
    search = pool if pool is not None else load_posts()
    matches = [p for p in search if selector.lower() in p["_filename"].lower()]
    if not matches:
        _die(f"Nothing matches '{selector}'. Use a review number or part of a filename.")
    if len(matches) > 1:
        names = "\n  ".join(p["_filename"] for p in matches[:10])
        _die(f"'{selector}' matches several files — be more specific:\n  {names}")
    return matches[0]


# ---------------------------------------------------------------------------
# Small presentation helpers (plain ASCII — safe in any Windows terminal)
# ---------------------------------------------------------------------------


def _muscat(dt_utc: datetime) -> str:
    return dt_utc.astimezone(MUSCAT).strftime("%a %d %b, %I:%M %p Muscat").replace(" 0", " ")


def _next_cron(hour_utc: int) -> datetime:
    now = datetime.now(timezone.utc)
    dt = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if dt <= now:
        dt += timedelta(days=1)
    return dt


def _chars(post: dict) -> str:
    n = post.get("char_count") or len(post.get("post", ""))
    flag = "  !! OVER 1500" if n > 1500 else ""
    return f"{n} chars{flag}"


def _rule(title: str = "") -> None:
    if title:
        print(f"\n=== {title} " + "=" * max(0, 56 - len(title)))
    else:
        print("=" * 60)


def _die(msg: str) -> None:
    print(f"\n[!] {msg}\n")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_status() -> int:
    posts = load_posts()
    queue = pending_drafts()
    approved = [p for p in posts if is_queued(p)]
    published = [p for p in posts if is_published(p)]

    print()
    _rule("LinkedIn Auto-Poster - control panel")
    print(f"  Today: {datetime.now(MUSCAT).strftime('%A %d %B %Y, %I:%M %p Muscat')}")
    print(f"  Drafts waiting for you : {len(queue)}")
    print(f"  Approved & scheduled   : {len(approved)}")
    print(f"  Published all-time     : {len(published)}")

    if queue:
        _rule("ACTION NEEDED — drafts waiting for review")
        for i, p in enumerate(queue, 1):
            preview = p.get("post", "").replace("\n", " ").strip()[:90]
            print(f"  [{i}] {p.get('pillar','?'):<12} {p.get('language','en')}  "
                  f"-> publish {p.get('publish_day','?')}  ({_chars(p)})")
            print(f"      {preview}...")
        print("\n  Next: `python panel.py show 1` to read, then `approve 1` or `reject 1`.")
    else:
        print("\n  You're all caught up - no drafts need review.")

    if approved:
        _rule("Approved - will auto-publish on schedule")
        for p in approved:
            print(f"  - {p.get('pillar','?'):<12} {p.get('language','en')}  "
                  f"-> {p.get('publish_day','next cron')}   {p['_filename']}")

    _rule("Automation clock (UTC crons)")
    print(f"  Next draft generated : {_muscat(_next_cron(GENERATE_HOUR_UTC))}")
    print(f"  Next auto-publish     : {_muscat(_next_cron(PUBLISH_HOUR_UTC))}")
    print(f"\n  Dashboard: docs/index.html   |   `python panel.py help` for all commands\n")
    return 0


def cmd_review() -> int:
    queue = pending_drafts()
    if not queue:
        print("\n  No drafts waiting for review. You're all caught up.\n")
        return 0
    _rule(f"{len(queue)} draft(s) waiting for review")
    for i, p in enumerate(queue, 1):
        preview = p.get("post", "").replace("\n", " ").strip()[:160]
        print(f"\n  [{i}]  {p.get('pillar','?')} / {p.get('language','en')}  "
              f"-> publish {p.get('publish_day','?')}   ({_chars(p)})")
        print(f"       file: {p['_filename']}")
        print(f"       {preview}...")
    print("\n  Read one in full:  python panel.py show <number>")
    print("  Approve it:        python panel.py approve <number>")
    print("  Remove it:         python panel.py reject <number>\n")
    return 0


def cmd_show(selector: str) -> int:
    p = resolve(selector)
    _rule(f"{p.get('pillar','?')} / {p.get('language','en')}  ({_chars(p)})")
    print(f"  file       : {p['_filename']}")
    print(f"  publish day: {p.get('publish_day','?')}")
    print(f"  topic      : {p.get('topic','-')}")
    if p.get("cta_comment"):
        print(f"  cta comment: {p['cta_comment']}")
    _rule("POST TEXT")
    print(p.get("post", "(empty)"))
    _rule()
    print("  Approve:  python panel.py approve "
          f"{selector}    |    Reject: python panel.py reject {selector}\n")
    return 0


def _call_main(mode: str, path: Path) -> int:
    """Delegate to main.py so approve/publish behave exactly like the workflow."""
    os.environ["PUBLISH_DRAFT_PATH"] = str(path)
    os.environ["POST_MODE"] = mode
    import importlib
    import main as _main
    importlib.reload(_main)  # re-read env on repeat calls within one process
    if mode == "approve_draft":
        return _main.approve_draft_file()
    if mode == "publish_draft":
        return _main.publish_saved_draft()
    _die(f"unknown main mode {mode}")
    return 1


def cmd_approve(selector: str) -> int:
    p = resolve(selector)
    print(f"\n  Approving: {p['_filename']}  ({p.get('pillar','?')} / {p.get('language','en')})")
    rc = _call_main("approve_draft", p["_path"])
    if rc == 0:
        print("  Done. It will publish automatically on its next scheduled cron,")
        print("  or run `python panel.py publish " + selector + "` to post it now.\n")
    return rc


def cmd_publish(selector: str) -> int:
    p = resolve(selector)
    if p.get("published"):
        _die(f"Already published: {p['_filename']}")
    print(f"\n  About to PUBLISH TO LINKEDIN NOW: {p['_filename']}")
    print(f"  {p.get('pillar','?')} / {p.get('language','en')}  ({_chars(p)})")
    confirm = input("  Type 'publish' to confirm: ").strip().lower()
    if confirm != "publish":
        print("  Cancelled — nothing was posted.\n")
        return 1
    return _call_main("publish_draft", p["_path"])


def cmd_reject(selector: str) -> int:
    p = resolve(selector)
    reason = " ".join(sys.argv[3:]).strip() or "rejected via panel"
    post = json.loads(p["_path"].read_text(encoding="utf-8-sig"))
    if post.get("published"):
        _die(f"Already published — cannot reject: {p['_filename']}")
    post.update({
        "status": "deleted",
        "approved": False,
        "approval_required": False,
        "rejected": True,
        "rejected_at": datetime.now(timezone.utc).isoformat(),
        "rejected_reason": reason,
    })
    p["_path"].write_text(json.dumps(post, indent=2), encoding="utf-8")
    print(f"\n  Removed from the queue: {p['_filename']}")
    print(f"  Reason: {reason}\n")
    return 0


def cmd_doctor() -> int:
    """Health check: canonical links live + no stale pricing / stacked CTAs queued."""
    rc = 0
    _rule("Link liveness (canonical URLs)")
    try:
        import check_links
        rc |= check_links.main([])
    except Exception as e:
        print(f"  link check failed to run: {e}")
        rc = 1

    _rule("Stale pricing / stacked CTAs in unpublished drafts")
    try:
        import flag_stale_content
        findings = flag_stale_content.scan()
        if not findings:
            print("  OK: no unpublished drafts carry stale pricing or stacked CTAs.")
        else:
            for f in findings:
                print(f"  {f['file']}  [pillar={f['pillar']}, status={f['status']}]")
                for issue in f["issues"]:
                    print(f"      - {issue}")
            print("\n  Reject these from the panel so the corrected pipeline regenerates them.")
    except Exception as e:
        print(f"  stale-content scan failed to run: {e}")
        rc = 1

    _rule("Queue hygiene (age cap + empty-body approvals)")
    try:
        import queue_hygiene as qh
        stale = qh.expire_stale(write=False)  # preview only — doctor never mutates
        if stale:
            print(f"  {len(stale)} draft(s) older than {qh.MAX_AGE_DAYS} days (auto-expire on next cron):")
            for p in stale:
                print(f"      - {Path(p).name}")
        else:
            print(f"  OK: no drafts older than {qh.MAX_AGE_DAYS} days.")
        bad = []
        for post in load_posts():
            if (post.get("approved") or post.get("status") == "approved") \
               and not post.get("published") and qh.is_empty_body(post):
                bad.append(post["_filename"])
        if bad:
            rc = 1
            print(f"  INVALID: {len(bad)} empty-body draft(s) marked approved:")
            for name in bad:
                print(f"      - {name}")
        else:
            print("  OK: no empty-body draft is approved.")
    except Exception as e:
        print(f"  queue-hygiene check failed to run: {e}")
        rc = 1
    print()
    return rc


def cmd_help() -> int:
    print(__doc__)
    return 0


COMMANDS = {
    "status": cmd_status,
    "": cmd_status,
    "review": cmd_review,
    "list": cmd_review,
    "show": cmd_show,
    "read": cmd_show,
    "approve": cmd_approve,
    "publish": cmd_publish,
    "reject": cmd_reject,
    "remove": cmd_reject,
    "doctor": cmd_doctor,
    "help": cmd_help,
    "-h": cmd_help,
    "--help": cmd_help,
}


def main(argv: list[str]) -> int:
    cmd = (argv[1] if len(argv) > 1 else "").lower()
    fn = COMMANDS.get(cmd)
    if fn is None:
        print(f"Unknown command: {cmd!r}")
        return cmd_help() or 2
    if fn in (cmd_show, cmd_approve, cmd_publish, cmd_reject):
        if len(argv) < 3:
            _die(f"`{cmd}` needs a target, e.g. `python panel.py {cmd} 1`")
        return fn(argv[2])
    return fn()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
