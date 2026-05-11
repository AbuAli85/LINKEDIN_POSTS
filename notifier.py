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
    preview = _clean_preview(post_preview)
    display_path = _display_draft_path(draft_path)

    return {
        "event": "draft_ready",
        "draft_path": display_path,
        "pillar": pillar,
        "post_preview": preview,
        "dashboard_url": dashboard,
        "publish_workflow_url": workflow_url,
        "github_run_url": run_url,
        "repository": repo,
        "instructions": (
            "Review the draft in the dashboard or posts_history JSON, use Chatbase for review, "
            "then manually run the publish_draft workflow with this draft path if approved."
        ),
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
    marker = "posts_history/"
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


def _email_html(context: dict[str, Any]) -> str:
    run_link = ""
    if context.get("github_run_url"):
        run_link = f'<p><strong>GitHub run:</strong> <a href="{escape(context["github_run_url"])}">View run</a></p>'

    return f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5; color: #111827; max-width: 640px;">
      <h2 style="margin-bottom: 8px;">LinkedIn draft ready for review</h2>
      <p>A new draft has been generated and is waiting for owner approval.</p>
      <table style="border-collapse: collapse; width: 100%; margin: 18px 0;">
        <tr><td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>Draft path</strong></td><td style="padding: 8px; border: 1px solid #e5e7eb;"><code>{escape(context['draft_path'])}</code></td></tr>
        <tr><td style="padding: 8px; border: 1px solid #e5e7eb;"><strong>Pillar</strong></td><td style="padding: 8px; border: 1px solid #e5e7eb;">{escape(context['pillar'])}</td></tr>
      </table>
      <p><strong>Preview</strong></p>
      <blockquote style="border-left: 4px solid #d1d5db; padding-left: 12px; color: #374151;">{escape(context['post_preview'])}</blockquote>
      <p><a href="{escape(context['dashboard_url'])}">Open dashboard</a></p>
      <p><a href="{escape(context['publish_workflow_url'])}">Open publish workflow</a></p>
      {run_link}
      <p style="font-size: 13px; color: #6b7280;">This alert does not publish anything. Review the draft, use Chatbase if helpful, and only then manually run <code>publish_draft</code> with the draft path above.</p>
    </div>
    """.strip()
