# Cal.com → GitHub Booking Tracker — Setup Guide

When a visitor books a demo or investor briefing via the SmartPRO Hub pages, the booking is recorded in `bookings.json` and the dashboard is rebuilt automatically. This guide explains how to wire that up.

---

## How it works

```
Visitor books on Cal.com
        ↓
Cal.com fires a webhook to Make.com (or your relay)
        ↓
Make.com sends a GitHub repository_dispatch event
        ↓
record-booking.yml workflow runs on GitHub Actions
        ↓
bookings.json is appended; dashboard.py rebuilds docs/
```

The `record-booking.yml` workflow expects a `repository_dispatch` event with type `cal_booking` and a `client_payload` containing:

```json
{
  "event_type": "smartpro-demo",
  "booked_at": "2026-05-18T10:30:00Z",
  "attendee": {
    "name": "Aisha Al-Balushi",
    "email": "aisha@example.com",
    "phone": "+96890000000",
    "company": "Al-Balushi Trading",
    "linkedin": "https://www.linkedin.com/in/aisha-al-balushi",
    "message": "Interested in WPS + Omanization tracking"
  },
  "utm": {
    "utm_source": "linkedin",
    "utm_medium": "post",
    "utm_campaign": "wps-pain-en",
    "utm_content": "cta-link"
  }
}
```

> **Map the attendee fields in your Make.com relay.** Cal.com's webhook payload
> already contains the attendee under `payload.attendees[0]` (name, email,
> timeZone) plus any custom booking-question `responses` (phone, company,
> LinkedIn). Map those into the `attendee` object above so each booking becomes
> a complete, contactable lead — not just an anonymous UTM hit. `lead_intake.py`
> then turns every contactable booking into a ready-to-send, attributed follow-up.

---

## Step 1 — Create a GitHub Personal Access Token

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token (classic)**
3. Name it `cal-booking-webhook`
4. Set expiry to **1 year** (or no expiry)
5. Check **`repo`** scope (needed to trigger `repository_dispatch`)
6. Click **Generate token** and copy it — you will need it in Step 3

---

## Step 2 — Set up a Cal.com webhook

1. Log in to **Cal.com → Settings → Developer → Webhooks**
2. Click **New Webhook**
3. Set the **Subscriber URL** to your Make.com webhook URL (from Step 3)
4. Select trigger: **Booking Created**
5. Enable the webhook and save

Cal.com will POST a JSON payload to that URL every time a booking is confirmed.

---

## Step 3 — Create a Make.com scenario

Make.com acts as the relay between Cal.com (no custom headers support) and GitHub.

### Modules in order:

**Module 1 — Webhooks → Custom webhook**
- Click **Add** → name it `cal-booking-relay`
- Copy the webhook URL — this is what you paste in Cal.com (Step 2)

**Module 2 — HTTP → Make a request**
- URL: `https://api.github.com/repos/AbuAli85/LINKEDIN_POSTS/dispatches`
- Method: `POST`
- Headers:
  ```
  Authorization: Bearer <your-github-pat-from-step-1>
  Accept: application/vnd.github+json
  X-GitHub-Api-Version: 2022-11-28
  Content-Type: application/json
  ```
- Body type: `Raw`
- Content type: `application/json`
- Body (map Cal.com fields into the payload):

```json
{
  "event_type": "cal_booking",
  "client_payload": {
    "event_type": "{{1.payload.eventType.slug}}",
    "booked_at": "{{formatDate(now; \"YYYY-MM-DDTHH:mm:ssZ\")}}",
    "utm": {
      "utm_source": "{{1.payload.responses.utm_source.value}}",
      "utm_medium": "{{1.payload.responses.utm_medium.value}}",
      "utm_campaign": "{{1.payload.responses.utm_campaign.value}}",
      "utm_content": "{{1.payload.responses.utm_content.value}}"
    }
  }
}
```

> **Note:** Cal.com passes UTM params in `responses` only if you added hidden UTM fields to your event type (see Step 4). Alternatively, the SmartPRO Hub pages append UTMs directly to the Cal.com iframe URL — Cal.com captures those automatically in `metadata.utm_*` fields. Adjust the Make.com mapping accordingly if your Cal.com plan exposes `metadata`.

**Activate the scenario** — set it to run **immediately** (not on a schedule).

---

## Step 4 — Add hidden UTM fields to Cal.com event types (optional but recommended)

This ensures UTM params are preserved even if the visitor refreshes.

1. In Cal.com, open the **SmartPRO Demo** event type → **Advanced → Custom inputs**
2. Add four fields with identifiers: `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`
3. Set each as **Hidden** type
4. Repeat for the **SmartPRO Investor** event type

---

## Step 5 — Add secrets to the GitHub repository

The `record-booking.yml` workflow needs LinkedIn credentials to rebuild the dashboard:

1. Go to **GitHub → AbuAli85/LINKEDIN_POSTS → Settings → Secrets and variables → Actions**
2. Ensure these secrets exist (they should already be set for the auto-post workflow):
   - `LINKEDIN_ACCESS_TOKEN`
   - `LINKEDIN_AUTHOR_URN`

No additional secrets are needed — the `repository_dispatch` call uses the PAT you configured in Make.com, not a repo secret.

---

## Step 6 — Test the integration end-to-end

**Option A — Live test:**
1. Open the SmartPRO Demo page with UTM params:
   `https://smartpro-hub.com/demo?utm_source=linkedin&utm_medium=post&utm_campaign=test-booking`
2. Book a slot using a test email
3. Check **GitHub Actions → record-booking** — the workflow should run within seconds
4. Check `bookings.json` for the new entry
5. Check **GitHub Pages dashboard** — the "Bookings from LinkedIn" section should update

**Option B — Manual trigger (no real booking needed):**
```bash
curl -X POST https://api.github.com/repos/AbuAli85/LINKEDIN_POSTS/dispatches \
  -H "Authorization: Bearer <your-github-pat>" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "cal_booking",
    "client_payload": {
      "event_type": "smartpro-demo",
      "booked_at": "2026-05-18T12:00:00Z",
      "utm": {
        "utm_source": "linkedin",
        "utm_medium": "post",
        "utm_campaign": "test-manual",
        "utm_content": ""
      }
    }
  }'
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Make.com HTTP module returns 401 | GitHub PAT expired or wrong scope | Re-generate PAT with `repo` scope |
| Make.com HTTP module returns 404 | Wrong repo owner/name in URL | Check the dispatches URL |
| `record-booking.yml` not triggered | Event type mismatch | Must be exactly `cal_booking` |
| `bookings.json` updated but dashboard not rebuilt | `pip install -r requirements.txt` failed | Check workflow logs; ensure `requirements.txt` is up to date |
| UTM fields empty in `bookings.json` | Cal.com not passing UTM metadata | Use iframe URL approach (DemoPage.tsx already handles this via sessionStorage) |
| Workflow runs but shows `utm_source: ""` | Visitor arrived without UTM params | Expected — only LinkedIn-sourced traffic carries UTMs |

---

## Dashboard KPIs updated by this flow

The dashboard's **"Bookings from LinkedIn"** section shows:

- **This week** — bookings in the last 7 days where `utm_source == "linkedin"`
- **Total from LinkedIn** — all-time LinkedIn-attributed bookings
- **Demo calls** — bookings where `event_type` contains `"demo"`
- **Investor briefings** — bookings where `event_type` contains `"investor"`
- **Top campaign** — the `utm_campaign` value with the most bookings

These update automatically each time `record-booking.yml` commits to the repo and GitHub Pages rebuilds.
