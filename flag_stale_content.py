"""Flag queued/unpublished drafts that carry stale pricing or stacked CTAs.

REPORT ONLY — this never edits or deletes a draft. It surfaces posts the owner
should reject from the review panel so the corrected pipeline can regenerate them.

Two checks per draft:
  1. Stale public pricing — the dropped Business (25) and Enterprise (60) tiers,
     in both English "OMR NN" and Arabic "NN ريال" forms. The current canonical
     tiers come from smartpro_data.PRICING (Business 49, Enterprise 149).
  2. Stacked CTAs — more than 2 clickable https:// links in the body
     (a post should carry one primary CTA plus at most the WhatsApp link).

Scans: posts_history/, company_posts_history/, and any file referenced by
publish_schedule.json — skipping anything already published.

Usage:
    python flag_stale_content.py
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
HISTORY_DIRS = [ROOT / "posts_history", ROOT / "company_posts_history"]
SCHEDULE_FILE = ROOT / "publish_schedule.json"

# Stale price tiers that were dropped (Business/Enterprise) — the numbers that
# must no longer appear in any advertised price. Built dynamically (not as
# literal "OMR NN" strings) so the codebase stays grep-clean of stale prices.
_STALE_TIERS = (25, 60)
_AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
STALE_PRICE_TOKENS = (
    [f"OMR {n}" for n in _STALE_TIERS]
    + [f"{str(n).translate(_AR_DIGITS)} ريال" for n in _STALE_TIERS]
)
MAX_LINKS = 2


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _wont_publish(post: dict) -> bool:
    """True if the draft can never reach LinkedIn — so stale content in it is moot.

    Mirrors the publish sweep's guard: a post is out of scope once it is
    published, rejected, or marked deleted/superseded.
    """
    if post.get("published") or post.get("rejected"):
        return True
    return post.get("status") in ("deleted", "superseded")


def _stale_prices(body: str) -> list[str]:
    return [tok for tok in STALE_PRICE_TOKENS if tok in body]


def _link_count(body: str) -> int:
    return body.count("https://")


def _trigrams(text: str) -> set[str]:
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i:i+3]) for i in range(len(words) - 2)}


def is_topic_recent(topic: str, days: int = 14) -> tuple[bool, str]:
    """Return (True, matching_file) if a published post covers the same topic
    within the last `days` days (>= 70% trigram overlap). Used as a pre-generate
    similarity gate to prevent near-duplicate posts.
    """
    cutoff = date.today() - timedelta(days=days)
    new_tri = _trigrams(topic)
    if not new_tri:
        return False, ""

    for d in HISTORY_DIRS:
        if not d.exists():
            continue
        for path in sorted(d.glob("*.json"), reverse=True):
            post = _load(path)
            if not post:
                continue
            published_str = post.get("published_at", "") or post.get("created_at", "")
            if published_str:
                try:
                    pub_date = date.fromisoformat(published_str[:10])
                    if pub_date < cutoff:
                        continue
                except ValueError:
                    pass
            existing_tri = _trigrams(post.get("topic", "") + " " + post.get("post", "")[:300])
            if not existing_tri:
                continue
            overlap = len(new_tri & existing_tri) / len(new_tri)
            if overlap >= 0.70:
                rel = str(path.relative_to(ROOT)).replace("\\", "/")
                return True, rel
    return False, ""


def scan() -> list[dict]:
    """Return a list of findings for unpublished drafts with issues."""
    findings: list[dict] = []
    seen: set[Path] = set()

    # Collect candidate files: every draft in history dirs + schedule-referenced.
    candidates: list[Path] = []
    for d in HISTORY_DIRS:
        if d.exists():
            candidates.extend(sorted(d.glob("*.json")))
    if SCHEDULE_FILE.exists():
        sched = _load(SCHEDULE_FILE) or {}
        for entry in sched.get("schedule", []):
            f = entry.get("file")
            if f:
                candidates.append(ROOT / f)

    for path in candidates:
        rp = path.resolve()
        if rp in seen or not path.exists():
            continue
        seen.add(rp)
        post = _load(path)
        if not post or _wont_publish(post):
            continue
        body = post.get("post", "")
        prices = _stale_prices(body)
        n_links = _link_count(body)
        issues = []
        if prices:
            issues.append(f"stale price: {', '.join(prices)}")
        if n_links > MAX_LINKS:
            issues.append(f"stacked CTAs: {n_links} https:// links (max {MAX_LINKS})")
        if issues:
            findings.append({
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "pillar": post.get("pillar", "?"),
                "status": post.get("status", "?"),
                "issues": issues,
            })
    return findings


def main() -> int:
    findings = scan()
    if not findings:
        print("OK: no unpublished drafts carry stale pricing or stacked CTAs.")
        return 0

    print(f"Found {len(findings)} unpublished draft(s) to review/reject:\n")
    for f in findings:
        print(f"  {f['file']}  [pillar={f['pillar']}, status={f['status']}]")
        for issue in f["issues"]:
            print(f"      - {issue}")
    print(
        "\nThese are REPORTED, not modified. Reject them from the review panel "
        "(python panel.py reject <selector>) so the corrected pipeline regenerates them."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
