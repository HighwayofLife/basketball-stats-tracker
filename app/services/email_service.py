"""Email service for sending feedback via SMTP."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings


class EmailService:
    """Service to send feedback emails via SMTP."""

    def __init__(
        self,
        smtp_server: str | None = None,
        smtp_port: int | None = None,
        smtp_username: str | None = None,
        smtp_password: str | None = None,
        feedback_email: str | None = None,
    ):
        self.smtp_server = smtp_server or settings.SMTP_SERVER
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.smtp_username = smtp_username or settings.SMTP_USERNAME
        self.smtp_password = smtp_password or settings.SMTP_PASSWORD
        self.feedback_email = feedback_email or settings.FEEDBACK_EMAIL

    async def send_feedback(self, issue_type: str, title: str, body: str, user_email: str | None = None) -> bool:
        """Send feedback email."""
        if not all([self.smtp_server, self.smtp_username, self.smtp_password, self.feedback_email]):
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_username
            msg["To"] = self.feedback_email
            msg["Subject"] = f"[{issue_type.upper()}] {title}"

            email_body = f"""
Feedback Type: {issue_type}
Title: {title}
User Email: {user_email or "Not provided"}

Message:
{body}

---
Sent from Basketball Stats Tracker
            """.strip()

            msg.attach(MIMEText(email_body, "plain"))

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return True
        except Exception:
            return False
