"""Tests for the email service."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import EmailService


@pytest.fixture
def email_service():
    """Create email service with test configuration."""
    return EmailService(
        smtp_server="test.smtp.com",
        smtp_port=587,
        smtp_username="test@example.com",
        smtp_password="password",
        feedback_email="feedback@example.com",
    )


@pytest.fixture
def unconfigured_email_service():
    """Create email service without configuration."""
    return EmailService(smtp_server=None, smtp_port=587, smtp_username=None, smtp_password=None, feedback_email=None)


class TestEmailService:
    """Test cases for EmailService."""

    @patch("app.services.email_service.smtplib.SMTP")
    def test_send_feedback_success(self, mock_smtp, email_service):
        """Test successful feedback email sending."""
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Test
        result = asyncio.run(
            email_service.send_feedback(
                issue_type="bug", title="Test Bug", body="Bug description", user_email="user@example.com"
            )
        )

        # Assert
        assert result is True
        mock_smtp.assert_called_once_with("test.smtp.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "password")
        mock_server.send_message.assert_called_once()

    def test_send_feedback_no_configuration(self, unconfigured_email_service):
        """Test feedback sending without proper configuration."""
        result = asyncio.run(
            unconfigured_email_service.send_feedback(issue_type="bug", title="Test Bug", body="Bug description")
        )

        assert result is False

    @patch("app.services.email_service.smtplib.SMTP")
    def test_send_feedback_smtp_error(self, mock_smtp, email_service):
        """Test feedback sending with SMTP error."""
        # Setup mock to raise exception
        mock_smtp.side_effect = Exception("SMTP Error")

        # Test
        result = asyncio.run(email_service.send_feedback(issue_type="bug", title="Test Bug", body="Bug description"))

        # Assert
        assert result is False

    @patch("app.services.email_service.smtplib.SMTP")
    def test_send_feedback_without_user_email(self, mock_smtp, email_service):
        """Test feedback sending without user email."""
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Test
        result = asyncio.run(
            email_service.send_feedback(issue_type="feature", title="Feature Request", body="Feature description")
        )

        # Assert
        assert result is True
        # Should still send email even without user email
        mock_server.send_message.assert_called_once()

    @patch("app.services.email_service.smtplib.SMTP")
    def test_email_content_formatting(self, mock_smtp, email_service):
        """Test that email content is properly formatted."""
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Test
        asyncio.run(
            email_service.send_feedback(
                issue_type="support", title="Need Help", body="I need help with something", user_email="user@test.com"
            )
        )

        # Get the message that was sent
        call_args = mock_server.send_message.call_args[0][0]

        # Assert email properties
        assert call_args["From"] == "test@example.com"
        assert call_args["To"] == "feedback@example.com"
        assert call_args["Subject"] == "[SUPPORT] Need Help"

        # Check email body contains expected content
        email_body = call_args.get_payload()[0].get_payload()
        assert "Feedback Type: support" in email_body
        assert "Title: Need Help" in email_body
        assert "User Email: user@test.com" in email_body
        assert "I need help with something" in email_body
