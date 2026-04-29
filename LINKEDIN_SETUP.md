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

- **Share on LinkedIn** (`w_member_social` scope)
- **Sign In with LinkedIn using OpenID Connect** (`openid`, `profile`, `email`)

These are auto-approved within minutes.

## Step 3: Get Your Author URN (your LinkedIn user ID)

1. Go to **Auth** tab in your app dashboard.
2. Note the **Client ID** and **Client Secret**.
3. Add this to **Authorized redirect URLs**: `https://www.linkedin.com/developers/tools/oauth/redirect`

Then visit (replace `CLIENT_ID`):

```
https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=CLIENT_ID&redirect_uri=https%3A%2F%2Fwww.linkedin.com%2Fdevelopers%2Ftools%2Foauth%2Fredirect&scope=openid%20profile%20email%20w_member_social
```

After authorizing, LinkedIn redirects back with a `code=...` in the URL. Copy that code.

## Step 4: Exchange the code for an access token

Run this in your terminal (replace placeholders):

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

1. Repeat Step 3 (get a new `code` from the OAuth URL)
2. Repeat Step 4 (exchange for a new token)
3. Update the `LINKEDIN_ACCESS_TOKEN` secret in GitHub

You can request a refresh token too (LinkedIn supports it for some apps) — see https://learn.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens
