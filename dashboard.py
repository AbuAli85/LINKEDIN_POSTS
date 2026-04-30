"""Generate a static HTML status dashboard from posts_history/."""

import html
import json
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HISTORY_DIR   = Path(__file__).parent / "posts_history"
DOCS_DIR      = Path(__file__).parent / "docs"
DOCS_DIR.mkdir(exist_ok=True)

REPO          = "AbuAli85/LINKEDIN_POSTS"
WORKFLOW_FILE = "auto-post.yml"
ACTIONS_URL   = f"https://github.com/{REPO}/actions/workflows/{WORKFLOW_FILE}"


def _current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or "main"
    except Exception:
        return "main"

PILLAR_COLOR = {
    "leadership": "#818cf8",
    "ai":         "#22d3ee",
    "marketing":  "#fbbf24",
}

CRON_WEEKDAYS  = {0, 2, 4}
CRON_HOUR_UTC  = 5
MUSCAT_OFFSET  = 4   # UTC+4, no DST


def _to_muscat(dt: datetime) -> str:
    m = dt + timedelta(hours=MUSCAT_OFFSET)
    return m.strftime("%b %d, %Y · %I:%M %p Muscat").replace(" 0", " ").replace("AM", "am").replace("PM", "pm")


def load_posts() -> list[dict]:
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)
    posts = []
    for f in files:
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            p["_filename"] = f.name
            posts.append(p)
        except Exception:
            continue
    return posts


def next_runs(n: int = 3) -> list[datetime]:
    now = datetime.now(timezone.utc)
    dt  = now.replace(hour=CRON_HOUR_UTC, minute=0, second=0, microsecond=0)
    if dt <= now:
        dt += timedelta(days=1)
    result = []
    for _ in range(14):
        if dt.weekday() in CRON_WEEKDAYS:
            result.append(dt)
        if len(result) >= n:
            break
        dt += timedelta(days=1)
    return result


def _token_health(posts: list[dict]) -> tuple[str, str]:
    """Return (message, level) where level is ok | warn | error | info | ''.

    NOTE: Expiry is estimated from the most-recent published post date because
    token_issued_at is not stored. For a more accurate countdown, store
    TOKEN_ISSUED_AT in a config file or GitHub secret when first authenticating.
    """
    published = [p for p in posts if p.get("published") and p.get("published_at")]
    if not published:
        return ("LinkedIn tokens expire after 60 days. Set a calendar reminder to renew yours.", "info")
    # Use most-recent published post as a conservative (shorter) expiry estimate
    newest = max(published, key=lambda p: p.get("published_at", ""))
    try:
        created  = datetime.fromisoformat(newest["published_at"].replace("Z", "+00:00"))
        expires  = created + timedelta(days=60)
        days_left = (expires - datetime.now(timezone.utc)).days
        if days_left <= 0:
            return ("LinkedIn token has likely expired — renew immediately (see LINKEDIN_SETUP.md)", "error")
        if days_left <= 10:
            return (f"LinkedIn token expires in ~{days_left} days — renew now (see LINKEDIN_SETUP.md)", "error")
        if days_left <= 20:
            return (f"LinkedIn token expires in ~{days_left} days — plan renewal soon", "warn")
        return (f"LinkedIn token valid for ~{days_left} more days (estimated)", "ok")
    except Exception as exc:
        print(f"WARNING: _token_health parse error: {exc}", flush=True)
        return ("", "")


def _badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{text}</span>'


def _card(post: dict, idx: int) -> str:
    pillar = post.get("pillar", "unknown")
    color  = PILLAR_COLOR.get(pillar, "#94a3b8")

    status_value = post.get("status") or ""
    if post.get("published") or status_value == "published":
        status = _badge("&#10003; Published", "published")
    elif post.get("publish_error") or status_value == "failed":
        status = _badge("&#10007; Failed", "failed")
    elif post.get("approved") or status_value == "approved":
        status = _badge("Approved", "approved")
    elif post.get("approval_required") or status_value == "draft":
        status = _badge("Needs review", "draft")
    elif post.get("dry_run"):
        status = _badge("Dry run", "dry-run")
    else:
        status = _badge("Draft", "draft")

    raw_date = post.get("published_at") or post.get("generated_at", "")
    try:
        dt       = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        date_str = _to_muscat(dt)
    except Exception:
        date_str = raw_date[:10]

    model_short  = post.get("model", "unknown").replace("claude-", "").split(":")[0]
    attempts     = post.get("attempts", 1)
    char_count   = post.get("char_count", 0)
    char_pct     = min(100, (char_count / 1500) * 100)
    char_ok      = 800 <= char_count <= 1500
    char_cls     = "ok" if char_ok else "warn"
    topic        = html.escape(post.get("topic", ""))
    fmt          = html.escape(post.get("format", ""))
    post_text    = html.escape(post.get("post", ""))

    alerts = ""
    if w := post.get("validation_warning"):
        alerts += f'<div class="alert warn">&#9888; {html.escape(w)}</div>'
    if e := post.get("publish_error"):
        alerts += f'<div class="alert error">&#10007; {html.escape(str(e)[:220])}</div>'

    metrics     = post.get("metrics") or {}
    metrics_html = ""
    if metrics:
        parts = []
        if (r := metrics.get("reactions")) is not None:
            parts.append(f'<span class="metric-item" title="Reactions">&#128077; {r}</span>')
        if (c := metrics.get("comments")) is not None:
            parts.append(f'<span class="metric-item" title="Comments">&#128172; {c}</span>')
        if (s := metrics.get("shares")) is not None:
            parts.append(f'<span class="metric-item" title="Shares">&#8635; {s}</span>')
        if (q := metrics.get("manual_quality_score")) is not None:
            parts.append(f'<span class="quality-score" title="Manual quality score">&#9733; {q}/10</span>')
        if hs := metrics.get("hook_style"):
            parts.append(f'<span class="hook-tag">{html.escape(hs)}</span>')
        if parts:
            metrics_html = '<div class="metrics-row">' + "".join(parts) + "</div>"

    li_link = ""
    if post_id := post.get("post_id", ""):
        safe_id = html.escape(str(post_id))
        li_link = (
            f'<a class="li-link" href="https://www.linkedin.com/feed/update/{safe_id}/" '
            f'target="_blank" rel="noopener">View on LinkedIn &#8599;</a>'
        )

    fmt_html      = f'<span class="fmt-tag" title="{fmt}">&#9999; {fmt[:38]}{"…" if len(fmt)>38 else ""}</span>' if fmt else ""
    attempts_html = f'<span class="retries">&#8635; {attempts} retries</span>' if attempts > 1 else ""

    needs_review = (
        (post.get("status") == "draft" or post.get("approval_required"))
        and not post.get("published")
    )
    filename       = post.get("_filename", "")
    draft_path_val = html.escape(f"posts_history/{filename}") if filename else ""
    preview_val    = html.escape(post.get("post", "")[:300].replace("\n", " "))
    pillar_val     = html.escape(pillar)

    review_actions = ""
    approve_btn    = ""
    if needs_review and draft_path_val:
        review_actions = f"""
  <div class="review-actions">
    <span class="review-label">Review:</span>
    <button class="rev-btn rev-changes" data-path="{draft_path_val}" data-pillar="{pillar_val}"
      onclick="showReviseModal(this)">&#9998; Request Changes</button>
    <button class="rev-btn rev-edit" data-path="{draft_path_val}" data-preview="{preview_val}"
      onclick="showEditModal(this)">&#128393; Edit</button>
    <button class="rev-btn rev-recreate" data-path="{draft_path_val}" data-pillar="{pillar_val}"
      onclick="confirmRecreate(this)">&#8635; Recreate</button>
  </div>"""
        approve_btn = (
            f'<button class="approve-publish-btn" '
            f'data-path="{draft_path_val}" data-preview="{preview_val}" '
            f'onclick="showApproveModal(this)">&#10003; Approve &amp; Publish</button>'
        )

    return f"""
<div class="card" id="post-{idx}">
  <div class="card-header">
    <span class="pillar-tag" style="color:{color};border-color:{color}55">{pillar}</span>
    {status}
    {li_link}
    <span class="meta-right">
      <span class="model-tag">{model_short}</span>
      <span class="date">{date_str}</span>
    </span>
  </div>
  {f'<div class="topic">{topic}</div>' if topic else ''}
  {f'<div class="fmt-row">{fmt_html}</div>' if fmt else ''}
  {alerts}
  {metrics_html}
  <div class="post-wrap">
    <div class="post-text collapsed" id="pt-{idx}">{post_text}</div>
    <button class="expand-btn" onclick="toggle({idx})">Show more &#9660;</button>
  </div>
  {review_actions}
  <div class="card-footer">
    <div class="bar-track"><div class="bar-fill {char_cls}" style="width:{char_pct:.1f}%"></div></div>
    <span class="chars {char_cls}">{char_count} chars</span>
    {attempts_html}
    {approve_btn}
    <button class="copy-btn" id="copy-{idx}" onclick="copyPost({idx})">&#128203; Copy</button>
  </div>
</div>"""


def _engagement_sections() -> str:
    """Build HTML for pending replies and outreach leads sections."""
    try:
        from engagement import get_repeat_engagers, load_all_engagement
        items   = load_all_engagement()
        engagers = get_repeat_engagers()
    except Exception:
        return ""

    RISK_COLOR = {"safe": "#4ade80", "review": "#fbbf24", "block": "#f87171"}
    STATUS_COLOR = {"pending": "#fbbf24", "approved": "#818cf8", "posted": "#4ade80",
                    "blocked": "#f87171"}

    pending = [d for d in items if d.get("status") in ("pending", "approved")]
    recent_posted = [d for d in items if d.get("status") == "posted"][:5]

    # ---- pending replies section ----
    if not pending:
        pending_html = '<div class="empty" style="padding:30px 20px">No pending replies</div>'
    else:
        cards = []
        for d in pending:
            risk   = d.get("risk_level", "review")
            status = d.get("status", "pending")
            rc     = RISK_COLOR.get(risk, "#94a3b8")
            sc     = STATUS_COLOR.get(status, "#94a3b8")
            rec    = d.get("recommended_reply", 0)
            comment_esc = html.escape(d.get("comment_text", "")[:200])
            topic_esc   = html.escape(d.get("post_topic", ""))
            fname       = html.escape(Path(d.get("post_file", "engagement_history/?.json")).name)

            reply_rows = ""
            for i, r in enumerate(d.get("reply_drafts", [])):
                star   = "&#9733; " if i == rec else ""
                r_esc  = html.escape(r)
                reply_rows += (
                    f'<div class="reply-opt{"rec" if i == rec else ""}">'
                    f'<span class="reply-idx">{star}[{i}]</span> {r_esc}</div>'
                )

            risk_cats = ", ".join(d.get("risk_categories", [])) or "none"
            risk_note = html.escape(d.get("risk_reason", ""))

            cards.append(f"""
<div class="eng-card">
  <div class="eng-header">
    <span class="eng-badge" style="background:#0f172a;color:{sc};border:1px solid {sc}55">{status.upper()}</span>
    <span class="eng-badge" style="background:#0f172a;color:{rc};border:1px solid {rc}55">risk: {risk}</span>
    <span class="eng-meta">post: {topic_esc[:60]}</span>
  </div>
  <div class="eng-comment">&#128172; {comment_esc}</div>
  {f'<div class="eng-risk-note">&#9888; {html.escape(risk_cats)} &mdash; {risk_note}</div>' if risk == "review" else ""}
  <div class="eng-replies">{reply_rows if reply_rows else "<em>No reply drafts — blocked or fetch failed.</em>"}</div>
  <div class="eng-cmd"><code>python engagement.py approve {fname} --reply {rec}</code></div>
</div>""")
        pending_html = "".join(cards)

    # ---- recently posted ----
    if recent_posted:
        rp_rows = ""
        for d in recent_posted:
            posted_text = html.escape(d.get("posted_reply", "")[:100])
            rp_rows += f'<div class="rp-item">&#10003; {posted_text}</div>'
        recent_html = f'<div class="section-lbl" style="margin-top:22px">Recently posted replies ({len(recent_posted)})</div>{rp_rows}'
    else:
        recent_html = ""

    # ---- outreach leads ----
    if engagers:
        lead_rows = ""
        for lead in engagers[:10]:
            name  = html.escape(lead.get("commenter_name", "unknown"))
            urn   = html.escape(lead.get("commenter_urn", ""))
            count = lead.get("post_count", 0)
            latest_comment = html.escape((lead.get("comments") or [{}])[-1].get("comment_text", "")[:80])
            lead_rows += (
                f'<div class="lead-row">'
                f'<span class="lead-name">{name}</span>'
                f'<span class="lead-count">{count} posts engaged</span>'
                f'<span class="lead-comment">{latest_comment}</span>'
                f'</div>'
            )
        outreach_html = f"""
<div class="section-lbl" style="margin-top:28px">Outreach leads — repeat engagers ({len(engagers)})</div>
<div class="leads-table">{lead_rows}</div>"""
    else:
        outreach_html = ""

    return f"""
<div class="content" style="margin-top:0">
  <div class="section-lbl">Pending replies ({len(pending)})</div>
  {pending_html}
  {recent_html}
  {outreach_html}
</div>"""


def generate(posts: list[dict]) -> str:
    total       = len(posts)
    n_published = sum(1 for p in posts if p.get("published") or p.get("status") == "published")
    n_drafts    = sum(1 for p in posts if (p.get("status") == "draft" or p.get("approval_required")) and not p.get("published"))
    n_approved  = sum(1 for p in posts if (p.get("approved") or p.get("status") == "approved") and not p.get("published"))
    n_failed    = sum(1 for p in posts if p.get("publish_error") or p.get("status") == "failed")
    success_pct = round((n_published / total * 100) if total else 0)

    scored_posts = [p for p in posts if (p.get("metrics") or {}).get("manual_quality_score") is not None]
    avg_score_html = ""
    if scored_posts:
        avg = round(sum(p["metrics"]["manual_quality_score"] for p in scored_posts) / len(scored_posts), 1)
        avg_score_html = f'<div class="stat"><div class="n">{avg}</div><div class="l">Avg score</div></div>'

    counts = Counter(p.get("pillar", "?") for p in posts)
    pillar_pills = "".join(
        f'<span class="pillar-pill" style="border-color:{PILLAR_COLOR.get(p,"#94a3b8")}55;'
        f'color:{PILLAR_COLOR.get(p,"#94a3b8")}">{p} <b>{c}</b></span>'
        for p, c in sorted(counts.items(), key=lambda x: -x[1])
    )

    from content_strategy import PILLARS
    weekday_to_pillar = {c["weekday"]: name for name, c in PILLARS.items()}

    def _run_html(r: datetime) -> str:
        pillar = weekday_to_pillar.get(r.weekday(), "?")
        color  = PILLAR_COLOR.get(pillar, "#94a3b8")
        date_s = (r + timedelta(hours=MUSCAT_OFFSET)).strftime("%a %b %d").replace(" 0", " ")
        return (
            f'<span class="run-item">'
            f'<b>{date_s}</b>'
            f' &middot; 9:00 am Muscat'
            f' &middot; <span class="run-pillar" style="color:{color}">{pillar}</span>'
            f'</span>'
        )

    runs_html = "".join(_run_html(r) for r in next_runs(3))

    token_msg, token_level = _token_health(posts)
    token_banner = ""
    if token_msg and token_level != "ok":
        icons = {"warn": "&#9888;", "error": "&#128308;", "info": "&#8505;"}
        icon  = icons.get(token_level, "&#8505;")
        token_banner = f'<div class="token-banner {token_level}">{icon} {html.escape(token_msg)}</div>'

    cards = "".join(_card(p, i) for i, p in enumerate(posts)) if posts else (
        '<div class="empty">&#128221;<br>No posts yet &mdash; '
        '<a href="' + ACTIONS_URL + '" target="_blank">trigger the workflow</a> to generate your first post.</div>'
    )

    now_muscat      = _to_muscat(datetime.now(timezone.utc))
    engagement_html = _engagement_sections()
    branch          = _current_branch()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LinkedIn Auto-Poster &middot; Dashboard</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
a{{color:inherit;text-decoration:none}}

/* TOP BAR */
.topbar{{background:#1e293b;border-bottom:1px solid #334155;padding:14px 24px;display:flex;flex-wrap:wrap;align-items:center;gap:10px}}
.topbar h1{{font-size:1.1rem;font-weight:700;color:#f1f5f9}}
.topbar h1 em{{color:#0ea5e9;font-style:normal}}
.topbar .updated{{font-size:.68rem;color:#64748b;margin-left:auto}}
.actions{{display:flex;gap:8px;margin-left:12px}}
.btn{{font-size:.75rem;padding:5px 12px;border-radius:6px;border:none;cursor:pointer;font-weight:500;text-decoration:none;display:inline-flex;align-items:center;gap:4px}}
.btn-primary{{background:#0ea5e9;color:#fff}}.btn-primary:hover{{background:#0284c7}}
.btn-ghost{{background:#1e293b;color:#94a3b8;border:1px solid #334155}}.btn-ghost:hover{{color:#f1f5f9;border-color:#475569}}

/* TOKEN BANNER */
.token-banner{{padding:10px 24px;font-size:.8rem;display:flex;align-items:center;gap:8px}}
.token-banner.warn{{background:#451a03;color:#fbbf24;border-bottom:1px solid #92400e}}
.token-banner.error{{background:#450a0a;color:#f87171;border-bottom:1px solid #7f1d1d}}
.token-banner.info{{background:#082f49;color:#7dd3fc;border-bottom:1px solid #0c4a6e}}

/* STATS */
.statsbar{{background:#1e293b;border-bottom:1px solid #334155;padding:12px 24px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}}
.stat{{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:9px 16px;text-align:center;min-width:68px}}
.stat .n{{font-size:1.4rem;font-weight:700;color:#f1f5f9;line-height:1.1}}
.stat .l{{font-size:.6rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-top:3px}}
.stat.success .n{{color:#4ade80}}
.sep{{width:1px;height:32px;background:#334155}}
.pillar-pill{{border:1px solid;border-radius:20px;padding:3px 11px;font-size:.75rem}}
.pillar-pill b{{color:#f1f5f9;margin-left:4px}}

/* SCHEDULE */
.schedbar{{background:#1e293b;border-bottom:1px solid #334155;padding:9px 24px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;font-size:.8rem}}
.schedbar .lbl{{color:#64748b;font-size:.66rem;text-transform:uppercase;letter-spacing:.08em}}
.run-item{{color:#94a3b8}}.run-item b{{color:#f1f5f9}}

/* CONTENT */
.content{{max-width:820px;margin:0 auto;padding:22px 24px}}
.section-lbl{{font-size:.66rem;color:#64748b;text-transform:uppercase;letter-spacing:.1em;margin-bottom:12px}}

/* CARD */
.card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:17px 19px;margin-bottom:13px;transition:border-color .15s}}
.card:hover{{border-color:#475569}}
.card-header{{display:flex;flex-wrap:wrap;align-items:center;gap:7px;margin-bottom:8px}}
.pillar-tag{{font-size:.64rem;font-weight:700;padding:3px 8px;border-radius:5px;border:1px solid;text-transform:uppercase;letter-spacing:.07em}}
.badge{{font-size:.68rem;padding:3px 8px;border-radius:4px;font-weight:500}}
.badge.published{{background:#052e16;color:#4ade80}}
.badge.approved{{background:#2f1f05;color:#fbbf24}}
.badge.dry-run{{background:#1c1917;color:#a8a29e}}
.badge.draft{{background:#1c1917;color:#fbbf24}}
.badge.failed{{background:#450a0a;color:#f87171}}
.li-link{{font-size:.68rem;color:#0ea5e9;border:1px solid #0c4a6e;border-radius:4px;padding:2px 7px}}
.li-link:hover{{background:#082f49}}
.meta-right{{margin-left:auto;display:flex;gap:7px;align-items:center}}
.model-tag{{font-size:.65rem;background:#1a1a2e;color:#818cf8;border:1px solid #3730a3;padding:2px 7px;border-radius:4px}}
.date{{font-size:.68rem;color:#64748b}}
.topic{{font-size:.8rem;color:#94a3b8;font-style:italic;margin-bottom:6px}}
.fmt-row{{margin-bottom:9px}}
.fmt-tag{{font-size:.72rem;color:#64748b;background:#0f172a;border:1px solid #1e293b;border-radius:4px;padding:2px 7px}}
.alert{{border-radius:6px;padding:7px 11px;font-size:.76rem;margin-bottom:9px}}
.alert.warn{{background:#451a03;border:1px solid #92400e;color:#fbbf24}}
.alert.error{{background:#450a0a;border:1px solid #7f1d1d;color:#f87171}}
.post-text{{font-size:.87rem;line-height:1.78;color:#cbd5e1;white-space:pre-wrap;word-break:break-word}}
.post-text.collapsed{{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
.expand-btn{{background:none;border:none;color:#0ea5e9;font-size:.74rem;cursor:pointer;padding:5px 0;display:block;margin-top:4px}}
.expand-btn:hover{{color:#38bdf8}}
.card-footer{{display:flex;align-items:center;gap:9px;margin-top:13px}}
.bar-track{{flex:1;height:3px;background:#334155;border-radius:2px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:2px}}
.bar-fill.ok{{background:#22c55e}}.bar-fill.warn{{background:#f59e0b}}
.chars{{font-size:.68rem}}.chars.ok{{color:#4ade80}}.chars.warn{{color:#fbbf24}}
.retries{{font-size:.68rem;color:#f59e0b}}
.copy-btn{{background:#1e293b;border:1px solid #334155;color:#94a3b8;font-size:.68rem;padding:3px 9px;border-radius:5px;cursor:pointer;margin-left:auto;transition:all .15s}}
.copy-btn:hover{{border-color:#475569;color:#f1f5f9}}
.copy-btn.copied{{border-color:#22c55e;color:#4ade80}}
.review-actions{{display:flex;flex-wrap:wrap;align-items:center;gap:7px;padding:9px 0 4px;border-top:1px solid #1e293b;margin-top:6px}}
.review-label{{font-size:.62rem;color:#475569;text-transform:uppercase;letter-spacing:.08em;margin-right:2px}}
.rev-btn{{border:none;font-size:.71rem;font-weight:500;padding:4px 11px;border-radius:5px;cursor:pointer;transition:all .15s}}
.rev-changes{{background:#2f1f05;color:#fbbf24;border:1px solid #92400e}}.rev-changes:hover{{background:#451a03}}
.rev-edit{{background:#1a1a2e;color:#818cf8;border:1px solid #3730a3}}.rev-edit:hover{{background:#1e1b4b}}
.rev-recreate{{background:#0f172a;color:#64748b;border:1px solid #334155}}.rev-recreate:hover{{color:#94a3b8;border-color:#475569}}
.approve-publish-btn{{background:#0ea5e9;border:none;color:#fff;font-size:.72rem;font-weight:600;padding:4px 12px;border-radius:5px;cursor:pointer;transition:background .15s}}
.approve-publish-btn:hover{{background:#0284c7}}
.empty{{text-align:center;padding:60px 20px;color:#475569;font-size:.95rem;line-height:2.4}}
.empty a{{color:#0ea5e9;border-bottom:1px solid #0ea5e9}}
.modal-overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:200;align-items:center;justify-content:center}}
.modal-overlay.open{{display:flex}}
.modal-box{{background:#1e293b;border:1px solid #334155;border-radius:14px;padding:28px 30px;max-width:560px;width:90%;max-height:88vh;overflow-y:auto}}
.modal-box h3{{color:#f1f5f9;font-size:1rem;margin-bottom:18px}}
.modal-field{{margin-bottom:14px}}
.modal-label{{font-size:.68rem;color:#64748b;margin-bottom:4px;display:block}}
.modal-preview{{font-size:.78rem;color:#cbd5e1;background:#0f172a;border-radius:6px;padding:9px 12px;line-height:1.65;max-height:110px;overflow-y:auto;white-space:pre-wrap;word-break:break-word}}
.modal-path{{font-size:.75rem;color:#94a3b8;font-family:monospace;background:#0f172a;padding:5px 9px;border-radius:5px;display:block}}
.modal-pat{{width:100%;padding:8px 10px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;font-size:.82rem;outline:none}}
.modal-pat:focus{{border-color:#0ea5e9}}
.modal-hint{{font-size:.63rem;color:#475569;margin-top:5px;line-height:1.4}}
.modal-status{{font-size:.78rem;min-height:20px;margin-bottom:12px}}
.modal-actions{{display:flex;gap:10px}}
.modal-confirm{{background:#0ea5e9;color:#fff;border:none;padding:8px 18px;border-radius:6px;cursor:pointer;font-size:.82rem;font-weight:600}}
.modal-confirm:disabled{{background:#334155;color:#475569;cursor:default}}
.modal-cancel{{background:#1e293b;color:#94a3b8;border:1px solid #334155;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:.82rem}}
.modal-cancel:hover{{color:#f1f5f9;border-color:#475569}}
.metrics-row{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:9px}}
.metric-item{{font-size:.72rem;color:#94a3b8;background:#0f172a;border:1px solid #334155;border-radius:4px;padding:2px 8px}}
.quality-score{{font-size:.72rem;color:#fbbf24;background:#2f1f05;border:1px solid #92400e;border-radius:4px;padding:2px 8px;font-weight:600}}
.hook-tag{{font-size:.68rem;color:#818cf8;background:#1a1a2e;border:1px solid #3730a3;border-radius:4px;padding:2px 8px}}
.eng-card{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px 16px;margin-bottom:10px}}
.eng-header{{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-bottom:8px}}
.eng-badge{{font-size:.65rem;font-weight:600;padding:2px 8px;border-radius:4px}}
.eng-meta{{font-size:.68rem;color:#64748b;margin-left:auto}}
.eng-comment{{font-size:.82rem;color:#cbd5e1;background:#0f172a;border-radius:6px;padding:8px 11px;margin-bottom:8px;line-height:1.6}}
.eng-risk-note{{font-size:.72rem;color:#fbbf24;background:#451a03;border-radius:5px;padding:5px 10px;margin-bottom:8px}}
.eng-replies{{display:flex;flex-direction:column;gap:5px;margin-bottom:9px}}
.reply-opt{{font-size:.78rem;color:#94a3b8;background:#0f172a;border:1px solid #1e293b;border-radius:5px;padding:6px 10px;line-height:1.6}}
.reply-optrec{{border-color:#818cf855;color:#c7d2fe}}
.reply-idx{{font-size:.68rem;color:#475569;font-weight:600;margin-right:4px}}
.eng-cmd{{font-size:.68rem;color:#64748b}}
.eng-cmd code{{background:#0f172a;border:1px solid #334155;border-radius:4px;padding:2px 7px;color:#94a3b8;font-family:monospace}}
.rp-item{{font-size:.78rem;color:#4ade80;background:#052e16;border-radius:5px;padding:5px 10px;margin-bottom:5px}}
.leads-table{{display:flex;flex-direction:column;gap:5px}}
.lead-row{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;background:#1e293b;border:1px solid #334155;border-radius:8px;padding:8px 12px}}
.lead-name{{font-size:.8rem;color:#f1f5f9;font-weight:600;min-width:100px}}
.lead-count{{font-size:.68rem;color:#818cf8;background:#1a1a2e;border:1px solid #3730a3;border-radius:4px;padding:2px 8px}}
.lead-comment{{font-size:.74rem;color:#64748b;flex:1}}

.run-pillar{{text-transform:uppercase;font-size:.72rem;letter-spacing:.06em;font-weight:600}}

footer{{max-width:820px;margin:24px auto 0;padding:18px 24px 30px;border-top:1px solid #1e293b;color:#475569;font-size:.74rem;line-height:1.7}}
footer a{{color:#64748b;border-bottom:1px dotted #475569}}
footer a:hover{{color:#94a3b8}}

@media(max-width:600px){{
  .topbar,.statsbar,.schedbar,.content{{padding-left:14px;padding-right:14px}}
  .meta-right,.actions{{display:none}}
  .stat{{padding:8px 12px}}
}}
</style>
</head>
<body>

<div class="topbar">
  <h1>LinkedIn <em>Auto-Poster</em> &mdash; Dashboard</h1>
  <span class="updated">Updated {now_muscat}</span>
  <div class="actions">
    <a class="btn btn-primary" href="{ACTIONS_URL}" target="_blank">&#9654; Run workflow</a>
    <a class="btn btn-ghost" href="https://github.com/{REPO}/actions" target="_blank">&#128200; All runs</a>
    <a class="btn btn-ghost" href="https://www.linkedin.com/in/" target="_blank">&#128279; LinkedIn</a>
  </div>
</div>

{token_banner}

<div class="statsbar">
  <div class="stat"><div class="n">{total}</div><div class="l">Total</div></div>
  <div class="stat"><div class="n">{n_published}</div><div class="l">Published</div></div>
  <div class="stat"><div class="n">{n_drafts}</div><div class="l">Needs review</div></div>
  <div class="stat"><div class="n">{n_approved}</div><div class="l">Approved</div></div>
  <div class="stat"><div class="n">{n_failed}</div><div class="l">Failed</div></div>
  {avg_score_html}
  <div class="stat success"><div class="n">{success_pct}%</div><div class="l">Success</div></div>
  <div class="sep"></div>
  {pillar_pills}
</div>

<div class="schedbar">
  <span class="lbl">Next scheduled &rarr;</span>
  {runs_html}
</div>

<div class="content">
  <div class="section-lbl">Post history ({total})</div>
  {cards}
</div>

{engagement_html}

<footer>
  Drafts are generated <b>Mon &middot; Wed &middot; Fri</b> at <b>9:00 am Muscat</b>; publishing requires manual approval &nbsp;&middot;&nbsp;
  <a href="https://github.com/{REPO}" target="_blank">Source</a> &middot;
  <a href="https://github.com/{REPO}/blob/main/LINKEDIN_SETUP.md" target="_blank">Renew LinkedIn token</a> &middot;
  <a href="{ACTIONS_URL}" target="_blank">Run workflow</a>
</footer>

<!-- Request Changes modal -->
<div class="modal-overlay" id="revise-modal">
  <div class="modal-box">
    <h3>&#9998; Request Changes</h3>
    <input type="hidden" id="revise-draft-path">
    <div class="modal-field">
      <span class="modal-label">Draft path</span>
      <code class="modal-path" id="revise-path-display"></code>
    </div>
    <div class="modal-field">
      <label class="modal-label" for="revise-notes">What should Claude change? Be specific.</label>
      <textarea id="revise-notes" rows="4" placeholder="e.g. The opening is too generic. Make it start with a concrete dollar number or business outcome. Keep the list format but tighten each point to one sentence." style="width:100%;padding:8px 10px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;font-size:.82rem;outline:none;resize:vertical;line-height:1.55"></textarea>
    </div>
    <div class="modal-field">
      <label class="modal-label" for="revise-pat">GitHub Personal Access Token (workflow scope)</label>
      <input class="modal-pat" id="revise-pat" type="password" placeholder="ghp_..." autocomplete="off">
    </div>
    <div class="modal-status" id="revise-status"></div>
    <div class="modal-actions">
      <button class="modal-confirm" id="revise-confirm-btn" onclick="confirmRevise()">&#9998; Request Changes</button>
      <button class="modal-cancel" onclick="closeReviseModal()">Cancel</button>
    </div>
  </div>
</div>

<!-- Edit modal -->
<div class="modal-overlay" id="edit-modal">
  <div class="modal-box" style="max-width:680px">
    <h3>&#128393; Edit Draft</h3>
    <input type="hidden" id="edit-draft-path">
    <div class="modal-field">
      <label class="modal-label" for="edit-content">Edit the post text directly</label>
      <textarea id="edit-content" rows="12" style="width:100%;padding:9px 11px;background:#0f172a;border:1px solid #334155;border-radius:6px;color:#e2e8f0;font-size:.82rem;outline:none;resize:vertical;line-height:1.65;font-family:inherit;white-space:pre-wrap"></textarea>
      <div style="font-size:.64rem;color:#475569;margin-top:4px" id="edit-charcount">0 chars</div>
    </div>
    <div class="modal-field">
      <label class="modal-label" for="edit-pat">GitHub Personal Access Token (repo scope)</label>
      <input class="modal-pat" id="edit-pat" type="password" placeholder="ghp_..." autocomplete="off">
      <div class="modal-hint">Saves the edit directly to the repo as a commit.</div>
    </div>
    <div class="modal-status" id="edit-status"></div>
    <div class="modal-actions">
      <button class="modal-confirm" id="edit-confirm-btn" onclick="confirmEdit()">&#128190; Save Edit</button>
      <button class="modal-cancel" onclick="closeEditModal()">Cancel</button>
    </div>
  </div>
</div>

<!-- Approve & Publish modal -->
<div class="modal-overlay" id="approve-modal">
  <div class="modal-box">
    <h3>Approve &amp; Publish Draft</h3>
    <input type="hidden" id="modal-draft-path">
    <div class="modal-field">
      <span class="modal-label">Draft path</span>
      <code class="modal-path" id="modal-path-display"></code>
    </div>
    <div class="modal-field">
      <span class="modal-label">Post preview</span>
      <div class="modal-preview" id="modal-preview"></div>
    </div>
    <div class="modal-field">
      <label class="modal-label" for="modal-pat">GitHub Personal Access Token <em>(workflow scope)</em></label>
      <input class="modal-pat" id="modal-pat" type="password" placeholder="ghp_..." autocomplete="off">
      <div class="modal-hint">
        Saved in browser localStorage &mdash; never sent anywhere except GitHub's API. &nbsp;
        <a href="#" onclick="clearPat();return false;" style="color:#475569;text-decoration:underline">Clear saved token</a><br>
        Create at <b>GitHub &rarr; Settings &rarr; Developer settings &rarr; Personal access tokens &rarr; Tokens (classic)</b> with <b>repo</b> + <b>workflow</b> scope.
      </div>
    </div>
    <div class="modal-status" id="modal-status"></div>
    <div class="modal-actions">
      <button class="modal-confirm" id="modal-confirm-btn" onclick="confirmApprove()">&#9654; Approve &amp; Publish</button>
      <button class="modal-cancel" onclick="closeApproveModal()">Cancel</button>
    </div>
  </div>
</div>

<script>
var _REPO = '{REPO}';
var _WORKFLOW = '{WORKFLOW_FILE}';
var _BRANCH = '{branch}';

function toggle(i){{
  var t=document.getElementById('pt-'+i),b=document.querySelector('#post-'+i+' .expand-btn');
  if(t.classList.contains('collapsed')){{t.classList.remove('collapsed');b.innerHTML='Show less &#9650;';}}
  else{{t.classList.add('collapsed');b.innerHTML='Show more &#9660;';}}
}}
function copyPost(i){{
  var el=document.getElementById('pt-'+i);
  var collapsed=el.classList.contains('collapsed');
  if(collapsed) el.classList.remove('collapsed');
  var text=el.innerText;
  if(collapsed) el.classList.add('collapsed');
  navigator.clipboard.writeText(text).then(function(){{
    var btn=document.getElementById('copy-'+i);
    btn.innerHTML='&#10003; Copied';btn.classList.add('copied');
    setTimeout(function(){{btn.innerHTML='&#128203; Copy';btn.classList.remove('copied');}},2000);
  }});
}}

function _getPat(){{ return localStorage.getItem('gh_pat')||''; }}
function _setPat(v){{ if(v) localStorage.setItem('gh_pat',v); }}
function clearPat(){{ localStorage.removeItem('gh_pat');alert('GitHub token cleared.'); }}

function showReviseModal(btn){{
  var path=btn.getAttribute('data-path');
  document.getElementById('revise-draft-path').value=path;
  document.getElementById('revise-path-display').textContent=path;
  document.getElementById('revise-notes').value='';
  document.getElementById('revise-status').textContent='';
  document.getElementById('revise-pat').value=_getPat();
  var cb=document.getElementById('revise-confirm-btn');
  cb.textContent='&#9998; Request Changes';cb.disabled=false;
  document.getElementById('revise-modal').classList.add('open');
}}
function closeReviseModal(){{ document.getElementById('revise-modal').classList.remove('open'); }}
document.getElementById('revise-modal').addEventListener('click',function(e){{ if(e.target===this) closeReviseModal(); }});

async function confirmRevise(){{
  var pat=document.getElementById('revise-pat').value.trim();
  var notes=document.getElementById('revise-notes').value.trim();
  var path=document.getElementById('revise-draft-path').value;
  var st=document.getElementById('revise-status');
  var cb=document.getElementById('revise-confirm-btn');
  if(!pat){{st.textContent='Enter your GitHub PAT.';st.style.color='#f87171';return;}}
  if(!notes){{st.textContent='Describe what needs to change.';st.style.color='#f87171';return;}}
  _setPat(pat);
  cb.textContent='Triggering…';cb.disabled=true;st.textContent='';
  try{{
    var resp=await fetch('https://api.github.com/repos/'+_REPO+'/actions/workflows/'+_WORKFLOW+'/dispatches',
      {{method:'POST',headers:{{'Authorization':'Bearer '+pat,'Accept':'application/vnd.github.v3+json','Content-Type':'application/json'}},
        body:JSON.stringify({{ref:_BRANCH,inputs:{{action:'revise_draft',draft_file:path,revision_notes:notes}}}})
      }});
    if(resp.status===204){{st.textContent='✓ Revision requested! Claude is rewriting the draft.';st.style.color='#4ade80';cb.textContent='Requested';}}
    else{{var e=await resp.json().catch(function(){{return{{}}}});st.textContent='Error '+resp.status+': '+(e.message||'check your PAT');st.style.color='#f87171';cb.textContent='&#9998; Request Changes';cb.disabled=false;}}
  }}catch(e){{st.textContent='Network error: '+e.message;st.style.color='#f87171';cb.textContent='&#9998; Request Changes';cb.disabled=false;}}
}}

function showEditModal(btn){{
  var path=btn.getAttribute('data-path');
  var preview=btn.getAttribute('data-preview');
  document.getElementById('edit-draft-path').value=path;
  var ta=document.getElementById('edit-content');
  ta.value=preview;
  document.getElementById('edit-charcount').textContent=preview.length+' chars';
  ta.oninput=function(){{ document.getElementById('edit-charcount').textContent=ta.value.length+' chars'; }};
  document.getElementById('edit-status').textContent='';
  document.getElementById('edit-pat').value=_getPat();
  var cb=document.getElementById('edit-confirm-btn');
  cb.textContent='&#128190; Save Edit';cb.disabled=false;
  document.getElementById('edit-modal').classList.add('open');
}}
function closeEditModal(){{ document.getElementById('edit-modal').classList.remove('open'); }}
document.getElementById('edit-modal').addEventListener('click',function(e){{ if(e.target===this) closeEditModal(); }});

async function confirmEdit(){{
  var pat=document.getElementById('edit-pat').value.trim();
  var path=document.getElementById('edit-draft-path').value;
  var content=document.getElementById('edit-content').value;
  var st=document.getElementById('edit-status');
  var cb=document.getElementById('edit-confirm-btn');
  if(!pat){{st.textContent='Enter your GitHub PAT.';st.style.color='#f87171';return;}}
  if(!content.trim()){{st.textContent='Post text cannot be empty.';st.style.color='#f87171';return;}}
  _setPat(pat);
  cb.textContent='Saving…';cb.disabled=true;st.textContent='';
  try{{
    // Get current file SHA
    var metaResp=await fetch('https://api.github.com/repos/'+_REPO+'/contents/'+path,
      {{headers:{{'Authorization':'Bearer '+pat,'Accept':'application/vnd.github.v3+json'}}}});
    if(!metaResp.ok){{var e=await metaResp.json().catch(function(){{return{{}}}});throw new Error('Could not read file: '+( e.message||metaResp.status));}}
    var meta=await metaResp.json();
    var sha=meta.sha;
    // Decode current JSON, update post field, re-encode
    var currentJson=JSON.parse(atob(meta.content.replace(/\\n/g,'')));
    currentJson.post=content;
    currentJson.char_count=content.length;
    currentJson.manually_edited=true;
    currentJson.edited_at=new Date().toISOString();
    var newContent=btoa(unescape(encodeURIComponent(JSON.stringify(currentJson,null,2))));
    var putResp=await fetch('https://api.github.com/repos/'+_REPO+'/contents/'+path,
      {{method:'PUT',headers:{{'Authorization':'Bearer '+pat,'Accept':'application/vnd.github.v3+json','Content-Type':'application/json'}},
        body:JSON.stringify({{message:'edit: manual draft revision via dashboard',content:newContent,sha:sha,branch:_BRANCH}})
      }});
    if(putResp.status===200||putResp.status===201){{
      st.textContent='✓ Edit saved to repo. Refresh the dashboard in ~30 seconds.';st.style.color='#4ade80';
      cb.textContent='Saved';
    }}else{{
      var e2=await putResp.json().catch(function(){{return{{}}}});
      st.textContent='Error '+putResp.status+': '+(e2.message||'check your PAT scope (needs repo)');
      st.style.color='#f87171';cb.textContent='&#128190; Save Edit';cb.disabled=false;
    }}
  }}catch(e){{st.textContent='Error: '+e.message;st.style.color='#f87171';cb.textContent='&#128190; Save Edit';cb.disabled=false;}}
}}

function confirmRecreate(btn){{
  var pillar=btn.getAttribute('data-pillar')||'same pillar';
  if(!confirm('Regenerate a new draft for the '+pillar+' pillar?\\nThe current draft will remain in posts_history but will be replaced in the dashboard.'))return;
  var pat=_getPat();
  if(!pat){{pat=prompt('Enter your GitHub PAT (workflow scope):');if(!pat)return;_setPat(pat);}}
  fetch('https://api.github.com/repos/'+_REPO+'/actions/workflows/'+_WORKFLOW+'/dispatches',
    {{method:'POST',headers:{{'Authorization':'Bearer '+pat,'Accept':'application/vnd.github.v3+json','Content-Type':'application/json'}},
      body:JSON.stringify({{ref:_BRANCH,inputs:{{action:'generate_draft',pillar:pillar}}}})
    }}
  ).then(function(r){{
    if(r.status===204){{alert('✓ New draft is being generated for the '+pillar+' pillar. Refresh in ~60 seconds.');}}
    else{{r.json().then(function(e){{alert('Error '+r.status+': '+(e.message||'check your PAT'));}}).catch(function(){{alert('Error '+r.status);}});}}
  }}).catch(function(e){{alert('Network error: '+e.message);}});
}}

function showApproveModal(btn){{
  var path=btn.getAttribute('data-path');
  var preview=btn.getAttribute('data-preview');
  document.getElementById('modal-draft-path').value=path;
  document.getElementById('modal-path-display').textContent=path;
  document.getElementById('modal-preview').textContent=preview;
  document.getElementById('modal-status').textContent='';
  document.getElementById('modal-status').style.color='';
  var cb=document.getElementById('modal-confirm-btn');
  cb.textContent='▶ Approve & Publish';cb.disabled=false;
  document.getElementById('modal-pat').value=_getPat();
  document.getElementById('approve-modal').classList.add('open');
}}

function closeApproveModal(){{
  document.getElementById('approve-modal').classList.remove('open');
}}

document.getElementById('approve-modal').addEventListener('click',function(e){{
  if(e.target===this) closeApproveModal();
}});

async function confirmApprove(){{
  var pat=document.getElementById('modal-pat').value.trim();
  var draftPath=document.getElementById('modal-draft-path').value;
  var st=document.getElementById('modal-status');
  var cb=document.getElementById('modal-confirm-btn');
  if(!pat){{st.textContent='Enter your GitHub PAT to continue.';st.style.color='#f87171';return;}}
  _setPat(pat);
  cb.textContent='Triggering…';cb.disabled=true;st.textContent='';
  try{{
    var resp=await fetch(
      'https://api.github.com/repos/'+_REPO+'/actions/workflows/'+_WORKFLOW+'/dispatches',
      {{method:'POST',
        headers:{{'Authorization':'Bearer '+pat,'Accept':'application/vnd.github.v3+json','Content-Type':'application/json'}},
        body:JSON.stringify({{ref:_BRANCH,inputs:{{action:'publish_draft',draft_file:draftPath}}}})
      }}
    );
    if(resp.status===204){{
      st.textContent='✓ Workflow triggered! Open GitHub Actions to track progress.';
      st.style.color='#4ade80';
      cb.textContent='Triggered';
    }}else{{
      var err=await resp.json().catch(function(){{return{{}}}});
      st.textContent='GitHub API error '+resp.status+': '+(err.message||'check your PAT and try again');
      st.style.color='#f87171';
      cb.textContent='▶ Approve & Publish';cb.disabled=false;
    }}
  }}catch(e){{
    st.textContent='Network error: '+e.message;
    st.style.color='#f87171';
    cb.textContent='▶ Approve & Publish';cb.disabled=false;
  }}
}}
</script>
</body>
</html>"""


if __name__ == "__main__":
    posts = load_posts()
    out   = DOCS_DIR / "index.html"
    out.write_text(generate(posts), encoding="utf-8")
    print(f"Dashboard generated → {out}  ({len(posts)} posts)")
