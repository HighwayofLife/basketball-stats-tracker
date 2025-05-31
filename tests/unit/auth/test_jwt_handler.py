"""Unit tests for JWT token handling."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.auth.jwt_handler import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
)


class TestJWTHandler:
    """Test cases for JWT handler functions."""

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        with patch("app.auth.jwt_handler.pwd_context") as mock_context:
            mock_context.verify.return_value = True

            result = verify_password("password123", "hashed_password")

            assert result is True
            mock_context.verify.assert_called_once_with("password123", "hashed_password")

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        with patch("app.auth.jwt_handler.pwd_context") as mock_context:
            mock_context.verify.return_value = False

            result = verify_password("wrongpassword", "hashed_password")

            assert result is False

    def test_get_password_hash(self):
        """Test password hashing."""
        with patch("app.auth.jwt_handler.pwd_context") as mock_context:
            mock_context.hash.return_value = "hashed_password"

            result = get_password_hash("password123")

            assert result == "hashed_password"
            mock_context.hash.assert_called_once_with("password123")

    def test_create_access_token_default_expiry(self):
        """Test access token creation with default expiry."""
        test_data = {"sub": "1", "username": "testuser"}

        with patch("app.auth.jwt_handler.jwt") as mock_jwt, patch("app.auth.jwt_handler.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_jwt.encode.return_value = "encoded_token"

            result = create_access_token(test_data)

            assert result == "encoded_token"

            # Verify the token data includes expiry
            call_args = mock_jwt.encode.call_args[0][0]
            assert call_args["sub"] == "1"
            assert call_args["username"] == "testuser"
            assert call_args["exp"] == mock_now + timedelta(minutes=30)  # Default expiry

    def test_create_access_token_custom_expiry(self):
        """Test access token creation with custom expiry."""
        test_data = {"sub": "1", "username": "testuser"}
        custom_expiry = timedelta(hours=2)

        with patch("app.auth.jwt_handler.jwt") as mock_jwt, patch("app.auth.jwt_handler.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_jwt.encode.return_value = "encoded_token"

            result = create_access_token(test_data, custom_expiry)

            assert result == "encoded_token"

            # Verify the token data includes custom expiry
            call_args = mock_jwt.encode.call_args[0][0]
            assert call_args["exp"] == mock_now + custom_expiry

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        test_data = {"sub": "1"}

        with patch("app.auth.jwt_handler.jwt") as mock_jwt, patch("app.auth.jwt_handler.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_jwt.encode.return_value = "refresh_token"

            result = create_refresh_token(test_data)

            assert result == "refresh_token"

            # Verify the token data
            call_args = mock_jwt.encode.call_args[0][0]
            assert call_args["sub"] == "1"
            assert call_args["type"] == "refresh"
            assert call_args["exp"] == mock_now + timedelta(days=7)

    def test_verify_token_valid_access_token(self):
        """Test verification of valid access token."""
        mock_payload = {"sub": "1", "username": "testuser", "exp": 1234567890}

        with patch("app.auth.jwt_handler.jwt") as mock_jwt:
            mock_jwt.decode.return_value = mock_payload

            result = verify_token("valid_token", "access")

            assert result == mock_payload
            mock_jwt.decode.assert_called_once()

    def test_verify_token_valid_refresh_token(self):
        """Test verification of valid refresh token."""
        mock_payload = {"sub": "1", "type": "refresh", "exp": 1234567890}

        with patch("app.auth.jwt_handler.jwt") as mock_jwt:
            mock_jwt.decode.return_value = mock_payload

            result = verify_token("valid_refresh_token", "refresh")

            assert result == mock_payload

    def test_verify_token_invalid_refresh_type(self):
        """Test verification of refresh token without correct type."""
        mock_payload = {"sub": "1", "exp": 1234567890}  # Missing type: "refresh"

        with patch("app.auth.jwt_handler.jwt") as mock_jwt:
            mock_jwt.decode.return_value = mock_payload

            result = verify_token("invalid_refresh_token", "refresh")

            assert result is None

    def test_verify_token_invalid_token(self):
        """Test verification of invalid token."""
        from jose import JWTError

        with patch("app.auth.jwt_handler.jwt") as mock_jwt:
            mock_jwt.decode.side_effect = JWTError("Invalid token")

            result = verify_token("invalid_token", "access")

            assert result is None

    def test_verify_token_expired_token(self):
        """Test verification of expired token."""
        from jose import JWTError

        with patch("app.auth.jwt_handler.jwt") as mock_jwt:
            mock_jwt.decode.side_effect = JWTError("Token expired")

            result = verify_token("expired_token", "access")

            assert result is None


class TestJWTConfiguration:
    """Test JWT configuration and environment variables."""

    def test_jwt_secret_key_required(self):
        """Test that JWT_SECRET_KEY environment variable is required."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable must be set"):
                # This will trigger the module-level code that checks for JWT_SECRET_KEY
                import importlib
                import app.auth.jwt_handler

                importlib.reload(app.auth.jwt_handler)

    def test_jwt_secret_key_length_validation(self):
        """Test that JWT_SECRET_KEY must be at least 32 characters."""
        with patch.dict("os.environ", {"JWT_SECRET_KEY": "short"}, clear=True):
            with pytest.raises(ValueError, match="JWT_SECRET_KEY must be at least 32 characters long"):
                import importlib
                import app.auth.jwt_handler

                importlib.reload(app.auth.jwt_handler)

    def test_jwt_secret_key_valid_length(self):
        """Test that valid JWT_SECRET_KEY length works."""
        long_key = "a" * 32  # 32 characters
        with patch.dict("os.environ", {"JWT_SECRET_KEY": long_key}, clear=True):
            try:
                import importlib
                import app.auth.jwt_handler

                importlib.reload(app.auth.jwt_handler)
                # Should not raise an exception
                assert True
            except ValueError:
                pytest.fail("Valid JWT_SECRET_KEY should not raise ValueError")
