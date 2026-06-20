"""Content strategy: SmartPro Hub COMPANY PAGE — third-person, brand-led voice.

Mirrors the surface area of `content_strategy.py` so the same generator
and main entrypoints can swap modules via LINKEDIN_AUDIENCE=company.

VOICE GUIDELINES for company posts:
  - Third person — "SmartPro Hub helps...", "Our team built...", "Customers tell us..."
  - Brand-led, never first-person founder voice
  - More formal than personal posts but still concrete and example-driven
  - Always tie back to a specific product capability or customer outcome
  - Avoid 'I' / 'me' — use 'we' or 'SmartPro' or 'our customers'

NOTE: This file is a SCAFFOLD. Pillars, formats, and topic lists below
are starting points — refine them with real product context before
enabling the company workflow on a schedule. Marked TODO sections need
your input.
"""

import json
from pathlib import Path

BRAND_URL = "www.thesmartpro.io"

# ── CTAs — third-person, demo-first, jobs-board for hiring posts ─────────────
COMPANY_CTA = (
    "See SmartPro Hub in action — book a 30-minute demo at www.thesmartpro.io"
)
COMPANY_CTA_AR = (
    "شاهد SmartPro Hub أثناء العمل — احجز عرضاً تجريبياً مدته ٣٠ دقيقة على www.thesmartpro.io"
)
PARTNER_CTA = (
    "Sanad offices, accountants, and HR consultancies: "
    "partner with SmartPro Hub — www.thesmartpro.io/partners"
)
JOBS_CTA = (
    "Browse open roles at SmartPro Hub — www.thesmartpro.io/careers"
)

# UTM-tracked variants the generator uses (template; {campaign} filled in)
CTA_DEMO = (
    "Book a 30-minute demo: "
    "https://www.thesmartpro.io/demo"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
)
CTA_DEMO_AR = (
    "احجز عرضاً تجريبياً مدته ٣٠ دقيقة: "
    "https://www.thesmartpro.io/demo"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
)
# Feasibility Studio — free AI feasibility-study generator (lead magnet).
# Used via a pillar's "cta" override (see _cta_block in generator.py).
CTA_FEASIBILITY = (
    "Build a bank-ready feasibility study free in ~10 minutes — covers all 10 "
    "Development Bank Oman / Riyada programs: "
    "https://www.thesmartpro.io/feasibility-studio"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
)
CTA_FEASIBILITY_AR = (
    "أنشئ دراسة جدوى جاهزة للبنك مجاناً خلال ١٠ دقائق — تغطّي جميع برامج بنك "
    "التنمية العُماني/ريادة العشرة: "
    "https://www.thesmartpro.io/feasibility-studio"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
)
CTA_INVESTORS = (
    "Investor and partnership inquiries: "
    "https://www.thesmartpro.io/investors"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
)
CTA_INVESTORS_AR = (
    "للاستفسارات الاستثمارية والشراكات: "
    "https://www.thesmartpro.io/investors"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
)
CTA_TECH = (
    "SmartPro Hub for early adopters — OMR 12/month, 14-day free trial: "
    "https://www.thesmartpro.io"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
)

# ── Hashtag sets per segment ─────────────────────────────────────────────────
# Company page leans harder on product + market hashtags than personal does.
HASHTAGS: dict[str, list[str]] = {
    "A": [
        "#SmartPROHub", "#OmanBusiness", "#HRTech", "#PayrollOman",
        "#WPS", "#Omanization", "#GCCBusiness", "#SMEOman",
    ],
    "B": [
        "#SmartPROHub", "#OmanVision2040", "#GCCBusiness", "#HRTech",
        "#SMEOman", "#BusinessGrowth", "#Oman", "#DigitalTransformation",
    ],
    "C": [
        "#SmartPROHub", "#SaaS", "#GCCTech", "#OmanTech", "#BuildInPublic",
        "#HRSaaS", "#ProductLaunch",
    ],
}

# ── SEO keywords ─────────────────────────────────────────────────────────────
SEO_KEYWORDS: list[str] = [
    "SmartPro Hub",
    "HR software Oman",
    "WPS payroll Oman",
    "Sanad office management software",
    "PRO services automation Oman",
    "work permit tracking GCC",
    "Omanization compliance software",
    "Ministry of Labour Oman compliance",
    "SME business operations platform Oman",
    "client portal for service businesses Oman",
]

# ── Brand context (system-prompt foundation) ────────────────────────────────
_COMPANY_BRAND_CONTEXT = (
    "BRAND CONTEXT: You are writing as the SmartPro Hub company page. "
    "Use third-person, brand-led voice — 'SmartPro Hub helps...', 'Our customers...', "
    "'We built this because...'. NEVER use first-person founder voice ('I think', 'when I started'). "
    "\n\nSmartPro Hub is the enterprise operations platform built exclusively for Oman and GCC businesses. "
    "Capabilities: CRM with deal pipeline and quotations, white-label client portal, HR and workforce management, "
    "WPS payroll with direct bank integration, SPF (Social Protection Fund) and Omanization compliance, "
    "Ministry of Labour government filings, Sanad office management, PRO services workflow, "
    "work permit and visa tracking, e-signature contracts, automated invoicing, growth partner program. "
    "\n\nReplaces WhatsApp groups, spreadsheets, and fragmented vendor systems with one connected platform. "
    "Bilingual Arabic and English. "
    "Pricing: Starter OMR 12/month, Business OMR 25/month, Enterprise OMR 60/month. 14-day free trial, no credit card. "
    "Target buyers: business owners, HR managers, finance managers, ops directors at Oman and GCC companies "
    "with 10–500 employees, PRO service firms, staffing agencies, Sanad offices. "
    f"\n\nWebsite: {BRAND_URL}. "
    f"End every post with this CTA on its own line: {COMPANY_CTA}"
)

# Feasibility pillar uses a single CTA — the tracked feasibility link injected by
# _cta_block. Drop the default demo sign-off so these posts don't carry two CTAs.
_COMPANY_BRAND_CONTEXT_FEASIBILITY = _COMPANY_BRAND_CONTEXT.replace(
    f"End every post with this CTA on its own line: {COMPANY_CTA}",
    "End every post with the exact tracked CTA provided below on its own line. "
    "Do not add any other call-to-action, demo link, phone number, or WhatsApp number.",
)

_COMPANY_BRAND_CONTEXT_AR = (
    "سياق العلامة التجارية: أنت تكتب باسم صفحة شركة SmartPro Hub. "
    "استخدم صيغة الغائب وصوت العلامة التجارية — 'SmartPro Hub تساعد...'، 'عملاؤنا...'، 'نحن بنينا هذا لأن...'. "
    "لا تستخدم أبداً صيغة المتكلم الفردي. "
    "\n\nSmartPro Hub هي منصة العمليات المتكاملة المصممة خصيصاً لشركات عُمان ودول الخليج. "
    "تجمع في نظام واحد: إدارة علاقات العملاء، بوابة العملاء، الموارد البشرية، رواتب WPS، "
    "الامتثال لصندوق الحماية الاجتماعية ونسب التعمين، تسجيلات وزارة العمل، إدارة مكاتب سند وخدمات PRO، "
    "تتبع تصاريح العمل والتأشيرات، إدارة العقود بالتوقيع الإلكتروني، إصدار الفواتير التلقائي. "
    f"\n\nالموقع الإلكتروني: {BRAND_URL}. "
    f"أنهِ كل منشور بهذه الدعوة للتصرف: {COMPANY_CTA_AR}"
)

# ── PILLARS ──────────────────────────────────────────────────────────────────
# Five pillars — three on schedule, two manual-only.
# Schedule: company workflow generates 06:30 UTC, publishes 07:15 UTC.
#   Mon publish: product_proof   (generate Saturday)
#   Wed publish: feature_spotlight (generate Monday)
#   Fri publish: oman_market     (generate Wednesday)
#   Manual:      hiring, partnership
PILLARS = {
    # ── PRODUCT_PROOF ────────────────────────────────────────────────────────
    "product_proof": {
        "weight":           3.0,
        "segment":          "A",
        "post_type":        ["Data/Insight", "Social Proof/Milestone"],
        "day":              "Monday",
        "weekday":          0,
        "generate_weekday": 5,
        "publish_day":      "Monday",
        "generate_day":     "Saturday",
        "tone":             "concrete, data-driven, brand-led — specific customer outcomes, no vague claims",
        "audience":         "business owners and operations leaders evaluating HR/PRO platforms",
        "brand_context":    _COMPANY_BRAND_CONTEXT,
        "formats": [
            "Lead with a specific customer outcome — time saved, errors eliminated, hours recovered — then describe what changed",
            "Before/after of a single workflow: same task, two completely different experiences",
            "Tight case study: company profile, problem, what changed, the one number that proves it worked",
            "Open with a SmartPro Hub product capability, then show the real-world business outcome it enables",
        ],
        "topics": [
            # TODO: refine with real customer outcomes once 3-5 case studies are documented
            "How one Oman retail company cut payroll prep from three days to two hours after switching to WPS-integrated payroll",
            "A Sanad office in Muscat moved 40 client work permits off WhatsApp — no missed renewals in six months",
            "What zero WPS rejections in twelve months actually means for a 200-person business",
            "A PRO services firm scaled from 15 to 60 client companies without adding admin headcount",
            "How a multi-branch operation manages payroll for four locations from one screen",
            "End-of-service calculations that used to take a spreadsheet morning now run in seconds",
            "The HR manager who finally stopped processing leave requests on WhatsApp — what changed in week one",
            "From three disconnected systems to one platform — what the first 30 days of transition look like",
        ],
    },

    # ── FEATURE_SPOTLIGHT ────────────────────────────────────────────────────
    "feature_spotlight": {
        "weight":           2.5,
        "segment":          "A",
        "post_type":        ["Educational/Tip", "Data/Insight"],
        "day":              "Wednesday",
        "weekday":          2,
        "generate_weekday": 0,
        "publish_day":      "Wednesday",
        "generate_day":     "Monday",
        "tone":             "educational, specific, useful — explain a capability through the problem it solves",
        "audience":         "HR managers, ops directors, business owners researching solutions",
        "brand_context":    _COMPANY_BRAND_CONTEXT,
        "formats": [
            "Open with the specific operational problem, then show how one SmartPro Hub feature addresses it end-to-end",
            "Walk through a feature in 4-5 steps: what triggers it, what it does, what it prevents, who saves time",
            "Compare 'how most Oman businesses do X today' with 'how SmartPro Hub customers do X'",
            "Lead with a quote or question from a customer, then explain the feature built in response",
        ],
        "topics": [
            "Direct bank integration for WPS submission — what disappears from the HR team's monthly checklist",
            "Auto-expiry alerts for work permits and visas — how the dashboard surfaces renewals 30/60/90 days out",
            "The white-label client portal — what a Sanad office's clients see when they log in",
            "E-signature for employment contracts — three signatures across two countries, end-to-end in one platform",
            "Growth partner commission tracking — what gets logged automatically and what no longer needs a spreadsheet",
            "Automated invoicing per service for PRO firms — billing 30 clients in the time it used to take to bill three",
            "WhatsApp Business integration — how client requests flow into a tracked case instead of a group chat",
            "Bilingual (Arabic/English) interface — why a single-language HR system fails Oman businesses",
        ],
    },

    # ── OMAN_MARKET ──────────────────────────────────────────────────────────
    "oman_market": {
        "weight":           2.0,
        "segment":          "B",
        "post_type":        ["Story", "Data/Insight"],
        "day":              "Friday",
        "weekday":          4,
        "generate_weekday": 2,
        "publish_day":      "Friday",
        "generate_day":     "Wednesday",
        "tone":             "thoughtful, market-aware, Vision-2040-aligned — broader context, not product-pushy",
        "audience":         "Omani business leaders, investors, government partners interested in the SME and HR tech landscape",
        "brand_context":    _COMPANY_BRAND_CONTEXT,
        "formats": [
            "Open with an Oman market data point or Vision 2040 reference, then connect it to operational reality for SMEs",
            "Walk through a structural shift in Oman business (digitization, Omanization, regulatory) and what it means for HR/ops",
            "Compare Oman's SME operations landscape today vs three years ago — what has changed, what is still broken",
            "Frame SmartPro Hub's roadmap or worldview in the context of Oman's broader business transformation",
        ],
        "topics": [
            "Vision 2040 and the digitization of SME operations — where Oman businesses actually stand",
            "Why 924 Sanad offices being the backbone of Oman business administration deserves better software",
            "Omanization compliance is shifting from quarterly headache to continuous monitoring — and that needs systems",
            "What WPS adoption taught Oman businesses about regulatory deadlines — and what is coming next",
            "The shift from family-business HR to professionalized operations — what triggers it, what it requires",
            "Why HR tech built outside the GCC consistently misses the Oman labour context",
            "GCC business growth and the operations infrastructure that has to scale with it",
            "From WhatsApp-run operations to platform-run operations — the SME journey in Oman, 2024 to 2026",
        ],
    },

    # ── HIRING ───────────────────────────────────────────────────────────────
    # Manual only — fire when a new role opens.
    "hiring": {
        "weight":           1.0,
        "segment":          "A",
        "post_type":        ["Story", "Engagement"],
        "day":              "Manual",
        "weekday":          -1,
        "generate_weekday": -1,
        "publish_day":      "Manual",
        "generate_day":     "Manual",
        "tone":             "warm, specific, candidate-focused — describe the actual work, not corporate fluff",
        "audience":         "engineers, designers, customer success and ops professionals in Oman/GCC and remote-friendly",
        "brand_context":    _COMPANY_BRAND_CONTEXT,
        "formats": [
            "Open with the real problem the new hire will work on, then describe what success looks like in 90 days",
            "A day in the life of the role — concrete, not generic",
            "Walk through what SmartPro Hub is building and where this role plugs in",
            "Three things the hiring manager wants candidates to know before applying",
        ],
        "topics": [
            "What we are building at SmartPro Hub and the kind of operators we are hiring",
            "Open role announcement — frame the problem, not the title",
            "Engineering at SmartPro Hub — small team, real customers, weekly shipping",
            "Customer success role — what a great week looks like in support of Oman SMEs",
        ],
    },

    # ── PARTNERSHIP ──────────────────────────────────────────────────────────
    # Manual only — fire when a new partnership ships.
    "partnership": {
        "weight":           1.0,
        "segment":          "B",
        "post_type":        ["Social Proof/Milestone", "Story"],
        "day":              "Manual",
        "weekday":          -1,
        "generate_weekday": -1,
        "publish_day":      "Manual",
        "generate_day":     "Manual",
        "tone":             "credible, specific, partnership-led — name partners, describe what changes for customers",
        "audience":         "Sanad offices, accountants, HR consultancies, bank partners, government bodies",
        "brand_context":    _COMPANY_BRAND_CONTEXT,
        "formats": [
            "Open with what the partnership unlocks for end customers, then explain the structural integration",
            "Walk through a specific workflow that is now end-to-end thanks to the new partner",
            "Quote the partner — what they say about working with SmartPro Hub",
            "Show the before/after of a customer journey that this partnership shortens",
        ],
        "topics": [
            "New partnership announcement template — partner name, what changes, who benefits",
            "Sanad office partner program — how it works, who qualifies",
            "Accounting and HR consultancy partners — what referral and co-sell look like",
            "Bank integrations for WPS — current partners and what is coming next",
        ],
    },

    # ── FEASIBILITY ──────────────────────────────────────────────────────────
    # Manual only (FORCE_PILLAR=feasibility). Promotes Feasibility Studio — the
    # free AI tool that produces a bank-ready feasibility study for Development
    # Bank Oman / Riyada loan applications. CTA -> /feasibility-studio.
    "feasibility": {
        "weight":           1.0,
        "segment":          "A",
        "cta":              "feasibility",  # override -> CTA_FEASIBILITY (see _cta_block)
        "post_type":        ["Educational/How-To", "Engagement"],
        "day":              "Manual",
        "weekday":          -1,
        "generate_weekday": -1,
        "publish_day":      "Manual",
        "generate_day":     "Manual",
        "tone":             "encouraging, practical, demystifying — make starting a funded business feel achievable, never salesy",
        "audience":         "aspiring entrepreneurs, SMEs, and Sanad-office clients in Oman who need a feasibility study to apply for Development Bank Oman (DBO) or Riyada funding",
        "brand_context":    _COMPANY_BRAND_CONTEXT_FEASIBILITY,
        "formats": [
            "Explain what a bank-ready feasibility study must contain, then show how to produce one free in about 10 minutes",
            "Map the 10 Development Bank Oman / Riyada programs to who qualifies for each, then point to the matching study",
            "Before/after: paying a consultant and waiting weeks versus a free AI-generated study ready the same day",
            "List the 9 documents a complete feasibility study includes — and what each tells the bank",
        ],
        "topics": [
            "SmartPro Hub Feasibility Studio — turn a business idea into a bank-ready study free in ~10 minutes",
            "The 9 documents every funded Oman business needs before applying to Development Bank Oman",
            "Program 5 (Craft/Home/Mobile) at 0% interest up to OMR 20K — who qualifies and how to apply",
            "Feasibility study vs business plan — what Development Bank Oman actually asks for",
            "From idea to bank-ready, in English or Arabic — covering all 10 DBO / Riyada programs",
        ],
    },
}

ALL_PILLARS: list[dict] = [{"name": name, **config} for name, config in PILLARS.items()]

# ── History directory — separate from personal ──────────────────────────────
HISTORY_DIR = Path(__file__).parent / "company_posts_history"


# ── Pillar picker (performance-weighted) ─────────────────────────────────────
# Mirrors content_strategy.pick_pillar / get_pillar_weights but reads from
# company_posts_history. Kept simple for V1 — uses static weights from PILLARS.

def get_pillar_weights() -> dict[str, float]:
    """Return pillar weights, optionally adjusted by past performance.

    V1: returns the static weights from PILLARS. Once enough scored
    company posts exist, this can be swapped for a content_feedback-based
    weighting just like the personal pipeline.
    """
    return {name: cfg.get("weight", 1.0) for name, cfg in PILLARS.items()}


def _recent_pillar_counts(days: int = 21) -> dict[str, int]:
    """Count how many times each pillar was used in the last N days."""
    from collections import Counter
    from datetime import datetime, timezone, timedelta

    if not HISTORY_DIR.exists():
        return {}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    counts: Counter[str] = Counter()
    for f in HISTORY_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            gen_at = data.get("generated_at", "")
            if not gen_at:
                continue
            dt = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
            if dt >= cutoff:
                counts[data.get("pillar", "")] += 1
        except Exception:
            continue
    return dict(counts)


def _pick_by_weight(weights: dict[str, float], avoid_recent: bool = True) -> str:
    """Pick a pillar weighted by weights, dampening recently-used pillars."""
    import random

    if not weights:
        raise ValueError("No pillars available to pick from.")

    adjusted = dict(weights)
    if avoid_recent:
        recent = _recent_pillar_counts()
        for name, count in recent.items():
            if name in adjusted and count > 0:
                adjusted[name] = adjusted[name] / (1 + count)

    names   = list(adjusted.keys())
    weights_list = [adjusted[n] for n in names]
    return random.choices(names, weights=weights_list, k=1)[0]


def pick_pillar(weekday: int, force: str | None = None) -> tuple[str, dict]:
    """Pick a pillar for the given weekday.

    Schedule mapping (Mon=0..Sun=6):
      Mon: product_proof
      Wed: feature_spotlight
      Fri: oman_market
      Other days: weighted pick across all auto-eligible pillars

    `force` overrides the weekday mapping. Manual-only pillars
    (hiring, partnership) require `force` and never auto-pick.
    """
    if force:
        if force not in PILLARS:
            raise ValueError(
                f"Unknown pillar {force!r}. Valid: {sorted(PILLARS)}"
            )
        return force, PILLARS[force]

    weekday_map = {
        0: "product_proof",
        2: "feature_spotlight",
        4: "oman_market",
    }
    if weekday in weekday_map:
        name = weekday_map[weekday]
        return name, PILLARS[name]

    # Fallback for off-schedule days — pick by weight among scheduled pillars
    weights = {n: c["weight"] for n, c in PILLARS.items() if c["weekday"] >= 0}
    name = _pick_by_weight(weights)
    return name, PILLARS[name]
