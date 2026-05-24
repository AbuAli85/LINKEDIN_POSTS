# /try landing page — setup notes

## What this is

A conversion-optimized landing page hosted on GitHub Pages at:
https://abuali85.github.io/LINKEDIN_POSTS/try/

It captures emails for a free SmartPro trial and routes warmer prospects to
WhatsApp. Pure static HTML — no backend, no API keys committed to the repo.

## Why it exists

The www.thesmartpro.io/try URL referenced in earlier LinkedIn posts returns a
404. Until that page is built on the real WordPress site, this landing page
gives you a working destination so the LinkedIn CTAs convert instead of bleeding.

## To make the email form work (one-time setup, 3 minutes)

1. Go to https://formspree.io and sign up with luxsess2001@gmail.com
2. Create a new form. Copy the endpoint URL (looks like
   `https://formspree.io/f/abcd1234`)
3. Open `docs/try/index.html` and find this line near the bottom:

       var FORMSPREE_ENDPOINT = '';

4. Paste the URL between the quotes. Save. Commit. Push.

Until you do this, the form falls back to opening a mailto: link — leads still
reach you, just via the user's email client instead of straight to Formspree.

## What still needs to happen on thesmartpro.io itself

The GitHub Pages landing page is a stopgap. The real fix is on
www.thesmartpro.io:

1. **Fix the positioning mismatch.** The homepage H1 says "Smart Business
   Platform" — generic. The portal at portal.thesmartpro.io is positioned as
   "Contract Management System." But all LinkedIn copy pitches HR/payroll/WPS.
   Pick one story and align all surfaces.
2. **Build a real /try page** with email capture and a clear path into trial
   onboarding. Then redirect or copy this landing page into WordPress.
3. **Add a /pricing page.** Without it, decision-makers bounce.
4. **Add public signup or a "request access" flow.** Right now portal sign-in
   says "Contact your administrator," which kills self-serve trials.

Once those are in place, change `content_strategy.py` line 8 back to point at
`www.thesmartpro.io/try` (or the real signup URL) and retire this landing page.

## URLs in use

- Main dashboard: https://abuali85.github.io/LINKEDIN_POSTS/
- This landing page: https://abuali85.github.io/LINKEDIN_POSTS/try/
- WhatsApp CTA: https://wa.me/96879665522
- Real product site: https://www.thesmartpro.io/
- Customer portal: https://portal.thesmartpro.io/
