"""Humanize AI-generated LinkedIn posts — remove tell-tale AI writing patterns.

English posts: strip AI clichés, add human rhythm and voice.
Arabic posts:  enforce correct Omani terminology, improve authentic Gulf voice.
"""

import os

import anthropic

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1200
MIN_OUTPUT_CHARS = 400

_ARABIC_PILLARS = {"pain_ar", "sanad_pro_ar"}

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

CRITICAL: Preserve all hashtags exactly as written. Preserve all URLs exactly. Keep character count within ±15% of the original. Output only the final post text — no explanation, no preamble."""

HUMANIZER_SYSTEM_AR = """أنت محرر كتابة متخصص في المحتوى العربي لمنصة LinkedIn، متمرس في الأسلوب الخليجي والعُماني.

مهمتك: اقرأ هذا المنشور وأخرج نسخة أقوى — لا تغيّر الجوهر، حسّن الأصالة والدقة.

ما تفحصه:
- هل صوت المنشور حقيقي ومحلي أم يبدو مترجماً من الإنجليزية؟
- هل الافتتاحية محددة وقوية أم عامة وفارغة؟
- هل المصطلحات الرسمية صحيحة؟ (أبرز الأخطاء الشائعة أدناه)
- هل الجمل قصيرة وذات إيقاع؟ أم ثقيلة ومطولة؟

المصطلحات الشائعة الخاطئة — صحّح فوراً إن وجدت:
- وزارة القوى العاملة ← وزارة العمل
- إذن العمل / ورقة العمل ← تصريح العمل
- PASI / هيئة التأمين الاجتماعي ← صندوق الحماية الاجتماعية (SPF)
- توطين العمالة / التعُّمن ← التعمين
- الإقامة / الفيزا ← تأشيرة الإقامة
- نظام الرواتب الحكومي ← نظام حماية الأجور (WPS)
- مكافأة نهاية الخدمة ← مخصص نهاية الخدمة

ما تصلحه فقط:
- استبدل المصطلحات الخاطئة بالمصطلحات الرسمية الصحيحة
- خفّف الأسلوب المترجم: جمل طويلة مركبة، أنماط "إنه ليس فقط X بل Y"، مبالغة في التوصيف
- التزم بالعربية الفصحى المبسطة طوال النص. حوّل أي لفظ عامي إلى مقابله الفصيح فوراً:
  وايد ← كثير ، مو ← ليس ، ما في ← لا يوجد ، الحين ← الآن ، وين ← أين ، اللي ← الذي/التي ،
  خلاص/عاد/عيل ← (احذفها أو أعد الصياغة بالفصحى) ، بس ← لكن/فقط ، زين ← جيد ، ايش/شو ← ماذا
- اجعل كل فقرة لا تتجاوز ٣ أسطر

ما لا تلمسه:
- الهاشتاقات — احفظها كما هي تماماً
- الأرقام والإحصاءات — لا تعدّلها
- الروابط والـ URLs — احفظها كما هي
- الجوهر والرسالة الأساسية للمنشور

الحد الحرفي: أبقِ النص في نطاق ±١٥٪ من طوله الأصلي.
أخرج نص المنشور النهائي فقط. لا شرح، لا مقدمة، لا تعليق."""

_USER_TEMPLATE = """Humanize this LinkedIn post. Tone: {tone}. Pillar: {pillar}.

{text}"""

_USER_TEMPLATE_AR = """حسّن هذا المنشور. النبرة: {tone}. المحور: {pillar}.

{text}"""


def humanize(text: str, pillar: str = "", tone: str = "") -> str:
    """Remove AI-writing patterns from a LinkedIn post. Falls back to original on any failure."""
    original_len = len(text)
    is_arabic = pillar in _ARABIC_PILLARS
    system   = HUMANIZER_SYSTEM_AR if is_arabic else HUMANIZER_SYSTEM
    template = _USER_TEMPLATE_AR   if is_arabic else _USER_TEMPLATE
    try:
        client = anthropic.Anthropic()
        model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{
                "role": "user",
                "content": template.format(tone=tone, pillar=pillar, text=text),
            }],
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]
        if not text_blocks:
            print("humanizer: SKIP - empty response")
            return text

        result = text_blocks[0].strip()

        if len(result) < MIN_OUTPUT_CHARS:
            print(f"humanizer: SKIP - output too short ({len(result)} chars)")
            return text

        lang_tag = "ar" if is_arabic else "en"
        print(f"humanizer[{lang_tag}]: OK ({original_len} → {len(result)} chars)")
        return result

    except Exception as exc:
        print(f"humanizer: SKIP - {exc}")
        return text


if __name__ == "__main__":
    sample = """In today's fast-paced business environment, it's crucial for HR managers to leverage innovative solutions that serve as a testament to organizational excellence.

The system. The tool. The platform. It's not just software — it's a transformative approach to workforce management that underscores the importance of seamless integration.

By highlighting key performance indicators and showcasing groundbreaking features, SmartPRO Hub contributes to a more intuitive experience for all stakeholders.

The future looks bright for Oman businesses ready to embark on this journey.

#HRManagement #Oman #SmartPro"""

    print("=== ORIGINAL ===")
    print(sample)
    print("\n=== HUMANIZED ===")
    result = humanize(sample, pillar="pain", tone="direct, empathetic")
    print(result)
