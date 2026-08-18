"""Fire any due campaign reminder to the owner, once, through the notifier.

A reminder in a markdown file pages nobody. This reads campaign_reminders.json
on a daily cron and emails anything whose `due` date has arrived, then stamps
`fired_at` so it cannot send twice. Best-effort like every other notification
path: a delivery failure is logged and never fails the workflow.

    python campaign_reminder.py            # fire anything due
    python campaign_reminder.py --dry-run  # show what would fire
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

from atomic_io import load_json, write_json

REMINDERS_FILE = Path(__file__).parent / "campaign_reminders.json"


def due_reminders(reminders: list[dict], today: date) -> list[dict]:
    """Reminders whose due date has arrived and which have not fired yet."""
    out = []
    for r in reminders:
        if r.get("fired_at"):
            continue
        try:
            due = date.fromisoformat((r.get("due") or "").strip())
        except ValueError:
            continue
        if due <= today:
            out.append(r)
    return out


def fire(reminder: dict) -> None:
    """Send one reminder through the shared notifier fan-out."""
    from notifier import _dispatch, _enabled

    if not _enabled():
        print(f"Reminder {reminder['id']} suppressed by NOTIFY_ON_DRAFT.")
        return

    title = reminder.get("title", reminder.get("id", "Campaign reminder"))
    body = reminder.get("body", "")
    context = {
        "event":    "campaign_reminder",
        "id":       reminder.get("id", ""),
        "campaign": reminder.get("campaign", ""),
        "due":      reminder.get("due", ""),
        "title":    title,
        "body":     body,
    }
    _dispatch(
        context,
        subject=f"Due today — {title}",
        html_body=(
            '<div style="font-family:Arial,sans-serif;line-height:1.6;color:#111827;max-width:640px">'
            f"<h2 style='margin-bottom:4px'>{title}</h2>"
            f"<p style='color:#6b7280;font-size:13px;margin-top:0'>Due {reminder.get('due','')}"
            f" &middot; {reminder.get('campaign','')}</p>"
            f"<pre style='white-space:pre-wrap;font-family:inherit;font-size:14px'>{body}</pre>"
            "</div>"
        ),
        text_body=f"{title}\nDue {reminder.get('due','')} · {reminder.get('campaign','')}\n\n{body}",
        label="Campaign reminder",
    )


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    reminders = load_json(REMINDERS_FILE, []) or []
    today = date.today()
    due = due_reminders(reminders, today)

    if not due:
        print(f"No campaign reminders due on {today.isoformat()}.")
        return 0

    for r in due:
        print(f"Due: {r.get('id')} ({r.get('due')}) — {r.get('title')}")
        if dry:
            continue
        fire(r)
        r["fired_at"] = datetime.now(timezone.utc).isoformat()

    if dry:
        print(f"\nDRY RUN — {len(due)} reminder(s) would fire; nothing written.")
        return 0

    write_json(REMINDERS_FILE, reminders)
    print(f"\nFired {len(due)} reminder(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
