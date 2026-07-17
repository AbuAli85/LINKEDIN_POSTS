# Company Page Setup — Decision Record

> **Status (2026-05-22):** ❌ **Direct company-page posting is not pursued.** The company pipeline publishes to Fahad's personal feed under the SmartPro brand voice, and tracks everything in `company_posts_history/`. This is the permanent design, not a workaround. Reasoning below.

---

## Why we are not chasing a real org token

The original plan (kept in [Appendix A](#appendix-a-the-original-org-token-plan-do-not-pursue) for the record) was to mint a `LINKEDIN_ORG_TOKEN` with `w_organization_social` scope and publish directly to the SmartPro Hub page. After investigating the LinkedIn Developer dashboard on 2026-05-22, this path is not realistically available to us:

1. **Marketing Developer Platform no longer exists as a single product.** LinkedIn restructured it. The capability we needed is now in **Community Management API**.
2. **Community Management API is restricted.** On our app, the "Request access" button is greyed out with no public application form. LinkedIn reserves this product for their Marketing Partner Program (Buffer, Hootsuite, Sprout Social, Publer, etc.). Individual developers and small businesses are not accepted directly.
3. **The personal feed is the better channel anyway.** Fahad's profile has 28k+ followers and direct audience engagement. The company page is a logo people click through after seeing a personal post. B2B reach in 2026 is human-to-human on LinkedIn — company pages are secondary.

**Net:** Spending more time on LinkedIn app approvals is negative ROI. The current setup ships the same content via the channel that performs better.

---

## How the company pipeline actually works today

The file [`.github/workflows/auto-post-company.yml`](.github/workflows/auto-post-company.yml) runs on its own schedule (06:30 / 07:15 UTC) and:

- Reads `LINKEDIN_AUDIENCE=company` at the job level
- Maps the personal secrets to the org variable names:
  ```yaml
  LINKEDIN_ORG_TOKEN: ${{ secrets.LINKEDIN_ACCESS_TOKEN }}
  LINKEDIN_ORG_URN:   ${{ secrets.LINKEDIN_AUTHOR_URN }}
  ```
- Drafts use the **company content strategy** (`company_content_strategy.py`) — pillars `product_proof`, `feature_spotlight`, `oman_market`, `hiring`, `partnership`
- Drafts are saved in `company_posts_history/` (separate from `posts_history/`)
- Publishes to Fahad's personal feed when approved
- Skips the Sanad CTA comment (the `post_cta_comment` function in `publisher.py` already special-cases `audience=company` to avoid double-promoting)

The personal pipeline (`auto-post.yml`) continues unchanged on its own cron and history folder.

---

## What to do when something breaks

| Symptom | Fix |
|---|---|
| `LINKEDIN_ORG_TOKEN and LINKEDIN_ORG_URN are required` in a workflow log | Check that both `secrets.LINKEDIN_ACCESS_TOKEN` and `secrets.LINKEDIN_AUTHOR_URN` are populated. Both company jobs (`post` and `sweep`) must map these into the `LINKEDIN_ORG_*` env vars. |
| `LinkedIn rejected the access token (401)` | Personal token has expired (60-day rolling) or lost scope. Re-run the OAuth flow in `LINKEDIN_SETUP.md` and update the `LINKEDIN_ACCESS_TOKEN` secret. |
| Draft stuck in `status: failed` | After fixing the underlying cause, reset its JSON to `status: approved`, `published: false`, clear `publish_error`, and trigger Actions → Auto-post (Company) → Run workflow → `publish_approved`. |

---

## What would make us revisit this

We would only re-open the direct-org-posting path if **all** of the following become true:

1. SmartPro grows to the point where the company page has more reach than Fahad's personal feed.
2. LinkedIn opens Community Management API to non-partner developers, **or** SmartPro qualifies for the Marketing Partner Program.
3. We have a dedicated content person who needs separate publishing controls.

Until then, the answer is no.

---

## Appendix A — The original org-token plan (do not pursue)

This is preserved for context. **Do not follow these steps.** They reference a LinkedIn product (Marketing Developer Platform) that no longer exists as described.

<details>
<summary>Click to expand the deprecated setup steps</summary>

### Step 1 — Add product access to your LinkedIn app

Go to https://www.linkedin.com/developers/apps and open the app. Under **Products**, request access to **Marketing Developer Platform**.

> Status 2026-05-22: This product no longer exists. The equivalent is **Community Management API**, which is restricted to LinkedIn Marketing Partners and cannot be requested directly.

### Step 2 — Link your app to the company page

App → Settings → Verified company page → link SmartPro Hub (ID `108832221`).

> Status 2026-05-22: Doing this alone does not unlock company posting. It's a prerequisite, not a sufficient condition.

### Step 3 — OAuth with org scopes

```
https://www.linkedin.com/oauth/v2/authorization?
response_type=code
&client_id=CLIENT_ID
&redirect_uri=https%3A%2F%2Fwww.linkedin.com%2Fdevelopers%2Ftools%2Foauth%2Fredirect
&scope=openid%20profile%20email%20w_member_social%20r_member_social%20w_organization_social%20r_organization_social
```

> Status 2026-05-22: The org scopes will be rejected with "invalid scope" because the app doesn't have a product that grants them.

### Step 4 — Get the organization URN

`urn:li:organization:108832221`.

### Step 5 — Add GitHub secrets

| Secret | Value |
|---|---|
| `LINKEDIN_ORG_TOKEN` | (would be the org-scoped token from Step 3) |
| `LINKEDIN_ORG_URN` | `urn:li:organization:108832221` |

### Step 6 — Smoke test

Was planned as the final verification.

</details>

---

## If we ever did want to publish to the company page

Realistic options, in increasing order of effort:

1. **Manual.** Generate drafts via this pipeline, copy-paste into the LinkedIn page composer once approved. Zero engineering, full control.
2. **Partner tool (Buffer / Publer / Postiz).** Connect SmartPro page to one of them via their UI (they have the partner-grade API access). Modify the publish step in this repo to push to their API instead of LinkedIn's. ~1 day of work, ~$15/month.
3. **Apply for LinkedIn Marketing Partner Program.** ~3–6 month process, requires a business case and a product LinkedIn cares about. Not realistic for a single-developer ops tool.

None of these is on the roadmap. Adding them later is straightforward; we just don't need them now.
