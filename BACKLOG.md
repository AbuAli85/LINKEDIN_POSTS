# Backlog

Deferred decisions and known gaps. Each entry says what it is, why it is not
being built now, and what would unblock it — so a later reader does not
rediscover the reasoning from scratch.

## Deferred: WhatsApp as an outreach next-action

**Status: deferred, product decision. Do not build toward it.**

The outreach chain's next-action is the existing LinkedIn DM sequence
(`outreach.py send-sequences` → connection request at step 1, DMs at steps
2–5). That is the channel that actually exists.

WhatsApp appears in the pipeline **only** as a `wa.me` CTA link inside post
bodies and newsletter footers (`links.py:100`). There is no WhatsApp API
integration, and nothing in the repo sends a WhatsApp message.

Making WhatsApp a real next-action needs a WhatsApp Business API decision
first — provider, number verification, template-message approval, and the
opt-in rules that come with it. That is a product and compliance decision,
not a wiring change, so no code should assume it is coming.

Recorded 2026-08-18, owner decision.

## Done: high-intent leads auto-promote into the tracker

Closed 2026-08-18. `outreach.py promote-leads` runs after `export` in the
daily scan and moves every `intent: high` qualified commenter into
`outreach_tracker.json` at step 1 of the LinkedIn DM sequence, deduped on the
normalised profile URL. Before this, a lead scored "high" only ever reached
`leads.csv`, and entering the sequence needed someone to run `manual-capture`
by hand.

## Open defects — document expiry alerts

Carried from the TEST-SWEEP-003 verification of 2026-08-18. The launch posts
name the first two; all five are in
`ANNOUNCEMENT_EXPIRY_ALERTS_SOURCING.md`.

1. Alert carries no document reference number.
2. `/company/documents` renders English strings in Arabic mode.
3. Ghost alerts — three identical rows for one document on
   `/company/documents/intelligence`; `/alerts` is clean.
4. RTL notification dropdown is 84% clipped off-canvas and its contents stay
   English in Arabic mode.
5. Alert email href still emits `www.thesmartpro.io`; the redirect absorbs it.

## Scheduled

Dated reminders live in `campaign_reminders.json` and fire by email from
`.github/workflows/campaign-reminder.yml` (daily, 04:30 UTC). Currently
queued: regenerate the day-13 launch recap with real numbers on 29 Aug.
