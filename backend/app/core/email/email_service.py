from typing import Protocol, Optional
import smtplib
from email.message import EmailMessage
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailProvider(Protocol):
    """
    Core abstraction for sending emails.
    """
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        campaign_id: Optional[int] = None,
        subscriber_id: Optional[int] = None,
        message_id_prefix: str = "tnt-"
    ) -> str:
        """
        Sends an email and returns the provider's unique message ID.
        """
        ...

class MockEmailProvider:
    """
    Mock provider for local development or testing without network access.
    """
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        campaign_id: Optional[int] = None,
        subscriber_id: Optional[int] = None,
        message_id_prefix: str = "tnt-"
    ) -> str:
        provider_id = f"mock-{message_id_prefix}{campaign_id}-{subscriber_id}"
        logger.info(f"MockEmailProvider: Simulated sending email to {to_email}. Subject: '{subject}'. Message ID: {provider_id}")
        return provider_id

class SmtpEmailProvider:
    """
    Basic SMTP provider for Mailtrap or local SMTP catchers.
    """
    def __init__(self, host: str, port: int, username: str = "", password: str = "", use_tls: bool = False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        campaign_id: Optional[int] = None,
        subscriber_id: Optional[int] = None,
        message_id_prefix: str = "tnt-"
    ) -> str:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.ADMIN_EMAIL # Or a configured FROM_EMAIL
        msg["To"] = to_email
        msg.set_content(text_content)
        msg.add_alternative(html_content, subtype='html')

        provider_id = f"smtp-{message_id_prefix}{campaign_id}-{subscriber_id}"
        
        try:
            # Note: This is synchronous SMTP for simplicity.
            # In a real async system, use aiosmtplib.
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"SmtpEmailProvider: Sent email to {to_email}. Message ID: {provider_id}")
            return provider_id
        except Exception as e:
            logger.error(f"SmtpEmailProvider: Failed to send email to {to_email}. Error: {e}")
            raise e

# Factory pattern to get the configured provider
def get_email_provider() -> EmailProvider:
    # In a real app, read from settings.EMAIL_PROVIDER_TYPE
    # For now, default to Mock for safety unless configured otherwise
    # If we wanted SMTP (e.g. mailtrap), we would return SmtpEmailProvider
    return MockEmailProvider()
