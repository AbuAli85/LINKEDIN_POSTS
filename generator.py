"""Generate LinkedIn posts using Claude."""

import json
import os
import random
from datetime import datetime
from pathlib import Path

import anthropic

HISTORY_DIR = Path(__file__).parent / "posts_history"
HISTORY_DIR.mkdir(exist_ok=True)

SYSTEM_PROMPT = """You are an expert LinkedIn ghostwriter who has built multiple 100K+ follower accounts.

You write posts that:
- Open with a scroll-stopping hook in the first 1-2 lines (the "above the fold" preview)
- Use short paragraphs (1-3 lines) with white space — never wall-of-text
- Tell a specific story, share a contrarian take, or deliver a sharp insight
- End with a clear takeaway or a question that drives comments
- Sound like a real human, not a marketing brochure
- Avoid AI-tells: no "in today's fast-paced world", no "delve", no "it's not just X, it's Y"
- Avoid emojis unless they genuinely add meaning (max 1-2 per post)
- Stay between 800-1500 characters (LinkedIn's sweet spot for reach)

You output ONLY the post text — no preamble, no explanation, no markdown code fences."""

USER_TEMPLATE = """Write a LinkedIn post for the {pillar} pillar.

TOPIC: {topic}
TONE: {tone}
AUDIENCE: {audience}

Constraints:
- 800-1500 characters
- Strong hook in line 1 (treat it like a headline)
- Use line breaks for readability
- Include 3-5 relevant hashtags at the end on their own lines
- End with a question or call to action that invites engagement

Write the post now."""


def _recent_topics(limit: int = 20) -> list[str]:
    """Return topics used in recent posts to avoid repetition."""
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)[:limit]
    out = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            out.append(data.get("topic", ""))
        except Exception:
            continue
    return out


def pick_topic(pillar_config: dict) -> str:
    """Pick a topic that hasn't been used recently."""
    recent = set(_recent_topics())
    available = [t for t in pillar_config["topics"] if t not in recent]
    if not available:
        available = pillar_config["topics"]
    return random.choice(available)


def generate_post(pillar: str, pillar_config: dict, topic: str | None = None) -> dict:
    """Generate a LinkedIn post for the given pillar. Returns dict with post + metadata."""
    if topic is None:
        topic = pick_topic(pillar_config)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_TEMPLATE.format(
                    pillar=pillar,
                    topic=topic,
                    tone=pillar_config["tone"],
                    audience=pillar_config["audience"],
                ),
            }
        ],
    )

    post_text = next(b.text for b in response.content if b.type == "text").strip()

    return {
        "pillar": pillar,
        "topic": topic,
        "post": post_text,
        "char_count": len(post_text),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "model": response.model,
    }


def save_post(post_data: dict) -> Path:
    """Persist the generated post to history."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = HISTORY_DIR / f"{ts}_{post_data['pillar']}.json"
    path.write_text(json.dumps(post_data, indent=2))
    return path


if __name__ == "__main__":
    from content_strategy import PILLARS, pick_pillar

    weekday = datetime.utcnow().weekday()
    force = os.environ.get("FORCE_PILLAR") or None
    pillar, config = pick_pillar(weekday, force)

    print(f"Generating {pillar} post...")
    post = generate_post(pillar, config)
    path = save_post(post)
    print(f"\n--- {pillar.upper()} ({post['char_count']} chars) ---")
    print(post["post"])
    print(f"\nSaved to {path}")
