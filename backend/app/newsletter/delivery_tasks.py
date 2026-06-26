from celery import shared_task
import logging
from app.core.email.email_service import get_email_provider
from app.core.database import SessionLocal
from app.newsletter.repository import NewsletterRepository
from app.core.config import settings

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_confirmation_email(self, subscriber_id: int):
    """
    Sends a double opt-in confirmation email to the subscriber.
    """
    logger.info(f"Task send_confirmation_email started for subscriber_id={subscriber_id}")
    db = SessionLocal()
    try:
        repo = NewsletterRepository(db)
        subscriber = repo.get_subscriber(subscriber_id)
        if not subscriber:
            logger.warning(f"Subscriber {subscriber_id} not found.")
            return

        if subscriber.status != "PENDING":
            logger.info(f"Subscriber {subscriber_id} is already {subscriber.status}. Skipping confirmation email.")
            return

        # Generate confirmation link
        confirm_url = f"{settings.API_V1_STR}/newsletter/confirm/{subscriber.confirmation_token}"
        base_url = "http://localhost:8000" # In production, this comes from settings.DOMAIN
        full_confirm_url = f"{base_url}{confirm_url}"

        # Send email
        provider = get_email_provider()
        
        subject = "Please confirm your subscription to Tech News Today"
        text_content = f"Welcome! Please confirm your subscription by visiting this link: {full_confirm_url}"
        html_content = f\"\"\"
        <html>
            <body>
                <h2>Welcome to Tech News Today!</h2>
                <p>We're excited to have you. Please confirm your email address by clicking the button below:</p>
                <a href="{full_confirm_url}" style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">Confirm Subscription</a>
            </body>
        </html>
        \"\"\"

        import asyncio
        provider_msg_id = asyncio.run(provider.send_email(
            to_email=subscriber.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            subscriber_id=subscriber.id,
            message_id_prefix="optin-"
        ))
        
        logger.info(f"Confirmation email sent to {subscriber.email} with Message ID: {provider_msg_id}")
        
    except Exception as e:
        logger.error(f"Failed to send confirmation email for subscriber {subscriber_id}: {e}")
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
