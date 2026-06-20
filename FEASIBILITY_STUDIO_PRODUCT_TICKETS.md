# Feasibility Studio — Product Tickets (thesmartpro.io)

Findings from a live review of `https://www.thesmartpro.io/feasibility-studio` on 2026-06-21
(Next.js + tRPC app). The page is in good shape overall: clean console, working 24-step
flow, progress saved/resumable, strong PDPL consent gate, clear disclaimers, full EN/AR
RTL, and all footer pages (privacy, terms, loan-guide, compliance-checker, activity-guide)
return 200.

These tickets are the gaps worth fixing — ordered by priority. Note: the LinkedIn posting
system now drives traffic here biweekly, so the share-card ticket (FS-3) directly affects
click-through.

---

## FS-1 — Language toggle wipes in-progress answers  ·  Priority: P0 (data loss)

**What:** Switching EN↔AR mid-flow resets the wizard to step 0 and clears all answers
already entered.

**Evidence:** After entering several answers then toggling to Arabic, `localStorage`
key `smartpro.feasibility.progress` showed `savedQIdx: 0, savedAnswers: {}` — the prior
answers were gone. The completed-studies list (`smartpro.feasibility.apps`) persists fine;
it's only the *in-progress* session that is lost.

**Impact:** A bilingual user 18/24 questions in who switches language loses ~8 minutes of
work. High abandonment risk for exactly the EN/AR audience the tool targets.

**Suggested fix:** Persist `savedAnswers`/`savedQIdx` across language switch; only swap the
display language and re-render the existing answers. Re-translate question/label strings
without resetting state.

**Acceptance:** Enter 3+ answers → toggle language → all answers retained, position
preserved, only UI language changes.

---

## FS-2 — No "Resume previous study" entry point  ·  Priority: P1

**What:** Completed/started studies are saved (`smartpro.feasibility.apps`, e.g.
`[{"id":...,"bizName":"Al Waha Bakery","targetBank":"prog1","date":...,"lang":"en"}]`)
but there is no UI to resume or reopen them — a returning user starts from scratch.

**Suggested fix:** On load, if saved studies exist, show a "Resume / view your studies"
list (business name + date + program) above "Let's start". Allow reopen and re-download.

**Acceptance:** A returning user sees their prior study and can resume or re-export it.

---

## FS-3 — Add OG/share meta + image for the page  ·  Priority: P1 (affects CTR)

**What:** Confirm `/feasibility-studio` has Open Graph / Twitter meta (`og:title`,
`og:description`, `og:image`, `twitter:card`) so LinkedIn renders a rich card.

**Why:** LinkedIn posts now link here on a biweekly cadence (UTM:
`utm_campaign=feasibility`). A bare link vs. a branded card materially changes
click-through.

**Suggested fix:** Add a 1200×627 OG image (clear value prop: "Bank-ready feasibility
study, free, ~10 min — all 10 DBO/Riyada programs"), bilingual-friendly, plus matching
`og:*`/`twitter:*` tags. Validate with LinkedIn Post Inspector.

**Acceptance:** LinkedIn Post Inspector shows a correct title/description/image for the URL.

---

## FS-4 — Verify & polish end-to-end document generation/export  ·  Priority: P2

**What:** The intro promises "9 professional documents." The review walked the first ~6 of
24 steps but did not complete the financials, so the final generation + PDF/export step was
not exercised end-to-end.

**Suggested fix:** Run a full pass to confirm all 9 documents render correctly (EN and AR,
RTL), the financial sections compute, and export (PDF/download) works on mobile + desktop.
Add a sample/preview of the output near the top so users see the value before investing
10 minutes.

**Acceptance:** A complete run produces all 9 documents with correct formatting in both
languages; a visible sample/preview exists pre-start.

---

## FS-5 — (Optional) Lead capture → funnel into /demo  ·  Priority: P3

**What:** The tool is a strong free lead magnet but currently has no capture step tying it
to the sales funnel.

**Suggested fix:** Optionally offer to email the finished documents (with consent), and on
completion surface a soft next step to `/demo` ("Want SmartPRO Hub to run the business you
just modelled? Book a 30-minute demo"). Keep it opt-in and PDPL-compliant (consistent with
the existing consent gate).

**Acceptance:** Completion screen offers an opt-in email + a /demo next step; captured leads
flow to the CRM/funnel.

---

_Generated from a Claude-in-Chrome live review. The posting-side integration (CTA, pillar,
biweekly rotation) is already done in this repo; these tickets are for the web app only._
