"""
Gmail tool — uses Gmail API via OAuth2.
On first run, opens browser to authorize. Token stored in token.json.
"""
import logging
from typing import Optional
from velo_core.tools.base import tool, register_tool

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _get_gmail_service():
    """Build authenticated Gmail service. Requires credentials.json in velo_core/."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        import os
        import json

        creds = None
        token_path = "token.json"
        creds_path = "credentials.json"

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    raise FileNotFoundError(
                        "credentials.json not found. Download it from Google Cloud Console → APIs & Services → Credentials"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as f:
                f.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)
    except ImportError:
        raise RuntimeError(
            "Google API packages missing. Install: pip install google-api-python-client google-auth-oauthlib"
        )


@tool(
    name="send_gmail",
    description="Send an email via Gmail. Requires OAuth2 setup (credentials.json).",
    requires_permission=True,
    risk_level="high",
)
async def send_gmail(to: str, subject: str, body: str) -> str:
    try:
        import base64
        from email.mime.text import MIMEText

        service = _get_gmail_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Email sent! Message ID: {sent['id']}"
    except Exception as e:
        logger.error(f"Gmail send error: {e}")
        return f"Error sending email: {str(e)}"


register_tool(send_gmail)
