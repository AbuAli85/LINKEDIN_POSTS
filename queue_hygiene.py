"""Queue-hygiene guards for the draft-first pipeline.

Two invariants keep the review queue trustworthy so stale drafts can't leak
through weeks after they were written:

  1. Age cap — an unpublished draft older than MAX_AGE_DAYS auto-expires to
     `rejected` (status=deleted), matching the panel's reject semantics. Normal
     drafts are generated ~2 days before their publish day, so 14 days is a wide
     safety margin; anything older is backlog, not a live post.
  2. Empty body can never be approved — `can_approve()` refuses a draft with no
     body, so a zero-character shell can never sit in the queue marked approved.

`expire_stale()` runs at the top of generation and the publish sweep (main.py),
and is exposed via `python queue_hygiene.py` and `panel.py doctor`.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
HISTORY_DIRS = [ROOT / "posts_history", ROOT / "company_posts_history"]
MAX_AGE_DAYS = 14

# A draft in one of these states is already out of the publish path.
_TERMINAL_STATUS = ("deleted", "superseded")
_TS_RE = re.compile(r"(\d{8})_(\d{6})")


def is_empty_body(post: dict) -> bool:
    """True if the draft has no post body (a zero-character shell)."""
    return not (post.get("post") or "").strip()


def can_approve(post: dict) -> tuple[bool, str]:
    """Whether a draft may be approved. Returns (ok, reason_if_not).

    Guard: an empty-body draft can NEVER hold approved=true.
    """
    if post.get("published"):
        return False, "already published"
    if is_empty_body(post):
        return False, "empty body — an empty draft can never be approved"
    return True, ""


def _parse_dt(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def draft_datetime(post: dict, filename: str = "") -> datetime | None:
    """Best-effort generation time: prefer generated_at, fall back to the
    YYYYMMDD_HHMMSS filename prefix (empty shells often lack generated_at)."""
    dt = _parse_dt(post.get("generated_at") or "")
    if dt is None and filename:
        m = _TS_RE.search(os.path.basename(filename))
        if m:
            dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(
                tzinfo=timezone.utc
            )
    return dt


def draft_age_days(post: dict, now: datetime, filename: str = "") -> float | None:
    dt = draft_datetime(post, filename)
    if dt is None:
        return None
    return (now - dt).total_seconds() / 86400.0


def is_terminal(post: dict) -> bool:
    """True if the draft is already published/rejected/deleted/superseded."""
    return bool(
        post.get("published")
        or post.get("rejected")
        or post.get("status") in _TERMINAL_STATUS
    )


def reject_fields(reason: str, now: datetime) -> dict:
    """The exact field set panel.cmd_reject writes — the canonical reject shape."""
    return {
        "status": "deleted",
        "approved": False,
        "approval_required": False,
        "rejected": True,
        "rejected_at": now.isoformat(),
        "rejected_reason": reason,
    }


def expire_stale(
    dirs: list | None = None,
    days: int = MAX_AGE_DAYS,
    now: datetime | None = None,
    write: bool = True,
) -> list[str]:
    """Reject every unpublished draft older than `days`. Returns the paths touched.

    Idempotent — skips anything already published/rejected/deleted/superseded.
    """
    now = now or datetime.now(timezone.utc)
    dirs = dirs if dirs is not None else HISTORY_DIRS
    expired: list[str] = []
    for d in dirs:
        d = Path(d)
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                post = json.loads(f.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            if is_terminal(post):
                continue
            age = draft_age_days(post, now, f.name)
            if age is not None and age > days:
                if write:
                    post.update(
                        reject_fields(
                            f"auto-expired: draft older than {days} days ({age:.0f}d)",
                            now,
                        )
                    )
                    f.write_text(json.dumps(post, indent=2), encoding="utf-8")
                expired.append(str(f))
    return expired


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    expired = expire_stale(write=not dry)
    verb = "would expire" if dry else "expired"
    if not expired:
        print(f"Queue hygiene: no drafts older than {MAX_AGE_DAYS} days.")
    else:
        print(f"Queue hygiene: {verb} {len(expired)} stale draft(s):")
        for p in expired:
            print(f"  - {os.path.relpath(p, ROOT)}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
