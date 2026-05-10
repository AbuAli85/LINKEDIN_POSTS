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
        return {
            "post_id":      post_id,
            "status":       response.status_code,
            "elapsed_s":    round(elapsed, 2),
            "attempts":     attempt,
            "image_path":   image_path,
        }
