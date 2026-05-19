# Company Page Setup — OAuth + Secrets

To post to your LinkedIn company page (ID `108832221`) the automation needs a token with org-scoped permissions that your current personal token does not have. This is a one-time setup. **Plan ~20 minutes.**

---

## What you'll need

- Admin access to the SmartPro company page (you already have this — confirmed by the admin dashboard URL you shared)
- Access to your LinkedIn Developer app (the same app you used for the personal token in `LINKEDIN_SETUP.md`)
- 20 minutes uninterrupted

---

## Step 1 — Add product access to your LinkedIn app

Go to https://www.linkedin.com/developers/apps and open the app you already use.

Under **Products**, request access to:

- **Marketing Developer Platform** — required for `w_organization_social` and `r_organization_social` scopes

Approval is usually instant for individual developers but can take up to 24 hours. You'll get an email when approved.

> **Why this product:** "Share on LinkedIn" only grants member-level scopes. Company posting requires the Marketing Developer Platform product, which adds the organization scopes.

---

## Step 2 — Link your app to the company page

In the same app, go to **Settings → Verified company page** and link `SmartPro Hub` (ID `108832221`). This tells LinkedIn that this app is authorized to act on behalf of the page.

You must be an Admin of the page to do this. The dashboard URL you shared confirms you are.

---

## Step 3 — Generate an OAuth token with org scopes

Replace `CLIENT_ID` below with your app's Client ID (Auth tab in the app dashboard), paste into a browser, then approve:

```
https://www.linkedin.com/oauth/v2/authorization?
response_type=code
&client_id=CLIENT_ID
&redirect_uri=https%3A%2F%2Fwww.linkedin.com%2Fdevelopers%2Ftools%2Foauth%2Fredirect
&scope=openid%20profile%20email%20w_member_social%20r_member_social%20w_organization_social%20r_organization_social
```

(Put it on one line in the browser — the line breaks are just for readability.)

> **Key difference from your personal-only setup:** the scope string now ends with `w_organization_social r_organization_social`.

After approving, LinkedIn redirects you back with a `code=` query parameter. Use it to exchange for a token using the same curl pattern you used in `LINKEDIN_SETUP.md` Step 4.

Save the resulting access token somewhere safe — it lasts 60 days, same as the personal one.

---

## Step 4 — Get your organization URN

This is already known: **`urn:li:organization:108832221`**. No lookup needed.

(If you ever change companies or add a second page, run `curl -H "Authorization: Bearer YOUR_TOKEN" https://api.linkedin.com/v2/organizationAcls?q=roleAssignee` to list pages your token can post to.)

---

## Step 5 — Add new GitHub secrets

Repo → Settings → Secrets and variables → Actions → New repository secret. Add:

| Secret name | Value |
|---|---|
| `LINKEDIN_ORG_TOKEN` | The access token from Step 3 |
| `LINKEDIN_ORG_URN` | `urn:li:organization:108832221` |

Leave your existing `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_AUTHOR_URN` untouched — the personal pipeline keeps using those.

---

## Step 6 — Verify the token works (manual smoke test)

Once Claude builds the company pipeline (see `IMPLEMENTATION_PLAN_COMPANY.md`), the first thing you'll do is run the new workflow with `action=publish_now` and `dry_run=true`. That generates a draft without publishing — proves the auth works end-to-end before anything goes live.

---

## Token renewal

LinkedIn tokens expire in 60 days. The repo already has a `LinkedIn token health check` workflow for the personal token. Once the company pipeline ships, we'll extend that workflow to monitor `LINKEDIN_ORG_TOKEN` too and warn you ~10 days before expiry.
