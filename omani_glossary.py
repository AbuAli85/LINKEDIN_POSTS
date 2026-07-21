"""Omani Arabic terminology glossary — single source of truth for the full project.

Two layers:
  OFFICIAL_TERMS  — correct Omani government/legal/HR terminology with wrong
                    alternatives to catch and reject at generation time.
  DIALECT_TO_FORMAL — colloquial words to avoid, each mapped to its formal
                    Modern Standard Arabic replacement, so posts stay formal
                    and professional (فصحى مبسطة), never colloquial.

Public API:
  build_terminology_block()    -> str   inject into Arabic system prompts
  build_voice_block()          -> str   formal-register guidance for the prompt
  validate_arabic_terms(text)  -> str|None  warn if wrong terminology detected
  validate_arabic_register(text) -> str|None  warn if colloquial/dialect detected
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
            "مكتب السند",
            "مكاتب السند",
        ],
        "category": "sanad",
        "note": "سند اسم علم للبرنامج — 'مكتب سند' و'مكاتب سند' بلا 'ال' التعريف",
    },
    "خدمات سند": {
        "wrong": [
            "خدمات PRO",
            "خدمات التأشيرات فقط",
            "خدمات المعاملات الحكومية",
        ],
        "category": "sanad",
    },
    "SmartPRO Hub": {
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
# Layer 2 — Register control: keep Arabic in FORMAL Modern Standard Arabic
# key   = colloquial / dialect word or phrase that must NOT appear in posts
# value = (formal_replacement, short Arabic note for the prompt)
#
# The audience is business owners and managers; LinkedIn is a professional
# register. Posts must read as polished فصحى مبسطة — natural and readable, but
# never colloquial. This map is injected into the prompt as "avoid X, use Y"
# guidance AND used by validate_arabic_register() to catch slips at generation.
# ---------------------------------------------------------------------------
DIALECT_TO_FORMAL: dict[str, tuple[str, str]] = {
    "وايد":    ("كثير / كثيراً",        "عامية خليجية لـ'كثير'"),
    "مو":      ("ليس / ليست",           "نفي عامي — استخدم 'ليس/ليست/لا'"),
    "ما في":   ("لا يوجد",              "نفي عامي — استخدم 'لا يوجد/ليس هناك'"),
    "الحين":   ("الآن",                 "عامية لـ'الآن'"),
    "وين":     ("أين",                  "عامية لـ'أين'"),
    "اللي":    ("الذي / التي / الذين",  "موصول عامي — استخدم 'الذي/التي/الذين'"),
    "خلاص":    ("(احذفها)",             "حشو عامي — احذفها أو استبدلها بجملة فصيحة"),
    "عاد":     ("(احذفها)",             "أداة خطاب عامية — احذفها"),
    "عيل":     ("إذن",                  "عامية عُمانية لـ'إذن'"),
    "بس":      ("لكن / فقط",            "عامية — استخدم 'لكن' أو 'فقط'"),
    "زين":     ("جيد / حسناً",          "عامية لـ'جيد'"),
    "تعبان":   ("مرهق / متعثّر",         "عامية — للأنظمة استخدم 'متعثّر/غير كفؤ'"),
    "شايل":    ("يحمل / يتحمّل",         "عامية لـ'يحمل العبء'"),
    "يجي":     ("يأتي",                 "عامية لـ'يأتي'"),
    "يجيك":    ("يأتيك / يصلك",         "عامية لـ'يأتيك'"),
    "تشوف":    ("ترى",                  "عامية لـ'ترى'"),
    "تدوّر":   ("تبحث",                 "عامية لـ'تبحث'"),
    "سويت":    ("فعلت / أنجزت",         "عامية لـ'فعلت'"),
    "ايش":     ("ماذا / ما",            "عامية لـ'ماذا'"),
    "شو":      ("ماذا / ما",            "عامية لـ'ماذا'"),
    "ودّي":    ("أودّ / أرغب",          "عامية لـ'أودّ'"),
    "ما أدري": ("لا أعرف",              "عامية لـ'لا أعرف'"),
    "ما درّيت":("لم أعلم",              "عامية لـ'لم أعلم'"),
    "يلا":     ("(احذفها) / إذن",       "عامية — احذفها"),
    "بعدين":   ("بعد ذلك / ثم",         "عامية لـ'ثم'"),
    "ردّيت":   ("أجبت / رددت",          "عامية لـ'أجبت'"),
    "ما رديت": ("لم أجب",               "عامية لـ'لم أجب'"),
    "جروب":    ("مجموعة",               "دخيلة — استخدم 'مجموعة'"),
    "ما يصير": ("لا يصحّ / لا يجوز",     "عامية لـ'لا يصحّ'"),
    "عشان":    ("لأن / كي",             "عامية لـ'لأنّ/كي'"),
    "علشان":   ("لأن / كي",             "عامية لـ'لأنّ/كي'"),
    "ليش":     ("لماذا",                "عامية لـ'لماذا'"),
    "أشوف":    ("أرى",                  "عامية لـ'أرى'"),
    "نشوف":    ("نرى",                  "عامية لـ'نرى'"),
    "شفت":     ("رأيت",                 "عامية لـ'رأيت'"),
    "شاف":     ("رأى",                  "عامية لـ'رأى'"),
    "شافت":    ("رأت",                  "عامية لـ'رأت'"),
    "يجيني":   ("يصلني / يأتيني",       "عامية لـ'يصلني'"),
    "شوي":     ("قليلاً",               "عامية لـ'قليلاً'"),
    "تروح":    ("تذهب / تضيع",          "عامية لـ'تذهب'"),
    "نروح":    ("نذهب",                 "عامية لـ'نذهب'"),
    "يبغى":    ("يريد",                 "عامية لـ'يريد'"),
    "يبي":     ("يريد",                 "عامية لـ'يريد'"),
}

# Dialect words that are HOMOGRAPHS of legitimate formal words — kept in the
# prompt guidance above, but excluded from validate_arabic_register() so they
# never trigger a false-positive regeneration:
#   عاد (formal: "returned")   زين (formal: a proper name / "adorned")
_REGISTER_SKIP: frozenset[str] = frozenset({"عاد", "زين"})

# All dialect keys (for prompt guidance / external callers).
DIALECT_WORDS: tuple[str, ...] = tuple(DIALECT_TO_FORMAL.keys())


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
    """Return the FORMAL-register guidance block for Arabic system prompts.

    The post must be polished Modern Standard Arabic (فصحى مبسطة): natural and
    readable, but never colloquial. This block lists the dialect words to avoid
    and the formal word to use instead.
    """
    lines = [
        "السجل اللغوي — التزم بالعربية الفصحى المبسطة طوال المنشور:",
        "- اكتب بفصحى احترافية واضحة تناسب جمهور الأعمال على LinkedIn — مفهومة بلا جهد، لكنها ليست عامية إطلاقاً.",
        "- ممنوع منعاً باتاً أي لفظ من اللهجة العامية أو الخليجية. استبدل كل عامية بمقابلها الفصيح:",
    ]
    for word, (formal, _note) in DIALECT_TO_FORMAL.items():
        lines.append(f"- ❌ {word}  ←  ✅ {formal}")
    lines.append(
        "- النفي بالفصحى: 'ليس/ليست/لا يوجد' لا 'مو/ما في'. "
        "الاستفهام بالفصحى: 'أين/ماذا/كيف' لا 'وين/ايش/شو'. "
        "الموصول 'الذي/التي/الذين' لا 'اللي'."
    )
    lines.append(
        "- ابقَ ودوداً ومباشراً دون تكلّف أكاديمي — الفصحى المبسطة، لا المعجمية الجافة."
    )
    return "\n".join(lines)


def validate_arabic_register(text: str) -> str | None:
    """Scan post text for colloquial/dialect words that break the formal register.

    Returns a warning string (Arabic) listing the violations with their formal
    replacements, or None if the text is clean. Caps at 5 to stay readable.
    Uses whitespace/punctuation boundaries so short words don't false-match
    inside longer formal words (e.g. 'بس' must not trip on 'بسبب').
    """
    import re

    found: list[str] = []
    for dialect, (formal, _note) in DIALECT_TO_FORMAL.items():
        if dialect in _REGISTER_SKIP:
            continue
        # Arabic word boundaries on both ends: the match must not be glued to
        # another Arabic letter. This stops 'بس' matching 'بسبب', 'مو' matching
        # 'موظف', or 'ما في' matching 'كما في'. Works for single words and
        # multi-word phrases alike.
        pattern = rf"(?<![ء-ي]){re.escape(dialect)}(?![ء-ي])"
        if re.search(pattern, text):
            found.append(f"'{dialect}' ← استخدم '{formal}'")
        if len(found) >= 5:
            break
    if not found:
        return None
    return "لهجة عامية (يجب أن يكون المنشور بالفصحى): " + " ؛ ".join(found)


def validate_arabic_terms(text: str) -> str | None:
    """Scan post text for incorrect term alternatives.

    Returns a warning string (Arabic) describing the violations, or None if clean.
    Caps at 3 violations to keep the warning readable.
    """
    found: list[str] = []
    # Mask out every correct term first. A "wrong" alternative that happens to
    # be a substring/prefix of its own correct term (e.g. wrong "إجازة الأب"
    # is a prefix of correct "إجازة الأبوة") would otherwise false-positive
    # against text that actually used the correct term.
    masked = text
    for correct in OFFICIAL_TERMS:
        masked = masked.replace(correct, " " * len(correct))
    for correct, info in OFFICIAL_TERMS.items():
        for wrong in info.get("wrong", []):
            # Exact substring match — sufficient for LinkedIn post body text.
            # Skip very short wrong-terms (≤2 chars) to avoid false positives.
            if len(wrong) <= 2:
                continue
            if wrong in masked:
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
