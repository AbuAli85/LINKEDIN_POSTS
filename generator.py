"""Generate LinkedIn posts using Claude.

Audience-aware: when LINKEDIN_AUDIENCE=company, the strategy_loader
routes pillar/hashtag/CTA reads to company_content_strategy and writes
drafts to company_posts_history/. Defaults to personal pipeline.
"""

import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from strategy_loader import history_dir as _history_dir, load_strategy

HISTORY_DIR = _history_dir()
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
- Feature lists: never write "it does X, Y, and Z" — one sentence on the benefit to the reader, not a spec sheet

FORMAT
- 800-1500 characters total (spaces and line breaks count).
- 3-5 hashtags at the bottom, each on its own line.
- No markdown, no code fences, no preamble. Output the post text only."""

def _build_system_prompt_ar() -> str:
    """Build the Arabic system prompt, injecting the live glossary at import time."""
    from omani_glossary import build_terminology_block, build_voice_block
    return (
        """أنت مدير عمليات عُماني بخبرة عشر سنوات، تكتب على LinkedIn لملاك الأعمال والمديرين في عُمان والخليج.
جمهورك يتعامل يومياً مع الرواتب وتصاريح العمل والتأشيرات ومعاملات وزارة العمل.
منشوراتك تصل إلى عشرات الآلاف من المديرين والمختصين.

الصوت والهوية:
- تكتب كممارس متمرس يصف واقعاً يعرفه القارئ من تجربته — لا كعلامة تجارية تسوّق لنفسها.
- صوتك: مباشر، موثوق، لا يتملق ولا يعظ ولا يستعرض.
- اللغة: عربية فصحى مبسطة — تحمل ثقل الخبرة، تُفهم بلا جهد، وليست أكاديمية جافة.

بنية المنشور:
- السطر الأول يوقف التمرير: محدد، صادم بلطف، أو يحمل موقفاً واضحاً — لا مقدمات أبداً.
- فقرات قصيرة (سطران أو ثلاثة). مسافات بيضاء. لا جدران نص.
- حادثة واحدة حقيقية، أو رقم واحد ملموس، أو مشهد واحد يعرفه القارئ — يُبنى حولها كل شيء.
- الخاتمة: سؤال أو جملة واحدة تدفع القارئ للتعليق الحقيقي، لا لمجرد الإعجاب.

أمثلة على خطافات قوية بهذا المستوى:
- "٩٢٤ مكتب سند في عُمان. معظمها يُدير ثلاثين عميلاً من مجموعة واتساب واحدة."
- "تصريح عمل انتهى في الصمت. العميل اكتشف ذلك في المطار — لا منك."
- "رُفض ملف WPS ليلة الرابع والعشرين. ليس لأن الأموال غير موجودة — بل لأن الملف خطأ."
- "فقدت عميلاً بعد أربع سنوات. ليس بسبب جودة الخدمة. بسبب رسالة واتساب لم تُجَب ثلاث ساعات."
- "مدير موارد بشرية أمضى ثماني ساعات يبحث عن عقد موظف في رسائل البريد الإلكتروني. العقد كان موجوداً — لا أحد يعرف أين بالضبط."

"""
        + build_terminology_block()
        + "\n\n"
        + build_voice_block()
        + """

المحظور — هذه العبارات تُفقد المنشور مصداقيته فوراً:
- الافتتاحيات الفارغة: "في عالم اليوم المتسارع"، "في ظل التحولات المتسارعة"، "نعيش اليوم في عصر"، "في خضم التطور"
- المصطلحات المبتذلة: "التحول الرقمي"، "منظومة متكاملة"، "نهج شمولي"، "التآزر"، "يتصل بالرقمنة"، "المرجع الموثوق"
- الافتتاحيات الكسولة: "إليك ما تعلمته:"، "الحقيقة هي:"، "دعني أشاركك:"، "سؤال مهم:"
- الكلام العام بدون أرقام: "كثير من الشركات"، "معظم المديرين"، "الجميع يعرف" — استبدلها بأرقام أو مشاهد محددة
- المديح الذاتي للمنتج في بداية المنشور — أظهر الألم أولاً
- قوائم مواصفات المنتج: لا تكتب "يفعل X، ويفعل Y، ويفعل Z" — اكتب جملة واحدة تصف الفائدة للقارئ، لا قائمة ميزات

التنسيق:
- ٨٠٠-١٥٠٠ حرف إجمالاً (المسافات وفواصل الأسطر تُحسب).
- ٣-٥ هاشتاقات في الأسفل، كل منها في سطر منفصل.
- لا markdown، لا مقدمات توضيحية، لا تعليق. أخرج نص المنشور فقط."""
    )


SYSTEM_PROMPT_AR = _build_system_prompt_ar()

USER_TEMPLATE = """Write a LinkedIn post for the {pillar} pillar.

TOPIC: {topic}
TONE: {tone}
AUDIENCE: {audience}
OPENING STYLE: {fmt}
{brand_context}
{cta_override}{brand_bridge}{hashtag_block}{seo_block}{metrics_block}PROCESS (do this in your head — output only the final post):
1. Draft 3 opening lines that follow the OPENING STYLE above. Make them specific and concrete.
2. Pick the one that would stop a busy professional mid-scroll.
3. Build the post around it. Short paragraphs. One concrete detail or data point. One clear takeaway.
4. End with a question or statement that makes someone want to comment.
5. Add 3-5 relevant hashtags on their own lines. Choose from the HASHTAGS list above if provided.

HARD LIMIT: 800-1500 characters.

{performance_block}{recent_block}Output only the final post. No explanation, no preamble, no label."""

USER_TEMPLATE_AR = """اكتب منشور LinkedIn لمحور {pillar}.

الموضوع: {topic}
النبرة: {tone}
الجمهور المستهدف: {audience}
أسلوب الافتتاح: {fmt}
{brand_context}
{cta_override}{brand_bridge}{hashtag_block}{seo_block}{metrics_block}العملية (نفّذ في ذهنك — أخرج المنشور النهائي فقط):
١. اكتب ٣ سطور افتتاحية مختلفة تماماً — كل واحدة تتبع أسلوب الافتتاح، ومحددة وملموسة وتحمل ثقل الخبرة.
٢. اختر السطر الذي سيوقف مدير موارد بشرية أو صاحب مكتب سند أو مسؤول PRO عن التمرير فوراً.
٣. ابنِ المنشور حوله — فقرات قصيرة، رقم واحد حقيقي أو مشهد واحد ملموس، فكرة واحدة واضحة لا أكثر.
٤. انتهِ بسؤال أو جملة حادة تدفع القارئ للتعليق من واقع تجربته.
٥. أضف ٣-٥ هاشتاقات ذات صلة في أسطر منفصلة.

حد صارم: ٨٠٠-١٥٠٠ حرف.

{performance_block}{recent_block}أخرج المنشور النهائي فقط. لا شرح، لا مقدمة، لا تعليق."""

JOB_POST_TEMPLATE = """Write a LinkedIn post announcing a new job opening.

JOB DETAILS:
- Title: {title}
- Company: {company_name}
- Location: {location}
- Employment type: {employment_type}
- Department: {department}
- Role summary: {description}

TONE: {tone}
AUDIENCE: {audience}
OPENING STYLE: {fmt}
{brand_context}

INSTRUCTIONS:
- Announce this specific role in a way that attracts the right candidates
- Make the opportunity feel real and worth applying for — not just a job spec
- Include the SmartPro jobs board as the place to apply (thesmartpro.io)
- End with a clear "Apply at thesmartpro.io" or "See details at thesmartpro.io"
- Add 3-5 relevant hashtags including #Oman #Hiring — each on its own line

HARD LIMIT: 800-1500 characters.

{recent_block}Output only the final post. No explanation, no preamble, no label."""


VALID_SEGMENTS = {"A", "B", "C"}

# ── Brand hashtag normalisation ──────────────────────────────────────────────
BRAND_HASHTAG_VARIANTS = [
    "#SmartPro", "#SmartPro_Hub", "#smartpro", "#smartprohub",
    "#Smartpro", "#SMARTPRO", "#SmartProHub",
]
BRAND_HASHTAG_CANONICAL = "#SmartPROHub"


def _sanitise_hashtags(content: str) -> str:
    """Replace all brand hashtag variants with the canonical form (case-insensitive).

    Also collapses runaway 'Hub' token repetition like #SmartPROHubHubHubHubHub —
    an LLM degeneration pattern that shows up on the variant + humanizer pipeline.
    """
    import re

    # First: collapse runaway `Hub` repetition. `#smartpro(?:hub)+` is whole-token
    # matched and rewritten to the canonical single-Hub form.
    content = re.sub(
        r'(?<![A-Za-z0-9_])#smartpro(?:hub)+(?![A-Za-z0-9_])',
        BRAND_HASHTAG_CANONICAL,
        content,
        flags=re.IGNORECASE,
    )

    # Then: normalize documented case/style variants.
    # Whole-token match via word-char lookarounds prevents the canonical
    # replacement from re-matching as a substring of its own output.
    sorted_variants = sorted(BRAND_HASHTAG_VARIANTS, key=len, reverse=True)
    pattern = (
        r'(?<![A-Za-z0-9_])'
        r'(?:' + '|'.join(re.escape(v) for v in sorted_variants) + r')'
        r'(?![A-Za-z0-9_])'
    )
    return re.sub(pattern, BRAND_HASHTAG_CANONICAL, content, flags=re.IGNORECASE)


def _hashtag_block(segment: str | None) -> str:
    """Return hashtag guidance for the segment. Normalises to uppercase; falls back to A."""
    try:
        HASHTAGS = load_strategy().HASHTAGS
    except Exception:
        return ""
    normalised = (segment or "").strip().upper()
    if normalised not in VALID_SEGMENTS:
        import warnings
        warnings.warn(
            f"_hashtag_block: invalid segment {segment!r} — falling back to Segment A. "
            "Check the pillar definition in content_strategy.py.",
            stacklevel=2,
        )
        normalised = "A"
    tags = HASHTAGS.get(normalised, [])
    if not tags:
        return ""
    return (
        f"Include these hashtags at the end of the post (after a blank line): "
        f"{' '.join(tags)}\n"
        f"Do not insert hashtags mid-post.\n"
    )


def _validate_pillars(pillars: list[dict]) -> None:
    """Raise ValueError listing all pillars with missing or invalid segment fields."""
    bad = [
        p.get("name", f"pillar[{i}]")
        for i, p in enumerate(pillars)
        if (p.get("segment") or "").strip().upper() not in VALID_SEGMENTS
    ]
    if bad:
        raise ValueError(
            f"The following pillars have missing or invalid 'segment' fields: {bad}. "
            "Each pillar must have segment='A', 'B', or 'C'."
        )


def _seo_block() -> str:
    """Return SEO keyword guidance."""
    try:
        SEO_KEYWORDS = load_strategy().SEO_KEYWORDS
        if not SEO_KEYWORDS:
            return ""
        return f"SEO KEYWORDS (weave 1-2 naturally into the post): {', '.join(SEO_KEYWORDS[:6])}\n"
    except Exception:
        return ""


def _cta_block(pillar_config: dict) -> str:
    """Return the UTM-tracked CTA for the given pillar's segment."""
    try:
        _s = load_strategy()
        CTA_DEMO, CTA_DEMO_AR = _s.CTA_DEMO, _s.CTA_DEMO_AR
        CTA_INVESTORS, CTA_INVESTORS_AR = _s.CTA_INVESTORS, _s.CTA_INVESTORS_AR
        CTA_TECH = _s.CTA_TECH
    except (ImportError, AttributeError):
        return ""
    segment  = (pillar_config.get("segment") or "A").strip().upper()
    language = pillar_config.get("language", "en")
    campaign = (pillar_config.get("name") or "general").replace("_", "-")

    if segment == "B":
        template = CTA_INVESTORS_AR if language == "ar" else CTA_INVESTORS
    elif segment == "C":
        return f"CTA: {CTA_TECH}\n"
    else:
        template = CTA_DEMO_AR if language == "ar" else CTA_DEMO

    return f"CTA (use this exact URL with tracking): {template.format(campaign=campaign)}\n"


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


def _recent_block(posts: list[dict], language: str = "en") -> str:
    if not posts:
        return ""
    if language == "ar":
        lines = ["المنشورات الأخيرة (تجنّب تكرار هذه الزوايا أو الصياغات أو الخطافات):"]
        for p in posts[:5]:
            first_line = p.get("post", "").split("\n", 1)[0][:140]
            lines.append(f"- [{p.get('pillar', '?')}] {first_line}")
    else:
        lines = ["RECENT POSTS (avoid repeating these angles, hooks, or phrasing):"]
        for p in posts[:5]:
            first_line = p.get("post", "").split("\n", 1)[0][:140]
            lines.append(f"- [{p.get('pillar', '?')}] {first_line}")
    return "\n".join(lines) + "\n\n"


def _performance_block(language: str = "en") -> str:
    """Return a performance insights section if enough scored posts exist, else ''."""
    try:
        from metrics import get_performance_summary
        summary = get_performance_summary()
    except Exception:
        return ""
    if not summary:
        return ""
    if language == "ar":
        lines = ["إحصاءات الأداء (بيانات جمهورك الحقيقي — اجعل هذه المعطيات تُوجّه اختياراتك):"]
        if bp := summary.get("best_pillar"):
            score = summary["pillar_avg_score"].get(bp, "?")
            lines.append(f"- أفضل محور: {bp} (متوسط {score}/10) — ركّز عليه.")
        if bh := summary.get("best_hook_style"):
            score = summary["hook_avg_score"].get(bh, "?")
            lines.append(f"- أفضل أسلوب افتتاح: {bh} (متوسط {score}/10) — استخدمه.")
        if tp := summary.get("top_topics"):
            lines.append(f"- أعلى الموضوعات تقييماً: {', '.join(tp[:2])}")
        if preview := summary.get("top_posts_preview"):
            lines.append("- سطور افتتاح من أعلى منشوراتك تقييماً (اجعل طاقتك بهذا المستوى):")
            for line in preview:
                lines.append(f"  • {line}")
    else:
        lines = ["PERFORMANCE INSIGHTS (your real audience data — weight toward what works):"]
        if bp := summary.get("best_pillar"):
            score = summary["pillar_avg_score"].get(bp, "?")
            lines.append(f"- Highest-scoring pillar: {bp} (avg {score}/10) — lean into this.")
        if bh := summary.get("best_hook_style"):
            score = summary["hook_avg_score"].get(bh, "?")
            lines.append(f"- Best-performing hook style: {bh} (avg {score}/10) — prefer this opening format.")
        if tp := summary.get("top_topics"):
            lines.append(f"- Top-rated topics so far: {', '.join(tp[:2])}")
        if preview := summary.get("top_posts_preview"):
            lines.append("- Opening lines from your highest-scoring posts (match this energy):")
            for line in preview:
                lines.append(f"  • {line}")
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


_MOJIBAKE_MARKERS = ("ÃÂ", "Ã¢", "â€", "â€™", "â€œ")


def _sanitize(text: str) -> str:
    """Attempt to fix doubly-encoded UTF-8 (mojibake). Returns text unchanged if fix fails."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _validate(post: str, language: str = "en") -> str | None:
    n = len(post)
    if n < MIN_CHARS:
        return f"too short ({n} chars, need >= {MIN_CHARS})"
    if n > MAX_CHARS:
        return f"too long ({n} chars, need <= {MAX_CHARS})"
    for marker in _MOJIBAKE_MARKERS:
        if marker in post:
            return f"encoding corruption detected ({marker!r}) — will retry"
    if language == "ar":
        from omani_glossary import validate_arabic_terms
        if term_warn := validate_arabic_terms(post):
            return term_warn
    else:
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
    performance_block: str = "",
    metrics_block: str = "",
    hashtag_block: str = "",
    seo_block: str = "",
    cta_override: str = "",
    brand_bridge: str = "",
) -> tuple[str, str]:
    language = pillar_config.get("language", "en")
    system_prompt = SYSTEM_PROMPT_AR if language == "ar" else SYSTEM_PROMPT
    user_template = USER_TEMPLATE_AR if language == "ar" else USER_TEMPLATE

    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {
                "role": "user",
                "content": user_template.format(
                    pillar=pillar,
                    topic=topic,
                    tone=pillar_config["tone"],
                    audience=pillar_config["audience"],
                    fmt=fmt,
                    brand_context=pillar_config.get("brand_context", ""),
                    cta_override=cta_override,
                    brand_bridge=brand_bridge,
                    hashtag_block=hashtag_block,
                    seo_block=seo_block,
                    metrics_block=metrics_block,
                    performance_block=performance_block,
                    recent_block=recent_block,
                ),
            }
        ],
    )
    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        raise RuntimeError(f"No text block in API response: {response.content}")
    text = _sanitize(text_blocks[0].strip())
    return text, response.model


def _apply_humanizer(post_text: str, pillar: str, tone: str) -> str:
    try:
        from humanizer import humanize
        return humanize(post_text, pillar=pillar, tone=tone)
    except Exception as exc:
        print(f"WARNING: humanizer failed, using original: {exc}")
        return post_text


def generate_post(pillar: str, pillar_config: dict, topic: str | None = None) -> dict:
    """Generate a LinkedIn post. Validates output and retries once if needed."""
    ALL_PILLARS = load_strategy().ALL_PILLARS
    _validate_pillars(ALL_PILLARS)

    # Load recent posts once — reused for topic/format dedup and recent_block
    recent_posts = _load_recent_posts(20)

    if topic is None:
        topic = pick_topic(pillar_config, recent_posts)

    fmt = pick_format(pillar_config, recent_posts)
    model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
    client = anthropic.Anthropic()
    language = pillar_config.get("language", "en")
    segment  = pillar_config.get("segment", "A")
    rb = _recent_block(recent_posts, language)
    pb = _performance_block(language)
    hb = _hashtag_block(segment)
    sb = _seo_block()

    # Inject live SmartPro metrics for proof/recruitment pillars
    mb = ""
    if pillar in ("proof", "recruitment", "vision"):
        try:
            from smartpro_data import fetch_metrics, build_metrics_context
            mb = build_metrics_context(fetch_metrics())
        except Exception:
            pass

    cb = _cta_block({**pillar_config, "name": pillar})
    bb = pillar_config.get("brand_bridge", "")
    if bb:
        bb = f"Brand connection: {bb}\n"

    last_error: str | None = None
    last_result: tuple[str, str] | None = None
    for attempt in range(2):
        post_text, model_used = _generate_once(
            client, model, pillar, pillar_config, topic, fmt, rb, pb, mb, hb, sb, cb, bb
        )
        post_text = _sanitise_hashtags(post_text)
        last_result = (post_text, model_used)
        err = _validate(post_text, language)
        if err is None:
            post_text = _apply_humanizer(post_text, pillar, pillar_config.get("tone", ""))
            # Re-sanitize after humanizer in case it mangled hashtags.
            post_text = _sanitise_hashtags(post_text)
            return {
                "pillar": pillar,
                "topic": topic,
                "format": fmt,
                "language": language,
                "segment": segment,
                "publish_day": pillar_config.get("publish_day", ""),
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
    post_text = _apply_humanizer(post_text, pillar, pillar_config.get("tone", ""))
    # Re-sanitize after humanizer in case it mangled hashtags.
    post_text = _sanitise_hashtags(post_text)
    print(f"WARNING: publishing despite validation issue: {last_error}")
    return {
        "pillar": pillar,
        "topic": topic,
        "format": fmt,
        "language": language,
        "segment": segment,
        "publish_day": pillar_config.get("publish_day", ""),
        "post": post_text,
        "char_count": len(post_text),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model_used,
        "attempts": 2,
        "validation_warning": last_error,
    }


def generate_job_post(job: dict, pillar_config: dict) -> dict:
    """Generate a job announcement post for a specific pending job."""
    ALL_PILLARS = load_strategy().ALL_PILLARS
    _validate_pillars(ALL_PILLARS)

    recent_posts = _load_recent_posts(20)
    fmt = pick_format(pillar_config, recent_posts)
    model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
    client = anthropic.Anthropic()
    rb = _recent_block(recent_posts)

    employment_map = {
        "full_time": "Full-time",
        "part_time": "Part-time",
        "contract": "Contract",
        "intern": "Internship",
    }
    title = job.get("title", "Open Position")
    company_name = job.get("company_name", "SmartPro client company")
    location = job.get("location") or "Oman"
    employment_type = employment_map.get(job.get("type", ""), job.get("type", "Full-time"))
    department = job.get("department") or "General"
    description = job.get("description") or f"Join {company_name} as a {title}."

    prompt = JOB_POST_TEMPLATE.format(
        title=title,
        company_name=company_name,
        location=location,
        employment_type=employment_type,
        department=department,
        description=description[:500],
        tone=pillar_config["tone"],
        audience=pillar_config["audience"],
        fmt=fmt,
        brand_context=pillar_config.get("brand_context", ""),
        recent_block=rb,
    )

    last_error: str | None = None
    last_result: tuple[str, str] | None = None
    for attempt in range(2):
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]
        if not text_blocks:
            raise RuntimeError("No text block in job post response")
        post_text = _sanitize(text_blocks[0].strip())
        last_result = (post_text, response.model)
        err = _validate(post_text)
        if err is None:
            post_text = _apply_humanizer(post_text, "jobs", pillar_config.get("tone", ""))
            return {
                "pillar": "jobs",
                "topic": f"{title} @ {company_name}",
                "format": fmt,
                "language": "en",
                "segment": pillar_config.get("segment", "A"),
                "post": post_text,
                "char_count": len(post_text),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": response.model,
                "attempts": attempt + 1,
                "job_id": job.get("id"),
                "job_title": title,
                "job_company": company_name,
            }
        last_error = err
        print(f"Job post validation warning (attempt {attempt + 1}): {err}. Retrying...")

    if last_result is None:
        raise RuntimeError("generate_once was never called for job post")
    post_text, model_used = last_result
    post_text = _apply_humanizer(post_text, "jobs", pillar_config.get("tone", ""))
    print(f"WARNING: using job post despite validation issue: {last_error}")
    return {
        "pillar": "jobs",
        "topic": f"{title} @ {company_name}",
        "format": fmt,
        "language": "en",
        "post": post_text,
        "char_count": len(post_text),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model_used,
        "attempts": 2,
        "validation_warning": last_error,
        "job_id": job.get("id"),
        "job_title": title,
        "job_company": company_name,
    }


_REVISE_TEMPLATE = """Revise this LinkedIn post based on the owner's feedback.

ORIGINAL POST:
{original_post}

OWNER FEEDBACK:
{revision_notes}

Apply the feedback precisely. Keep every element that works. Fix only what was flagged.
Maintain the same pillar ({pillar}), tone, and character range (800-1500 chars).
Output only the revised post text. No explanation, no preamble, no label."""

_REVISE_TEMPLATE_AR = """عدّل هذا المنشور بناءً على ملاحظات المالك.

المنشور الأصلي:
{original_post}

ملاحظات المالك:
{revision_notes}

طبّق الملاحظات بدقة. احتفظ بكل عنصر يعمل جيداً. صحّح فقط ما طُلب تغييره.
حافظ على نفس المحور ({pillar}) والنبرة ونطاق الأحرف (٨٠٠-١٥٠٠ حرف).
أخرج نص المنشور المعدّل فقط. لا شرح، لا مقدمة، لا تعليق."""


def revise_post(original: dict, revision_notes: str) -> dict:
    """Rewrite an existing draft based on owner feedback. Returns updated post dict."""
    client = anthropic.Anthropic()
    model  = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
    language = original.get("language", "en")
    system_prompt = SYSTEM_PROMPT_AR if language == "ar" else SYSTEM_PROMPT
    revise_template = _REVISE_TEMPLATE_AR if language == "ar" else _REVISE_TEMPLATE

    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": revise_template.format(
                original_post=original["post"],
                revision_notes=revision_notes,
                pillar=original.get("pillar", ""),
            ),
        }],
    )
    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        raise RuntimeError("No text in revision response.")
    text = text_blocks[0].strip()
    text = _apply_humanizer(text, original.get("pillar", ""), "")

    err = _validate(text)
    revised = original.copy()
    revised.update({
        "post":            text,
        "char_count":      len(text),
        "model":           response.model,
        "status":          "draft",
        "approved":        False,
        "approval_required": True,
        "revision_notes":  revision_notes,
        "revised_at":      datetime.now(timezone.utc).isoformat(),
    })
    revised.pop("validation_warning", None)
    if err:
        revised["validation_warning"] = err
    return revised


_ARABIC_PILLARS = {"pain_ar", "sanad_pro_ar"}

_VARIANT_SYSTEM = """You are an elite LinkedIn ghostwriter. Your job is to rewrite ONLY the opening hook of a post — the first 1-2 lines — using a different hook style.

Keep everything after the first paragraph exactly as-is. Only rewrite the opening hook.

The new hook must:
- Deliver the same core message as the original
- Use a noticeably different approach (e.g. if original is a question, try a bold statement or a data-lead)
- Be specific and concrete — no vague generalities
- Stay within the same character budget (800-1500 chars total)

Output only the complete revised post. No explanation, no preamble."""

_VARIANT_USER = """Original post (pillar: {pillar}, tone: {tone}):

{post}

Write a version with a different opening hook style. Keep everything after the first paragraph unchanged."""


def generate_hook_variant(original: dict, pillar_config: dict) -> dict | None:
    """Generate an alternative hook for an existing post. Returns None if skipped."""
    pillar = original.get("pillar", "")
    if pillar in _ARABIC_PILLARS:
        print(f"hook_variant: SKIP — Arabic pillar ({pillar})")
        return None

    post_text = original.get("post", "")
    if not post_text:
        print("hook_variant: SKIP — empty post text")
        return None

    tone = pillar_config.get("tone", "")
    client = anthropic.Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=[{"type": "text", "text": _VARIANT_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{
                "role": "user",
                "content": _VARIANT_USER.format(pillar=pillar, tone=tone, post=post_text),
            }],
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]
        if not text_blocks:
            print("hook_variant: SKIP — empty API response")
            return None

        variant_text = _sanitize(text_blocks[0].strip())
        variant_text = _sanitise_hashtags(variant_text)
        err = _validate(variant_text, pillar_config.get("language", "en"))
        if err:
            print(f"hook_variant: SKIP — validation failed: {err}")
            return None

        variant_text = _apply_humanizer(variant_text, pillar, tone)
        # Re-sanitize after humanizer in case it mangled hashtags (LLM token repetition).
        variant_text = _sanitise_hashtags(variant_text)
        print(f"hook_variant: OK ({len(post_text)} → {len(variant_text)} chars)")

        variant = original.copy()
        variant.update({
            "post":           variant_text,
            "char_count":     len(variant_text),
            "model":          response.model,
            "is_variant":     True,
            "variant_of":     "",   # overwritten by caller (main.py) with primary filename
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "status":         "draft",
            "approved":       False,
            "approval_required": True,
            "published":      False,
            "dry_run":        True,
        })
        variant.pop("_filename", None)
        variant.pop("has_variant", None)
        variant.pop("validation_warning", None)
        return variant

    except Exception as exc:
        print(f"hook_variant: SKIP — {exc}")
        return None


def save_post(post_data: dict) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = HISTORY_DIR / f"{ts}_{post_data['pillar']}.json"
    path.write_text(json.dumps(post_data, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    pick_pillar = load_strategy().pick_pillar

    weekday = datetime.now(timezone.utc).weekday()
    force = os.environ.get("FORCE_PILLAR") or None
    pillar, config = pick_pillar(weekday, force)

    print(f"Generating {pillar} post...")
    post = generate_post(pillar, config)
    path = save_post(post)
    print(f"\n--- {pillar.upper()} ({post['char_count']} chars) ---")
    print(post["post"])
    print(f"\nSaved to {path}")
