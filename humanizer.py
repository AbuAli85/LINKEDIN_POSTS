"""Humanize AI-generated LinkedIn posts — remove tell-tale AI writing patterns."""

import os

import anthropic

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1200
MIN_OUTPUT_CHARS = 400

HUMANIZER_SYSTEM = """You are an expert writing editor. Remove all AI-generated writing patterns from the text and rewrite it to sound like a real person wrote it.

Remove these patterns:
- Significance inflation: "pivotal moment", "marks a shift", "testament to", "underscores", "enduring legacy", "transformative"
- Superficial -ing phrases: "highlighting", "underscoring", "reflecting", "contributing to", "showcasing", "emphasizing"
- Promotional language: "groundbreaking", "seamless", "intuitive", "innovative", "game-changer", "unlock"
- Chatbot artifacts: "Great question!", "Certainly!", "I hope this helps", "Let me know if you'd like me to expand"
- Rule of three everywhere
- Synonym cycling ("The system. The tool. The platform.")
- Em dash overuse
- Negative parallelism ("It's not just X; it's Y")
- Vague attributions ("experts say", "studies show", "industry observers note")
- Excessive hedging ("could potentially", "it might be argued")
- Filler phrases ("At its core", "In order to", "It's worth noting")
- Copula avoidance ("serves as", "functions as", "stands as" → use "is")
- Generic conclusions ("the future looks bright", "exciting times lie ahead")
- Signposting ("Let's dive in", "Here's what you need to know")

Add soul:
- Vary sentence rhythm (mix short punchy and longer flowing)
- Have a point of view — react to the content, not just report it
- Use first person when it fits
- Be specific about feelings and observations
- Let some roughness in — perfect structure feels algorithmic

Do a final anti-AI pass: ask yourself "what makes this obviously AI-generated?" then fix those things.

CRITICAL: Preserve all hashtags exactly as written. Preserve all URLs exactly. Preserve all Arabic text exactly. Keep character count within ±15% of the original. Output only the final post text — no explanation, no preamble."""

_USER_TEMPLATE = """Humanize this LinkedIn post. Tone: {tone}. Pillar: {pillar}.

{text}"""


def humanize(text: str, pillar: str = "", tone: str = "") -> str:
    """Remove AI-writing patterns from a LinkedIn post. Falls back to original on any failure."""
    original_len = len(text)
    try:
        client = anthropic.Anthropic()
        model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=[{"type": "text", "text": HUMANIZER_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{
                "role": "user",
                "content": _USER_TEMPLATE.format(tone=tone, pillar=pillar, text=text),
            }],
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]
        if not text_blocks:
            print(f"humanizer: SKIP - empty response")
            return text

        result = text_blocks[0].strip()

        if len(result) < MIN_OUTPUT_CHARS:
            print(f"humanizer: SKIP - output too short ({len(result)} chars)")
            return text

        print(f"humanizer: OK ({original_len} → {len(result)} chars)")
        return result

    except Exception as exc:
        print(f"humanizer: SKIP - {exc}")
        return text


if __name__ == "__main__":
    sample = """In today's fast-paced business environment, it's crucial for HR managers to leverage innovative solutions that serve as a testament to organizational excellence.

The system. The tool. The platform. It's not just software — it's a transformative approach to workforce management that underscores the importance of seamless integration.

By highlighting key performance indicators and showcasing groundbreaking features, SmartPro Hub contributes to a more intuitive experience for all stakeholders.

The future looks bright for Oman businesses ready to embark on this journey.

#HRManagement #Oman #SmartPro"""

    print("=== ORIGINAL ===")
    print(sample)
    print("\n=== HUMANIZED ===")
    result = humanize(sample, pillar="pain", tone="direct, empathetic")
    print(result)
