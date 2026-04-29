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
    "here's what i've learned:",
    "here's the truth:",
    "let that sink in",
    "unpopular opinion:",
    "hot take:",
]

SYSTEM_PROMPT = """You are an elite LinkedIn ghostwriter behind several 100K+ follower accounts in tech and business.

VOICE & STRUCTURE
- The first line must stop the scroll. Specific, surprising, or contrarian — never generic.
- Short paragraphs (1-3 lines). White space is your friend. Never a wall of text.
- Tell a specific story, share a sharp insight, or take a clear position.
- End with one crisp takeaway or a question that invites real comments.
- Sound like a thoughtful operator talking, not a brand or a content creator.

EXAMPLES OF STRONG HOOKS
- "I fired my best engineer last quarter. It was the right call."
- "Most AI pilots fail for the same boring reason."
- "Three years ago, I made a $40K marketing mistake. Here's what it taught me."
- "The cheapest way to keep great people: pay them before they have to ask."
- "We hit 10K users. Then we deleted the feature that got us there."

BANNED — never use:
- AI clichés: "in today's fast-paced world", "delve", "tapestry", "unlock the power",
  "game-changer", "embark on", "ever-evolving", "in the realm of"
- Lazy setup phrases: "Here's what I've learned:", "Here's the truth:", "Let that sink in",
  "Unpopular opinion:", "Hot take:" (just state the take directly)
- Empty openers: "In a world where...", "We live in an era..."
- Corporate jargon: "synergy", "circle back", "thought leadership", "move the needle"

FORMAT
- 800-1500 characters total (spaces and line breaks count).
- 3-5 hashtags at the bottom, each on its own line.
- No markdown, no code fences, no preamble. Output the post text only."""


USER_TEMPLATE = """Write a LinkedIn post for the {pillar} pillar.

TOPIC: {topic}
TONE: {tone}
AUDIENCE: {audience}
OPENING STYLE: {fmt}

PROCESS (do this in your head — output only the final post):
1. Draft 3 opening lines that follow the OPENING STYLE above. Make them specific and concrete.
2. Pick the one that would stop a busy professional mid-scroll.
3. Build the post around it. Short paragraphs. One concrete detail or data point. One clear takeaway.
4. End with a question or statement that makes someone want to comment.
5. Add 3-5 relevant hashtags on their own lines.

HARD LIMIT: 800-1500 characters.

{recent_block}Output only the final post. No explanation, no preamble, no label."""


def _load_recent_posts(limit: int = 10) -> list[dict]:
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)[:limit]
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def _recent_topics(posts: list[dict]) -> set[str]:
    return {p.get("topic", "") for p in posts}


def _recent_formats(posts: list[dict]) -> list[str]:
    return [p.get("format", "") for p in posts if p.get("format")]


def _recent_block(posts: list[dict]) -> str:
    if not posts:
        return ""
    lines = ["RECENT POSTS (avoid repeating these angles, hooks, or phrasing):"]
    for p in posts[:5]:
        first_line = p.get("post", "").split("\n", 1)[0][:140]
        lines.append(f"- [{p.get('pillar', '?')}] {first_line}")
    return "\n".join(lines) + "\n\n"


def pick_topic(pillar_config: dict, recent_posts: list[dict]) -> str:
    recent = _recent_topics(recent_posts)
    available = [t for t in pillar_config["topics"] if t not in recent]
    if not available:
        available = pillar_config["topics"]
    return random.choice(available)


def pick_format(pillar_config: dict, recent_posts: list[dict]) -> str:
    recent = set(_recent_formats(recent_posts[-len(pillar_config["formats"]):]))
    available = [f for f in pillar_config["formats"] if f not in recent]
    if not available:
        available = pillar_config["formats"]
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
    fmt: str,
    recent_block: str,
) -> tuple[str, str]:
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {
                "role": "user",
                "content": USER_TEMPLATE.format(
                    pillar=pillar,
                    topic=topic,
                    tone=pillar_config["tone"],
                    audience=pillar_config["audience"],
                    fmt=fmt,
                    recent_block=recent_block,
                ),
            }
        ],
    )
    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        raise RuntimeError(f"No text block in API response: {response.content}")
    text = text_blocks[0].strip()
    return text, response.model


def generate_post(pillar: str, pillar_config: dict, topic: str | None = None) -> dict:
    """Generate a LinkedIn post. Validates output and retries once if needed."""
    # Load recent posts once — reused for topic/format dedup and recent_block
    recent_posts = _load_recent_posts(20)

    if topic is None:
        topic = pick_topic(pillar_config, recent_posts)

    fmt = pick_format(pillar_config, recent_posts)
    model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
    # Module-level singleton avoids creating a new HTTP connection pool per call
    client = anthropic.Anthropic()
    rb = _recent_block(recent_posts)

    last_error: str | None = None
    last_result: tuple[str, str] | None = None
    for attempt in range(2):
        post_text, model_used = _generate_once(
            client, model, pillar, pillar_config, topic, fmt, rb
        )
        last_result = (post_text, model_used)
        err = _validate(post_text)
        if err is None:
            return {
                "pillar": pillar,
                "topic": topic,
                "format": fmt,
                "post": post_text,
                "char_count": len(post_text),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": model_used,
                "attempts": attempt + 1,
            }
        last_error = err
        print(f"Validation warning (attempt {attempt + 1}): {err}. Retrying...")

    if last_result is None:
        raise RuntimeError("generate_once was never called — retry loop did not execute")
    post_text, model_used = last_result
    print(f"WARNING: publishing despite validation issue: {last_error}")
    return {
        "pillar": pillar,
        "topic": topic,
        "format": fmt,
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
    path.write_text(json.dumps(post_data, indent=2), encoding="utf-8")
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
