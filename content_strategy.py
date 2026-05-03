"""Content strategy: SmartPro — HR, Payroll & Operations platform for Oman businesses."""

# Update these when you have live contact details
DEMO_CTA  = "DM me 'DEMO' on LinkedIn or WhatsApp and I will set it up."
BRAND_URL = "thesmartpro.io"

_BRAND_CONTEXT = (
    "BRAND CONTEXT: You are writing on behalf of SmartPro — an end-to-end HR, payroll, "
    "and business operations platform built for companies in Oman. It integrates directly "
    "with Omani banks for WPS (Wage Protection System) submission and with government systems "
    "including the Ministry of Manpower. Target buyers: business owners, HR managers, and "
    "finance managers in Oman running companies with 10–200 employees. The goal of every post "
    "is to build trust, surface a pain point the reader recognises, and generate demo requests. "
    f"Website: {BRAND_URL}. Demo CTA: {DEMO_CTA}"
)

PILLARS = {
    # ── PAIN ─────────────────────────────────────────────────────────────────────
    # Monday posts. Surface the operational pain Oman business owners feel daily.
    # Never mention SmartPro by name — just make the reader feel seen and understood.
    "pain": {
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
            "The onboarding process that makes a new hire question whether they made the right choice",
            "What manual HR really costs over a full year when you total every hidden expense",
            "Why growing from 20 to 50 employees breaks most manual HR and payroll systems",
            "The salary dispute that a proper system would have prevented entirely",
            "Your entire HR operation exists in one person's head — what happens when they are unreachable",
            "The difference between processing payroll and processing it accurately every time",
        ],
    },

    # ── PROOF ────────────────────────────────────────────────────────────────────
    # Wednesday posts. Show concrete evidence that the problem is solvable.
    # Specific numbers, real outcomes, before/after. Build credibility without hype.
    "proof": {
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
            "What happened to staff turnover when HR operations started working properly",
            "The direct bank integration that eliminated manual WPS submission permanently",
            "How one founder recovered eight hours every week by automating business operations",
            "Employee self-service: what changes when staff can check their own leave balance anytime",
            "Processing 200 salaries in a single run — what that means in practice for the team",
            "What the HR team said after their first fully automated payroll run",
            "Government integration that used to consume a full week — now handled in real time",
            "How data accuracy changed the hiring decisions at one Oman business",
            "The operations dashboard that gave a CEO genuine visibility into their business for the first time",
            "What end-to-end actually means when HR, payroll, and operations are in one connected system",
            "How proper contract management stopped a costly labour dispute before it escalated",
            "The company that scaled from 30 to 120 employees without adding HR headcount",
            "Real numbers: what manual HR was costing annually before the switch",
            "How accurate labour cost data changed the way one owner made pricing decisions",
        ],
    },

    # ── VISION ───────────────────────────────────────────────────────────────────
    # Friday posts. Speak to where Oman business is heading.
    # Ambitious, forward-looking. Makes the reader want to be part of what is coming.
    "vision": {
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
            "The platform economy and what it means for service businesses operating in Oman",
            "What world-class operations look like when you are building the whole thing from Muscat",
        ],
    },

    # ── CONVERSION ───────────────────────────────────────────────────────────────
    # Manually triggered only — FORCE_PILLAR=conversion.
    # Run every 2 weeks, alternating with the regular Mon pain post.
    # Direct offer. Name SmartPro. Clear CTA. No fluff.
    "conversion": {
        "day":             "Monday",
        "weekday":         0,
        "generate_weekday": -1,  # -1 = not on automatic schedule; manual only
        "publish_day":     "on demand",
        "generate_day":    "on demand",
        "tone":            "direct, specific, confident, zero pressure — make the offer clear and the next step obvious in one read",
        "audience":        "business owners and HR managers in Oman who have seen your content, recognise the problem, and are ready to see a solution",
        "brand_context":   _BRAND_CONTEXT,
        "formats": [
            "Name the exact problem SmartPro solves, then make the specific offer with one clear next step — no buildup needed",
            "Walk through what a 20-minute SmartPro demo actually shows — what they will see, what questions it answers, what they will know by the end",
            "List three specific SmartPro features with the exact pain each one eliminates — close with a direct demo invitation",
            "Open with a qualifying question that identifies the right reader, confirm SmartPro solves it, state the next step clearly",
            "Lead with a result a SmartPro user achieved — make it specific and real — then invite the reader to see it for themselves",
            "Before/after: the manual process most Oman businesses run today versus SmartPro — end with a clear 20-minute demo invitation",
        ],
        "topics": [
            "If you run a business in Oman with 10 or more employees — I want to show you something specific",
            "SmartPro: one platform for HR, payroll, and business operations built for Oman",
            "WPS compliance made fully automatic — what SmartPro does for Oman businesses every month",
            "What a 20-minute SmartPro demo shows you — and what you will know by the end of it",
            "Three problems SmartPro solves that most Oman businesses deal with every single month",
            "If payroll still takes your team more than four hours — there is a faster and more accurate way",
            "What SmartPro's direct bank integration means for your WPS submission process",
            "Built specifically for Oman: what makes SmartPro different from generic HR software",
            "See SmartPro handle your entire payroll run automatically — free 20-minute demo",
            "SmartPro: HR, payroll, operations, government compliance — one connected platform for Oman",
        ],
    },
}


def pick_pillar(weekday: int, force: str | None = None) -> tuple[str, dict]:
    """Return the pillar for the given weekday, or the forced override.

    Scheduled crons fire on generate_weekday (Sat/Mon/Wed).
    The conversion pillar (generate_weekday=-1) is excluded from scheduled matching
    and must be triggered manually via FORCE_PILLAR=conversion.
    """
    if force and force in PILLARS:
        return force, PILLARS[force]
    for name, config in PILLARS.items():
        if config["generate_weekday"] == weekday:
            return name, config
    schedulable = {k: v for k, v in PILLARS.items() if v["generate_weekday"] >= 0}
    name = min(schedulable.items(), key=lambda x: (x[1]["generate_weekday"] - weekday) % 7)[0]
    return name, PILLARS[name]
