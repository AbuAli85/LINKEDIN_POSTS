# Start Here 👋

This is your LinkedIn growth engine for **SmartPRO Hub**. It writes posts for you,
waits for your OK, publishes them at the right time, and quietly runs outreach in
the background — so you get leads and demo bookings without living inside LinkedIn.

You do **one thing**: review the drafts it writes and say *yes* or *no*.
Everything else is automatic.

---

## The 2‑minute daily routine

Open a terminal in this folder and run:

```bash
python panel.py
```

That's your control panel. It tells you exactly what (if anything) needs you:

```
Drafts waiting for you : 1
Approved & scheduled   : 9
Published all-time     : 61

ACTION NEEDED — drafts waiting for review
  [1] pain         en  -> publish Monday  (1187 chars)
      Most Oman business owners lose 6 hours a week to...
```

If it says **“You're all caught up”**, you're done. Close the terminal. 🎉

If a draft is waiting, do this:

```bash
python panel.py show 1       # read the full post
python panel.py approve 1    # 👍 looks good — it publishes on schedule
# or
python panel.py reject 1     # 👎 not this one — removes it from the queue
```

That's the whole job. Approve good drafts, reject weak ones.

> **No terminal?** You can do everything from the web instead — see
> [“Approve from your phone”](#approve-from-your-phone-no-terminal) below.

---

## What the panel can do

| Command | What it does |
|---|---|
| `python panel.py` | Status overview — what needs you right now |
| `python panel.py review` | List every draft waiting for review, with previews |
| `python panel.py show 1` | Read draft #1 in full |
| `python panel.py approve 1` | Approve it — publishes automatically on its day |
| `python panel.py publish 1` | Publish it to LinkedIn **right now** (asks you to confirm) |
| `python panel.py reject 1` | Remove it from the queue |
| `python panel.py help` | Show all commands |

You can also target a draft by name instead of number, e.g.
`python panel.py show pain`.

---

## What runs on its own (you don't touch this)

Every day, GitHub Actions does this for you:

- **5:00 AM UTC (9 AM Muscat)** — writes the next draft and saves it for your review.
- **6:00 AM UTC (10 AM Muscat)** — publishes any draft you've **approved** for that day.
- Runs the **outreach sequence** to warm leads, and refreshes the **dashboard**.

The weekly content rhythm (each post is drafted 2 days before it publishes):

| Publishes | Post type | Audience |
|---|---|---|
| Monday | Pain (EN) | HR managers & owners |
| Tuesday | Sanad (AR) | HR managers & owners |
| Wednesday | Proof (EN) | HR managers & owners |
| Thursday | Sanad (EN) | HR managers & owners |
| Friday | Vision (EN) | Investors / government |
| Saturday | Tech (EN) | Tech founders / SaaS |
| Sunday | Pain (AR) | HR managers & owners |

Nothing is ever posted without your approval.

---

## Your dashboard

A full visual view lives at **`docs/index.html`** (open it in a browser) and is
published online via GitHub Pages. It shows every post, its status, performance
scores, booking stats, and the outreach pipeline. The panel and the dashboard
always agree — use whichever you prefer.

---

## Approve from your phone (no terminal)

Prefer not to use a terminal? Approve from the GitHub website:

1. Open the **Actions** tab → **Auto-post to LinkedIn** workflow.
2. Click **Run workflow**, choose `approve_draft`, and paste the draft path
   (the panel and dashboard both show it, e.g. `posts_history/20260601_..._pain.json`).
3. The next publish cron posts it automatically.

Same result as `python panel.py approve` — just from the browser.

---

## When something needs attention

| Symptom | What to do |
|---|---|
| Publishing fails with **401** | Your LinkedIn token expired (every ~60 days). Redo steps 3–4 of [`LINKEDIN_SETUP.md`](./LINKEDIN_SETUP.md) and update the `LINKEDIN_ACCESS_TOKEN` secret. |
| Want an email when a draft is ready | Add `RESEND_API_KEY` + `NOTIFY_EMAIL` secrets (see [README](./README.md#draft-ready-notifications)). |
| First-time setup | Follow the [README **Setup** section](./README.md#setup-one-time-15-min) — it's a one-time, ~15‑minute job. |

---

## Going deeper (optional)

You never *need* these, but they're here when you want them:

- **[`README.md`](./README.md)** — full architecture, setup, performance tracking.
- **[`LINKEDIN_SETUP.md`](./LINKEDIN_SETUP.md)** — get / renew your LinkedIn token.
- **[`OUTREACH_MASTER_CALENDAR.md`](./OUTREACH_MASTER_CALENDAR.md)** — the outreach sequence plan.
- **[`COMPANY_SETUP.md`](./COMPANY_SETUP.md)** — the SmartPRO Hub company-page poster.
- **[`ENRICH_LEADS.md`](./ENRICH_LEADS.md)** — optional Apollo / Bright Data lead enrichment.

---

**The bottom line:** run `python panel.py` once a day, approve the good drafts,
and let the rest run itself. That's the system. 🚀
