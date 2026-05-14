"""Send approved newsletter issues via Resend.

Setup (one-time):
  1. Sign up at https://resend.com (free tier: 3,000 emails/month).
  2. Verify a sending domain — e.g. thesmartpro.io.
     If you don't own DNS yet, you can send from the default `onboarding@resend.dev`
     for testing only; production sends should use your own domain.
  3. Create an API key in the Resend dashboard.
  4. Set environment variables before running:
        RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxx
        RESEND_FROM="SmartPro <newsletter@thesmartpro.io>"
        RESEND_AUDIENCE_ID=...              # optional, for broadcasts
        NEWSLETTER_TEST_TO=you@yourdomain   # for --test sends

Run:
    python newsletter_publisher.py --issue 1 --test
        Sends Issue #1 to NEWSLETTER_TEST_TO only.

    python newsletter_publisher.py --issue 1 --broadcast
        Sends Issue #1 to the full Resend audience.
        Requires RESEND_AUDIENCE_ID.

    python newsletter_publisher.py --issue 1 --to alice@example.com
        Sends Issue #1 to a single explicit recipient.

The script never broadcasts without an explicit --broadcast flag.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from newsletter import (
    NEWSLETTER_DIR,
    render_html,
    render_text,
)

RESEND_API_BASE = "https://api.resend.com"


def _load_issue(issue_num: int) -> dict:
    matches = sorted(NEWSLETTER_DIR.glob(f"issue_{issue_num:03d}_*.json"))
    if not matches:
        raise SystemExit(f"No issue file found for issue #{issue_num} in {NEWSLETTER_DIR}")
    return json.loads(matches[-1].read_text(encoding="utf-8"))


def _save_issue(issue: dict) -> None:
    n = issue["_meta"]["issue_number"]
    d = issue["_meta"]["date"]
    (NEWSLETTER_DIR / f"issue_{n:03d}_{d}.json").write_text(
        json.dumps(issue, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _post_json(url: str, payload: dict, api_key: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Resend API error {e.code}: {detail}") from e


def send_test(issue: dict, recipient: str) -> dict:
    """Send a single test email."""
    api_key = os.environ.get("RESEND_API_KEY")
    sender  = os.environ.get("RESEND_FROM", "SmartPro <onboarding@resend.dev>")
    if not api_key:
        raise SystemExit("RESEND_API_KEY is not set. See setup notes at the top of this file.")

    payload = {
        "from":    sender,
        "to":      [recipient],
        "subject": issue["subject"],
        "html":    render_html(issue),
        "text":    render_text(issue),
        "headers": {"X-Issue-Number": str(issue["_meta"]["issue_number"])},
        "tags":    [
            {"name": "issue", "value": f"{issue['_meta']['issue_number']:03d}"},
            {"name": "kind",  "value": "test"},
        ],
    }
    result = _post_json(f"{RESEND_API_BASE}/emails", payload, api_key)
    print(f"Test sent to {recipient} — Resend id={result.get('id')}")
    return result


def send_broadcast(issue: dict) -> dict:
    """Send to the configured Resend audience."""
    api_key     = os.environ.get("RESEND_API_KEY")
    sender      = os.environ.get("RESEND_FROM", "")
    audience_id = os.environ.get("RESEND_AUDIENCE_ID", "")
    if not (api_key and sender and audience_id):
        raise SystemExit(
            "Broadcast requires RESEND_API_KEY, RESEND_FROM, and RESEND_AUDIENCE_ID."
        )

    payload = {
        "audience_id": audience_id,
        "from":        sender,
        "subject":     issue["subject"],
        "html":        render_html(issue),
        "name":        f"SmartPro Weekly #{issue['_meta']['issue_number']:03d}",
        "preview_text": issue.get("preview", ""),
    }
    result = _post_json(f"{RESEND_API_BASE}/broadcasts", payload, api_key)
    broadcast_id = result.get("id")
    print(f"Broadcast queued — id={broadcast_id}")

    # Schedule immediate send
    if broadcast_id:
        _post_json(
            f"{RESEND_API_BASE}/broadcasts/{broadcast_id}/send",
            {"scheduled_at": "in 1 minute"},
            api_key,
        )
        print("Broadcast send scheduled (in 1 minute).")
    return result


def mark_sent(issue: dict, mode: str, recipient: str = "") -> None:
    issue["_meta"]["status"]       = "sent" if mode == "broadcast" else issue["_meta"].get("status", "draft")
    issue["_meta"]["last_send"]    = {
        "mode":      mode,
        "to":        recipient,
        "at":        datetime.now(timezone.utc).isoformat(),
    }
    _save_issue(issue)


def main():
    ap = argparse.ArgumentParser(description="Send a newsletter issue via Resend")
    ap.add_argument("--issue", type=int, required=True, help="Issue number (1, 2, ...)")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--test", action="store_true", help="Send only to NEWSLETTER_TEST_TO")
    group.add_argument("--broadcast", action="store_true", help="Send to RESEND_AUDIENCE_ID")
    group.add_argument("--to", help="Send to a single explicit recipient")
    args = ap.parse_args()

    issue = _load_issue(args.issue)

    if args.test:
        recipient = os.environ.get("NEWSLETTER_TEST_TO")
        if not recipient:
            raise SystemExit("Set NEWSLETTER_TEST_TO=your-email@example.com for --test")
        send_test(issue, recipient)
        mark_sent(issue, "test", recipient)
    elif args.to:
        send_test(issue, args.to)
        mark_sent(issue, "to", args.to)
    elif args.broadcast:
        # Safety prompt — broadcast goes to the whole list.
        confirm = input(f"Broadcast Issue #{args.issue} to the full audience? Type YES: ")
        if confirm.strip() != "YES":
            print("Aborted. No broadcast sent.")
            sys.exit(1)
        send_broadcast(issue)
        mark_sent(issue, "broadcast", "audience")


if __name__ == "__main__":
    main()
