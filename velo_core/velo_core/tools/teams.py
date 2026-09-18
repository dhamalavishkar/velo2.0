"""
Microsoft Teams tool — uses Microsoft Graph API via MSAL OAuth2.
On first run, opens browser to authorize.
"""
import logging
from velo_core.tools.base import tool, register_tool

logger = logging.getLogger(__name__)

GRAPH_SCOPES = ["https://graph.microsoft.com/Chat.ReadWrite", "https://graph.microsoft.com/User.Read"]


def _get_teams_token() -> str:
    """Acquire access token via MSAL interactive flow. Cached in .teams_cache."""
    try:
        import msal
        import json
        import os

        client_id = os.environ.get("TEAMS_CLIENT_ID", "")
        tenant_id = os.environ.get("TEAMS_TENANT_ID", "common")
        cache_file = ".teams_cache"

        if not client_id:
            raise ValueError(
                "TEAMS_CLIENT_ID not set in .env. Register an app in Azure AD → App registrations."
            )

        cache = msal.SerializableTokenCache()
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                cache.deserialize(f.read())

        app = msal.PublicClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            token_cache=cache,
        )

        accounts = app.get_accounts()
        result = None
        if accounts:
            result = app.acquire_token_silent(GRAPH_SCOPES, account=accounts[0])

        if not result:
            result = app.acquire_token_interactive(scopes=GRAPH_SCOPES)

        if cache.has_state_changed:
            with open(cache_file, "w") as f:
                f.write(cache.serialize())

        if "access_token" not in result:
            raise RuntimeError(f"Teams auth failed: {result.get('error_description', 'unknown')}")

        return result["access_token"]
    except ImportError:
        raise RuntimeError("MSAL missing. Install: pip install msal")


@tool(
    name="send_teams_message",
    description="Send a message to a Microsoft Teams chat. Requires Azure AD app registration.",
    requires_permission=True,
    risk_level="high",
)
async def send_teams_message(chat_id: str, message: str) -> str:
    """
    Send a message to a Teams chat by chat_id.
    chat_id can be found via: GET https://graph.microsoft.com/v1.0/me/chats
    """
    try:
        import httpx
        token = _get_teams_token()
        url = f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {"body": {"content": message}}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
        return f"Teams message sent to chat {chat_id}"
    except Exception as e:
        logger.error(f"Teams send error: {e}")
        return f"Error sending Teams message: {str(e)}"


register_tool(send_teams_message)
