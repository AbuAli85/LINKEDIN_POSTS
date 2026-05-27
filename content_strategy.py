"""Content strategy: SmartPRO Hub — enterprise operations platform for Oman & GCC businesses."""

import json
from pathlib import Path

BRAND_URL      = "www.thesmartpro.io"
# CTA for posts targeting companies (HR managers, business owners, PRO service firms).
COMPANY_CTA    = "Book a 20-minute demo at www.thesmartpro.io — or WhatsApp +96879665522 to see SmartPRO Hub live."
# CTA for Sanad/PRO posts — free AI assistant is the entry point, no login needed.
SANAD_CTA      = "Try the Sanad AI Assistant free — instant answers on work permits, visas & government fees: www.thesmartpro.io/sanad/assistant"
SANAD_CTA_AR   = "جرّب مساعد سند الذكي مجاناً — إجابات فورية عن تصاريح العمل والتأشيرات والرسوم الحكومية: www.thesmartpro.io/sanad/assistant"
# CTA for Arabic posts targeting companies (pain_ar pillar)
COMPANY_CTA_AR = "احجز عرضاً تجريبياً مجانياً مدته ٢٠ دقيقة على www.thesmartpro.io — أو راسلنا على واتساب +96879665522 لمشاهدة SmartPRO Hub مباشرة."
# CTA for posts targeting candidates (job seekers)
CANDIDATE_CTA  = "Browse open jobs and apply at www.thesmartpro.io"
# CTA for Segment C (tech/build-in-public posts targeting engineers and SaaS founders)
TECH_CTA       = "SmartPRO Hub is open for early adopters — OMR 12/month, 14-day free trial: www.thesmartpro.io"
# Legacy alias kept so existing code that references DEMO_CTA still works
DEMO_CTA       = COMPANY_CTA

# ── UTM-tracked CTA templates per segment ──────────────────────────────────
# {campaign} is filled at generation time with the pillar name (e.g. "pain-en").
# Segment A — HR managers and business owners
CTA_DEMO = (
    "Book a free 20-minute demo: "
    "https://www.thesmartpro.io/demo"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
    "\nOr WhatsApp +96879665522"
)
CTA_DEMO_AR = (
    "احجز عرضاً تجريبياً مجانياً مدته ٢٠ دقيقة: "
    "https://www.thesmartpro.io/demo"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
    "\nأو واتساب +96879665522"
)
# Segment B — Investors and government
CTA_INVESTORS = (
    "Request an investor briefing: "
    "https://www.thesmartpro.io/investors"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
)
CTA_INVESTORS_AR = (
    "اطلب جلسة إحاطة للمستثمرين: "
    "https://www.thesmartpro.io/investors"
    "?utm_source=linkedin&utm_medium=social&utm_campaign={campaign}"
)
# Segment C — Tech founders
CTA_TECH = (
    "Follow for build-in-public updates from SmartPRO Hub. "
    "DM if you want to compare notes on multi-tenant architecture."
)

# Segment-specific hashtag sets (3-5 per post; generator picks from the segment's list)
HASHTAGS: dict[str, list[str]] = {
    "A": ["#OmanBusiness", "#HRManagement", "#PayrollOman", "#WPS", "#SmartPROHub", "#Omanization", "#GCCBusiness"],
    "B": ["#OmanVision2040", "#GCCBusiness", "#HRTech", "#SMEOman", "#BusinessGrowth", "#SmartPROHub", "#Oman"],
    "C": ["#BuildInPublic", "#SaaS", "#GCCTech", "#TypeScript", "#ClaudeAI", "#OmanTech", "#SmartPROHub"],
}

# SEO keywords to surface in generation context — models weave these in naturally
SEO_KEYWORDS: list[str] = [
    "HR software Oman",
    "WPS payroll Oman",
    "Ministry of Labour Oman compliance",
    "Sanad office management",
    "work permit tracking Oman",
    "end-of-service gratuity Oman",
    "Omanization compliance software",
    "SME HR platform GCC",
    "payroll automation Muscat",
    "SmartPRO Hub",
]

_BRAND_CONTEXT = (
    "BRAND CONTEXT: You are writing on behalf of SmartPRO Hub — the enterprise operations platform "
    "built exclusively for Oman and GCC businesses. SmartPRO Hub brings together in one system: "
    "CRM with deal pipeline and quotations, a white-label client portal, HR and workforce management, "
    "WPS payroll with direct bank integration, SPF (Social Protection Fund) and Omanisation compliance, Ministry of Labour (MOL) "
    "government filings, Sanad office management, PRO services workflow, work permit and visa "
    "tracking, e-signature contract management, automated invoicing and billing, and a growth partner "
    "programme with automatic commission tracking. "
    "It replaces WhatsApp groups, spreadsheets, and fragmented vendor systems with one connected platform. "
    "Bilingual — Arabic and English. "
    "Pricing: Starter OMR 12/month, Business OMR 25/month, Enterprise OMR 60/month. 14-day free trial, no credit card. "
    "Target buyers: business owners, HR managers, finance managers, and operations directors at Oman and GCC "
    "companies with 10–500 employees, PRO service firms, staffing agencies, Sanad offices, and any "
    "multi-client B2B service business. "
    "The goal of every post is to surface a pain the reader recognises, build trust, and drive trial signups or demo requests. "
    f"Website: {BRAND_URL}. "
    f"End every post with this CTA on its own line: {COMPANY_CTA}"
)

_BRAND_CONTEXT_CANDIDATES = (
    "BRAND CONTEXT: You are writing on behalf of SmartPRO Hub — a platform that connects job seekers "
    "with companies actively hiring in Oman. Candidates can create a free profile, browse open roles, "
    "apply in seconds, and track their application from applied to hired. "
    f"Website: {BRAND_URL}. "
    f"End every post with this CTA on its own line: {CANDIDATE_CTA}"
)

_BRAND_CONTEXT_AR = (
    "سياق العلامة التجارية: أنت تكتب نيابةً عن SmartPRO Hub — منصة العمليات المتكاملة "
    "المصممة خصيصاً لشركات عُمان ودول الخليج العربي. تجمع SmartPRO Hub في نظام واحد: "
    "إدارة علاقات العملاء مع خط صفقات وعروض الأسعار، بوابة العملاء الإلكترونية، "
    "إدارة الموارد البشرية والقوى العاملة، رواتب WPS مع تكامل مصرفي مباشر، "
    "الامتثال لصندوق الحماية الاجتماعية (SPF) ونسب التعمين، تسجيلات وزارة العمل، "
    "إدارة مكاتب سند وخدمات PRO، تتبع تصاريح العمل والتأشيرات، "
    "إدارة العقود بالتوقيع الإلكتروني، إصدار الفواتير التلقائي، "
    "وبرنامج شركاء النمو مع تتبع العمولات تلقائياً. "
    "تحل محل مجموعات واتساب والجداول الورقية والأنظمة المتفرقة بمنصة واحدة متكاملة. "
    "ثنائية اللغة — العربية والإنجليزية. "
    f"الأسعار: Starter بـ١٢ ريال عُماني/شهر، Business بـ٢٥ ريالاً/شهر، Enterprise بـ٦٠ ريالاً/شهر. تجربة مجانية ١٤ يوماً بدون بطاقة ائتمانية. "
    "المستهدفون: أصحاب الأعمال والمديرون في شركات عُمان ودول الخليج التي تضم ١٠ إلى ٥٠٠ موظف. "
    "هدف كل منشور: إبراز الألم الذي يعرفه القارئ، وبناء الثقة، وتوليد طلبات تجريب أو عروض توضيحية. "
    f"الموقع الإلكتروني: {BRAND_URL}. "
    f"أنهِ كل منشور بهذه الدعوة للتصرف في سطر منفصل: {COMPANY_CTA_AR}"
)

_BRAND_CONTEXT_SANAD_AR = (
    "سياق العلامة التجارية: أنت تكتب نيابةً عن SmartPRO Hub — المنصة المصممة خصيصاً "
    "لمكاتب سند وشركات خدمات PRO في عُمان. "
    "يوجد ٩٢٤ مكتب سند مرخص في عُمان، ويشترط القانون أن يعمل بها مواطنون عُمانيون حصراً — "
    "وهي قناة التعمين الحكومية الإلزامية. مكاتب سند هي البوابة الرسمية بين كل شركة في عُمان "
    "وكل جهة حكومية. كل شركة تعتمد على مكتب سند لإنجاز: تصاريح العمل، "
    "التأشيرات، بطاقات الهوية، تسجيل الشركات، تخليص وزارة العمل، "
    "معاملات هيئة الوضع المدني، تخليص الشرطة العُمانية، شهادات التعمين، وغيرها. "
    "معظم مكاتب سند تُدير كل هذا اليوم عبر مجموعات واتساب وملفات إكسل مشتركة وسجلات ورقية. "
    "SmartPRO Hub تستبدل ذلك كلياً بـ: استقبال منظّم للقضايا لكل شركة عميل، "
    "كتالوج خدمات بأسعار حية، تنبيهات تلقائية بانتهاء صلاحية تصاريح العمل والتأشيرات، "
    "إسناد المهام لمسؤول PRO، خزينة وثائق رقمية لكل عميل، "
    "بوابة عميل تتيح للشركات تتبع طلباتها دون اتصال، "
    "إصدار فواتير تلقائي لكل خدمة منجزة، ولوحة امتثال شاملة لجميع العملاء. "
    "الميزة المميزة — مساعد سند الذكي (www.thesmartpro.io/sanad/assistant): "
    "وكيل ذكاء اصطناعي مجاني متاح للعموم — لا تسجيل دخول مطلوب — يعمل كمسؤول PRO متمرس. "
    "ثنائي اللغة عربي وإنجليزي، مع إدخال صوتي وإخراج صوتي باللهجة العُمانية (ar-OM). "
    "يُجيب على أسئلة تصاريح العمل والتأشيرات وتسجيل الشركات والتصديق وغيرها. "
    "يبحث في الرسوم الحكومية الرسمية المعتمدة، ويجد مكاتب سند مرخصة قريبة من المستخدم بحسب المحافظة، "
    "ويُصدر عروض أسعار كاملة (رسوم حكومية + رسوم المكتب). "
    "مدعوم بـClaude AI. أي صاحب شركة أو مدير موارد بشرية أو فرد يستطيع استخدامه مجاناً فوراً، "
    "ثم يُوصَل بمكتب سند مرخص لإتمام الخدمة. "
    f"الأسعار: Starter بـ١٢ ريال عُماني/شهر، Business بـ٢٥ ريالاً/شهر، Enterprise بـ٦٠ ريالاً/شهر. تجربة مجانية ١٤ يوماً. "
    "المستهدفون: أصحاب ومديرو مكاتب سند الـ٩٢٤ في عُمان، ومديرو شركات خدمات PRO، "
    "ومديرو الموارد البشرية المتعاملون مع الجهات الحكومية، وكل صاحب شركة يحتاج خدمات حكومية. "
    "هدف كل منشور: أن يشعر القارئ أنك تصف واقعه اليومي بالضبط، ثم تدعوه لتجربة مساعد سند الذكي المجاني. "
    f"الموقع الإلكتروني: {BRAND_URL}. "
    f"أنهِ كل منشور بهذه الدعوة للتصرف في سطر منفصل: {SANAD_CTA_AR}"
)

_BRAND_CONTEXT_SANAD = (
    "BRAND CONTEXT: You are writing on behalf of SmartPRO Hub — the platform purpose-built for "
    "Sanad offices and PRO service firms in Oman. "
    "There are 924 licensed Sanad offices across Oman — and by law, they must be staffed exclusively "
    "by Omani nationals. This is a government-mandated Omanisation channel: Sanad offices are the "
    "legal gateway between every company in Oman and every government authority. Every business — "
    "from a 2-person shop to a 500-employee enterprise — depends on a Sanad office to handle all their "
    "government paperwork: work permits, residency visas, ID cards, company registrations, labour "
    "clearances, Ministry of Labour (MOL) filings, Civil Status Authority transactions, Royal Oman Police "
    "clearances, Omanisation certificates, and more. "
    "Most Sanad offices today manage all of this through WhatsApp groups, shared Excel files, and "
    "handwritten registers. SmartPRO Hub replaces that entirely with: structured case intake per "
    "client company, service catalog with live pricing, automatic work permit and visa expiry alerts, "
    "PRO officer task assignment, digital document vault per client, a client portal so companies can "
    "track every request themselves without calling, automated invoicing per service delivered, "
    "and a compliance dashboard across all clients. "
    "KEY DIFFERENTIATOR — Sanad AI Assistant (www.thesmartpro.io/sanad/assistant): "
    "A free public AI agent — no login required — that acts like an experienced PRO officer. "
    "Bilingual English and Arabic, with Omani Arabic voice input and voice output. "
    "It answers questions on work permits, visas, business registration, attestation, and more. "
    "It looks up verified Oman government fees, finds licensed Sanad offices near the user by "
    "governorate, and builds full service quotes (government fees + office fees). "
    "Powered by Claude AI. Any company owner, HR manager, or individual can use it instantly for "
    "free — then get matched to a licensed Sanad office to complete the work. "
    "Pricing: Starter OMR 12/month, Business OMR 25/month, Enterprise OMR 60/month. "
    "14-day free trial, no credit card required. "
    "Target readers: Sanad office owners and managers, PRO service firm directors, HR managers "
    "dealing with government paperwork, and any Oman business owner who needs government services done right. "
    "Goal: make the reader feel understood, surface their exact daily pain, drive them to try the "
    "free Sanad AI Assistant or book a platform demo. "
    f"Website: {BRAND_URL}. "
    f"End every post with this CTA on its own line: {SANAD_CTA}"
)

_BRAND_CONTEXT_TECH = (
    "BRAND CONTEXT: You are writing in first person as a technical co-founder of SmartPRO Hub — "
    "Oman's first multi-tenant HR intelligence platform. "
    "Stack: tRPC, Drizzle ORM, MySQL, TypeScript, Claude AI. 4,000+ automated tests. "
    "The platform handles WPS payroll with direct bank integration, Ministry of Labour compliance, "
    "end-of-service gratuity, Sanad office management, and work permit tracking for Oman businesses. "
    "This post is for the global tech community — engineers, SaaS founders, and builders who care about "
    "architecture tradeoffs, engineering culture, and what it's like to build in an underserved market. "
    "Write candidly. Share real numbers and real tradeoffs. Don't pitch — build in public. "
    "Assume the reader can read code, but don't paste walls of it — describe decisions and their consequences. "
    f"Website: {BRAND_URL}. "
    f"End every post with this CTA on its own line: {TECH_CTA}"
)

PILLARS = {
    # ── PAIN ─────────────────────────────────────────────────────────────────────
    # Monday posts. Surface the operational pain Oman business owners feel daily.
    # Never mention SmartPro by name — just make the reader feel seen and understood.
    "pain": {
        "weight":          2.0,  # strong lead generator; moderate B2B conversion rate
        "segment":         "A",
        "post_type":       ["Story", "Engagement"],
        "day":             "Monday",
        "weekday":         0,
        "generate_weekday": 5,   # Saturday — 2 days before Monday publish
        "publish_day":     "Monday",
        "generate_day":    "Saturday",
        "tone":            "empathetic, direct, problem-aware — the reader should feel understood, not sold to",
        "audience":        "business owners, HR managers, and finance managers in Oman with 10–200 employees who still run HR and payroll manually",
        "brand_context":   _BRAND_CONTEXT,
        "formats": [
            "Open with a specific failure moment — a real date, a real cost, a real consequence that feels immediately familiar to the reader",
            "State the uncomfortable truth about how most Oman businesses handle this problem — be specific and honest, not preachy",
            "Walk through a day-in-the-life of an HR team managing this manually — show every broken step in sequence",
            "Write a numbered list of 4-5 warning signs — make them specific enough that most readers recognise at least three of them",
            "Before/after: describe exactly what this problem looks like unsolved versus what changes when it is solved",
            "Open with a question that forces the reader to calculate their own answer — time lost, money wasted, or risk carried",
        ],
        "topics": [
            # HR & Payroll pain
            "WPS rejection on payday — what it actually costs a business in Oman beyond the technical fix",
            "How many hours does your HR team spend on payroll every month — and what is that time really worth?",
            "The hidden cost of managing leave requests over WhatsApp group chats",
            "What happens to your business operations when your HR manager resigns unexpectedly",
            "Employee contracts stored in a drawer — why that matters far more than most owners realise",
            "Processing payroll manually for 50 people: the compliance risks nobody talks about openly",
            "Why Oman businesses fail government audits they could have passed with the right system",
            "The overtime calculation mistake that costs companies real money every single month",
            "Managing three locations in Oman with no central HR system — what breaks first",
            "When the bank rejects your WPS file at 11pm the night before payday",
            "How long does it actually take your team to fully onboard one new employee?",
            "The compliance gaps most Oman businesses do not know they are carrying",
            "Why HR data stored in Excel is a liability, not just an inconvenience",
            "End-of-service calculation errors — how they happen and exactly what they cost",
            "What Oman labour law actually requires versus how most companies operate day to day",
            "When a government inspection reveals what a manual HR system has been missing",
            "The month payroll ran three days late because the accountant was on sick leave",
            "Tracking 80 leave balances in a shared spreadsheet — someone always gets the wrong number",
            "Why your best employees leave when HR and payroll operations are chaotic",
            "The salary dispute that a proper system would have prevented entirely",
            "Your entire HR operation exists in one person's head — what happens when they are unreachable",
            "Why growing from 20 to 50 employees breaks most manual HR and payroll systems",
            # Client management & portal pain
            "Managing 15 client companies from a WhatsApp group — what breaks and when",
            "Your client calls to ask for a status update you cannot give because no one has logged it",
            "Sending a quotation as a Word document attached to an email — why that approach is costing you deals",
            "The service request that fell through the cracks because it came in on WhatsApp at 9pm",
            "How much time does your team spend answering client status questions every week?",
            "When a client disputes an invoice and you cannot show them the paper trail in 60 seconds",
            "Managing client contracts across email, WhatsApp, and a shared drive — what a government audit sees",
            "Your client signed a contract. It is now in someone's email attachment. What happens when that person leaves?",
            # PRO / Sanad / government services pain
            "The work permit that expired because no one was tracking the renewal date",
            "Managing 40 client work permits in a shared Excel — what the first missed expiry actually costs",
            "How PRO service firms in Oman lose clients: it is never about the service, it is always about visibility",
            "The MOL filing deadline your team missed because it was written on a sticky note",
            "Your client finds out their employee's residency visa expired from the airport — not from you",
            "Tracking Omanisation quotas manually across 10 client companies — what happens when one is non-compliant",
            "The government service request that took three WhatsApp messages, two phone calls, and four days",
            "Running a Sanad office with no case tracking system — what every busy week actually looks like",
            # Contract & e-signature pain
            "A contract that needs three signatures in two countries — how long does that take your business right now?",
            "The deal you lost because the contract sat unsigned in someone's email for eight days",
            "Printing, signing, scanning, and emailing a contract in 2026 — why this is still how most Oman businesses operate",
            "What happens when you cannot find the signed version of a client contract you need right now",
            # Partner & commission pain
            "Tracking referral commissions in a spreadsheet — what happens when two salespeople claim the same lead",
            "Your growth partner brought you three clients last quarter and is still waiting for their commission statement",
            "The commission dispute that damaged a business relationship because there was no audit trail",
        ],
    },

    # ── PROOF ────────────────────────────────────────────────────────────────────
    # Wednesday posts. Show concrete evidence that the problem is solvable.
    # Specific numbers, real outcomes, before/after. Build credibility without hype.
    "proof": {
        "weight":          3.0,  # highest-converting pillar for B2B SaaS — social proof closes deals
        "segment":         "A",
        "post_type":       ["Data/Insight", "Social Proof/Milestone"],
        "day":             "Wednesday",
        "weekday":         2,
        "generate_weekday": 0,   # Monday — 2 days before Wednesday publish
        "publish_day":     "Wednesday",
        "generate_day":    "Monday",
        "tone":            "concrete, data-driven, credible — specific results only, no vague claims",
        "audience":        "business owners and HR managers in Oman who are open to change but need real evidence before they act",
        "brand_context":   _BRAND_CONTEXT,
        "formats": [
            "Open with a specific measurable result — a number, a time saved, a cost eliminated — then explain exactly what created it",
            "Walk through the before and after in precise detail — same task, completely different experience from start to finish",
            "Build a tight case study: type of company, the problem they had, what changed, the one number that proves it worked",
            "Open with a data point about Oman businesses and explain the root cause behind it",
            "Tell the story from the employee's perspective — what they experienced before and what changed for them after",
            "State the result first, then walk backwards step by step to show exactly what made it possible",
        ],
        "topics": [
            # HR & Payroll proof
            "Payroll that used to take three days now takes under two hours — what changed",
            "Zero WPS rejections in twelve months after switching to an integrated system",
            "What onboarding ten new employees looks like when every step is automated",
            "How one company in Muscat passed a government audit without the usual last-minute panic",
            "The leave approval that used to take three days — now resolved in ten minutes",
            "What a business owner's Monday looks like without HR administration overhead",
            "End-of-service calculations done in seconds instead of spreadsheet hours",
            "How a retail operation in Oman manages payroll across four branches from one screen",
            "The HR manager who finally stopped taking payroll work home on weekends",
            "From three spreadsheets to one system — what the first month of transition looked like",
            "How payroll accuracy changed employee trust at one Oman business",
            "The direct bank integration that eliminated manual WPS submission permanently",
            "How one founder recovered eight hours every week by automating business operations",
            "Processing 200 salaries in a single run — what that means in practice for the team",
            "The company that scaled from 30 to 120 employees without adding HR headcount",
            "Real numbers: what manual HR was costing annually before the switch",
            "How accurate labour cost data changed the way one owner made pricing decisions",
            # Client portal & CRM proof
            "The client portal that cut inbound status-update calls by 80% in the first month",
            "From WhatsApp to a client portal: what the first week of transition looked like for a Muscat service firm",
            "A quotation built, sent, and accepted in the same afternoon — what that pipeline looks like in SmartPRO Hub",
            "How one service firm tracked 25 active client deals without a single spreadsheet",
            "The client who renewed their contract without a single phone call — what made that possible",
            "Before and after: what client communication looked like for a PRO firm running on WhatsApp vs. a portal",
            "How real-time deal visibility changed the way a business owner prioritised their week",
            # PRO / Sanad / government services proof
            "Zero missed permit renewals in six months — how a PRO firm achieved it with automatic expiry tracking",
            "Managing 40 client work permits from one compliance dashboard — what the daily routine now looks like",
            "The government filing that used to take a full day — now submitted in 20 minutes from one screen",
            "How a Sanad office in Muscat eliminated double-entry and cut admin time by half",
            "What happened when one PRO firm gave every client a portal to track their own government cases",
            "From paper forms and WhatsApp to structured case tracking — one Oman PRO firm's first 60 days",
            "Omanisation compliance across 12 client companies — how one firm now reports it in minutes not days",
            # Contract & e-signature proof
            "A contract signed by two parties in different cities in under four minutes — what that workflow looks like",
            "How digital contracts eliminated a class of client dispute for one Oman service business",
            "The contract renewal that was automatic — owner got an email, clicked approve, done",
            # Partner program proof
            "How one growth partner tracked every referral commission in real time without a single email",
            "The partner dashboard that replaced a monthly spreadsheet reconciliation with live numbers",
        ],
    },

    # ── VISION ───────────────────────────────────────────────────────────────────
    # Friday posts. Speak to where Oman business is heading.
    # Ambitious, forward-looking. Makes the reader want to be part of what is coming.
    "vision": {
        "weight":          1.0,  # brand positioning; lowest direct conversion — generate least
        "segment":         "B",
        "post_type":       ["Story", "Data/Insight"],
        "day":             "Friday",
        "weekday":         4,
        "generate_weekday": 2,   # Wednesday — 2 days before Friday publish
        "publish_day":     "Friday",
        "generate_day":    "Wednesday",
        "tone":            "forward-looking, strategic, confident — speak to founders and leaders thinking about the next 3-5 years, not just today's problems",
        "audience":        "founders, CEOs, and senior managers in Oman thinking about where their business is heading and how to get it there",
        "brand_context":   _BRAND_CONTEXT,
        "formats": [
            "Open with a sharp observation about where Oman business is heading and why most companies are not prepared for it",
            "State a counterintuitive truth about what actually drives business growth in Oman — then prove it with a specific example",
            "Draw the clear line between where businesses are today and where the successful ones will be in five years",
            "Open with an Oman Vision 2040 or government policy angle and translate it into a practical implication for business owners",
            "Write a numbered list of what separates scaling businesses from stalled ones — every point specific to the Oman context",
            "Before/after: describe what a business looks like before and after it builds proper operational infrastructure — show how it feels to run",
        ],
        "topics": [
            # Broad Oman business vision
            "Oman Vision 2040 demands private sector productivity — that starts with how you run daily operations",
            "The real difference between Oman businesses that scale and businesses that stay stuck",
            "Why digital transformation in Oman is no longer a choice for any company with employees",
            "What modern HR looks like for a growing Oman company in 2026 — and who is building it",
            "The businesses that will lead Oman's next decade are already running on integrated systems",
            "Why the next phase of Oman's economy requires automated compliance, not manual checking",
            "What integrated business operations mean for Oman's SME sector over the next five years",
            "The competitive advantage of knowing your exact labour cost in real time",
            "How government-connected platforms are changing what Oman businesses can actually do",
            "What a fully digital business operation looks like in 2026 and who is building one from Muscat",
            "The founders building the next generation of Oman companies — what they are doing differently now",
            "Why SMEs in Oman need enterprise-grade systems — without enterprise budgets or timelines",
            "The future of payroll in Oman: what has already changed and what is still coming in the next two years",
            "How direct bank integration changes cash flow management for Oman businesses",
            "What Oman's private sector looks like in 2030 — and what it takes to still be growing by then",
            "The shift from managing employees to actually leading teams — what infrastructure makes that possible",
            "Why the best talent in Oman increasingly chooses employers with professional HR systems",
            "What it means to build a business in Oman that can grow without depending on you personally",
            "The operations layer that separates growing companies from companies that are permanently stretched",
            "How real-time business data changes the decisions a founder makes every single week",
            "The compliance landscape in Oman — what is tightening and what it will mean for your business",
            "Why government system integrations are a competitive opportunity, not just an administrative burden",
            "Building an Oman business that is ready for foreign investment — what investors check before they commit",
            # PRO / Sanad industry vision
            "The PRO services industry in Oman is moving from WhatsApp to platforms — what that means for firms that adapt early",
            "What a modern Sanad office looks like in 2026 — and why the ones running on spreadsheets will not survive the next five years",
            "Government digitisation in Oman is accelerating — the service businesses that connect to it now will own the market",
            "The client portal is becoming the baseline expectation in Oman B2B — service firms that still rely on WhatsApp updates are losing contracts to those that do not",
            "Why Oman's government services sector will consolidate around platforms — and what that means if you run a PRO firm today",
            "The competitive advantage of a Sanad office that can show every client the live status of every government case at any moment",
            # Client experience vision
            "The future of B2B client relationships in Oman is self-service — what your business needs to be ready",
            "What Oman's most successful service firms are building now that their clients did not know they wanted yet",
            "The business that gives clients a portal instead of a phone number will win the next decade of Oman B2B",
            # Partner economy vision
            "The partner economy is arriving in Oman — what it means to build a growth model that rewards the people who bring you clients",
            "Why referral programmes with transparent commission tracking are the most efficient sales channel most Oman businesses are not using",
        ],
    },

    # ── SANAD / PRO SERVICES ─────────────────────────────────────────────────────
    # Thursday posts — targeting the 924 licensed Sanad offices across Oman.
    # Every company in Oman depends on a Sanad office for work permits, visas,
    # ID cards, clearances, MOL filings, and all government paperwork.
    # This is the highest-leverage channel in the platform: win Sanad offices,
    # reach every business they serve.
    "sanad_pro": {
        "weight":           2.5,   # high-priority scheduled pillar — 924 offices, massive channel
        "segment":          "A",
        "post_type":        ["Story", "Engagement"],
        "day":              "Thursday",
        "weekday":          3,
        "generate_weekday": 1,     # Tuesday — 2 days before Thursday publish
        "publish_day":      "Thursday",
        "generate_day":     "Tuesday",
        "tone":             "peer-to-peer, operational, direct — write as someone who has sat inside a Sanad office and knows exactly what it feels like to track 40 work permits, 15 visa renewals, and 8 MOL filings across 20 client companies using nothing but WhatsApp and Excel",
        "audience":         "owners and managers of the 924 licensed Sanad offices in Oman, PRO service firm directors, and anyone running a government services business handling work permits, residency visas, ID cards, clearances, and Ministry filings for multiple client companies",
        "brand_context":    _BRAND_CONTEXT_SANAD,
        "formats": [
            "Open with a specific Sanad or PRO failure moment — a visa that expired, a client who found out at the airport, a missed MOL filing — make it so specific the reader stops scrolling",
            "Walk through the exact day-in-the-life of a Sanad office manager handling 20+ client companies with no case tracking system — every painful step in sequence",
            "Build a sharp before/after: managing government services with WhatsApp and Excel versus SmartPRO Hub case tracking and a client portal — show the same week, completely different experience",
            "Write a numbered list of 5 signs that a Sanad office has outgrown its current setup — make each one precise enough that most readers recognise at least four",
            "Open with a number that puts the problem in scale — 924 offices, 40 permits, 15 visa renewals, 200 filings per month — then show what managing that volume without a system actually looks like",
            "Client trust story: the Sanad office that started giving every client a portal to track their own cases — what happened to client retention and referrals in the first three months",
            "Open with a question that forces the reader to calculate their own answer: how many work permits are you tracking right now, and where exactly is that information?",
        ],
        "topics": [
            # Pain — daily operational reality
            "There are 924 Sanad offices in Oman — staffed entirely by Omani nationals, handling every company's government paperwork. Most are still managing 30+ clients on WhatsApp. Here is what that looks like on a busy Tuesday.",
            "How Sanad offices in Oman lose clients: it is never the service quality, it is always the communication gap",
            "The work permit expiry your team missed — and the exact phone call you had to make to the client afterward",
            "Why most Sanad offices plateau at 15–20 clients — and what the operational ceiling is made of",
            "Managing MOL filing deadlines across 20 client companies in a shared Excel file — when exactly does it break?",
            "The government service request that came in by WhatsApp at 8pm — and how your team is expected to handle it",
            "What happens to your Sanad office when your most experienced PRO officer is on leave for two weeks?",
            "Client A calls about their work permit. Client B sends a WhatsApp. Client C emails. Client D walks in. How many hours does this take every single week?",
            "Tracking 80 residency visa expiry dates across 25 companies — what system are you actually using right now?",
            "The ID card renewal request that was submitted, processed, and collected — but nobody told the client",
            "How Omanisation non-compliance quietly builds when you manage 10 client companies from a spreadsheet",
            "The Sanad office that won the contract and lost the client at renewal — what went wrong between those two moments",
            "A clearance application that needed three follow-ups, two visits, and four WhatsApp messages — for one client",
            "What your Sanad office looks like to a client who cannot get a status update without calling you directly",
            "The monthly MOL filing that was late because the file was on a laptop that was being repaired",
            "Managing work permits for a client's 40 employees — how many expiry dates are stored in your head right now?",
            "The visa that was ready for collection for three days before anyone thought to tell the client",
            "Your Sanad office handles work permits, visas, ID cards, clearances, and MOL filings — for how many companies, tracked where exactly?",
            # Pain — growth and scale
            "Why the Sanad offices growing fastest in Oman all share one thing — and it is not location or pricing",
            "At what client count does a Sanad office running on WhatsApp and Excel start making serious mistakes?",
            "The Sanad office owner who cannot take a week off because the entire operation is in their head",
            "How do you onboard a new PRO officer without losing track of open cases mid-handover?",
            "The Sanad office that could not take on a new client because it had no capacity to track one more company",
            # Vision — opportunity and industry direction
            "924 Sanad offices. All staffed by Omani nationals. All serving every company in the country. The ones that digitise their operations first will take the market — the rest will lose clients to them.",
            "What the highest-performing Sanad offices in Oman are doing differently from the average office right now",
            "Sanad offices that give every client a portal to track their own cases are winning the retention game",
            "Government digitisation in Oman is accelerating. The Sanad offices that connect to it early will own the compliance services market.",
            "What a Sanad office with 100 active client companies and zero missed deadlines actually looks like operationally",
            "Why Oman's 924 Sanad offices represent the single biggest untapped B2B software market in the country",
            "The Sanad office that doubled its client capacity without hiring a single new PRO officer — what changed",
            # Proof / feature specific
            "Zero missed permit renewals across 40 client companies for six consecutive months — what makes that possible",
            "What automatic work permit and visa expiry alerts change about the daily routine of a Sanad office team",
            "A client portal that shows every company the live status of every government case — without a single phone call",
            "From WhatsApp intake to structured case tracking: what the first month looks like for a Sanad office that switches",
            "How a Sanad office cut its client status-update calls by 80% in one month — exactly what changed",
            "The service catalog that generates an invoice automatically when a case is closed — what that does for cash flow",
            "One compliance dashboard: every client's work permits, visas, clearances, and MOL filings in a single morning view",
            "What it means to hand a new PRO officer a structured case queue instead of a WhatsApp group and a spreadsheet",
            # Omani-staffing angle
            "Sanad offices are staffed entirely by Omani nationals — the only sector in Oman where 100% Omanisation is mandatory. Here is what that means for how they operate.",
            "Every Sanad office employee is Omani. That is a strength. But when the operation runs on WhatsApp and Excel, it is also a single point of failure.",
            "Sanad offices create direct employment for Omani nationals. SmartPRO Hub is built to make those jobs more professional, more efficient, and more scalable.",
            "Why Sanad offices — 100% Omani-staffed, government-mandated — are the most important B2B channel in Oman that nobody has built software for yet",
            # Sanad AI Assistant angle
            "We built an AI agent that answers any question about Oman government services — work permits, visas, fees, business registration — in Arabic or English. It is free. No login. Try it.",
            "The Sanad AI Assistant: ask it how much a work permit costs, where the nearest licensed Sanad office is, or how to set up a company in Oman. It answers like a PRO officer who has done it hundreds of times.",
            "Most people in Oman have no idea what a work permit actually costs or how long it takes. We built a free AI agent that tells them — with verified government fees, step-by-step, in Arabic or English.",
            "Voice input in Omani Arabic. Instant government fee lookups. Nearby Sanad office matching. Full service quotes. Free. No login. This is the Sanad AI Assistant at www.thesmartpro.io/sanad/assistant",
            "What happens when a company owner can ask an AI 'how do I get a work permit for my new employee?' and get the exact steps, real fees, and a list of licensed Sanad offices near them — instantly, for free",
            "The Sanad AI Assistant finds the nearest licensed Sanad office to you, tells you exactly what it will cost, and walks you through every step. We built this because the information is scattered and confusing.",
        ],
    },

    # ── CONVERSION ───────────────────────────────────────────────────────────────
    # Manually triggered only — FORCE_PILLAR=conversion.
    # Run every 2 weeks, alternating with the regular Mon pain post.
    # Direct offer. Name SmartPro. Clear CTA. No fluff.
    "conversion": {
        "weight":          0.0,  # manual-only; excluded from automatic weighted scheduling
        "segment":         "A",
        "post_type":       ["Social Proof/Milestone"],
        "day":             "Monday",
        "weekday":         0,
        "generate_weekday": -1,  # -1 = not on automatic schedule; manual only
        "publish_day":     "on demand",
        "generate_day":    "on demand",
        "tone":            "direct, specific, confident, zero pressure — make the offer clear and the next step obvious in one read",
        "audience":        "business owners and HR managers in Oman who have seen your content, recognise the problem, and are ready to see a solution",
        "brand_context":   _BRAND_CONTEXT,
        "formats": [
            "Name the exact problem SmartPRO Hub solves, then make the specific offer with one clear next step — no buildup needed",
            "Walk through what a 20-minute SmartPRO Hub demo actually shows — what they will see, what questions it answers, what they will know by the end",
            "List three specific SmartPRO Hub features with the exact pain each one eliminates — close with a direct demo invitation",
            "Open with a qualifying question that identifies the right reader, confirm SmartPRO Hub solves it, state the next step clearly",
            "Lead with a result a SmartPRO Hub user achieved — make it specific and real — then invite the reader to see it for themselves",
            "Before/after: the manual process most Oman businesses run today versus SmartPRO Hub — end with a clear 20-minute demo invitation",
        ],
        "topics": [
            # HR / payroll conversion
            "If you run a business in Oman with 10 or more employees — I want to show you something specific",
            "SmartPRO Hub: one platform for HR, payroll, CRM, client portal, and government compliance in Oman",
            "WPS compliance made fully automatic — what SmartPRO Hub does for Oman businesses every month",
            "What a 20-minute SmartPRO Hub demo shows you — and what you will know by the end of it",
            "Three problems SmartPRO Hub solves that most Oman businesses deal with every single month",
            "If payroll still takes your team more than four hours — there is a faster and more accurate way",
            "What SmartPRO Hub's direct bank integration means for your WPS submission process",
            "Built specifically for Oman: what makes SmartPRO Hub different from generic HR software",
            "See SmartPRO Hub handle your entire payroll run automatically — free 20-minute demo",
            # Client management / CRM conversion
            "If you manage more than five client companies — SmartPRO Hub has a dashboard built for exactly that",
            "Replace the WhatsApp group and the shared spreadsheet: SmartPRO Hub's client portal in 20 minutes",
            "Send a professional quotation, get it signed, deliver the service, generate the invoice — all in one system",
            "What SmartPRO Hub's CRM shows a business owner that a spreadsheet never can",
            # PRO / Sanad conversion
            "If you run a PRO service firm or Sanad office in Oman — this 20-minute demo is built for you",
            "SmartPRO Hub tracks every work permit, visa, and MOL filing across all your clients — automatically",
            "What automatic permit expiry alerts mean for a PRO firm managing 30+ client work permits",
            "See how Sanad offices use SmartPRO Hub to give every client live visibility into their government cases",
            # Contract conversion
            "Sign contracts digitally, store them centrally, get renewal alerts automatically — SmartPRO Hub",
            "The e-signature workflow that replaces printing, scanning, and emailing — see it in 20 minutes",
            # Partner programme conversion
            "SmartPRO Hub's growth partner programme: refer clients, track commissions in real time, get paid automatically",
            "If you know Oman businesses that need better operations — SmartPRO Hub's partner programme rewards every referral",
            # Trial CTA
            "SmartPRO Hub: 14-day free trial, no credit card required — starts at OMR 12/month after trial",
            "Start your SmartPRO Hub trial today: HR, payroll, CRM, client portal, and government compliance from OMR 12/month",
        ],
    },

    # ── JOBS ─────────────────────────────────────────────────────────────────────
    # Auto-triggered when pending jobs exist in smartpro_feed/pending_jobs.json.
    # Announces a specific new job opening with a direct apply CTA.
    "jobs": {
        "weight":           0.0,   # queue-driven only — excluded from scheduled rotation
        "segment":          "A",
        "post_type":        ["Story"],
        "day":              "any",
        "weekday":          -1,
        "generate_weekday": -1,    # triggered by pending_jobs.json queue, not cron
        "publish_day":      "when job is posted",
        "generate_day":     "when job is posted",
        "tone":             "clear, professional, human — describe the role honestly and make the opportunity feel worth pursuing",
        "audience":         "job seekers and professionals in Oman looking for their next role, and their networks who may refer someone",
        "brand_context":    _BRAND_CONTEXT_CANDIDATES,
        "formats": [
            "Open with the role and company type, then describe what makes this specific opportunity worth considering — not just the job spec",
            "Lead with the day-in-the-life of someone in this role — what they would actually do and why it matters to the business",
            "Frame the role as a problem the company is trying to solve — what gap does this hire fill and what does success look like in six months",
            "Open with what the right candidate will gain — growth, team, environment — before listing any requirements",
        ],
        "topics": [],  # set dynamically from pending_jobs.json
    },

    # ── RECRUITMENT ──────────────────────────────────────────────────────────────
    # Weekly data-driven post using live SmartPro platform metrics.
    # Shows the talent engine is active — jobs being posted, candidates applying.
    "recruitment": {
        "weight":           0.0,   # manual-only for now; will auto-schedule once pillar is validated
        "segment":          "A",
        "post_type":        ["Data/Insight"],
        "day":              "Thursday",
        "weekday":          3,
        "generate_weekday": -1,    # manual only: FORCE_PILLAR=recruitment
        "publish_day":      "on demand",
        "generate_day":     "on demand",
        "tone":             "data-driven, platform-confident, market-aware — show that SmartPRO Hub is where Oman hiring is happening right now",
        "audience":         "hiring managers, business owners, and HR leads in Oman who want to reach qualified candidates efficiently",
        "brand_context":    _BRAND_CONTEXT,
        "formats": [
            "Open with a live metric from SmartPRO Hub's platform — applications this week, active jobs, companies hiring — then zoom out on what it means for Oman's job market",
            "Frame the weekly hiring activity as a market signal: what roles are in demand, what companies are growing, what this tells us about where Oman's economy is moving",
            "Build a tight weekly market snapshot: fastest-moving roles, most active industries, candidate-to-job ratio — close with one thing employers should do now",
            "Open with a pattern in the data — then explain why it matters for anyone hiring or being hired in Oman this week",
        ],
        "topics": [
            "What the most applied-for roles on SmartPRO Hub tell us about Oman's job market right now",
            "Hiring velocity this week — which industries are growing fastest and what it signals",
            "The candidate pool is building — what Oman employers need to do to attract the right applications",
            "Jobs posted vs applications received — what the current ratio says about talent competition in Oman",
            "Which locations in Oman are seeing the most hiring activity right now — and what is driving it",
            "What the fastest-growing job categories on SmartPRO Hub reveal about Oman's economy in 2026",
        ],
    },

    # ── PAIN (ARABIC) ────────────────────────────────────────────────────────────
    # Sunday posts — Arabic content targeting Omani business owners and HR managers.
    # Sunday is the first working day of the Oman week — highest attention.
    # Generate Friday (2 days before Sunday publish).
    "pain_ar": {
        "weight":           2.0,
        "segment":          "A",
        "post_type":        ["Story", "Engagement"],
        "day":              "Sunday",
        "weekday":          6,       # Python: Sunday = 6
        "generate_weekday": 4,       # Python: Friday = 4
        "publish_day":      "Sunday",
        "generate_day":     "Friday",
        "language":         "ar",
        "tone":             "متعاطف، مباشر، مدرك للمشكلة — يجب أن يشعر القارئ أنك تصف واقعه بالضبط، لا تبيع له شيئاً",
        "audience":         "أصحاب الأعمال ومديرو الموارد البشرية والمديرون الماليون في شركات عُمان التي تضم ١٠ إلى ٢٠٠ موظف، ولا يزالون يُديرون الرواتب والإجازات والامتثال يدوياً",
        "brand_context":    _BRAND_CONTEXT_AR,
        "formats": [
            "افتح بلحظة فشل محددة — تاريخ حقيقي، تكلفة حقيقية، عاقبة حقيقية يتعرف عليها القارئ فوراً",
            "اذكر الحقيقة المزعجة عن طريقة معظم الشركات في عُمان للتعامل مع هذه المشكلة — كن محدداً وصادقاً لا واعظاً",
            "سِرْ عبر يوم كامل لفريق HR يُدير هذا يدوياً — أظهر كل خطوة مكسورة بالتسلسل",
            "اكتب قائمة مرقّمة من ٤-٥ علامات تحذيرية — كن محدداً بما يكفي ليتعرف القارئ على ثلاث منها على الأقل",
            "قبل وبعد: صِفْ بالضبط كيف تبدو المشكلة دون حل، ثم ما الذي يتغير حين تُحَل",
            "افتح بسؤال يُجبر القارئ على حساب إجابته الخاصة — الوقت الضائع، المال المهدر، المخاطر المحمولة",
        ],
        "topics": [
            "رفض ملف WPS ليلة قبل يوم الراتب — ما الذي يكلفه فعلاً في عُمان؟",
            "كم ساعة يقضي فريق HR لديك في إعداد الرواتب كل شهر؟ وما قيمة هذا الوقت حقاً؟",
            "التكلفة الخفية لإدارة طلبات الإجازة عبر مجموعات واتساب",
            "ماذا يحدث لعمليات شركتك حين يستقيل مدير الموارد البشرية فجأة؟",
            "عقود الموظفين في درج المكتب — لماذا هذا أخطر بكثير مما يظن معظم أصحاب الأعمال",
            "معالجة الرواتب يدوياً لـ٥٠ موظفاً: مخاطر الامتثال التي لا يتحدث عنها أحد",
            "لماذا تفشل الشركات في عُمان في التفتيش الحكومي رغم أنها كانت تستطيع النجاح؟",
            "خطأ حساب الوقت الإضافي الذي يكلف الشركات أموالاً حقيقية كل شهر",
            "إدارة ثلاثة فروع في عُمان بدون نظام موحد للموارد البشرية — ماذا ينكسر أولاً؟",
            "تتبع ٨٠ رصيد إجازة في جدول إكسل مشترك — شخص ما يحصل دائماً على الرقم الخاطئ",
            "لماذا يغادر أفضل موظفيك حين تكون عمليات الموارد البشرية فوضوية؟",
            "ما الذي تكلفه إدارة الموارد البشرية اليدوية فعلاً على مدار عام كامل حين تجمع كل النفقات؟",
            "لماذا النمو من ٢٠ إلى ٥٠ موظف يُفكك معظم أنظمة الموارد البشرية اليدوية؟",
            "نزاع الراتب الذي كان نظام سليم سيمنعه قبل أن يحدث",
            "كل عملية الموارد البشرية في شركتك موجودة في ذهن شخص واحد — ماذا يحدث حين يكون غير متاح؟",
            "الفرق بين معالجة الرواتب ومعالجتها بدقة في كل مرة",
            "الشهر الذي تأخر فيه الراتب ثلاثة أيام لأن المحاسب كان في إجازة مرضية",
            "حين يكشف التفتيش الحكومي ما كان النظام اليدوي يُخفيه طوال هذا الوقت",
        ],
    },

    # ── SANAD / PRO (ARABIC) ─────────────────────────────────────────────────────
    # Tuesday posts — Arabic content targeting Sanad office owners directly.
    # Arabic is the primary language of Omani Sanad office operators.
    # Generate Sunday (2 days before Tuesday publish).
    "sanad_pro_ar": {
        "weight":           2.5,   # highest priority — 924 Omani-staffed offices, Arabic-first audience
        "segment":          "A",
        "post_type":        ["Story", "Engagement"],
        "day":              "Tuesday",
        "weekday":          1,       # Python: Tuesday = 1
        "generate_weekday": 6,       # Python: Sunday = 6
        "publish_day":      "Tuesday",
        "generate_day":     "Sunday",
        "language":         "ar",
        "tone":             "من زميل إلى زميل، عملي، مباشر — اكتب كشخص جلس داخل مكتب سند ويعرف بالضبط كيف يبدو تتبع ٤٠ تصريح عمل و١٥ تأشيرة و٨ تسجيلات وزارة العمل لـ٢٠ شركة عميل بواتساب وإكسل",
        "audience":         "أصحاب ومديرو مكاتب سند الـ٩٢٤ المرخصة في عُمان، ومديرو شركات خدمات PRO، وكل من يُدير معاملات حكومية لشركات متعددة: تصاريح عمل، تأشيرات، بطاقات هوية، تسجيلات، تخليص وزاري",
        "brand_context":    _BRAND_CONTEXT_SANAD_AR,
        "formats": [
            "افتح بلحظة فشل محددة في مكتب سند أو PRO — تأشيرة انتهت صلاحيتها، عميل علم في المطار، تسجيل فات موعده — اجعلها محددة لدرجة توقف القارئ عن التمرير",
            "سِرْ بالتفصيل عبر يوم كامل لمدير مكتب سند يتابع ٢٠+ شركة عميل بدون نظام — كل خطوة مؤلمة بالتسلسل",
            "ابنِ مقارنة حادة قبل/بعد: إدارة الخدمات الحكومية بواتساب وإكسل مقابل SmartPRO Hub — نفس الأسبوع، تجربة مختلفة تماماً",
            "اكتب قائمة مرقّمة من ٥ علامات تدل على أن مكتب السند قد تجاوز طاقته الحالية — كن محدداً بما يكفي ليتعرف معظم القراء على أربع منها",
            "افتح برقم يضع المشكلة في حجمها الحقيقي — ٩٢٤ مكتباً، ٤٠ تصريحاً، ١٥ تأشيرة، ٢٠٠ معاملة شهرياً — ثم أظهر كيف يبدو تتبع هذا الحجم يدوياً",
            "قصة ثقة العميل: مكتب السند الذي بدأ يمنح كل عميل بوابة لتتبع قضاياه بنفسه — ماذا حدث للاحتفاظ بالعملاء والإحالات في أول ثلاثة أشهر",
            "افتح بسؤال يُجبر القارئ على حساب إجابته: كم تصريح عمل تتابعه الآن، وأين بالضبط يوجد هذا السجل؟",
        ],
        "topics": [
            # ألم — الواقع التشغيلي اليومي
            "٩٢٤ مكتب سند في عُمان. يعمل بها مواطنون عُمانيون حصراً. معظمها يُدير ٣٠+ عميل من مجموعة واتساب واحدة.",
            "كيف تخسر مكاتب سند في عُمان عملاءها: ليس بسبب جودة الخدمة، بل بسبب فجوة التواصل",
            "تصريح العمل الذي انتهت صلاحيته في صمت — والمكالمة التي اضطررت لإجرائها مع العميل بعدها",
            "لماذا تتوقف معظم مكاتب سند عند ١٥-٢٠ عميلاً — وما الذي يُشكّل السقف التشغيلي؟",
            "تتبع مواعيد تسجيل وزارة العمل لـ٢٠ شركة عميل في إكسل مشترك — متى بالضبط ينكسر هذا؟",
            "طلب الخدمة الحكومية الذي وصل عبر واتساب الساعة الثامنة مساءً — وكيف يُفترض أن يتعامل معه فريقك",
            "ماذا يحدث لمكتب سندك حين يكون مسؤول PRO الأكثر خبرة في إجازة لأسبوعين؟",
            "عميل أ يتصل بشأن تصريح عمله. عميل ب يرسل واتساب. عميل ج يُرسل بريداً. عميل د يأتي شخصياً. كم ساعة يستغرق هذا كل أسبوع؟",
            "تتبع ٨٠ تاريخ انتهاء تأشيرة إقامة لـ٢٥ شركة — ما النظام الذي تستخدمه الآن فعلاً؟",
            "طلب تجديد بطاقة الهوية الذي أُنجز وسُلّم — لكن لم يُخبر العميل",
            "مكتب السند الذي فاز بالعقد وخسر العميل عند التجديد — ماذا حدث بين اللحظتين؟",
            "معاملة التخليص التي احتاجت ثلاث متابعات وزيارتين وأربع رسائل واتساب — لعميل واحد",
            "إدارة تصاريح عمل موظفي عميل الأربعين — كم تاريخ انتهاء محفوظ في ذاكرتك الآن؟",
            "التأشيرة التي كانت جاهزة للاستلام ثلاثة أيام قبل أن يُخطر أحد العميل بها",
            # ألم — النمو والتوسع
            "لماذا تتشابه مكاتب سند الأسرع نمواً في عُمان في شيء واحد — ليس الموقع ولا السعر",
            "مكتب سند لا يستطيع صاحبه أخذ أسبوع إجازة لأن كل العملية موجودة في رأسه",
            "كيف تُدرّب مسؤول PRO جديداً دون أن تفقد متابعة القضايا المفتوحة أثناء التسليم؟",
            "مكتب السند الذي لم يستطع قبول عميل جديد لأنه لا طاقة تشغيلية لمتابعة شركة إضافية",
            # رؤية — الفرصة واتجاه القطاع
            "٩٢٤ مكتب سند في عُمان. المكاتب التي ترقمن عملياتها في السنتين القادمتين ستأخذ السوق. الباقي سيخسر العملاء لصالحها.",
            "ما الذي تفعله مكاتب سند الأفضل أداءً في عُمان بشكل مختلف عن المتوسط الآن",
            "مكاتب سند التي تمنح كل عميل بوابة لمتابعة قضاياه بنفسه تربح معركة الاحتفاظ بالعملاء",
            "عميل اتصل بمكتب سند منافس لأنك لم ترد في ١٠ دقائق — وهو يعرف أن معاملته انتظرت ثلاثة أيام بدون تحديث",
            "لماذا تُمثّل مكاتب سند الـ٩٢٤ في عُمان — المُشغَّلة بالعُمانيين حصراً — أكبر سوق برمجيات B2B غير مستغل في البلاد",
            # دليل / ميزات محددة
            "صفر تصاريح عمل منتهية الصلاحية لدى ٤٠ شركة عميل في ستة أشهر متتالية — ما الذي جعل هذا ممكناً",
            "ما الذي تغيّره تنبيهات انتهاء صلاحية تصاريح العمل والتأشيرات التلقائية في الروتين اليومي لفريق مكتب سند",
            "بوابة عميل تُظهر لكل شركة الحالة الحية لكل قضية حكومية — دون أي مكالمة هاتفية",
            "من استقبال الطلبات بواتساب إلى تتبع القضايا المنظّم: الشهر الأول لمكتب سند بعد التحول",
            "كيف قلّص مكتب سند مكالمات استفسار العملاء بنسبة ٨٠٪ في شهر واحد — بالضبط ماذا تغيّر",
            "كتالوج الخدمات الذي يُصدر الفاتورة تلقائياً حين تُغلق القضية — ما الذي يفعله هذا للتدفق النقدي",
            "لوحة امتثال واحدة: تصاريح العمل والتأشيرات والتخليص وتسجيلات وزارة العمل لكل عملائك في نظرة صباحية واحدة",
            # مساعد سند الذكي
            "بنينا وكيل ذكاء اصطناعي يُجيب على أي سؤال عن المعاملات الحكومية في عُمان — تصاريح العمل، التأشيرات، الرسوم، تسجيل الشركات — بالعربية أو الإنجليزية. مجاني. بدون تسجيل دخول.",
            "مساعد سند الذكي: اسأله كم تكلفة تصريح العمل، وأين أقرب مكتب سند مرخص، وكيف تؤسس شركة في عُمان. يُجيب كمسؤول PRO متمرس أنجز المعاملة مئات المرات.",
            "معظم أصحاب الشركات في عُمان لا يعرفون بالضبط ما تكلفه تصاريح العمل أو كم تستغرق. بنينا مساعداً ذكياً مجانياً يُخبرهم — بالرسوم الرسمية المعتمدة، خطوة بخطوة، بالعربية أو الإنجليزية.",
            "إدخال صوتي باللهجة العُمانية. بحث فوري في الرسوم الحكومية. مطابقة مع أقرب مكتب سند مرخص. عرض سعر كامل. مجاني. بدون تسجيل. هذا مساعد سند الذكي على www.thesmartpro.io/sanad/assistant",
            "ماذا يحدث حين يستطيع صاحب شركة أن يسأل ذكاءً اصطناعياً: كيف أستخرج تصريح عمل لموظفي الجديد؟ ويحصل على الخطوات الدقيقة والرسوم الحقيقية وقائمة مكاتب سند مرخصة قريبة منه — فوراً ومجاناً",
            "مساعد سند الذكي يجد أقرب مكتب سند مرخص إليك، ويُخبرك بالتكلفة الدقيقة، ويشرح كل خطوة. بنيناه لأن المعلومة كانت متفرقة وغير واضحة — وهذا يُكلّف الشركات وقتاً ومالاً كل يوم.",
        ],
    },
    # ── LEADERSHIP (SEGMENT A) ───────────────────────────────────────────────────
    # Manual-only. Shares leadership principles from running an Oman tech startup.
    # Bridges to SmartPRO Hub at the end — one sentence, natural not salesy.
    "leadership": {
        "weight":           0.0,   # manual-only: FORCE_PILLAR=leadership
        "segment":          "A",
        "post_type":        ["Story", "Data/Insight"],
        "day":              "any",
        "weekday":          -1,
        "generate_weekday": -1,
        "publish_day":      "on demand",
        "generate_day":     "on demand",
        "tone":             "reflective, direct, peer-to-peer — a founder sharing what they've learned running a team in Oman, not a business coach",
        "audience":         "founders, CEOs, and senior managers in Oman who lead teams and think about building a company that works without them",
        "brand_context":    _BRAND_CONTEXT,
        "brand_bridge": (
            "End with one sentence connecting the leadership lesson to how SmartPRO Hub "
            "helps Oman business owners focus on leadership instead of HR administration. "
            "Natural, not salesy. One sentence only. Example: "
            "'This is exactly why SmartPRO Hub exists — so founders spend time on "
            "decisions like this, not on chasing payroll spreadsheets.'"
        ),
        "formats": [
            "Share a specific leadership decision — what you chose, why, and what you learned six months later",
            "Describe a moment your team surprised you — what it revealed about the culture you'd actually built",
            "Before/after: how you handled a team problem the wrong way first, then the right way",
            "Open with a counterintuitive leadership truth — prove it with one specific story from your own experience",
        ],
        "topics": [
            "The hire that changed how I think about delegation",
            "What I got wrong about accountability in the first two years",
            "The performance review I dreaded giving — and what happened when I gave it honestly",
            "How I stopped being the bottleneck in my own company",
            "The meeting that cost us three weeks — and how I prevented it from happening again",
        ],
    },

    # ── MARKETING (SEGMENT A) ────────────────────────────────────────────────────
    # Manual-only. Shares content and growth lessons from building SmartPRO's audience.
    # Bridges to SmartPRO Hub at the end — one sentence, peer-to-peer not promotional.
    "marketing": {
        "weight":           0.0,   # manual-only: FORCE_PILLAR=marketing
        "segment":          "A",
        "post_type":        ["Story", "Data/Insight"],
        "day":              "any",
        "weekday":          -1,
        "generate_weekday": -1,
        "publish_day":      "on demand",
        "generate_day":     "on demand",
        "tone":             "candid, tactical, peer-to-peer — a founder sharing what actually worked in growing a B2B SaaS audience in Oman",
        "audience":         "founders and marketing leads at Oman and GCC companies who are figuring out content and growth without a big team or budget",
        "brand_context":    _BRAND_CONTEXT,
        "brand_bridge": (
            "End with one sentence connecting the marketing lesson to SmartPRO Hub's "
            "own content approach or growth story. Natural, peer-to-peer. One sentence only."
        ),
        "formats": [
            "Share a specific content experiment — what you tested, the result, and what you changed because of it",
            "Open with a counterintuitive growth insight and prove it with your own numbers",
            "Before/after: the marketing approach that wasn't working and what replaced it",
            "A tactical breakdown of one specific thing that drove measurable growth — no theory",
        ],
        "topics": [
            "The LinkedIn post format that drives 3× more comments than any other",
            "Why we stopped running ads and doubled down on content instead",
            "The cold outreach approach that actually gets replies in the GCC market",
            "What 6 months of daily posting taught me about building an audience in Oman",
            "The CTA change that doubled our demo bookings",
        ],
    },

    # ── TECH / BUILD-IN-PUBLIC (SEGMENT C) ───────────────────────────────────────
    # Saturday posts — peer-to-peer technical content targeting engineers and SaaS founders.
    # Candid, first-person, architecture and engineering decisions. No marketing language.
    # Generate Thursday (2 days before Saturday publish).
    "tech": {
        "weight":           1.5,
        "segment":          "C",
        "post_type":        ["Story", "Data/Insight", "Carousel"],
        "day":              "Saturday",
        "weekday":          5,       # Python: Saturday = 5
        "generate_weekday": 3,       # Python: Thursday = 3
        "publish_day":      "Saturday",
        "generate_day":     "Thursday",
        "language":         "en",
        "tone":             "peer-to-peer, technical, candid — write as an engineer who respects the reader's intelligence and shares real tradeoffs without spin",
        "audience":         "tech founders, SaaS builders, and engineers in the GCC and globally who follow build-in-public accounts and care about architecture decisions, stack choices, and what it's like to build a real product",
        "brand_context":    _BRAND_CONTEXT_TECH,
        "formats": [
            "Share a specific architectural decision — what the options were, what you chose, and what you've learned 6 months later",
            "Describe a technical problem that took longer than it should have — what made it hard, what fixed it, what you'd do differently",
            "A sprint retrospective: what shipped, what slipped, what surprised you — honest, specific, no PR spin",
            "Open with a counterintuitive engineering decision and explain the reasoning — readers should come away having learned something concrete",
            "Before/after: a technical approach you changed and why — show the old code in words, the new approach, and the measurable difference",
            "Share a specific number from production that changed how you think about a system design problem",
        ],
        "topics": [
            "Multi-tenant architecture: how we isolate 200+ company workspaces without per-company databases",
            "Why we chose tRPC over REST — and the one place we regret it",
            "4,000 automated tests in a B2B SaaS: what we actually catch vs. what slips through",
            "Building WPS payroll integration with Oman's banking system — the undocumented parts",
            "Drizzle ORM vs Prisma: six months into production, here's what changed our minds",
            "How we handle multi-currency payroll in a single MySQL schema",
            "Sprint retrospective: the feature that took 3 sprints but could have taken 3 days",
            "Building voice AI in Omani Arabic dialect — what Claude handles and what it doesn't",
            "End-of-service gratuity: the edge cases in Oman labour law that break naive implementations",
            "How we built a government fee database that stays current without scraping",
            "Why we didn't use Next.js: our boring stack decision and how it's aged",
            "The performance problem that wasn't: diagnosing a slow dashboard in production",
            "Building the Sanad AI Assistant: from Claude API to production in 6 weeks",
            "How we test Ministry of Labour compliance rules without a staging government API",
            "Shipping to 200 real companies: what breaks that unit tests never catch",
            "The database migration that cost us 4 hours of downtime — and how we'd do it now",
            "Type safety end-to-end in a multi-tenant SaaS: what tRPC + Drizzle actually buys you",
            "Why we open-sourced our WPS file generation library",
            "Building in Oman: the engineering talent market nobody writes about",
            "How we handle timezone complexity when payroll runs at midnight across GCC offices",
            "What 4,000 tests and zero staging environment taught us about production confidence",
            "The Claude AI integration that cut our support ticket volume by 60%",
            "How we priced a B2B SaaS for a market where most competitors charge nothing",
            "Multi-language SaaS: the engineering cost of Arabic RTL support nobody tells you about",
        ],
    },
}


ALL_PILLARS: list[dict] = [{"name": name, **config} for name, config in PILLARS.items()]


def get_pillar_weights() -> dict[str, float]:
    """Return pillar weights from content_analysis.json when available, else PILLARS defaults.

    Source priority:
      1. content_analysis.json → frequency_multipliers  (written by content_feedback.py analyze)
      2. PILLARS[*]["weight"]  (evidence-based priors — proof 3×, pain 2×, vision 1×)

    Once real deal_value / engagement data has accumulated the priors are overridden
    automatically without any manual change to this file.
    """
    defaults = {name: float(cfg.get("weight", 1.0)) for name, cfg in PILLARS.items()}
    try:
        analysis = Path(__file__).parent / "content_analysis.json"
        if analysis.exists():
            data        = json.loads(analysis.read_text(encoding="utf-8"))
            multipliers = data.get("frequency_multipliers", {})
            if multipliers:
                return {k: float(multipliers.get(k, defaults.get(k, 1.0))) for k in defaults}
    except Exception:
        pass
    return defaults


def _recent_pillar_counts(days: int = 21) -> dict[str, int]:
    """Count generated posts per schedulable pillar over the last `days` days."""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    counts: dict[str, int] = {k: 0 for k in PILLARS}
    history = Path(__file__).parent / "posts_history"
    if not history.exists():
        return counts
    for f in history.glob("*.json"):
        try:
            p      = json.loads(f.read_text(encoding="utf-8"))
            pillar = p.get("pillar", "")
            gen_at = p.get("generated_at", "")
            if not pillar or not gen_at:
                continue
            dt = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
            if dt >= cutoff:
                counts[pillar] = counts.get(pillar, 0) + 1
        except Exception:
            continue
    return counts


def _pick_by_weight(
    schedulable: dict[str, dict],
    weights: dict[str, float],
    recent: dict[str, int],
) -> tuple[str, dict]:
    """Pick the schedulable pillar most under-represented relative to its weight target."""
    total_w = sum(weights.get(k, 1.0) for k in schedulable) or 1.0
    total_r = sum(recent.get(k, 0) for k in schedulable) or 1
    name = max(
        schedulable,
        key=lambda k: weights.get(k, 1.0) / total_w - recent.get(k, 0) / total_r,
    )
    return name, PILLARS[name]


def pick_pillar(weekday: int, force: str | None = None) -> tuple[str, dict]:
    """Return the pillar for the given weekday, weighted by conversion performance.

    The scheduled pillar (from generate_weekday) is used by default. If the
    highest-weight schedulable pillar is >30% under-represented relative to its
    fair share of the last 21 days, it substitutes for the scheduled slot —
    gradually shifting generation toward higher-converting content (proof 3×,
    pain 2×, vision 1×) without breaking the fixed cron schedule.

    Conversion pillar (weight=0.0, generate_weekday=-1) is always manual-only.
    """
    if force and force in PILLARS:
        return force, PILLARS[force]

    schedulable = {k: v for k, v in PILLARS.items() if v.get("generate_weekday", -1) >= 0}
    weights     = get_pillar_weights()
    recent      = _recent_pillar_counts(days=21)

    # Pillar scheduled for today's weekday
    scheduled = next(
        (name for name, cfg in schedulable.items() if cfg["generate_weekday"] == weekday),
        None,
    )
    if scheduled is None:
        # Off-schedule trigger — pick most under-represented high-weight pillar
        return _pick_by_weight(schedulable, weights, recent)

    # Check whether the highest-weight pillar is substantially under-represented
    total_weight = sum(weights.get(k, 1.0) for k in schedulable) or 1.0
    total_recent = sum(recent.get(k, 0) for k in schedulable) or 1
    best         = max(schedulable, key=lambda k: weights.get(k, 1.0))
    best_weight  = weights.get(best, 1.0)
    target_share = best_weight / total_weight          # e.g. proof → 3/6 = 0.50
    actual_share = recent.get(best, 0) / total_recent  # e.g. proof → 2/9 = 0.22

    if best != scheduled and actual_share < target_share * 0.70:
        # Highest-weight pillar is >30% below its fair share — substitute this slot
        return best, PILLARS[best]

    return scheduled, PILLARS[scheduled]
