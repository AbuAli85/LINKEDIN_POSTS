"""Publish a post to LinkedIn via the UGC Posts API."""

import os
import requests

LINKEDIN_API = "https://api.linkedin.com/v2/ugcPosts"


class LinkedInError(Exception):
    pass


def publish_post(text: str) -> dict:
    """Publish text to LinkedIn. Returns the API response."""
    token = (os.environ.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
    author = (os.environ.get("LINKEDIN_AUTHOR_URN") or "").strip()

    if not token or not author:
        raise LinkedInError(
            "LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN are required. "
            "See LINKEDIN_SETUP.md."
        )

    if not author.startswith("urn:li:"):
        raise LinkedInError(
            f"LINKEDIN_AUTHOR_URN must look like 'urn:li:person:XXX' (got: {author!r})."
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

    response = requests.post(LINKEDIN_API, headers=headers, json=payload, timeout=30)
    if response.status_code == 401:
        raise LinkedInError(
            "LinkedIn rejected the access token (401). The token is likely "
            "expired or revoked — LinkedIn tokens last 60 days. Re-run the "
            "OAuth flow in LINKEDIN_SETUP.md (Steps 3-4) and update the "
            f"LINKEDIN_ACCESS_TOKEN secret. Raw response: {response.text}"
        )
    if response.status_code not in (200, 201):
        raise LinkedInError(
            f"LinkedIn API error {response.status_code}: {response.text}"
        )

    return {
        "post_id": response.headers.get("x-restli-id") or response.json().get("id"),
        "status": response.status_code,
    }
