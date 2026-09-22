"""
Notification dispatcher: Email (SMTP) primarily, Telegram optionally.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import settings
from core.utils import logger


def send_email(subject: str, body: str, to: str | None = None) -> bool:
    """Send an email via SMTP. Returns True on success."""
    if not settings.smtp_user or not settings.smtp_pass:
        logger.warning("Email not configured — skipping send_email")
        return False

    to_addr = to or settings.email_to or settings.smtp_user

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_user
    msg["To"] = to_addr
    msg["Subject"] = subject

    # Plain text + a very light HTML version
    text_part = MIMEText(body, "plain", "utf-8")
    html_body = f"<pre style='font-family: system-ui, sans-serif'>{body}</pre>"
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(text_part)
    msg.attach(html_part)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.sendmail(settings.smtp_user, [to_addr], msg.as_string())
        logger.info(f"Email sent to {to_addr}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_discord(text: str) -> bool:
    """Send a message to the Discord channel via the bot API."""
    if not settings.discord_bot_token or not settings.discord_channel_id:
        return False
    try:
        import httpx
        url = (
            f"https://discord.com/api/v10/channels/"
            f"{settings.discord_channel_id}/messages"
        )
        headers = {
            "Authorization": f"Bot {settings.discord_bot_token}",
            "Content-Type": "application/json",
        }
        # Discord caps at 2000 chars per message
        chunks = [text[i:i + 1900] for i in range(0, len(text), 1900)]
        for chunk in chunks:
            r = httpx.post(url, json={"content": chunk}, headers=headers, timeout=15)
            r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Discord send failed: {e}")
        return False


def notify(subject: str, body: str) -> None:
    """Send via all configured channels."""
    send_email(subject, body)
    send_discord(f"*{subject}*\n\n{body}")
    send_discord(f"**{subject}**\n\n{body}")
