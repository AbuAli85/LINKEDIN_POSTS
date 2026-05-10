"""Orchestrator: generate LinkedIn drafts and publish only explicit approved drafts."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from content_strategy import pick_pillar
from generator import generate_post, save_post
from publisher import LinkedInError, publish_post

load_dotenv()

VALID_MODES = {
    "draft",
    "generate_draft",
    "publish_approved",
    "publish_draft",
    "publish",
    "publish_now",
    "revise_draft",
    "fetch_metrics",
    "fetch_comments",
    "post_reply",
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
    if mode == "publish_now":
        return generate_and_publish_now()
    if mode == "revise_draft":
        return revise_saved_draft()
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
    _notify_draft_ready(path, post, pillar)

    print(f"Saved draft -> {path}")
    _print_post(post)
    print("Draft mode — not publishing to LinkedIn. Review the draft, then run POST_MODE=publish_draft with PUBLISH_DRAFT_PATH.")
    return 0


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
    """Cron phase-2: find the most recent approved draft for today's publish pillar and publish it.

    Runs Mon/Wed/Fri at 6am UTC. If no approved draft exists, exits cleanly — the owner
    simply hasn't approved yet and the post will be skipped for this cycle.
    """
    from content_strategy import PILLARS

    now     = datetime.now(timezone.utc)
    weekday = now.weekday()  # 0=Mon … 6=Sun

    # Identify which scheduled pillar publishes today (exclude conversion — manual only)
    todays_pillar = next(
        (name for name, cfg in PILLARS.items()
         if cfg["weekday"] == weekday and cfg.get("generate_weekday", -1) >= 0),
        None,
    )
    if todays_pillar is None:
        print(f"No pillar scheduled to publish today (weekday={weekday}). Nothing to do.")
        return 0

    history = Path(__file__).parent / "posts_history"
    candidates: list[tuple[Path, dict]] = []
    for f in sorted(history.glob("*.json"), reverse=True):
        try:
            post = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if (
            post.get("pillar") == todays_pillar
            and (post.get("approved") or post.get("status") == "approved")
            and not post.get("published")
        ):
            candidates.append((f, post))

    if not candidates:
        print(
            f"No approved draft found for pillar={todays_pillar!r} (weekday={weekday}). "
            "Owner has not approved a draft yet — skipping this publish cycle."
        )
        return 0

    path, _ = candidates[0]  # most recently generated approved draft
    print(f"Auto-publishing approved {todays_pillar} draft: {path.name}")
    return _publish_post_file(path)


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
            "status": "published",
            "published": True,
            "post_id": result["post_id"],
            "published_at": datetime.now(timezone.utc).isoformat(),
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


def _notify_draft_ready(path: Path, post: dict, pillar: str) -> None:
    """Send optional draft-ready alerts without blocking draft creation."""
    try:
        from notifier import send_draft_ready

        send_draft_ready(
            draft_path=str(path),
            post_preview=post.get("post", "")[:200],
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
