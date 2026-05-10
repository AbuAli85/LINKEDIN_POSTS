"""Publish a post to LinkedIn via the UGC Posts API."""

import logging
import os
import time

import requests

LINKEDIN_API = "https://api.linkedin.com/v2/ugcPosts"
CHAR_LIMIT   = 3000   # LinkedIn shareCommentary hard cap
MAX_RETRIES  = 3
RETRY_CODES  = {429, 500, 502, 503, 504}

logger = logging.getLogger(__name__)


class LinkedInError(Exception):
    pass


def publish_post(text: str) -> dict:
    """Publish text to LinkedIn. Returns the API response dict."""
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

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.monotonic()
        response = requests.post(LINKEDIN_API, headers=headers, json=payload, timeout=30)
        elapsed = time.monotonic() - t0

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
            "Published post_id=%s chars=%d elapsed=%.2fs attempt=%d",
            post_id, len(text), elapsed, attempt,
        )
        return {
            "post_id":   post_id,
            "status":    response.status_code,
            "elapsed_s": round(elapsed, 2),
            "attempts":  attempt,
        }
