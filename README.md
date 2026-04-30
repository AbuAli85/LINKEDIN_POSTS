# LinkedIn Auto-Poster

Draft-first LinkedIn content system — generates posts with Claude, requires owner approval before publishing, and tracks performance to improve future content.

## Content strategy

| Day | Pillar | What it covers |
|---|---|---|
| **Monday** | Leadership | Management, hiring, team building, career growth |
| **Wednesday** | AI & Tech | LLMs, agents, AI in business, practical insights |
| **Friday** | Marketing & Growth | Content, branding, B2B, growth tactics |

Drafts are generated at **9:00 AM Muscat time** (5:00 AM UTC) Mon/Wed/Fri. Approved drafts are published only when you manually run the `publish_draft` workflow.

## How it works

```
GitHub Actions cron (Mon/Wed/Fri 9am Muscat)
        |
        v
main.py picks pillar by weekday
        |
        v
generator.py asks Claude to write a draft
        |   (avoids topics used in last 20 posts)
        |   (uses performance data to prefer high-scoring pillars and hooks)
        v
posts_history/ archives the draft with status=draft
        |
        v
notifier.py optionally sends email/webhook alert that a draft needs review
        |
        v
dashboard.py updates docs/index.html — draft shows as "Needs review"
        |
        v
Owner reviews via Chatbase (see CHATBASE_APPROVAL.md) and approves
        |
        v
Owner runs publish_draft workflow with the selected JSON path
        |
        v
publisher.py POSTs the approved draft to LinkedIn UGC API
        |
        v
Owner scores the post (1-10) and records hook style via metrics.py
        |
        v
After 10+ scored posts, generator automatically favors what performed best
```

By default, scheduled runs are **draft-first**. This protects your LinkedIn reputation by requiring an explicit manual publish action before anything goes live.

## Setup (one-time, ~15 min)

1. **Fork or push this repo to your GitHub account.**
2. **Get a LinkedIn access token.** Follow [`LINKEDIN_SETUP.md`](./LINKEDIN_SETUP.md) — it's a step-by-step OAuth walkthrough.
3. **Add 3 secrets to GitHub** (Settings → Secrets and variables → Actions):
   - `ANTHROPIC_API_KEY` — from https://console.anthropic.com/
   - `LINKEDIN_ACCESS_TOKEN` — from the OAuth setup
   - `LINKEDIN_AUTHOR_URN` — your LinkedIn URN (`urn:li:person:xxx`)
4. **Enable GitHub Actions** for the repo (Actions tab → enable).
5. **Optional: enable draft-ready notifications** so you do not need to manually check the dashboard. Add `RESEND_API_KEY` and `NOTIFY_EMAIL` for email, `NOTIFY_WEBHOOK_URL` for webhook alerts, or both.

That's it. The cron will automatically generate drafts Mon/Wed/Fri. Publishing requires a manual `publish_draft` workflow run.

## Test it manually

From the **Actions** tab in GitHub:

1. Click "Auto-post to LinkedIn" workflow
2. Click "Run workflow"
3. Choose `generate_draft` to create a safe draft, or `publish_draft` to publish an approved draft
4. For `publish_draft`, provide the draft JSON path, e.g. `posts_history/20260430_090000_ai.json`
5. Optionally force a pillar (`leadership` / `ai` / `marketing`)

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your keys

# Generate draft only (default safe mode)
python main.py

# Force a specific pillar while drafting
FORCE_PILLAR=ai python main.py

# Publish an approved saved draft
POST_MODE=publish_draft PUBLISH_DRAFT_PATH=posts_history/20260430_090000_ai.json python main.py

# Emergency/manual immediate publish; requires explicit confirmation
POST_MODE=publish_now CONFIRM_PUBLISH_NOW=true python main.py

# Pull LinkedIn engagement stats for all published posts
POST_MODE=fetch_metrics python main.py
```

## Draft-ready notifications

The workflow can alert you when a new draft is ready for review. Notifications are **optional** and **best-effort**: if secrets are missing or a delivery provider is temporarily unavailable, draft generation still succeeds and publishing remains manual.

| Channel | GitHub configuration | What happens |
|---|---|---|
| Resend email | Add repository secrets `RESEND_API_KEY` and `NOTIFY_EMAIL` | Sends a review email with the draft path, pillar, preview, dashboard link, and publish workflow link |
| Webhook | Add repository secret `NOTIFY_WEBHOOK_URL` | Sends a JSON payload to Slack, Make, Zapier, Discord, or a custom endpoint |
| Disable alerts | Add repository variable `NOTIFY_ON_DRAFT=false` | Skips all notification channels while keeping draft generation active |

For Resend, you may also set repository variable `NOTIFY_FROM` to a verified sender such as `LinkedIn Draft Bot <drafts@yourdomain.com>`. If it is blank, the notifier uses Resend's onboarding sender. You may set repository variable `DASHBOARD_URL` if your dashboard is not served from the default GitHub Pages URL.

A webhook receiver will receive a JSON payload like this:

```json
{
  "event": "draft_ready",
  "draft_path": "posts_history/20260430_090000_ai.json",
  "pillar": "ai",
  "post_preview": "First 200 characters of the post...",
  "dashboard_url": "https://AbuAli85.github.io/LINKEDIN_POSTS/",
  "publish_workflow_url": "https://github.com/AbuAli85/LINKEDIN_POSTS/actions/workflows/auto-post.yml"
}
```

The alert is intentionally informational. It never approves, publishes, or triggers LinkedIn posting. The operating model remains: **Chatbase advises, GitHub Actions executes, owner decides**.

## Performance tracking

After each published post goes live and accumulates engagement, score it manually:

```bash
# Record a quality score (1-10) with optional hook style and notes
python metrics.py score posts_history/20260430_090000_ai.json \
  --score 8 --style numbered-list --notes "strong hook, good engagement"

# Fetch LinkedIn reactions/comments/shares for a single post
python metrics.py fetch posts_history/20260430_090000_ai.json

# Fetch stats for all published posts at once
python metrics.py fetch-all

# Show aggregated performance summary
python metrics.py summary
```

Once 3+ posts are scored, the generator automatically receives a **Performance Insights** block in its prompt, biasing future posts toward your highest-scoring pillar and hook style.

**Hook styles to classify:**

| Style | Example opening |
|---|---|
| `numbered-list` | "5 ways AI is changing knowledge work..." |
| `question` | "Why do most hiring processes fail the best candidates?" |
| `bold-statement` | "I stopped writing job descriptions. Here's what I do instead." |
| `story` | "Last quarter we doubled pipeline without adding headcount." |
| `data-lead` | "72% of AI pilots fail in the same way." |
| `observation` | "I've noticed something about the best operators I know." |
| `contrast` | "Everyone says post consistently. I say post deliberately." |

## Customizing the content

Edit [`content_strategy.py`](./content_strategy.py):

- Add/remove/reword topics in the `topics` list for each pillar
- Adjust `tone` and `audience` to match your voice
- Change `weekday` if you want different days

Edit [`generator.py`](./generator.py):

- Tune the `SYSTEM_PROMPT` to match your writing style
- Adjust character limits, hook style, hashtag rules

## Cost

- Claude Sonnet generates ~1500 chars per post → ~$0.01/post → **~$0.12/month**
- LinkedIn API: free
- GitHub Actions: free for public repos / generous free tier for private

## Token renewal

LinkedIn tokens expire every 60 days. When publishing fails with a 401, repeat steps 3-4 in `LINKEDIN_SETUP.md` and update the `LINKEDIN_ACCESS_TOKEN` secret.

## Files

| File | Purpose |
|---|---|
| `main.py` | Orchestrator — generates drafts by default; publishes only explicitly approved drafts |
| `content_strategy.py` | Pillar definitions, topic library, day mapping |
| `generator.py` | Claude API call, deduplication, performance-aware prompt injection |
| `publisher.py` | LinkedIn UGC API client |
| `notifier.py` | Optional draft-ready notifications via Resend email and webhook POST |
| `metrics.py` | Performance tracking: fetch LinkedIn stats, score posts, summarise for generator |
| `dashboard.py` | Generates docs/index.html with status, metrics, and next scheduled runs |
| `.github/workflows/auto-post.yml` | GitHub Actions draft schedule and manual publish/metrics controls |
| `posts_history/` | JSON archive of every generated draft and published post |
| `LINKEDIN_SETUP.md` | One-time OAuth walkthrough |
| `CHATBASE_APPROVAL.md` | Chatbase-assisted draft review and approval workflow |
