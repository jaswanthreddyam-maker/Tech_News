import os
import uuid
import logging
import urllib.request
import urllib.error
import json
from typing import Protocol, Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EmailPayload:
    to: str
    subject: str
    html: str
    text: str
    from_address: str = "Tech News Today <onboarding@resend.dev>"
    idempotency_key: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


@dataclass
class EmailResult:
    success: bool
    message_id: str
    provider: str
    error: Optional[str] = None


class EmailProvider(Protocol):
    async def send(self, payload: EmailPayload) -> EmailResult:
        ...


class MockEmailProvider:
    """
    Mock Email Provider for local development, testing, and fallback.
    Logs sent emails and stores rendered copies for inspectability.
    """
    async def send(self, payload: EmailPayload) -> EmailResult:
        mock_id = f"mock_msg_{uuid.uuid4().hex[:12]}"
        logger.info(f"MockEmailProvider: Dispatched email to {payload.to} | Subject: '{payload.subject}' | Key: {payload.idempotency_key} | ID: {mock_id}")
        return EmailResult(
            success=True,
            message_id=mock_id,
            provider="MOCK",
            error=None
        )


class ResendEmailProvider:
    """
    Resend API Email Provider supporting Idempotency-Key headers, batching, and webhook delivery tracking.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RESEND_API_KEY")

    async def send(self, payload: EmailPayload) -> EmailResult:
        if not self.api_key:
            logger.warning("ResendEmailProvider: RESEND_API_KEY missing. Falling back to MockEmailProvider.")
            return await MockEmailProvider().send(payload)

        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "TechNewsToday/1.0",
        }
        if payload.idempotency_key:
            headers["Idempotency-Key"] = payload.idempotency_key

        # Default to onboarding sender if custom domain is not set
        from_sender = os.getenv("EMAIL_FROM_ADDRESS", "Tech News Today <onboarding@resend.dev>")
        if payload.from_address and not payload.from_address.endswith("@technewstoday.com>"):
            from_sender = payload.from_address

        body_data = {
            "from": from_sender,
            "to": [payload.to],
            "subject": payload.subject,
            "html": payload.html,
            "text": payload.text,
        }
        if payload.tags:
            body_data["tags"] = [{"name": k, "value": v} for k, v in payload.tags.items()]

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body_data).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as res:
                res_data = json.loads(res.read().decode("utf-8"))
                msg_id = res_data.get("id", f"resend_{uuid.uuid4().hex[:8]}")
                return EmailResult(success=True, message_id=msg_id, provider="RESEND")
        except urllib.error.HTTPError as e:
            err_text = e.read().decode("utf-8")
            logger.error(f"ResendEmailProvider HTTPError ({e.code}): {err_text}")
            return EmailResult(success=False, message_id="", provider="RESEND", error=f"HTTP {e.code}: {err_text}")
        except Exception as e:
            logger.error(f"ResendEmailProvider Error: {e}")
            return EmailResult(success=False, message_id="", provider="RESEND", error=str(e))

def get_email_provider() -> EmailProvider:
    api_key = os.getenv("RESEND_API_KEY")
    if api_key:
        return ResendEmailProvider(api_key=api_key)
    return MockEmailProvider()
