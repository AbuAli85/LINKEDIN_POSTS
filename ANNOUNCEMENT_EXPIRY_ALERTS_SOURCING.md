# Sourcing ledger — document-expiry alert announcement

**Draft:** `posts_history/20260818_122149_proof.json` · pillar `proof` · segment A ·
publish_day Wednesday · 1479 chars · status `draft`, awaiting human approval.

Per `smartpro-voice` step 8: every concrete claim in the post is listed here with
what it rests on, and every claim with nothing behind it is named. `_validate()`
enforces mechanics only — length, links, hashtags, markdown, mojibake, banned
phrases, fabricated testimonials. Sourcing, product state and clearance are human.

**Evidence base:** the TEST-SWEEP-003 verification session of 2026-08-18
(Asia/Muscat), run against production `thesmartpro.io`. Document under test:
Municipality Licence / رخصة البلدية, issuer بلدية مسقط, expiry 2026-09-12.

## Claims in the post

| Claim | Rests on |
|---|---|
| The pre-fix alert told the reader to renew the CR first | 2:38 PM email, verbatim: «…ولديك 1 تصريح عمل ساري — يرجى تجديد السجل التجاري أولاً.» / "…and you have 1 active work permit — renew the CR first." — on a Municipality Licence alert |
| Caught in our own test sweep | TEST-SWEEP-002 run, delivered to the founder's own inbox. No client received it |
| A municipality licence 25 days from expiry | 2026-08-18 → 2026-09-12, Asia/Muscat = 25 days |
| Fixed; the alert is live | 3:41 PM post-fix email carries no CR clause. Fix landed between 14:38 and 15:41. Sender `noreply@thesmartpro.io`, deep link resolves on the live site |
| Email carries document name, issuing authority, exact expiry date | 3:41 PM email: الوثيقة **رخصة البلدية** · الجهة المصدرة **بلدية مسقط** · تاريخ الانتهاء **2026-09-12** |
| Arabic and English in one message; Arabic RTL and formal | Same email — Arabic heading right-aligned, label column right, values left; English block below in LTR. Body is MSA (فصحى) |
| 25 on the document card, the alerts page, the email subject in both languages, the run history | Card badge `25d left` · `/alerts` chip `25 days` and sentence "expires in 25 days" · subject خلال **25** يومًا / "expires in **25** days" · Run History `25d` |
| Fires once — three engine runs, no second email, no second run-history row | Runs 2 and 3 both returned "0 cases created, 0 triggered". Triggered counter held at 3, Failed 0. One TEST-SWEEP-003 row at 15:41. `/alerts` still "Showing 1 alert". Gmail unchanged — latest still 3:41 PM |
| The alert carries no document reference number | `TEST-SWEEP-003` returns nothing in Gmail search; absent from alert text and email. Present only in the `/alerts` row title and document card |
| Parts of the documents screen still render in English in Arabic mode | `/company/documents` in Arabic still shows `All (3)`, `No:`, `Expires:`, `Issued:`, `25d left`, `Valid`, `Expired`, `View`, `Extracted Documents` |

Nothing in the post is unsourced. No client, no volume, no outcome, and no
revenue figure is claimed — the deleted `proof` drafts of 2026-08-03 are the
precedent for why.

## Deliberately excluded

Open defects from the same session that the post does **not** assert away, and
does not mention:

1. **Ghost alerts on `/company/documents/intelligence`** — three byte-identical
   "expires on 2026-09-12" rows for one document; 001/002 leftovers survive
   deletion on that surface. `/alerts` is clean. This is why the post's dedup
   claim is scoped to "no second row in the run history" rather than a general
   "no duplicates" — the narrower sentence is the one the evidence supports.
2. **RTL notification dropdown** — panel spans x = −267 → 51 in a 1534px
   viewport, 84% clipped past the left edge, and its contents stay English in
   Arabic mode. The post therefore claims RTL correctness for the **email
   only**, never for the notification UI.
3. **Email href retains `www.`** — emitted as
   `https://www.thesmartpro.io/company/documents/intelligence`; the redirect
   absorbs it and the landing page is correct. Cosmetic, not post-worthy.

Defects 1 and 2 are the reason the post does not say "Arabic throughout" or
"no duplicates". If either is fixed, this ledger is the record of what the
published post already committed to — do not widen a live claim retroactively.

## Cleared against the standing gates

- **Counsel gate (Article 61 / gratuity):** not engaged. The post makes no
  gratuity, accrual, or split-period claim.
- **Omanisation gate:** not engaged. No sector percentage, no cadence, no
  omanisation alerting claim.
- **Product-state:** the feature is live in production, unflagged. Verified by
  execution, not by reading source.

---

# Campaign: `document-alerts-launch`

**Spec status: satisfied as-built, 2026-08-18.** These seven were drafted from
the six themes the owner listed plus the two sourcing rules recorded below, not
from a written campaign document — none exists in this repo, and `grep` finds
the tag nowhere else. The owner reviewed the drafts and accepted them as
matching the original prompt's intent, so no reconciliation pass is outstanding.
If a written spec surfaces later, this section is the record of what was
actually built and why.

Seven posts, tagged `campaign: "document-alerts-launch"` with `campaign_day` on
each. Day 1 is the announcement above (already approved). Days 2–13 are drafts
awaiting approval. All clear `generator._validate()`; `require_link=True` for
every post except day 4, whose pillar CTA (`CTA_TECH`) carries no URL.

| Day | publish_day | Pillar | Seg | Chars | File |
|---|---|---|---|---|---|
| 1 | Wednesday | proof | A | 1479 | `20260818_122149_proof.json` (approved) |
| 2 | Thursday | pain | A | 1462 | `20260818_131104_pain.json` |
| 4 | Saturday | tech | C | 1494 | `20260818_131105_tech.json` |
| 6 | Monday | pain | A | 1493 | `20260818_131106_pain.json` |
| 8 | Wednesday | proof | A | 1477 | `20260818_131107_proof.json` |
| 10 | Friday | sanad_pro | A | 1287 | `20260818_131108_sanad_pro.json` |
| 13 | Monday | proof | A | 1493 | `20260818_131109_proof.json` |

## Sourcing per post

**Day 2 — cost of an expired licence.** Carries **no rial figure**, by
instruction: no Omani penalty amount is verified. The cost is stated
qualitatively — stopped transactions at a government counter, days the PRO
spends chasing a renewal, fine exposure, standing with authorities. The one
concrete claim is owner-supplied and first-party: *the first violation the
system caught was our own expired OCCI certificate.* The "90 days out" figure
is **owner-supplied product state**, not something this session verified —
the only alerting interval observed in TEST-SWEEP-003 was 25 days.

**Day 4 — build story.** Every claim traces to the TEST-SWEEP-003 session
recorded above: the CR clause on a municipality-licence alert, the fix landing
between 14:38 and 15:41, day-count parity, three engine runs producing no
second email and no second run-history row, and the two gaps left open. The
post says "five surfaces" and lists five; the session measured six numeric
surfaces, with the two `/alerts` readings collapsed into one line.

**Days 6 and 8 — sector document loads.** Owner-supplied from the SmartPRO
`document_types` catalogue shipped in production, not from external research.
Logistics: driver licences per driver, vehicle mulkiya, operating cards,
vehicle inspection certificates — 20+ documents for a 12-driver fleet beyond
the company's own CR / OCCI / municipality set. F&B: health certificates per
employee, food-safety licence per branch, municipality licence per branch. Both
posts claim only what the product tracks; no sector rule, ministry, or penalty
is named.

**Day 10 — Sanad offices.** Reuses the verified document set and the
per-client shape. No client count, no office name, no outcome claim.

**Day 13 — recap.** Restates days 1–4 and both still-open defects. Metrics are
left as `[DEMOS_BOOKED]`, `[DOCS_TRACKED]`, `[ALERTS_SENT]` — **square
brackets, not braces**: `_validate()` rejects any `{` or `}` as an
un-interpolated placeholder, confirmed by running it. Fill them before
approving; the post must not publish with the brackets in place.

## Two scheduling facts worth knowing before approving

**Days 6 and 13 share Monday.** `publish_approved` takes the *oldest* approved
draft whose `publish_day` matches today, and the files carry sequential
timestamps, so 24 Aug publishes day 6 and 31 Aug publishes day 13. Approving
them out of order does not change this — the timestamp decides, not the
approval time.

**Day 13 has 1.3 days of slack against queue hygiene.** `expire_stale()` rejects
any non-terminal draft older than `MAX_AGE_DAYS = 14`, and it does **not** skip
approved drafts — that is deliberate, so an aged approved draft cannot publish
after the facts move. The day-13 draft is 12.7 days old at its 31 Aug sweep. If
that Monday slips by two days, or a sweep fails and the post lands on the
following Monday, the draft auto-rejects instead of publishing. Either
regenerate it nearer the date or raise `MAX_AGE_DAYS` for the campaign window.
