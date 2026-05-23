# Lead Enrichment — Apollo + Bright Data

Wires the two services into your existing outreach pipeline. Pulls public LinkedIn signals from Bright Data, contact details (email/phone/title) from Apollo, then appends a merged row to `leads.csv` that `outreach.py qualify` and `outreach_tracker.py` already understand.

## One-time setup

```bash
# 1. Bright Data — get an API key + LinkedIn People dataset access
#    https://brightdata.com/cp/setting/users
export BRIGHTDATA_API_KEY=brd_xxxxxxxxxxxx

# 2. Apollo — get an API key
#    https://app.apollo.io/#/settings/integrations/api
export APOLLO_API_KEY=xxxxxxxx

# Already in requirements.txt: requests
pip install -r requirements.txt
```

## Run it

```bash
# Sanity check — enrich one profile, log to enrichment_history/ without touching leads.csv
python enrich_leads.py one https://www.linkedin.com/in/fahad-alamri-smartpro/ --dry-run

# Real run — appends to leads.csv (deduped by linkedin_url)
python enrich_leads.py one https://www.linkedin.com/in/<someone>/

# Batch — one URL per line in prospects.txt
python enrich_leads.py batch prospects.txt
```

## What gets written

Each row matches your existing `leads.csv` schema. Email/phone/segment land in the `notes` column so the canonical columns stay clean for `outreach.py`:

```
notes: email=fahad@smartpro.om | phone=+96812345678 | seg=A | country=OM | li_followers=4200
```

`title_guess` is filled from Apollo when available, falling back to Bright Data's headline. `first_seen` is set to `datetime.now(UTC)`. `intent`, `reply_status`, etc. stay empty for `outreach.py qualify` to populate.

## Segment auto-assignment

Heuristic against title/company/headline, matching your A/B/C segments in `outreach_tracker.py`:

- **A** — HR, people, talent, founder, CEO, operations, manager
- **B** — invest, government, vision 2040, policy, fund, VC, board
- **C** — engineer, developer, SaaS, CTO, tech, build, software

Unclear → empty (tracker assigns default).

## Raw API responses

Every call is logged to `enrichment_history/YYYYMMDD_HHMMSS_<slug>.json` with both Bright Data and Apollo payloads plus the merged row. Useful when an enriched record looks off and you need to see what each source actually returned.

## Cost guardrails

- Bright Data: charged per profile scraped — keep `prospects.txt` to known-good URLs.
- Apollo: People Match consumes 1 credit per match. The script does **not** call `reveal_personal_emails: true` so it sticks to work emails (cheaper, no PII surprise).
- `ENRICH_RATE_LIMIT_SECS=1.5` pauses between batch entries — bump up if you hit 429s.

## Wire-in to the daily flow

```bash
# After you publish a post and comments come in:
python outreach.py fetch          # pulls new commenters from LinkedIn
# Then enrich each new commenter URL:
python enrich_leads.py batch new_commenters.txt
# Then qualify + draft:
python outreach.py qualify
python outreach.py draft-dms
```

You can also have GitHub Actions do this on a cron — just add the two secrets (`BRIGHTDATA_API_KEY`, `APOLLO_API_KEY`) and call `enrich_leads.py batch` after the comment fetch.
