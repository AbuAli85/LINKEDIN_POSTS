"""One-shot queue triage — 2026-07-30 review session.

Run AFTER `git pull`. Approves the picks, rejects the stale/duplicate drafts,
in both the personal and company pipelines. Safe to re-run (idempotent).

    python triage.py            # apply decisions
    python triage.py --dry-run  # show what would change, touch nothing
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DRY = "--dry-run" in sys.argv

APPROVE = [
    # Personal: Wednesday proof slot — story-hook primary wins over data-lead variant
    "posts_history/20260727_070928_proof.json",
    # Personal: sanad_pro (Thursday). Approving queues it for the NEXT Thursday
    # sweep — use `python panel.py publish <n>` instead if you want it out today.
    "posts_history/20260728_055626_sanad_pro.json",
    # Company: newest per pillar
    "company_posts_history/20260730_072304_feature_spotlight.json",  # bilingual platform (Wed)
    "company_posts_history/20260728_072537_product_proof.json",      # 12 months zero WPS (Mon)
    "company_posts_history/20260725_071846_oman_market.json",        # 924 Sanad offices (Fri)
]

REJECT = [
    # Personal: losing variant of the approved proof post
    "posts_history/20260727_070927_proof_v.json",
    # Company: stale drafts and losing halves of primary/variant pairs
    "company_posts_history/20260716_084133_feature_spotlight.json",
    "company_posts_history/20260718_082155_product_proof_v.json",
    "company_posts_history/20260722_072521_feature_spotlight_v.json",
    "company_posts_history/20260723_072347_product_proof_v.json",
    "company_posts_history/20260724_072240_oman_market.json",
    "company_posts_history/20260725_071845_oman_market_v.json",
    "company_posts_history/20260726_072507_product_proof_v.json",
    "company_posts_history/20260726_072508_product_proof.json",
    "company_posts_history/20260727_074525_product_proof_v.json",
    "company_posts_history/20260727_074526_product_proof.json",
    "company_posts_history/20260728_072536_product_proof_v.json",
    "company_posts_history/20260729_072830_feature_spotlight_v.json",
    "company_posts_history/20260729_072831_feature_spotlight.json",
]


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"  SKIP  {path.name} — unreadable ({exc})")
        return None


def _save(path: Path, data: dict) -> None:
    if DRY:
        return
    try:
        from atomic_io import write_json
        write_json(path, data)
    except ImportError:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    approved = rejected = skipped = 0

    print(("DRY RUN — no files will change\n" if DRY else "") + "=== APPROVING ===")
    for rel in APPROVE:
        path = ROOT / rel
        if not path.exists():
            print(f"  SKIP  {rel} — not found (did you git pull?)")
            skipped += 1
            continue
        post = _load(path)
        if post is None:
            skipped += 1
            continue
        if post.get("published"):
            print(f"  SKIP  {rel} — already published")
            skipped += 1
            continue
        if post.get("rejected") or post.get("status") in ("superseded", "deleted"):
            print(f"  SKIP  {rel} — was rejected/removed")
            skipped += 1
            continue
        if not post.get("post"):
            print(f"  SKIP  {rel} — empty post body")
            skipped += 1
            continue
        if post.get("approved"):
            print(f"  OK    {rel} — already approved")
            continue
        post.update({
            "status": "approved",
            "approved": True,
            "approval_required": False,
            "approved_at": now,
            "dry_run": False,
        })
        _save(path, post)
        print(f"  APPROVED  {rel}  (publishes {post.get('publish_day', 'next slot')})")
        approved += 1

    print("\n=== REJECTING ===")
    for rel in REJECT:
        path = ROOT / rel
        if not path.exists():
            print(f"  SKIP  {rel} — not found")
            skipped += 1
            continue
        post = _load(path)
        if post is None:
            skipped += 1
            continue
        if post.get("published"):
            print(f"  SKIP  {rel} — already published, leaving untouched")
            skipped += 1
            continue
        if post.get("rejected") or post.get("status") in ("deleted", "superseded"):
            print(f"  OK    {rel} — already rejected")
            continue
        post.update({
            "status": "deleted",
            "rejected": True,
            "rejected_at": now,
            "approved": False,
            "approval_required": False,
            "rejected_reason": "triage 2026-07-30: stale draft / losing variant of an approved pair",
        })
        _save(path, post)
        print(f"  REJECTED  {rel}")
        rejected += 1

    print(f"\nDone: {approved} approved, {rejected} rejected, {skipped} skipped."
          + (" (dry run — nothing written)" if DRY else ""))
    print("Next: git add -A && git commit -m \"triage: queue cleanup 2026-07-30\" && git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
