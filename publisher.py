"""Publish a post to LinkedIn via the UGC Posts API."""

import logging
import os
import time

import requests

LINKEDIN_API     = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_ASSETS  = "https://api.linkedin.com/v2/assets?action=registerUpload"
CHAR_LIMIT       = 3000   # LinkedIn shareCommentary hard cap
MAX_RETRIES      = 3
RETRY_CODES      = {429, 500, 502, 503, 504}

CTA_URL = "https://www.thesmartpro.io/sanad/assistant"

CTA_COMMENTS: dict[str, str] = {
    "pain": (
        "🤖 Related question that comes up a lot:\n"
        '"What\'s the penalty if our WPS file is rejected after the salary deadline?"\n\n'
        "Ask Sanad — free, instant answers on Oman government services. English or Arabic:\n"
        f"{CTA_URL}\n\n"
        "Government fees verified May 2026. No signup needed."
    ),
    "proof": (
        "🤖 Sanad handles the government compliance side the same way SmartPro\n"
        "handles payroll — instant answers, no manual lookup.\n\n"
        "Work permits, visa renewals, business registration fees, Sanad office finder.\n\n"
        f"Try it free: {CTA_URL}\n\n"
        "English or Arabic. No account needed."
    ),
}

logger = logging.getLogger(__name__)


class LinkedInError(Exception):
    pass


# ---------------------------------------------------------------------------
# Image upload helpers
# ---------------------------------------------------------------------------

def _upload_image(token: str, author: str, image_bytes: bytes) -> str | None:
    """Register and upload a PNG to LinkedIn. Returns the asset URN or None on failure."""
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    reg_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author,
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent",
            }],
        }
    }

    try:
        reg = requests.post(LINKEDIN_ASSETS, headers=headers, json=reg_payload, timeout=30)
    except Exception as exc:
        logger.warning("image_register network error: %s", exc)
        return None

    if reg.status_code != 200:
        logger.warning("image_register failed HTTP %s: %s", reg.status_code, reg.text[:200])
        return None

    value      = reg.json().get("value", {})
    asset_urn  = value.get("asset")
    upload_url = (
        value.get("uploadMechanism", {})
             .get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
             .get("uploadUrl")
    )

    if not asset_urn or not upload_url:
        logger.warning("image_register: missing asset or uploadUrl in response")
        return None

    try:
        put = requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "image/png"},
            data=image_bytes,
            timeout=60,
        )
    except Exception as exc:
        logger.warning("image_upload network error: %s", exc)
        return None

    if put.status_code not in (200, 201):
        logger.warning("image_upload failed HTTP %s", put.status_code)
        return None

    logger.info("image_registered asset=%s", asset_urn)
    return asset_urn


# ---------------------------------------------------------------------------
# CTA comment
# ---------------------------------------------------------------------------

def post_cta_comment(post_urn: str, pillar: str, token: str) -> bool:
    """Post a Sanad CTA as the first comment on a just-published post.

    Only fires for pain and proof pillars. Non-fatal — a failed comment
    never aborts or rolls back the publish.

    Returns True if the comment was posted (HTTP 201), False otherwise.
    """
    comment_text = CTA_COMMENTS.get(pillar)
    if not comment_text:
        return False

    person_id = (os.environ.get("LINKEDIN_PERSON_ID") or "").strip()
    if not person_id:
        author_urn = (os.environ.get("LINKEDIN_AUTHOR_URN") or "").strip()
        if author_urn.startswith("urn:li:person:"):
            person_id = author_urn[len("urn:li:person:"):]
    if not person_id:
        logger.warning("cta_comment skipped: cannot derive person ID from LINKEDIN_AUTHOR_URN")
        return False

    url     = f"https://api.linkedin.com/v2/socialActions/{post_urn}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    payload = {
        "actor":   f"urn:li:person:{person_id}",
        "message": {"text": comment_text},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
    except Exception as exc:
        logger.warning("cta_comment network error: %s", exc)
        return False

    if resp.status_code == 201:
        logger.info("✓ Sanad CTA comment posted on %s", post_urn)
        return True

    logger.warning(
        "cta_comment failed HTTP %s on %s: %s",
        resp.status_code, post_urn, resp.text[:200],
    )
    return False


# ---------------------------------------------------------------------------
# Main publisher
# ---------------------------------------------------------------------------

def publish_post(text: str, pillar: str = "", attach_image: bool = True) -> dict:
    """Publish text to LinkedIn. Returns the API response dict.

    Args:
        text:         Post body. Must be ≤ CHAR_LIMIT characters.
        pillar:       Content pillar (used to pick quote-card accent colour).
        attach_image: When True, attempt to render and attach a quote card.
                      Falls back to text-only if any image step fails.
    """
    token  = (os.environ.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
    author = (os.environ.get("LINKEDIN_AUTHOR_URN")   or "").strip()

    if not token or not author:
        raise LinkedInError(
            "LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN are required. "
            "See LINKEDIN_SETUP.md."
        )

    if not author.startswith("urn:li:"):
        raise LinkedInError(
            f"LINKEDIN_AUTHOR_URN must look like 'urn:li:person:XXX' (got: {author!r})."
        )

    if len(text) > CHAR_LIMIT:
        raise LinkedInError(
            f"Post exceeds LinkedIn's {CHAR_LIMIT}-character limit "
            f"({len(text)} chars). Shorten before publishing."
        )

    # ── Try image attach ────────────────────────────────────────────────────
    asset_urn  = None
    image_path = "no_image"

    if attach_image:
        try:
            from image_card import render_quote_card
            image_bytes = render_quote_card(text, pillar=pillar)
            asset_urn   = _upload_image(token, author, image_bytes)
            image_path  = "image_attached" if asset_urn else "image_fallback"
        except Exception as exc:
            logger.warning("image_fallback: %s", exc)
            image_path = "image_fallback"

    logger.info("publish path=%s", image_path)

    # ── Build payload ────────────────────────────────────────────────────────
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    share_content: dict = {
        "shareCommentary": {"text": text},
    }
    if asset_urn:
        share_content["shareMediaCategory"] = "IMAGE"
        share_content["media"] = [{"status": "READY", "media": asset_urn}]
    else:
        share_content["shareMediaCategory"] = "NONE"

    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    # ── Retry loop ──────────────────────────────────────────────────────────
    for attempt in range(1, MAX_RETRIES + 1):
        t0       = time.monotonic()
        response = requests.post(LINKEDIN_API, headers=headers, json=payload, timeout=30)
        elapsed  = time.monotonic() - t0

        if response.status_code == 401:
            raise LinkedInError(
                "LinkedIn rejected the access token (401). The token is likely "
                "expired or revoked — LinkedIn tokens last 60 days. Re-run the "
                "OAuth flow in LINKEDIN_SETUP.md (Steps 3-4) and update the "
                f"LINKEDIN_ACCESS_TOKEN secret. Raw response: {response.text}"
            )

        if response.status_code in RETRY_CODES:
            if attempt == MAX_RETRIES:
                raise LinkedInError(
                    f"LinkedIn API {response.status_code} after {MAX_RETRIES} attempts: "
                    f"{response.text}"
                )
            wait = 2 ** attempt
            logger.warning(
                "LinkedIn %s on attempt %d/%d — retrying in %ds",
                response.status_code, attempt, MAX_RETRIES, wait,
            )
            time.sleep(wait)
            continue

        if response.status_code not in (200, 201):
            raise LinkedInError(
                f"LinkedIn API error {response.status_code}: {response.text}"
            )

        post_id = response.headers.get("x-restli-id") or response.json().get("id")
        logger.info(
            "Published post_id=%s chars=%d elapsed=%.2fs attempt=%d image=%s",
            post_id, len(text), elapsed, attempt, image_path,
        )
        cta_posted = post_cta_comment(post_id, pillar, token)
        return {
            "post_id":            post_id,
            "status":             response.status_code,
            "elapsed_s":          round(elapsed, 2),
            "attempts":           attempt,
            "image_path":         image_path,
            "cta_comment_posted": cta_posted,
            "cta_comment_url":    CTA_URL if cta_posted else "",
        }
