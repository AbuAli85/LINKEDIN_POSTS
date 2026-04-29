"""Generate LinkedIn posts using Claude."""

import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

import anthropic

HISTORY_DIR = Path(__file__).parent / "posts_history"
HISTORY_DIR.mkdir(exist_ok=True)

DEFAULT_MODEL = "claude-sonnet-4-6"
MIN_CHARS = 800
MAX_CHARS = 1500
MAX_TOKENS = 1200

BANNED_PHRASES = [
    "in today's fast-paced",
    "in the ever-evolving",
    "delve into",
    "delving into",
    "it's not just",
    "unlock the power",
    "game-changer",
    "tapestry",
    "embark on",
    "in the realm of",
    "at the end of the day",
    "in a world where",
    "we live in an era",
]

SYSTEM_PROMPT = """You are an elite LinkedIn ghostwriter behind several 100K+ follower accounts in tech and business.

VOICE & STRUCTURE
- The first line must stop the scroll. Specific, surprising, or contrarian.
- Short paragraphs (1-3 lines). White space is your friend.
- Tell a specific story, share a sharp insight, or take a clear position.
- End with a takeaway or a question that invites real comments.
- Sound like a thoughtful operator talking, not a brand.

EXAMPLES OF STRONG HOOKS
- "I fired my best engineer last quarter. It was the right call."
- "Most AI pilots fail for the same boring reason."
- "Three years ago, I made a $40K marketing mistake. Here's what it taught me."
- "The cheapest way to keep great people: pay them before they have to ask."

BANNED — never use these:
- AI clichés: "in today's fast-paced world", "delve", "tapestry", "unlock the power", "game-changer", "embark on", "ever-evolving", "in the realm of"
- Setup-payoff: "It's not just X — it's Y"
- Empty openers: "In a world where...", "We live in an era..."
- Corporate jargon: "synergy", "circle back", "thought leadership"

FORMAT
- 800-1500 characters total (spaces and line breaks count).
- 3-5 hashtags at the bottom, each on its own line.
- No markdown, no code fences, no preamble. Output the post text only."""


USER_TEMPLATE = """Write a LinkedIn post for the {pillar} pillar.

TOPIC: {topic}
TONE: {tone}
AUDIENCE: {audience}

PROCESS (do this in your head, output only the final post):
1. Draft 3 candidate opening hooks. Make them specific, surprising, or contrarian.
2. Pick the strongest hook — the one a busy professional would stop scrolling for.
3. Write the post around it. Short paragraphs. Concrete details. One clear takeaway.
4. End with a question or call to action that invites genuine comments.
5. Add 3-5 relevant hashtags on their own lines at the bottom.

CHARACTER LIMIT: 800-1500 (strict).

{recent_block}Write the final post now. Output only the post — no explanation, no preamble."""


def _load_recent_posts(limit: int = 5) -> list[dict]:
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)[:limit]
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            continue
    return out


def _recent_topics(limit: int = 20) -> set[str]:
    return {p.get("topic", "") for p in _load_recent_posts(limit)}


def _recent_block(limit: int = 5) -> str:
    posts = _load_recent_posts(limit)
    if not posts:
        return ""
    lines = ["RECENT POSTS (avoid repeating these angles, hooks, or phrasing):"]
    for p in posts:
        first_line = p.get("post", "").split("\n", 1)[0][:140]
        lines.append(f"- [{p.get('pillar', '?')}] {first_line}")
    return "\n".join(lines) + "\n\n"


def pick_topic(pillar_config: dict) -> str:
    recent = _recent_topics()
    available = [t for t in pillar_config["topics"] if t not in recent]
    if not available:
        available = pillar_config["topics"]
    return random.choice(available)


def _validate(post: str) -> str | None:
    n = len(post)
    if n < MIN_CHARS:
        return f"too short ({n} chars, need >= {MIN_CHARS})"
    if n > MAX_CHARS:
        return f"too long ({n} chars, need <= {MAX_CHARS})"
    lower = post.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower:
            return f"contains banned phrase: {phrase!r}"
    return None


def _generate_once(
    client: anthropic.Anthropic,
    model: str,
    pillar: str,
    pillar_config: dict,
    topic: str,
    recent_block: str,
) -> tuple[str, str]:
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_TEMPLATE.format(
                    pillar=pillar,
                    topic=topic,
                    tone=pillar_config["tone"],
                    audience=pillar_config["audience"],
                    recent_block=recent_block,
                ),
            }
        ],
    )
    text = next(b.text for b in response.content if b.type == "text").strip()
    return text, response.model


def generate_post(pillar: str, pillar_config: dict, topic: str | None = None) -> dict:
    """Generate a LinkedIn post. Validates output and retries once if needed."""
    if topic is None:
        topic = pick_topic(pillar_config)

    model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
    client = anthropic.Anthropic()
    recent_block = _recent_block()

    last_error: str | None = None
    last_result: tuple[str, str] | None = None
    for attempt in range(2):
        post_text, model_used = _generate_once(
            client, model, pillar, pillar_config, topic, recent_block
        )
        last_result = (post_text, model_used)
        err = _validate(post_text)
        if err is None:
            return {
                "pillar": pillar,
                "topic": topic,
                "post": post_text,
                "char_count": len(post_text),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": model_used,
                "attempts": attempt + 1,
            }
        last_error = err
        print(f"Validation warning (attempt {attempt + 1}): {err}. Retrying...")

    # Both attempts failed validation — publish the last draft anyway with a logged warning,
    # so we never miss a scheduled post over a borderline-strict check.
    assert last_result is not None
    post_text, model_used = last_result
    print(f"WARNING: publishing despite validation issue: {last_error}")
    return {
        "pillar": pillar,
        "topic": topic,
        "post": post_text,
        "char_count": len(post_text),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model_used,
        "attempts": 2,
        "validation_warning": last_error,
    }


def save_post(post_data: dict) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = HISTORY_DIR / f"{ts}_{post_data['pillar']}.json"
    path.write_text(json.dumps(post_data, indent=2))
    return path


if __name__ == "__main__":
    from content_strategy import pick_pillar

    weekday = datetime.now(timezone.utc).weekday()
    force = os.environ.get("FORCE_PILLAR") or None
    pillar, config = pick_pillar(weekday, force)

    print(f"Generating {pillar} post...")
    post = generate_post(pillar, config)
    path = save_post(post)
    print(f"\n--- {pillar.upper()} ({post['char_count']} chars) ---")
    print(post["post"])
    print(f"\nSaved to {path}")
