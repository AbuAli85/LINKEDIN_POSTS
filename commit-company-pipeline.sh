#!/usr/bin/env bash
# Run this from C:\Users\HP\Documents\GitHub\LINKEDIN_POSTS in Git Bash
# (or PowerShell with bash) to commit the company-pipeline work in one go.
#
# It:
#   1. clears the stuck .git/index.lock if present
#   2. stages only the intentional company-pipeline files (no CRLF churn)
#   3. commits with a descriptive message
#   4. shows you the new commit so you can git push when ready

set -e

# 1. Clear stale lock
if [ -f .git/index.lock ]; then
  echo ">>> Removing stale .git/index.lock"
  rm -f .git/index.lock
fi

# 2. Stage intentional files
echo ">>> Staging company pipeline files"
git add \
  company_content_strategy.py \
  strategy_loader.py \
  COMPANY_SETUP.md \
  IMPLEMENTATION_PLAN_COMPANY.md \
  STATUS_REPORT_2026-05-19.md \
  .github/workflows/auto-post-company.yml \
  company_posts_history/.gitkeep \
  main.py \
  generator.py \
  publisher.py

echo ">>> Staged:"
git diff --cached --stat

# 3. Commit
echo ""
echo ">>> Committing"
git commit -m "feat(company): add parallel company-page publishing pipeline

Mirror of the personal pipeline for the SmartPro Hub company page
(urn:li:organization:108832221). Activated by LINKEDIN_AUDIENCE=company.

New files:
  - company_content_strategy.py: 5 pillars (product_proof, feature_spotlight,
    oman_market, hiring, partnership) with third-person brand voice, separate
    hashtags/CTAs/SEO keywords, pillar picker reading company_posts_history/
  - strategy_loader.py: env-aware loader that routes generator/main/publisher
    to the right strategy module + history dir + token/URN env vars
  - company_posts_history/: separate draft archive
  - .github/workflows/auto-post-company.yml: staggered cron (06:30 generate,
    07:15 publish UTC) so it doesn't race the personal workflow
  - COMPANY_SETUP.md: OAuth + secrets walkthrough
  - IMPLEMENTATION_PLAN_COMPANY.md: 6-phase plan, file list, decisions
  - STATUS_REPORT_2026-05-19.md: repo audit findings

Modified (audience-aware routing, no behavior change for personal):
  - generator.py: HISTORY_DIR + content_strategy imports via strategy_loader
  - main.py: pick_pillar/PILLARS + history dir via strategy_loader
  - publisher.py: token/URN env vars selected by audience; CTA comments
    skipped on company posts (org pages comment via different flow)

Backwards-compatible: LINKEDIN_AUDIENCE unset or =personal yields the
exact prior behavior. No personal-pipeline regressions.

Not yet active: requires LINKEDIN_ORG_TOKEN + LINKEDIN_ORG_URN secrets
(see COMPANY_SETUP.md) before the company workflow can publish."

# 4. Show the new commit
echo ""
echo ">>> Done. New commit:"
git log --oneline -1
echo ""
echo ">>> Push when ready:"
echo "    git push origin claude/linkedin-post-automation-lQiJZ"
