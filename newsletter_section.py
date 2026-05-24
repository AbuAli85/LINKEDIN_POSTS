"""HTML section for the dashboard showing newsletter issues.

Drop-in module — call newsletter_dashboard_section() from dashboard.py and
inject its output into the main content area.
"""

import html
import json
from pathlib import Path

ROOT           = Path(__file__).parent
NEWSLETTER_DIR = ROOT / "newsletter_history"


def _load_issues() -> list[dict]:
    """Return newsletter issues, newest first."""
    if not NEWSLETTER_DIR.exists():
        return []
    files = sorted(NEWSLETTER_DIR.glob("issue_*.json"), reverse=True)
    out = []
    for f in files:
        try:
            issue = json.loads(f.read_text(encoding="utf-8"))
            issue["_filename"] = f.name
            out.append(issue)
        except Exception:
            continue
    return out


def _issue_card(issue: dict) -> str:
    m         = issue.get("_meta", {})
    num       = m.get("issue_number", "?")
    date      = m.get("date", "")
    model     = m.get("model", "")
    status    = m.get("status", "draft")
    last_send = m.get("last_send", {}) or {}
    subject   = html.escape(issue.get("subject", "(no subject)"))
    preview   = html.escape(issue.get("preview", ""))
    opening   = html.escape((issue.get("opening") or "")[:280])

    status_badge = {
        "draft":     '<span class="badge draft">Draft</span>',
        "approved":  '<span class="badge approved">Approved</span>',
        "sent":      '<span class="badge published">&#10003; Sent</span>',
    }.get(status, f'<span class="badge">{html.escape(status)}</span>')

    sent_info = ""
    if last_send:
        sent_info = (
            f'<div class="news-sent">'
            f'Last send: <b>{html.escape(last_send.get("mode", ""))}</b>'
            + (f' &rarr; {html.escape(last_send.get("to", ""))}'
               if last_send.get("to") else "")
            + f' &middot; <span style="color:rgba(255,255,255,.4)">{html.escape(last_send.get("at", "")[:19])}</span>'
            "</div>"
        )

    num_esc = html.escape(str(num))

    draft_actions = ""
    if status == "draft":
        draft_actions = f"""
      <div style="display:flex;flex-wrap:wrap;gap:7px;margin-top:12px;padding-top:10px;border-top:1px solid rgba(255,255,255,.06)">
        <span style="font-size:10px;color:rgba(255,255,255,.3);text-transform:uppercase;letter-spacing:.08em;align-self:center;margin-right:2px">Newsletter:</span>
        <button type="button" class="approve-btn" style="font-size:11px;padding:6px 14px"
                onclick="showNewsletterApproveModal('{num_esc}')">&#10003; Approve &amp; Test Send</button>
        <button type="button" class="rev-btn rev-recreate"
                onclick="showNewsletterTestModal('{num_esc}')">&#128231; Send Test</button>
      </div>"""
    elif status == "sent":
        draft_actions = '<div style="margin-top:10px"><span class="badge published" style="font-size:11px">&#10003; Sent to audience</span></div>'

    return f"""
    <div class="card news-card" data-issue="{num_esc}">
      <div class="card-header">
        <span class="pillar-tag" style="background:rgba(42,154,92,.15);color:#2a9a5c;border-color:rgba(42,154,92,.35)">NEWSLETTER &middot; #{num_esc}</span>
        {status_badge}
        <span class="meta-right">
          <span class="model-tag">{html.escape(model)}</span>
          <span class="date">{html.escape(date)}</span>
        </span>
      </div>
      <div class="topic" style="font-size:16px;margin-top:8px">{subject}</div>
      <div class="news-preview">{preview}</div>
      <div class="post-text collapsed" style="margin-top:10px">{opening}&hellip;</div>
      {sent_info}
      {draft_actions}
      <div class="card-footer" style="margin-top:14px">
        <span class="chars" style="color:rgba(255,255,255,.45)">Issue #{num_esc}</span>
        <span style="color:rgba(255,255,255,.3);font-size:11px;font-family:'DM Mono',monospace">
          newsletter_history/{html.escape(issue.get("_filename", ""))}
        </span>
      </div>
    </div>"""


def newsletter_dashboard_section() -> str:
    """Return the full Newsletter section HTML for the dashboard."""
    issues = _load_issues()
    total  = len(issues)
    drafts = sum(1 for i in issues if (i.get("_meta", {}).get("status", "draft") == "draft"))
    sent   = sum(1 for i in issues if (i.get("_meta", {}).get("status") == "sent"))

    if not issues:
        body = (
            '<div class="empty" style="padding:24px">'
            'No newsletter issues yet. Run <code style="font-family:\'DM Mono\',monospace">'
            'python newsletter.py</code> to draft your first issue, or wait for the weekly workflow.'
            '</div>'
        )
    else:
        body = "".join(_issue_card(i) for i in issues[:6])
        if total > 6:
            body += (
                f'<div class="empty" style="padding:14px;font-size:13px;color:rgba(255,255,255,.4)">'
                f'+{total - 6} older issues in newsletter_history/'
                "</div>"
            )

    return f"""
<div class="statsbar" style="padding-top:30px;border-top:1px solid rgba(255,255,255,.05);margin-top:12px">
  <div class="stat"><div class="n">{total}</div><div class="l">Newsletter issues</div></div>
  <div class="stat"><div class="n">{drafts}</div><div class="l">Drafts</div></div>
  <div class="stat green"><div class="n">{sent}</div><div class="l">Sent</div></div>
</div>

<div class="content" style="margin-top:0;padding-top:18px">
  <h2 class="section-lbl">Newsletter ({total})</h2>
  {body}
</div>

<style>
.news-card{{border-left-color:#2a9a5c !important}}
.news-preview{{font-size:13px;color:rgba(255,255,255,.55);margin-top:6px;font-style:italic}}
.news-sent{{font-size:12px;color:rgba(255,255,255,.55);margin-top:10px;
           padding:8px 12px;background:rgba(42,154,92,.06);border-radius:6px;
           border-left:2px solid rgba(42,154,92,.4)}}
</style>"""
