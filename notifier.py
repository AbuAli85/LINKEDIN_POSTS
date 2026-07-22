"""Optional draft-ready notifications for the LinkedIn content workflow.

The notifier is intentionally best-effort. Missing configuration or delivery
failures must never block draft generation, because the repository's safety
model is that GitHub Actions creates drafts while the owner decides whether to
publish them.
"""

from __future__ import annotations

import os
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote as _url_quote

import requests


DEFAULT_FROM_EMAIL = "LinkedIn Draft Bot <onboarding@resend.dev>"
WORKFLOW_FILE = "auto-post.yml"


def send_draft_ready(
    draft_path: str,
    post_preview: str,
    pillar: str,
    dashboard_url: str | None = None,
) -> None:
    """Send optional email and/or webhook notifications for a new draft.

    Notification settings are read from environment variables:

    - NOTIFY_ON_DRAFT: set to "false", "0", or "no" to disable notifications
    - RESEND_API_KEY and NOTIFY_EMAIL: send a Resend email when both are set
    - NOTIFY_WEBHOOK_URL: POST a JSON notification payload when set
    - NOTIFY_FROM: optional Resend sender address

    All channels are best-effort and fail gracefully.
    """

    if not _enabled():
        print("Draft notifications disabled by NOTIFY_ON_DRAFT.")
        return

    context = _notification_context(draft_path, post_preview, pillar, dashboard_url)

    if _env_value("RESEND_API_KEY") and _env_value("NOTIFY_EMAIL"):
        _send_email(context)
    else:
        print("Draft email notification skipped: RESEND_API_KEY or NOTIFY_EMAIL not configured.")

    if _env_value("NOTIFY_WEBHOOK_URL"):
        _send_webhook(context)
    else:
        print("Draft webhook notification skipped: NOTIFY_WEBHOOK_URL not configured.")


def _env_value(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _enabled() -> bool:
    raw = _env_value("NOTIFY_ON_DRAFT", "true") or "true"
    return raw.lower() not in {"0", "false", "no", "off"}


def _notification_context(
    draft_path: str,
    post_preview: str,
    pillar: str,
    dashboard_url: str | None,
) -> dict[str, Any]:
    repo = os.environ.get("GITHUB_REPOSITORY", "AbuAli85/LINKEDIN_POSTS")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.environ.get("GITHUB_RUN_ID")
    run_url = f"{server_url}/{repo}/actions/runs/{run_id}" if run_id else None

    workflow_url = f"{server_url}/{repo}/actions/workflows/{WORKFLOW_FILE}"
    dashboard = _clean_url(dashboard_url) or _env_value("DASHBOARD_URL") or _default_dashboard_url(repo)
    display_path = _display_draft_path(draft_path)
    encoded_path = _url_quote(display_path, safe="")
    base = dashboard.rstrip("/")
    approve_url = f"{base}/?approve={encoded_path}" if base else ""
    revise_url  = f"{base}/?revise={encoded_path}"  if base else ""

    return {
        "event": "draft_ready",
        "draft_path": display_path,
        "pillar": pillar,
        "post_preview": _clean_preview(post_preview),
        "post_full": (post_preview or "").strip(),
        "dashboard_url": dashboard,
        "approve_url": approve_url,
        "revise_url": revise_url,
        "publish_workflow_url": workflow_url,
        "github_run_url": run_url,
        "repository": repo,
    }


def _default_dashboard_url(repo: str) -> str:
    owner, _, name = repo.partition("/")
    if owner and name:
        return f"https://{owner}.github.io/{name}/"
    return ""


def _clean_url(value: str | None) -> str:
    return "" if value is None else value.strip()


def _display_draft_path(draft_path: str) -> str:
    clean_path = draft_path.strip()
    # Check company_posts_history/ BEFORE posts_history/ — the latter is a
    # substring of the former and would strip the 'company_' prefix otherwise.
    for marker in ("company_posts_history/", "posts_history/"):
        if marker in clean_path:
            return marker + clean_path.split(marker, 1)[1]

    try:
        path = Path(clean_path)
        if not path.is_absolute():
            return clean_path
        return path.name
    except Exception:  # noqa: BLE001 - display cleanup must not block notifications
        return clean_path


def _clean_preview(text: str) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= 200:
        return compact
    return compact[:197].rstrip() + "..."


def _send_email(context: dict[str, Any]) -> None:
    try:
        import resend

        sender = _env_value("NOTIFY_FROM", DEFAULT_FROM_EMAIL) or DEFAULT_FROM_EMAIL
        resend.api_key = _env_value("RESEND_API_KEY") or ""
        response = resend.Emails.send(
            {
                "from": sender,
                "to": [_env_value("NOTIFY_EMAIL") or ""],
                "subject": f"LinkedIn draft ready for review: {context['pillar']}",
                "html": _email_html(context),
                "text": _email_text(context),
            }
        )
        message_id = response.get("id") if isinstance(response, dict) else None
        if message_id:
            print(f"Draft email notification sent via Resend: {message_id}")
        else:
            print("Draft email notification sent via Resend.")
    except Exception as exc:  # noqa: BLE001 - notifications must not abort drafts
        print(f"WARNING: draft email notification failed: {exc}")


def _send_webhook(context: dict[str, Any]) -> None:
    try:
        response = requests.post(
            _env_value("NOTIFY_WEBHOOK_URL") or "",
            json=context,
            timeout=10,
            headers={"User-Agent": "linkedin-draft-notifier/1.0"},
        )
        response.raise_for_status()
        print(f"Draft webhook notification sent: HTTP {response.status_code}")
    except Exception as exc:  # noqa: BLE001 - notifications must not abort drafts
        print(f"WARNING: draft webhook notification failed: {exc}")


def _email_text(context: dict[str, Any]) -> str:
    run_line = f"\nGitHub run: {context['github_run_url']}" if context.get("github_run_url") else ""
    return (
        "A new LinkedIn draft is ready for owner review.\n\n"
        f"Draft path: {context['draft_path']}\n"
        f"Pillar: {context['pillar']}\n"
        f"Preview: {context['post_preview']}\n\n"
        f"Dashboard: {context['dashboard_url']}\n"
        f"Publish workflow: {context['publish_workflow_url']}"
        f"{run_line}\n\n"
        "This alert does not publish anything. Review the draft, use Chatbase if helpful, "
        "and only then manually run publish_draft with the draft path above."
    )


def send_empty_slot_alert(pillar: str, publish_date: str) -> None:
    """Alert the owner that tomorrow's scheduled publish slot has no approved draft.

    Uses the same Resend + webhook fan-out as send_draft_ready.
    Both channels are best-effort — failures are logged but never raised.
    """
    if not _enabled():
        print("Notifications disabled by NOTIFY_ON_DRAFT.")
        return

    repo       = os.environ.get("GITHUB_REPOSITORY", "AbuAli85/LINKEDIN_POSTS")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    dashboard  = _env_value("DASHBOARD_URL") or _default_dashboard_url(repo)
    workflow_url = f"{server_url}/{repo}/actions/workflows/{WORKFLOW_FILE}"

    subject = f"[Action needed] Tomorrow’s {pillar} slot is empty"
    context: dict[str, Any] = {
        "event":               "empty_slot_warning",
        "pillar":              pillar,
        "publish_date":        publish_date,
        "dashboard_url":       dashboard,
        "publish_workflow_url": workflow_url,
    }

    if _env_value("RESEND_API_KEY") and _env_value("NOTIFY_EMAIL"):
        try:
            import resend
            sender = _env_value("NOTIFY_FROM", DEFAULT_FROM_EMAIL) or DEFAULT_FROM_EMAIL
            resend.api_key = _env_value("RESEND_API_KEY") or ""
            resend.Emails.send({
                "from": sender,
                "to":   [_env_value("NOTIFY_EMAIL") or ""],
                "subject": subject,
                "html": _empty_slot_html(context, subject),
                "text": _empty_slot_text(context, subject),
            })
            print(f"Empty-slot alert email sent (pillar={pillar})")
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: empty-slot email failed: {exc}")
    else:
        print("Empty-slot email skipped: RESEND_API_KEY or NOTIFY_EMAIL not configured.")

    if _env_value("NOTIFY_WEBHOOK_URL"):
        try:
            resp = requests.post(
                _env_value("NOTIFY_WEBHOOK_URL") or "",
                json=context,
                timeout=10,
                headers={"User-Agent": "linkedin-draft-notifier/1.0"},
            )
            resp.raise_for_status()
            print(f"Empty-slot webhook sent: HTTP {resp.status_code}")
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: empty-slot webhook failed: {exc}")
    else:
        print("Empty-slot webhook skipped: NOTIFY_WEBHOOK_URL not configured.")


def _empty_slot_text(context: dict[str, Any], subject: str) -> str:
    return (
        f"{subject}\n\n"
        f"Tomorrow ({context['publish_date']}) is the {context['pillar']} publish day "
        "but no approved draft was found.\n\n"
        f"Dashboard:        {context['dashboard_url']}\n"
        f"Dispatch workflow: {context['publish_workflow_url']}\n\n"
        "Options: run generate_draft with FORCE_PILLAR and approve immediately, "
        "or open the dashboard and approve an existing draft.\n\n"
        "This alert does not generate or publish anything."
    )


def _empty_slot_html(context: dict[str, Any], subject: str) -> str:
    return (
        '<div style="font-family:Arial,sans-serif;line-height:1.5;color:#111827;max-width:640px">'
        f'<h2 style="color:#dc2626;margin-bottom:8px">{escape(subject)}</h2>'
        f'<p>Tomorrow (<strong>{escape(context["publish_date"])}</strong>) is the '
        f'<strong>{escape(context["pillar"])}</strong> publish day, '
        "but no approved draft was found for this slot.</p>"
        "<p><strong>Options</strong></p>"
        "<ul>"
        f'<li>Run <code>generate_draft</code> with <code>FORCE_PILLAR={escape(context["pillar"])}</code>'
        " and approve immediately from the dashboard.</li>"
        f'<li>Open the <a href="{escape(context["dashboard_url"])}">dashboard</a>'
        " and approve an existing draft.</li>"
        "</ul>"
        f'<p><a href="{escape(context["publish_workflow_url"])}">Open dispatch workflow</a></p>'
        '<p style="font-size:13px;color:#6b7280">'
        "This alert does not generate or publish anything.</p>"
        "</div>"
    )


_PILLAR_COLORS: dict[str, tuple[str, str, str]] = {
    "pain":       ("#e8372a", "rgba(232,55,42,.12)",  "rgba(232,55,42,.3)"),
    "proof":      ("#2a9a5c", "rgba(42,154,92,.12)",   "rgba(42,154,92,.3)"),
    "vision":     ("#818cf8", "rgba(129,140,248,.12)", "rgba(129,140,248,.3)"),
    "conversion": ("#d4840a", "rgba(212,132,10,.12)",  "rgba(212,132,10,.3)"),
    "leadership": ("#2e7de0", "rgba(46,125,224,.12)",  "rgba(46,125,224,.3)"),
    "marketing":  ("#d4840a", "rgba(212,132,10,.12)",  "rgba(212,132,10,.3)"),
}
_DEFAULT_PILLAR_COLOR = ("#94a3b8", "rgba(148,163,184,.12)", "rgba(148,163,184,.3)")


def _email_html(context: dict[str, Any]) -> str:
    pillar = context.get("pillar", "")
    color, bg, border = _PILLAR_COLORS.get(pillar, _DEFAULT_PILLAR_COLOR)
    post_text   = escape(context.get("post_full") or context.get("post_preview", ""))
    draft_path  = escape(context.get("draft_path", ""))
    approve_url = escape(context.get("approve_url", context.get("dashboard_url", "")))
    revise_url  = escape(context.get("revise_url",  context.get("dashboard_url", "")))
    dashboard   = escape(context.get("dashboard_url", ""))
    run_url     = escape(context.get("github_run_url", "") or "")
    run_cell    = (
        f'&nbsp;&middot;&nbsp;<a href="{run_url}" style="color:rgba(255,255,255,.35);text-decoration:none">View run</a>'
        if run_url else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LinkedIn draft ready &mdash; {escape(pillar)}</title>
</head>
<body style="margin:0;padding:0;background-color:#0b0b0c;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#0b0b0c">
<tr><td align="center" style="padding:32px 16px">
<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%">

  <!-- Header -->
  <tr><td style="padding-bottom:22px">
    <table cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="background-color:#e8372a;border-radius:7px;padding:5px 9px;font-size:11px;font-weight:700;color:#ffffff;line-height:1">LI</td>
      <td style="padding-left:10px;color:#ede9e3;font-size:13px;font-weight:500;vertical-align:middle">
        LinkedIn&nbsp;<span style="color:#e8372a">Auto&#8209;Poster</span>
      </td>
    </tr></table>
  </td></tr>

  <!-- Card -->
  <tr><td style="background-color:#111113;border-radius:12px;border:1px solid rgba(255,255,255,.07);border-left:4px solid {color};padding:24px 26px">

    <!-- Pillar + status badges -->
    <div style="margin-bottom:14px">
      <span style="background-color:{bg};color:{color};border:1px solid {border};font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;padding:3px 9px;border-radius:4px">{escape(pillar) or "draft"}</span>
      <span style="background-color:rgba(212,132,10,.12);color:#d4840a;border:1px solid rgba(212,132,10,.3);font-size:10px;font-weight:600;padding:3px 9px;border-radius:4px;margin-left:6px">Needs Review</span>
    </div>

    <!-- Label -->
    <p style="color:rgba(255,255,255,.4);font-size:12px;margin:0 0 14px 0;text-transform:uppercase;letter-spacing:.08em">New draft ready for approval</p>

    <!-- Full post text -->
    <div style="background-color:#0b0b0c;border-radius:8px;padding:16px 18px;margin-bottom:24px">
      <pre style="color:rgba(255,255,255,.72);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:13px;line-height:1.85;white-space:pre-wrap;word-break:break-word;margin:0;padding:0">{post_text}</pre>
    </div>

    <!-- Action buttons -->
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="padding-right:6px" width="50%">
        <a href="{approve_url}" style="display:block;background-color:#e8372a;color:#ffffff;text-decoration:none;text-align:center;padding:13px 18px;border-radius:8px;font-size:14px;font-weight:700;letter-spacing:.01em">&#10003;&nbsp; Approve</a>
      </td>
      <td style="padding-left:6px" width="50%">
        <a href="{revise_url}" style="display:block;background-color:#1c1000;color:#d4840a;text-decoration:none;text-align:center;padding:13px 18px;border-radius:8px;font-size:14px;font-weight:600;border:1px solid rgba(212,132,10,.4)">&#9998;&nbsp; Request Changes</a>
      </td>
    </tr></table>

    <!-- Hint -->
    <p style="color:rgba(255,255,255,.22);font-size:11px;text-align:center;margin:14px 0 0 0;line-height:1.6">
      Clicking Approve opens the dashboard and triggers the workflow automatically.<br>You&rsquo;ll be asked for a GitHub PAT &mdash; held only for that browser tab, never saved.
    </p>

  </td></tr>

  <!-- Footer -->
  <tr><td style="padding-top:18px;text-align:center">
    <p style="color:rgba(255,255,255,.22);font-size:11px;margin:0;line-height:2">
      <code style="color:rgba(255,255,255,.35);font-size:11px">{draft_path}</code><br>
      <a href="{dashboard}" style="color:rgba(255,255,255,.32);text-decoration:none">Open dashboard</a>{run_cell}
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""
