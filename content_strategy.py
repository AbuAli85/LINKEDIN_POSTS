"""Content strategy: 3 posts/week across 3 pillars."""

PILLARS = {
    "leadership": {
        "day": "Monday",
        "weekday": 0,
        "tone": "thoughtful, story-driven, reflective",
        "audience": "managers, founders, ambitious professionals",
        "topics": [
            "What separates good managers from great ones",
            "The hardest leadership lesson I learned the hard way",
            "Why hiring slow and firing fast still matters",
            "How to give feedback people actually act on",
            "Building trust on a remote team",
            "The cost of avoiding hard conversations",
            "Why your top performer just quit (and how to prevent it)",
            "How to lead a team through ambiguity",
            "The one meeting every leader should run weekly",
            "Why your culture is what you tolerate",
            "Decision-making frameworks for high-stakes moments",
            "How to delegate without losing quality",
            "The leader's job is to absorb pressure, not pass it down",
            "Why psychological safety is your competitive moat",
            "Career growth: managing up without being political",
        ],
    },
    "ai": {
        "day": "Wednesday",
        "weekday": 2,
        "tone": "sharp, practical, slightly contrarian",
        "audience": "engineers, product leaders, AI-curious professionals",
        "topics": [
            "What AI agents actually do well in 2026 (and what they still can't)",
            "The most underrated AI use case in business right now",
            "Why prompt engineering is becoming context engineering",
            "How AI is quietly changing knowledge work",
            "The real cost of building with LLMs at scale",
            "Why most AI pilots fail to reach production",
            "RAG vs fine-tuning: when each one wins",
            "How to evaluate an LLM application properly",
            "The skills AI won't replace anytime soon",
            "Why every team should have an AI workflow audit",
            "Building AI products that users actually trust",
            "The hidden ROI of AI: time-to-decision, not headcount",
            "How small teams can outcompete giants with AI leverage",
            "The agent era: what changes for software architecture",
            "Why Claude, GPT, and Gemini are not interchangeable",
        ],
    },
    "marketing": {
        "day": "Friday",
        "weekday": 4,
        "tone": "punchy, data-informed, tactical",
        "audience": "marketers, founders, growth practitioners",
        "topics": [
            "The one marketing metric most teams measure wrong",
            "Why your content isn't converting (it's not the copy)",
            "How to build a personal brand without being cringe",
            "The funnel is dead. What replaced it.",
            "Why LinkedIn outperforms paid ads for B2B in 2026",
            "How to write a hook that stops the scroll",
            "The 3-post framework that grew my following 10x",
            "Why 'thought leadership' fails — and what works instead",
            "Lead generation tactics that still work this year",
            "How to turn one piece of content into ten",
            "Why your CTA is killing your conversion rate",
            "The case for owned audience over rented audience",
            "How to position a product no one is searching for",
            "B2B marketing: why ICP beats persona every time",
            "The newsletter strategy quietly outperforming paid ads",
        ],
    },
}


def pick_pillar(weekday: int, force: str | None = None) -> tuple[str, dict]:
    """Pick the pillar for the given weekday, or use forced override."""
    if force and force in PILLARS:
        return force, PILLARS[force]
    for name, config in PILLARS.items():
        if config["weekday"] == weekday:
            return name, config
    # Fallback: pick the next upcoming pillar
    name = min(PILLARS.items(), key=lambda x: (x[1]["weekday"] - weekday) % 7)[0]
    return name, PILLARS[name]
