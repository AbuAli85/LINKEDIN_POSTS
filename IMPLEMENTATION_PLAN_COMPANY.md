# Implementation Plan — Separate Company Pipeline

**Goal:** mirror the personal LinkedIn automation for the SmartPro company page (`urn:li:organization:108832221`), with its own pillars, schedule, generator prompts, draft history, and dashboard. Personal pipeline keeps running untouched.

**Approach:** parameterize the existing code with an `audience` dimension (`personal` | `company`) rather than forking the codebase. Files that need audience-awareness gain a small branching layer; everything else stays shared.

---

## Phase 0 — Prerequisite (you do this)

Complete `COMPANY_SETUP.md`. Until `LINKEDIN_ORG_TOKEN` and `LINKEDIN_ORG_URN` are in GitHub Secrets, the company workflow will fail-fast with a clear error. Building can proceed in parallel — code lands first, secrets light it up.

---

## Phase 1 — Strategy + content config (new file)

**New: `company_content_strategy.py`** (~200 lines, mirrors `content_strategy.py`)

- `COMPANY_PILLARS` — company-page-appropriate pillars. Suggested initial set, you'll edit:
  - `product_proof` — concrete customer outcomes (vs personal `proof` which is more first-person)
  - `feature_spotlight` — specific SmartPro Hub or Sanad capabilities
  - `oman_market` — Oman-specific business context, Vision 2040, Omanization
  - `hiring` — pipeline + jobs board posts (your repo already has hiring-flavored modules)
  - `partnership` — Sanad office partnerships, integrations
- `COMPANY_HASHTAGS` — segments tailored for a company voice (more `#SmartPROHub`, `#OmanBusiness`, fewer first-person tags)
- `COMPANY_CTAS` — book-a-demo, partnership inquiries, jobs board links
- `COMPANY_SEO_KEYWORDS` — focused on what SmartPro the *company* should rank for

I'll generate a starting template; you'll refine the pillar copy before first publish.

---

## Phase 2 — Generator + main parameterization

**Modify: `generator.py`** — add `audience` parameter to `generate_post()`. When `audience="company"`:
- Loads from `company_content_strategy` instead of `content_strategy`
- Uses a company-voice system prompt (third-person, brand-led, more formal)
- Skips first-person CTAs

**Modify: `main.py`** — read `LINKEDIN_AUDIENCE` env var, default `personal`. Pipe through to generator, history dir, and publisher.

**Modify: `publisher.py`** — read `LINKEDIN_AUDIENCE` to pick which token + URN env var pair to use. (Publisher itself is already URN-agnostic so this is just env routing.)

---

## Phase 3 — Storage + workflow

**New directory: `company_posts_history/`**

**New file: `.github/workflows/auto-post-company.yml`** — clone of `auto-post.yml` with:
- Different cron times (stagger from personal — e.g. generate at 06:00 UTC, publish at 07:15 UTC) so the two pipelines don't fight for git
- `LINKEDIN_AUDIENCE=company` set at job level
- Uses `LINKEDIN_ORG_TOKEN` + `LINKEDIN_ORG_URN`
- Writes to `company_posts_history/`
- Same workflow_dispatch surface (generate_draft, publish_draft, approve_draft, etc.)

---

## Phase 4 — Dashboard

**Modify: `dashboard.py`** — add a tabbed view in `docs/index.html`:
- Tab 1 (default): Personal — reads `posts_history/`
- Tab 2: Company — reads `company_posts_history/`
- Same token-health, recent-runs, performance widgets per tab

Or generate `docs/company.html` as a second page if tabs feel cramped. Final call depends on the existing UI density.

---

## Phase 5 — Metrics + token health

**Modify: `metrics.py`** — for company posts, fetch from `organizationalEntityShareStatistics` endpoint (different from personal). Engagement counts attach back to each draft JSON same as today.

**Modify: `.github/workflows/token-health.yml`** — check both tokens, warn 10 days before either expires.

---

## Phase 6 — Approval flow

The same Chatbase approval mechanism described in `CHATBASE_APPROVAL.md` works — the workflow_dispatch `approve_draft` action just takes a file path, and `company_posts_history/` paths route through `LINKEDIN_AUDIENCE=company` to the right publisher.

If you want different approvers for company vs personal (e.g. only you for personal, you + co-founder for company), that's a Chatbase config change, not a code change.

---

## Files touched (summary)

**New:**
- `company_content_strategy.py`
- `.github/workflows/auto-post-company.yml`
- `company_posts_history/.gitkeep`
- `COMPANY_SETUP.md` (already written)

**Modified:**
- `generator.py` (add `audience` parameter, ~30 LOC)
- `main.py` (read `LINKEDIN_AUDIENCE`, ~20 LOC)
- `publisher.py` (env routing for org token, ~15 LOC)
- `dashboard.py` (tabbed view or second page, ~80 LOC)
- `metrics.py` (org endpoint branch, ~40 LOC)
- `.github/workflows/token-health.yml` (check both tokens, ~10 LOC)

**Total estimate:** ~600 LOC net new + modifications. Roughly a half-day of focused work in a single session.

---

## Rollout sequence (recommended)

1. **Phase 0** (you): Complete `COMPANY_SETUP.md` — add the two new secrets.
2. **Phase 1–3** (Claude, one session): scaffolding + workflow + minimal generator. Smoke-test with `dry_run=true` first.
3. **Generate first company draft** manually, review it, edit `company_content_strategy.py` until the voice feels right.
4. **First live publish** — manually approved, manually triggered.
5. **Phase 4–5** (Claude, follow-up session): dashboard + metrics — only after first publish proves the pipeline works.
6. **Enable the cron** — flip the company workflow from manual-only to scheduled.

This way nothing goes live until you've seen at least one real generated draft.

---

## Open decisions for you

1. **Schedule overlap.** Personal generates at 05:00 UTC / publishes at 05:15+06:00. Company default proposal: generate 06:30, publish 07:15. OK? Or different days entirely?
2. **Pillar set.** The five proposed company pillars above — start with these, or do you already have a content map for the company page?
3. **Cross-promotion.** Should company posts ever reference your personal posts (e.g. "Our CEO recently wrote about this — link in comments")? If yes, the generator needs awareness of the personal history.
