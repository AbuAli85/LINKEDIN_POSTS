"""Publish a post to LinkedIn via the UGC Posts API."""

import os
import requests

LINKEDIN_API = "https://api.linkedin.com/v2/ugcPosts"


class LinkedInError(Exception):
    pass


def publish_post(text: str) -> dict:
    """Publish text to LinkedIn. Returns the API response."""
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    author = os.environ.get("LINKEDIN_AUTHOR_URN")

    if not token or not author:
        raise LinkedInError(
            "LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN are required. "
            "See LINKEDIN_SETUP.md."
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
    if response.status_code not in (200, 201):
        raise LinkedInError(
            f"LinkedIn API error {response.status_code}: {response.text}"
        )

    return {
        "post_id": response.headers.get("x-restli-id") or response.json().get("id"),
        "status": response.status_code,
    }
