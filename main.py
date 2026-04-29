"""Orchestrator: pick pillar, generate post, publish to LinkedIn."""

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from content_strategy import pick_pillar
from generator import generate_post, save_post
from publisher import LinkedInError, publish_post

load_dotenv()


def main() -> int:
    now = datetime.now(timezone.utc)
    force = os.environ.get("FORCE_PILLAR") or None
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    pillar, config = pick_pillar(now.weekday(), force)
    print(f"[{now.isoformat()}] Pillar: {pillar} ({config['day']})")

    print("Generating post with Claude...")
    post = generate_post(pillar, config)
    path = save_post(post)
    print(f"Saved draft -> {path}")
    print("\n" + "=" * 60)
    print(post["post"])
    print(
        "=" * 60
        + f"\n({post['char_count']} chars, model={post['model']}, attempts={post.get('attempts', 1)})\n"
    )

    if dry_run:
        print("DRY_RUN=true — skipping LinkedIn publish.")
        return 0

    print("Publishing to LinkedIn...")
    try:
        result = publish_post(post["post"])
        print(f"Published! Post ID: {result['post_id']}")
        return 0
    except LinkedInError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
