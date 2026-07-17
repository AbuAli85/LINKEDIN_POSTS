# LinkedIn Setup — One-Time OAuth

You need a LinkedIn access token before the bot can post. This takes ~10 minutes.

## Step 1: Create a LinkedIn Developer App

1. Go to https://www.linkedin.com/developers/apps
2. Click **Create app**
3. Fill in:
   - **App name**: e.g. "Auto Poster"
   - **LinkedIn Page**: pick any page you admin (or your personal one)
   - **Privacy policy URL**: any URL works for personal use (e.g. your LinkedIn profile)
   - **App logo**: upload anything
4. Agree to terms and create.

## Step 2: Add Required Products

In your app dashboard, go to the **Products** tab and request access to:

- **Share on LinkedIn** (`w_member_social` scope) — needed to publish posts
- **Sign In with LinkedIn using OpenID Connect** (`openid`, `profile`, `email`) — needed for auth

Both are auto-approved within minutes.

> **Note on Community Management API.** LinkedIn requires the Community Management API
> (which unlocks `r_member_social` for reading comments) to be the **only** product on its
> app, for legal and security reasons. It cannot be added to this app. To enable
> `outreach.py fetch`, create a second dedicated app — see **Step 7** below.

## Step 3: Get Your Author URN (your LinkedIn user ID)

1. Go to **Auth** tab in your app dashboard.
2. Note the **Client ID** and **Client Secret**.
3. Add this to **Authorized redirect URLs**: `https://www.linkedin.com/developers/tools/oauth/redirect`

Then visit (replace `CLIENT_ID`):

```
https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=77oxpmdoa8qe2k&redirect_uri=https%3A%2F%2Fwww.linkedin.com%2Fdevelopers%2Ftools%2Foauth%2Fredirect&scope=openid%20profile%20email%20w_member_social
```

After authorizing, LinkedIn redirects back with a `code=...` in the URL. Copy that code.

## Step 4: Exchange the code for an access token

Easiest: use the bundled helper (handles the form encoding so you don't get `invalid_client` from a malformed curl):

```bash
LINKEDIN_CLIENT_ID=YOUR_CLIENT_ID \
LINKEDIN_CLIENT_SECRET=YOUR_CLIENT_SECRET \
  python oauth_helper.py PASTE_CODE_HERE
```

Or run curl directly:

```bash
curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
  -d grant_type=authorization_code \
  -d code=PASTE_CODE_HERE \
  -d redirect_uri=https://www.linkedin.com/developers/tools/oauth/redirect \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET
```

Response:

```json
{ "access_token": "AQXxxxxx...", "expires_in": 5184000 }
```

Save the `access_token` — this is your `LINKEDIN_ACCESS_TOKEN`. **It's valid for 60 days**, then you'll need to repeat steps 3-4.

### Troubleshooting `invalid_client` / "Client authentication failed"

If the token endpoint returns `401 {"error":"invalid_client"}`:

- Re-copy `Client ID` and `Client Secret` from the **Auth** tab — make sure there's no trailing whitespace, newline, or surrounding quotes.
- Regenerate the secret in the LinkedIn app dashboard if you're not 100% sure it's current.
- Confirm the **Share on LinkedIn** product is approved (Products tab) — the app can't authenticate against APIs it doesn't have access to.
- The `code` from Step 3 is single-use and expires in ~30s. If you reused it, get a fresh one.
- Make sure the `redirect_uri` exactly matches what's registered in the Auth tab.

## Step 5: Get your Author URN

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://api.linkedin.com/v2/userinfo
```

Response includes `"sub": "abc123def"`. Your `LINKEDIN_AUTHOR_URN` is:

```
urn:li:person:abc123def
```

## Step 6: Add secrets to GitHub

In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**

Add three secrets:

| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | from https://console.anthropic.com/ |
| `LINKEDIN_ACCESS_TOKEN` | from Step 4 |
| `LINKEDIN_AUTHOR_URN` | from Step 5 (e.g. `urn:li:person:abc123def`) |

That's it. The cron will start posting Mon/Wed/Fri at 9 AM UTC.

## Renewing the token

LinkedIn access tokens expire after 60 days. To renew:

1. Repeat Step 3 — paste the OAuth URL above, replace `CLIENT_ID`
2. Repeat Step 4 (exchange the new `code` for a new token)
3. Update the `LINKEDIN_ACCESS_TOKEN` secret in GitHub

You can request a refresh token too (LinkedIn supports it for some apps) — see https://learn.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens

---

## Step 7: (Optional) Second app for comment reading — `r_member_social`

`outreach.py` reads comments on your published posts to drive lead qualification. That endpoint requires the `r_member_social` scope, which is gated behind the **Community Management API** product. LinkedIn requires this product to be the **only** product on its app — so it can't go on the main posting app. The fix is a dedicated second app.

### Why two apps?

- **App A — posting** (Share on LinkedIn): `w_member_social` token → `LINKEDIN_ACCESS_TOKEN`
- **App B — reading** (Community Management API): `r_member_social` token → `LINKEDIN_READ_TOKEN`

`outreach.py` prefers `LINKEDIN_READ_TOKEN` when set, and falls back to `LINKEDIN_ACCESS_TOKEN` otherwise — so single-app setups keep working (just with 0 comment results until App B is wired up).

### Steps

1. **Create the second app** at https://www.linkedin.com/developers/apps/new
   - App name: e.g. `SmartPro Outreach Reader`
   - LinkedIn Page: same Company Page as App A
   - Tick the terms checkbox, click **Create app**
2. **Verify the Page association** — Settings → next to the Page name, click **Verify** → Generate URL → open the URL as a Page Admin → Approve.
3. **Request access to Community Management API** — Products tab → click **Request access** on Community Management API.
   - Verify your business email when prompted (you'll get a 6-digit code by email).
   - Tick the legal agreement checkbox.
   - Fill out the external Qualtrics form (~5 minutes): legal name, alternate name, website, registered address, and check **Profile management** as the use case.
4. **Wait for approval** (1–14 days). Microsoft Vetting Services will email your business email; respond promptly to keep the review moving.
5. **OAuth with `r_member_social` scope** — once approved, use the second app's Client ID and this scope string:

   ```
   https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=SECOND_APP_CLIENT_ID&redirect_uri=https%3A%2F%2Fwww.linkedin.com%2Fdevelopers%2Ftools%2Foauth%2Fredirect&scope=openid%20profile%20email%20r_member_social
   ```

6. **Exchange the code** for a token using `oauth_helper.py` (same as Step 4 above) — but with the **second app's** Client ID and Secret.
7. **Add a new GitHub secret**:

   | Name | Value |
   |---|---|
   | `LINKEDIN_READ_TOKEN` | the access token from the second app |

The workflow already passes this env var to the outreach job (`auto-post.yml` → outreach-sequence step). The next 06:00 UTC cron will start populating `outreach_history/` and `leads.csv` with real comment data.
