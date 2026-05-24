"""Omani Arabic terminology glossary — single source of truth for the full project.

Two layers:
  OFFICIAL_TERMS  — correct Omani government/legal/HR terminology with wrong
                    alternatives to catch and reject at generation time.
  OMANI_VOICE     — authentic Omani/Gulf dialect expressions that make posts
                    sound locally written, not translated.

Public API:
  build_terminology_block() -> str   inject into Arabic system prompts
  build_voice_block()        -> str   inject into Arabic system prompts
  validate_arabic_terms(text)-> str|None  warn if wrong alternatives detected
"""

# ---------------------------------------------------------------------------
# Layer 1 — Official / Formal / Legal terms
# Keys   = correct Omani government term
# wrong  = alternatives the model must never produce
# abbr   = common abbreviation (injected beside the term)
# note   = short explanation shown in the prompt
# ---------------------------------------------------------------------------
OFFICIAL_TERMS: dict[str, dict] = {

    # ── Government bodies ──────────────────────────────────────────────────
    "وزارة العمل": {
        "wrong": [
            "وزارة القوى العاملة",
            "وزارة الموارد البشرية",
            "الجهة الحكومية",
            "الوزارة المعنية",
        ],
        "category": "government",
        "note": "سُمّيت سابقاً وزارة القوى العاملة — الاسم الرسمي الحالي منذ 2020",
    },
    "صندوق الحماية الاجتماعية": {
        "wrong": [
            "PASI",
            "هيئة التأمين الاجتماعي",
            "التأمينات الاجتماعية",
            "الهيئة العامة للتأمين الاجتماعي",
        ],
        "category": "government",
        "abbr": "SPF",
        "note": "خلف هيئة التأمين الاجتماعي PASI",
    },
    "هيئة الوضع المدني": {
        "wrong": [
            "الأحوال المدنية",
            "إدارة الجوازات",
            "مكتب الجوازات",
        ],
        "category": "government",
    },
    "هيئة تنمية الموارد البشرية": {
        "wrong": [
            "تنمية الموارد البشرية",
            "هيئة التشغيل",
            "مركز التوظيف",
        ],
        "category": "government",
        "abbr": "HRDF",
        "note": "تُعرف أيضاً بـ Tanmia",
    },
    "البنك المركزي العُماني": {
        "wrong": [
            "مؤسسة النقد العُماني",
            "المصرف المركزي",
        ],
        "category": "government",
        "abbr": "CBO",
    },
    "الشرطة العُمانية": {
        "wrong": [
            "الشرطة فقط",
            "القوات الأمنية",
            "جهاز الشرطة",
        ],
        "category": "government",
    },
    "المركز الوطني للإحصاء والمعلومات": {
        "wrong": [
            "الجهاز المركزي للتخطيط",
            "مكتب الإحصاء",
            "هيئة الإحصاء",
        ],
        "category": "government",
        "abbr": "NCSI",
    },

    # ── Payroll & payments ─────────────────────────────────────────────────
    "نظام حماية الأجور": {
        "wrong": [
            "نظام الرواتب الحكومي",
            "نظام الأجور الإلكتروني",
            "بوابة الرواتب",
            "نظام صرف الرواتب",
        ],
        "category": "payroll",
        "abbr": "WPS",
    },
    "مخصص نهاية الخدمة": {
        "wrong": [
            "مكافأة نهاية الخدمة",
            "راتب الفصل",
            "تعويض نهاية الخدمة",
            "مكافأة الخروج",
        ],
        "category": "payroll",
    },
    "كشف الرواتب": {
        "wrong": [
            "قسيمة الراتب",
            "إيصال الراتب",
            "ورقة الراتب",
        ],
        "category": "payroll",
    },
    "الراتب الأساسي": {
        "wrong": [
            "الراتب القاعدي",
            "الأجر الأساسي",
            "الراتب الثابت",
        ],
        "category": "payroll",
    },
    "بدل السكن": {
        "wrong": [
            "علاوة السكن",
            "مساعدة السكن",
            "إعانة الإيجار",
        ],
        "category": "payroll",
    },
    "بدل النقل": {
        "wrong": [
            "علاوة النقل",
            "مصاريف المواصلات",
            "بدل المواصلات",
        ],
        "category": "payroll",
    },
    "الاستقطاعات": {
        "wrong": [
            "الخصومات",
            "المقتطعات",
        ],
        "category": "payroll",
        "note": "المصطلح المالي الرسمي في عُمان",
    },

    # ── Permits & visas ────────────────────────────────────────────────────
    "تصريح العمل": {
        "wrong": [
            "إذن العمل",
            "ورقة العمل",
            "وثيقة التشغيل",
            "تصريح التشغيل",
        ],
        "category": "permits",
    },
    "تصريح الاستقدام": {
        "wrong": [
            "تأشيرة الاستقدام",
            "موافقة الاستقدام",
            "إذن الاستقدام",
        ],
        "category": "permits",
    },
    "تأشيرة الإقامة": {
        "wrong": [
            "الإقامة فقط",
            "الفيزا",
            "تصريح الإقامة",
            "وثيقة الإقامة",
        ],
        "category": "permits",
    },
    "تأشيرة الزيارة": {
        "wrong": [
            "فيزا الزيارة",
            "تصريح الزيارة",
            "تأشيرة السياحة",
        ],
        "category": "permits",
    },
    "بطاقة الإقامة": {
        "wrong": [
            "هوية المقيم",
            "بطاقة الهوية للأجانب",
            "وثيقة الإقامة",
        ],
        "category": "permits",
    },

    # ── Workforce & Omanization ────────────────────────────────────────────
    "التعمين": {
        "wrong": [
            "توطين العمالة",
            "توظيف العُمانيين",
            "التعُّمن",
            "الأعمنة",
            "التوطين",
        ],
        "category": "workforce",
    },
    "نسبة التعمين": {
        "wrong": [
            "نسبة التوطين",
            "معدل التعمين",
            "حصة العُمانيين",
            "نسبة الوطنيين",
        ],
        "category": "workforce",
    },
    "العمالة الوافدة": {
        "wrong": [
            "العمالة الأجنبية",
            "الموظفون الأجانب",
            "غير العُمانيين",
            "العمال الوافدون",
        ],
        "category": "workforce",
    },
    "خطة التعمين": {
        "wrong": [
            "خطة التوطين",
            "برنامج التوظيف الوطني",
            "مبادرة التعمين",
        ],
        "category": "workforce",
    },

    # ── HR & leave ─────────────────────────────────────────────────────────
    "رصيد الإجازة": {
        "wrong": [
            "أيام الإجازة المتبقية",
            "الإجازة المتراكمة",
            "باقي الإجازات",
        ],
        "category": "hr",
    },
    "الإجازة السنوية": {
        "wrong": [
            "إجازة العمل",
            "الإجازة الرسمية",
            "العطلة السنوية",
            "إجازة الراحة",
        ],
        "category": "hr",
    },
    "الإجازة المرضية": {
        "wrong": [
            "إجازة المرض",
            "غياب مرضي",
            "إجازة صحية",
        ],
        "category": "hr",
    },
    "إجازة الأمومة": {
        "wrong": [
            "إجازة الولادة للمرأة",
            "إجازة الحمل",
            "إجازة الوضع",
        ],
        "category": "hr",
    },
    "إجازة الأبوة": {
        "wrong": [
            "إجازة ولادة الرجل",
            "إجازة الأب",
            "إجازة الولادة للرجل",
        ],
        "category": "hr",
    },
    "سجل الحضور والانصراف": {
        "wrong": [
            "بصمة الحضور",
            "سجل الدوام",
            "ورقة الحضور",
        ],
        "category": "hr",
    },
    "ساعات العمل الإضافية": {
        "wrong": [
            "الأوفر تايم",
            "الساعات الزائدة",
            "العمل الإضافي الزائد",
        ],
        "category": "hr",
    },
    "الهيكل التنظيمي": {
        "wrong": [
            "الهيكل الإداري",
            "مخطط التنظيم",
            "شجرة الموظفين",
        ],
        "category": "hr",
    },

    # ── Business & legal ────────────────────────────────────────────────────
    "السجل التجاري": {
        "wrong": [
            "تسجيل الشركة",
            "شهادة التسجيل التجاري",
            "وثيقة تأسيس الشركة",
        ],
        "category": "legal",
    },
    "الرخصة التجارية": {
        "wrong": [
            "ترخيص العمل",
            "إذن التجارة",
            "شهادة النشاط التجاري",
        ],
        "category": "legal",
    },
    "عقد العمل": {
        "wrong": [
            "اتفاقية العمل",
            "وثيقة التوظيف",
            "ورقة التوظيف",
        ],
        "category": "legal",
    },
    "النظام الأساسي للشركة": {
        "wrong": [
            "عقد التأسيس",
            "لائحة الشركة",
            "وثيقة تأسيس الشركة",
        ],
        "category": "legal",
    },
    "الشركة ذات المسؤولية المحدودة": {
        "wrong": [
            "الشركة المحدودة",
            "الشركة الخاصة",
        ],
        "category": "legal",
        "abbr": "LLC",
    },

    # ── Sanad-specific ─────────────────────────────────────────────────────
    "مكتب سند المرخَّص": {
        "wrong": [
            "مكتب الخدمات",
            "مكتب المعاملات",
            "مكتب PRO",
            "مكتب الاستشارات الحكومية",
        ],
        "category": "sanad",
    },
    "خدمات سند": {
        "wrong": [
            "خدمات PRO",
            "خدمات التأشيرات فقط",
            "خدمات المعاملات الحكومية",
        ],
        "category": "sanad",
    },
    "SmartPro Hub": {
        "wrong": [
            "نظام سمارت برو",
            "برنامج سمارت برو",
            "تطبيق سند",
        ],
        "category": "sanad",
        "note": "الاسم الرسمي للمنصة — لا تترجمه",
    },
}


# ---------------------------------------------------------------------------
# Layer 2 — Omani / Gulf dialect voice expressions
# key   = the dialect word/phrase
# value = usage note (Arabic) — shown in system prompt as guidance
# ---------------------------------------------------------------------------
OMANI_VOICE: dict[str, str] = {
    "وايد":     "بمعنى 'جداً' أو 'كثير' — أقوى وأكثر خليجية من 'جداً'",
    "عاد":      "أداة خطاب محادثاتية: 'تعرف'، 'يعني'، 'بعدين' — تُضفي طابعاً طبيعياً",
    "خلاص":     "للإشارة إلى الإنجاز والتسوية — 'خلاص، الأمر محسوم' أقوى من 'انتهى'",
    "ما يصير":  "هذا لا يمكن / غير مقبول — أكثر مباشرةً وعُمانيةً من 'لا يمكن'",
    "شايل":     "يحمل / يتعامل مع — 'شايل شغل' = مثقل بالأعباء، مألوفة جداً",
    "الحين":    "الآن / في هذه اللحظة — خليجي وعُماني بامتياز، أسرع وقعاً من 'الآن'",
    "تعبان":    "يُعاني / مثقل — يُستخدم للأشخاص والأنظمة: 'الإكسل تعبان' يفهمها الجميع",
    "زين":      "جيد / حسناً / موافق — تأكيد محادثاتي أصيل في الخليج وعُمان",
    "بس":       "فقط / لكن — متعددة المعاني، تُوقف الجملة أو تُعطيها تحفظاً: 'بس ما في تنبيه'",
    "مو":       "ليس / لا — نفي مباشر وقوي: 'مو المشكلة في التنظيم' أقوى من 'ليست'",
    "والله":    "للتأكيد الحقيقي — ليست دائماً دينية، تعني 'صدقاً': 'والله ما أدري وين الملف'",
    "يلا":      "هيا / تمام / إذن — للانتقال أو الحث على الفعل في خاتمة المنشور",
    "بعدين":    "لاحقاً / ثم — أقوى من 'بعد ذلك' في السياق السردي المتسارع",
    "صح":       "صحيح / تماماً — تأكيد سريع ومحادثاتي أكثر من 'صحيح'",
    "عيل":      "إذن / إذاً — رابط نتيجة طبيعي: 'عيل شو الحل؟' يدفع للتعليق",
    "شوي":      "قليلاً / تدريجياً — 'شوي شوي' = بدون تسرع، مألوفة في وصف التحسن",
    "ودّي":     "أريد / أودّ — أكثر ليونةً من 'أريد'، تُناسب اقتراح الحلول",
    "ما أدري":  "لا أعرف — أكثر صدقاً وأقل رسميةً، تُناسب الاعتراف بالغموض",
}


# ---------------------------------------------------------------------------
# Category labels (Arabic) — used when building the terminology block
# ---------------------------------------------------------------------------
_CATEGORY_LABELS: dict[str, str] = {
    "government": "الجهات الحكومية الرسمية",
    "payroll":    "الرواتب والمدفوعات",
    "permits":    "التصاريح والتأشيرات",
    "workforce":  "العمالة والتعمين",
    "hr":         "الموارد البشرية والإجازات",
    "legal":      "التجاري والقانوني",
    "sanad":      "مكاتب سند وSmartPro",
}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def build_terminology_block() -> str:
    """Return a formatted Arabic terminology section for injection into system prompts."""
    by_cat: dict[str, list[tuple[str, dict]]] = {}
    for term, info in OFFICIAL_TERMS.items():
        cat = info.get("category", "other")
        by_cat.setdefault(cat, []).append((term, info))

    lines = [
        "المصطلحات الرسمية — استخدم هذه الأسماء دائماً ورفض بدائلها الخاطئة:",
    ]
    for cat_key, label in _CATEGORY_LABELS.items():
        if cat_key not in by_cat:
            continue
        lines.append(f"\n{label}:")
        for term, info in by_cat[cat_key]:
            wrong = info.get("wrong", [])
            abbr  = info.get("abbr", "")
            note  = info.get("note", "")
            display = f"- {term}"
            if abbr:
                display += f" — {abbr}"
            if wrong:
                display += f"\n  وليس: {' / '.join(wrong[:3])}"
            if note:
                display += f"\n  ↳ {note}"
            lines.append(display)
    lines.append(
        "\nاستخدام المصطلح الرسمي الصحيح يُثبت أنك تعرف النظام من الداخل — "
        "الخطأ يُفقد المنشور المصداقية فوراً."
    )
    return "\n".join(lines)


def build_voice_block() -> str:
    """Return a formatted dialect voice section for injection into Arabic system prompts."""
    lines = [
        "عبارات عُمانية وخليجية أصيلة — استخدمها بجرعة مناسبة (٢-٣ عبارات كحد أقصى) "
        "لتُضفي طابعاً محلياً حقيقياً بدلاً من الأسلوب المترجم:",
    ]
    for word, meaning in OMANI_VOICE.items():
        lines.append(f"- {word}: {meaning}")
    return "\n".join(lines)


def validate_arabic_terms(text: str) -> str | None:
    """Scan post text for incorrect term alternatives.

    Returns a warning string (Arabic) describing the violations, or None if clean.
    Caps at 3 violations to keep the warning readable.
    """
    found: list[str] = []
    for correct, info in OFFICIAL_TERMS.items():
        for wrong in info.get("wrong", []):
            # Exact substring match — sufficient for LinkedIn post body text.
            # Skip very short wrong-terms (≤2 chars) to avoid false positives.
            if len(wrong) <= 2:
                continue
            if wrong in text:
                found.append(f"'{wrong}' ← يجب أن تكون '{correct}'")
        if len(found) >= 3:
            break
    if not found:
        return None
    return "مصطلح خاطئ: " + " ؛ ".join(found)


if __name__ == "__main__":
    print("=== Terminology block ===\n")
    print(build_terminology_block())
    print("\n\n=== Voice block ===\n")
    print(build_voice_block())
    print("\n\n=== Validation test ===")
    sample = "تواصلت مع وزارة القوى العاملة بخصوص إذن العمل الجديد."
    result = validate_arabic_terms(sample)
    print(f"Input:  {sample}")
    print(f"Result: {result}")
