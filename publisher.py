"""Publish a post to LinkedIn via the UGC Posts API.

Audience-aware: when LINKEDIN_AUDIENCE=company, publishes via the
organization URN using LINKEDIN_ORG_TOKEN and LINKEDIN_ORG_URN.
Defaults to personal posting (LINKEDIN_ACCESS_TOKEN + LINKEDIN_AUTHOR_URN)
to keep the existing pipeline backwards-compatible.
"""

import logging
import os
import time

import requests

from strategy_loader import (
    access_token_env_var,
    author_urn_env_var,
    get_audience,
)

LINKEDIN_API     = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_ASSETS  = "https://api.linkedin.com/v2/assets?action=registerUpload"
CHAR_LIMIT       = 3000
MAX_RETRIES      = 3
RETRY_CODES      = {429, 500, 502, 503, 504}

CTA_URL = "https://www.thesmartpro.io/sanad/assistant"

CTA_COMMENTS: dict[str, str] = {
    "pain": (
        "\U0001F916 Related question that comes up a lot:\n"
        '"What\'s the penalty if our WPS file is rejected after the salary deadline?"\n\n'
        "Ask Sanad - free, instant answers on Oman government services. English or Arabic:\n"
        f"{CTA_URL}\n\n"
        "Government fees verified May 2026. No signup needed."
    ),
    "proof": (
        "\U0001F916 Sanad handles the government compliance side the same way SmartPro\n"
        "handles payroll - instant answers, no manual lookup.\n\n"
        "Work permits, visa renewals, business registration fees, Sanad office finder.\n\n"
        f"Try it free: {CTA_URL}\n\n"
        "English or Arabic. No account needed."
    ),
}

logger = logging.getLogger(__name__)


class LinkedInError(Exception):
    pass


def _upload_image(token: str, author: str, image_bytes: bytes) -> str | None:
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


def post_cta_comment(post_urn: str, pillar: str, token: str) -> bool:
    """Post a Sanad CTA as the first comment. Skipped when audience=company.

    Token priority:
      1. LINKEDIN_COMMENT_TOKEN  — dedicated comment token (optional, cleanest)
      2. LINKEDIN_READ_TOKEN     — may have w_member_social if Community Mgmt API approved
      3. token (publish token)   — fallback; will fail if missing r_member_social scope

    Root cause of historical CTA failures: the publish token (w_member_social only)
    cannot POST to /v2/socialActions — that requires Community Management API approval.
    Set LINKEDIN_COMMENT_TOKEN or LINKEDIN_READ_TOKEN with the correct scope to fix.
    """
    comment_text = CTA_COMMENTS.get(pillar)
    if not comment_text:
        return False
    if get_audience() == "company":
        logger.info("cta_comment skipped: audience=company")
        return False
    person_id = (os.environ.get("LINKEDIN_PERSON_ID") or "").strip()
    if not person_id:
        author_urn = (os.environ.get("LINKEDIN_AUTHOR_URN") or "").strip()
        if author_urn.startswith("urn:li:person:"):
            person_id = author_urn[len("urn:li:person:"):]
    if not person_id:
        logger.warning("cta_comment skipped: cannot derive person ID")
        return False

    # Try each token in priority order; stop at first 201 or on non-auth errors
    comment_token = (
        os.environ.get("LINKEDIN_COMMENT_TOKEN")
        or os.environ.get("LINKEDIN_READ_TOKEN")
        or token
    ).strip()

    url = f"https://api.linkedin.com/v2/socialActions/{post_urn}/comments"
    headers = {
        "Authorization": f"Bearer {comment_token}",
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
        logger.info("cta_comment posted on %s", post_urn)
        return True
    if resp.status_code in (401, 403):
        logger.warning(
            "cta_comment auth error HTTP %s on %s — set LINKEDIN_COMMENT_TOKEN with "
            "Community Management API + w_member_social scope. Details: %s",
            resp.status_code, post_urn, resp.text[:300],
        )
    else:
        logger.warning("cta_comment failed HTTP %s on %s: %s", resp.status_code, post_urn, resp.text[:200])
    return False


def publish_post(text: str, pillar: str = "", attach_image: bool = True) -> dict:
    token_var  = access_token_env_var()
    author_var = author_urn_env_var()
    token  = (os.environ.get(token_var)  or "").strip()
    author = (os.environ.get(author_var) or "").strip()

    if not token or not author:
        audience = get_audience()
        if audience == "company":
            raise LinkedInError(
                f"{token_var} and {author_var} are required when LINKEDIN_AUDIENCE=company. "
                "See COMPANY_SETUP.md."
            )
        raise LinkedInError(
            f"{token_var} and {author_var} are required. See LINKEDIN_SETUP.md."
        )

    if not author.startswith("urn:li:"):
        raise LinkedInError(
            f"{author_var} must look like 'urn:li:person:XXX' or 'urn:li:organization:XXX' "
            f"(got: {author!r})."
        )

    if len(text) > CHAR_LIMIT:
        raise LinkedInError(
            f"Post exceeds LinkedIn's {CHAR_LIMIT}-character limit ({len(text)} chars)."
        )

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

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    share_content: dict = {"shareCommentary": {"text": text}}
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

    for attempt in range(1, MAX_RETRIES + 1):
        t0       = time.monotonic()
        response = requests.post(LINKEDIN_API, headers=headers, json=payload, timeout=30)
        elapsed  = time.monotonic() - t0

        if response.status_code == 401:
            audience = get_audience()
            setup_doc = "COMPANY_SETUP.md" if audience == "company" else "LINKEDIN_SETUP.md"
            raise LinkedInError(
                "LinkedIn rejected the access token (401). "
                f"Re-run the OAuth flow in {setup_doc} and update the {token_var} secret. "
                f"Raw response: {response.text}"
            )

        if response.status_code in RETRY_CODES:
            if attempt == MAX_RETRIES:
                raise LinkedInError(
                    f"LinkedIn API {response.status_code} after 