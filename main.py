"""Orchestrator: generate LinkedIn drafts and publish only explicit approved drafts."""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from content_strategy import pick_pillar, PILLARS
from generator import generate_post, generate_job_post, generate_hook_variant, save_post
from publisher import LinkedInError, publish_post

load_dotenv()

VALID_MODES = {
    "draft",
    "generate_draft",
    "publish_approved",
    "publish_draft",
    "approve_draft",
    "publish",
    "publish_now",
    "revise_draft",
    "fetch_metrics",
    "fetch_comments",
    "post_reply",
    "announce_jobs",   # process pending job queue from SmartPro Hub
}


def _mode() -> str:
    """Return the requested run mode.

    Defaults to draft generation because scheduled automation should not publish
    directly without an explicit owner action.
    """
    raw = (os.environ.get("POST_MODE") or os.environ.get("ACTION") or "draft").strip().lower()
    if raw not in VALID_MODES:
        raise SystemExit(
            f"Unsupported POST_MODE={raw!r}. Use one of: {', '.join(sorted(VALID_MODES))}."
        )
    if raw == "generate_draft":
        return "draft"
    if raw == "publish":
        return "publish_draft"
    return raw


def main() -> int:
    mode = _mode()
    if mode == "publish_approved":
        return publish_approved_for_today()
    if mode == "publish_draft":
        return publish_saved_draft()
    if mode == "approve_draft":
        return approve_draft_file()
    if mode == "publish_now":
        return generate_and_publish_now()
    if mode == "revise_draft":
        return revise_saved_draft()
    if mode == "announce_jobs":
        return announce_pending_jobs()
    if mode == "fetch_metrics":
        from metrics import fetch_all_published
        fetch_all_published()
        return 0
    if mode == "fetch_comments":
        from engagement import fetch_all_comments
        fetch_all_comments()
        return 0
    if mode == "post_reply":
        from engagement import post_reply_cmd
        raw = (os.environ.get("ENGAGEMENT_PATH") or "").strip()
        if not raw:
            raise SystemExit("ENGAGEMENT_PATH is required for POST_MODE=post_reply.")
        post_reply_cmd(Path(raw))
        return 0
    return generate_draft()


def generate_draft() -> int:
    now = datetime.now(timezone.utc)
    force = os.environ.get("FORCE_PILLAR") or None

    pillar, config = pick_pillar(now.weekday(), force)
    print(f"[{now.isoformat()}] Pillar: {pillar} ({config['day']})")
    print("Generating draft with Claude...")

    post = generate_post(pillar, config)
    post.update({
        "status": "draft",
        "published": False,
        "approved": False,
        "approval_required": True,
        "dry_run": True,
    })
    path = save_post(post)
    if force:
        _supersede_previous_draft(pillar, path)
    _notify_draft_ready(path, post, pillar)

    print(f"Saved draft -> {path}")
    _print_post(post)

    # Generate hook variant (English pillars only — skipped for Arabic automatically)
    print("Generating hook variant...")
    variant = generate_hook_variant(post, config)
    if variant is not None:
        variant["variant_of"] = path.name
        # Save variant with timestamp 1 s before the primary so it sorts AFTER
        # the primary in the descending-timestamp dashboard list.
        primary_parts = path.stem.split("_")  # ["20260516", "095923", "pain"]
        primary_dt = datetime.strptime(
            primary_parts[0] + "_" + primary_parts[1], "%Y%m%d_%H%M%S"
        )
        variant_ts = (primary_dt - timedelta(seconds=1)).strftime("%Y%m%d_%H%M%S")
        variant_path = path.parent / f"{variant_ts}_{pillar}_v.json"
        variant_path.write_text(json.dumps(variant, indent=2), encoding="utf-8")
        # Tag primary draft with has_variant
        post["has_variant"] = True
        path.write_text(json.dumps(post, indent=2), encoding="utf-8")
        print(f"Saved hook variant -> {variant_path}")
    else:
        print("hook_variant: no variant generated (skipped or failed)")

    print("Draft mode — not publishing to LinkedIn. Review the draft, then run POST_MODE=publish_draft with PUBLISH_DRAFT_PATH.")
    return 0


def _supersede_previous_draft(pillar: str, new_path: Path) -> None:
    """Mark the most recent unreviewed draft for *pillar* as superseded.

    Called when Recreate generates a replacement draft so the old one stops
    appearing as 'Needs review' in the dashboard.  Only affects drafts that
    are not yet approved or published — approved drafts are left alone.
    """
    history = Path(__file__).parent / "posts_history"
    for f in sorted(history.glob("*.json"), reverse=True):
        if f.resolve() == new_path.resolve():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if (
            data.get("pillar") == pillar
            and not data.get("published")
            and not data.get("approved")
            and data.get("status") in ("draft", None)
        ):
            data.update({
                "status":        "superseded",
                "superseded_at": datetime.now(timezone.utc).isoformat(),
                "superseded_by": new_path.name,
            })
            f.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Superseded old draft: {f.name}")
            break  # only the most recent eligible draft


def generate_and_publish_now() -> int:
    """Emergency/manual path: generate and publish in a single explicit run."""
    if os.environ.get("CONFIRM_PUBLISH_NOW", "false").lower() != "true":
        raise SystemExit(
            "POST_MODE=publish_now requires CONFIRM_PUBLISH_NOW=true. "
            "Use draft mode for normal scheduled runs."
        )

    now = datetime.now(timezone.utc)
    force = os.environ.get("FORCE_PILLAR") or None
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    pillar, config = pick_pillar(now.weekday(), force)
    print(f"[{now.isoformat()}] Pillar: {pillar} ({config['day']})")
    print("Generating post with Claude for explicit publish_now run...")

    post = generate_post(pillar, config)
    post.update({
        "status": "draft" if dry_run else "approved",
        "published": False,
        "approved": not dry_run,
        "approval_required": False,
        "dry_run": dry_run,
    })
    path = save_post(post)
    print(f"Saved post -> {path}")
    _print_post(post)

    if dry_run:
        print("DRY_RUN=true — skipping LinkedIn publish.")
        return 0

    return _publish_post_file(path)


def publish_approved_for_today() -> int:
    """Publish sweep: find the oldest approved draft whose publish_day matches today.

    Pillar-agnostic — publishes any approved post scheduled for today, regardless of
    which pillar generated it.  Legacy posts with no publish_day are included so they
    are never silently stuck.  Publishes at most one post per run to avoid bulk-publishing.
    """
    dry_run    = os.environ.get("DRY_RUN", "false").lower() == "true"
    now        = datetime.now(timezone.utc)
    today_name = now.strftime("%A")  # e.g. "Monday"

    history    = Path(__file__).parent / "posts_history"
    candidates: list[tuple[Path, dict]] = []

    # Walk oldest-first so candidates[0] is the post that has waited longest
    for f in sorted(history.glob("*.json")):
        try:
            post = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not (post.get("approved") or post.get("status") == "approved"):
            continue
        if post.get("published"):
            continue
        if post.get("status") == "superseded":
            continue
        post_publish_day = post.get("publish_day", "")
        # Include posts whose publish_day matches today, or legacy posts with no publish_day
        if post_publish_day and post_publish_day != today_name:
            continue
        candidates.append((f, post))

    if not candidates:
        print(f"No approved posts scheduled for {today_name}. Nothing to publish.")
        return 0

    path, post = candidates[0]
    print(f"[publish_approved] Candidate: {path.name}  pillar={post.get('pillar')}  publish_day={post.get('publish_day', 'legacy')}")

    if dry_run:
        print(f"DRY_RUN=true — would publish {path.name}. Remaining candidates: {len(candidates) - 1}")
        for p, _ in candidates[1:]:
            print(f"  (queued) {p.name}")
        return 0

    return _publish_post_file(path)


def approve_draft_file() -> int:
    """Flip a draft's status to approved without publishing.

    Reads PUBLISH_DRAFT_PATH, sets approved=True, status='approved',
    approval_required=False, approved_at=now.  The workflow's commit step
    uses the approve: <basename> message for this action.
    """
    raw_path = (os.environ.get("PUBLISH_DRAFT_PATH") or "").strip()
    if not raw_path:
        raise SystemExit(
            "PUBLISH_DRAFT_PATH is required for approve_draft mode. "
            "Example: posts_history/20260430_090000_pain.json"
        )

    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    if not path.exists():
        raise SystemExit(f"Draft not found: {path}")

    post = json.loads(path.read_text(encoding="utf-8"))
    if post.get("published"):
        raise SystemExit(f"Post is already published — cannot re-approve: {path}")

    post.update({
        "status":           "approved",
        "approved":         True,
        "approval_required": False,
        "approved_at":      datetime.now(timezone.utc).isoformat(),
        "dry_run":          False,
    })
    path.write_text(json.dumps(post, indent=2), encoding="utf-8")
    print(f"Approved: {path.name}  (will publish on next scheduled {post.get('pillar', '')} cron)")
    return 0


def publish_saved_draft() -> int:
    raw_path = (os.environ.get("PUBLISH_DRAFT_PATH") or "").strip()
    if not raw_path:
        raise SystemExit(
            "PUBLISH_DRAFT_PATH is required for POST_MODE=publish_draft. "
            "Example: posts_history/20260430_090000_ai.json"
        )

    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    return _publish_post_file(path)


def _publish_post_file(path: Path) -> int:
    if not path.exists():
        raise SystemExit(f"Draft file not found: {path}")

    post = json.loads(path.read_text(encoding="utf-8"))
    if not post.get("post"):
        raise SystemExit(f"Draft file does not contain a post body: {path}")
    if post.get("published"):
        print(f"Already published: {path}")
        return 0

    post.update({
        "status": "approved",
        "approved": True,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approval_required": False,
        "dry_run": False,
    })
    path.write_text(json.dumps(post, indent=2), encoding="utf-8")

    print(f"Publishing approved draft -> {path}")
    try:
        result = publish_post(post["post"], pillar=post.get("pillar", ""))
        print(f"Published! Post ID: {result['post_id']}  image={result.get('image_path','')}")
        _update_json(path, {
            "status":              "published",
            "published":           True,
            "post_id":             result["post_id"],
            "published_at":        datetime.now(timezone.utc).isoformat(),
            "cta_comment_posted":  result.get("cta_comment_posted", False),
            "cta_comment_url":     result.get("cta_comment_url", ""),
        })
        return 0
    except LinkedInError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        _update_json(path, {"status": "failed", "published": False, "publish_error": str(e)})
        return 1


def revise_saved_draft() -> int:
    """Rewrite an existing draft based on owner feedback (REVISION_NOTES env var)."""
    raw_path = (os.environ.get("PUBLISH_DRAFT_PATH") or "").strip()
    notes    = (os.environ.get("REVISION_NOTES") or "").strip()
    if not raw_path:
        raise SystemExit("PUBLISH_DRAFT_PATH is required for revise_draft mode.")
    if not notes:
        raise SystemExit("REVISION_NOTES is required for revise_draft mode.")

    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    if not path.exists():
        raise SystemExit(f"Draft not found: {path}")

    original = json.loads(path.read_text(encoding="utf-8"))
    print(f"Revising draft: {path.name}")
    print(f"Feedback: {notes}")

    from generator import revise_post
    revised = revise_post(original, notes)
    path.write_text(json.dumps(revised, indent=2), encoding="utf-8")
    print(f"Draft revised → {path}")
    _print_post(revised)
    return 0


def announce_pending_jobs() -> int:
    """Generate job announcement drafts for all pending (unannounced) jobs.

    Run manually: POST_MODE=announce_jobs python main.py
    This is completely separate from the 3x/week marketing schedule.
    """
    try:
        from smartpro_data import get_pending_jobs, mark_job_announced
    except ImportError:
        print("smartpro_data.py not found — cannot process job queue.")
        return 1

    pending = get_pending_jobs()
    if not pending:
        print("No pending jobs to announce.")
        return 0

    jobs_config = PILLARS["jobs"]
    announced = 0

    for job in pending:
        try:
            print(f"\nGenerating announcement for: {job.get('title')} @ {job.get('company_name')}")
            post = generate_job_post(job, jobs_config)
            post.update({
                "status": "draft",
                "published": False,
                "approved": False,
                "approval_required": True,
                "dry_run": True,
            })
            path = save_post(post)
            mark_job_announced(job["id"])
            _notify_draft_ready(path, post, "jobs")
            print(f"Saved job draft -> {path}")
            _print_post(post)
            announced += 1
        except Exception as e:
            print(f"ERROR generating announcement for job {job.get('id')}: {e}")

    print(f"\nDone — {announced}/{len(pending)} job announcement drafts created.")
    print("Review and approve each draft, then publish with POST_MODE=publish_draft.")
    return 0


def _notify_draft_ready(path: Path, post: dict, pillar: str) -> None:
    """Send optional draft-ready alerts without blocking draft creation."""
    try:
        from notifier import send_draft_ready

        send_draft_ready(
            draft_path=str(path),
            post_preview=post.get("post", ""),
            pillar=pillar,
            dashboard_url=os.environ.get("DASHBOARD_URL"),
        )
    except Exception as exc:  # noqa: BLE001 - notifications must never abort drafting
        print(f"WARNING: draft notification failed unexpectedly: {exc}")


def _print_post(post: dict) -> None:
    print("\n" + "=" * 60)
    print(post["post"])
    print(
        "=" * 60
        + f"\n({post['char_count']} chars  model={post['model']}"
        + f"  attempts={post.get('attempts', 1)}  status={post.get('status', 'draft')})\n"
    )


def _update_json(path: Path, updates: dict) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(updates)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
