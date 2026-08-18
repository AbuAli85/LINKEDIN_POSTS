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
