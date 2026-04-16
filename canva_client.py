"""
Canva Connect API client — fetches brand templates from the company account.

Docs:  https://www.canva.dev/docs/connect/
Auth:  OAuth 2.0 — set credentials in .env (see .env for required keys)

Required scopes (configure in Canva Developer Portal):
    brandtemplate:meta:read
    brandtemplate:content:read
    design:content:read
    design:meta:read
    profile:read
"""

import os
import requests

# ── Defaults read from environment ────────────────────────────────────────────
_DEFAULT_API_BASE = os.getenv(
    "BASE_CANVA_CONNECT_API_URL", "https://api.canva.com/rest/v1"
)
_DEFAULT_AUTH_URL = os.getenv(
    "BASE_CANVA_CONNECT_AUTH_URL", "https://www.canva.com/api/oauth/token"
)


def get_access_token_via_client_credentials(
    client_id: str | None = None,
    client_secret: str | None = None,
) -> str:
    """
    Exchange client_id + client_secret for a Bearer access token.
    Falls back to CANVA_CLIENT_ID / CANVA_CLIENT_SECRET env vars.
    Raises requests.HTTPError on failure.
    """
    cid = client_id or os.getenv("CANVA_CLIENT_ID", "")
    csecret = client_secret or os.getenv("CANVA_CLIENT_SECRET", "")
    if not cid or not csecret:
        raise ValueError(
            "Canva client_id and client_secret are required. "
            "Set CANVA_CLIENT_ID and CANVA_CLIENT_SECRET in your .env file."
        )

    resp = requests.post(
        _DEFAULT_AUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": csecret,
            "scope": (
                "brandtemplate:meta:read brandtemplate:content:read "
                "design:content:read design:meta:read profile:read"
            ),
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_brand_templates(
    access_token: str,
    query: str = "",
    limit: int = 6,
    api_base: str | None = None,
) -> list[dict]:
    """
    Fetch brand templates visible to the authenticated user (team/company account).

    Args:
        access_token: OAuth 2.0 Bearer token (from CANVA_ACCESS_TOKEN or
                      get_access_token_via_client_credentials()).
        query:        Optional keyword to filter templates by title.
        limit:        Max number of templates to return (default 6).
        api_base:     Override API base URL (falls back to env / default).

    Returns:
        List of dicts — each has: id, title, thumbnail_url, edit_url, view_url.

    Raises:
        requests.HTTPError on non-2xx responses.
    """
    base = api_base or _DEFAULT_API_BASE
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    params: dict = {"limit": limit}
    if query:
        params["query"] = query

    resp = requests.get(
        f"{base}/brand-templates",
        headers=headers,
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    results: list[dict] = []
    for item in data.get("items", []):
        results.append(
            {
                "id": item.get("id", ""),
                "title": item.get("title", "Untitled Template"),
                "thumbnail_url": item.get("thumbnail", {}).get("url", ""),
                "edit_url": item.get("urls", {}).get("edit_url", ""),
                "view_url": item.get("urls", {}).get("view_url", ""),
            }
        )
    return results
