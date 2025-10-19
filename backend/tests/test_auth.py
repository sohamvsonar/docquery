"""
Unit tests for authentication utilities.
Tests password hashing, JWT token creation/verification, and user authentication.
"""

import pytest
from datetime import timedelta
from jose import jwt

from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    authenticate_user
)
from app.config import settings


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test that password hashing produces a hash."""
        password = "mysecretpassword"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_hash_password_different_for_same_input(self):
        """Test that hashing the same password twice produces different hashes (due to salt)."""
        password = "mysecretpassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password."""
        password = "mysecretpassword"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password."""
        password = "mysecretpassword"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"user_id": 1, "username": "testuser"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiration(self):
        """Test access token creation with custom expiration."""
        data = {"user_id": 1, "username": "testuser"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta=expires_delta)

        assert token is not None

        # Decode and verify expiration is set correctly
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert "exp" in decoded
        assert "iat" in decoded

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"user_id": 1, "username": "testuser"}
        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)

        # Decode and verify it's marked as refresh token
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert decoded.get("type") == "refresh"

    def test_decode_token_valid(self):
        """Test decoding a valid token."""
        data = {"user_id": 1, "username": "testuser"}
        token = create_access_token(data)

        decoded = decode_token(token)

        assert decoded is not None
        assert decoded["user_id"] == 1
        assert decoded["username"] == "testuser"

    def test_decode_token_invalid(self):
        """Test decoding an invalid token raises HTTPException."""
        invalid_token = "invalid.token.string"

        with pytest.raises(Exception):  # Should raise HTTPException
            decode_token(invalid_token)

    def test_token_contains_original_data(self):
        """Test that decoded token contains original data."""
        data = {
            "user_id": 42,
            "username": "alice",
            "is_admin": True
        }
        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded["user_id"] == 42
        assert decoded["username"] == "alice"
        assert decoded["is_admin"] is True


class TestUserAuthentication:
    """Test user authentication logic."""

    def test_authenticate_user_success(self, db_session, test_user):
        """Test successful user authentication."""
        user = authenticate_user(db_session, "testuser", "testpassword123")

        assert user is not None
        assert user.id == test_user.id
        assert user.username == test_user.username

    def test_authenticate_user_wrong_password(self, db_session, test_user):
        """Test authentication fails with wrong password."""
        user = authenticate_user(db_session, "testuser", "wrongpassword")

        assert user is None

    def test_authenticate_user_nonexistent(self, db_session):
        """Test authentication fails for nonexistent user."""
        user = authenticate_user(db_session, "nonexistent", "password")

        assert user is None

    def test_authenticate_inactive_user(self, db_session, test_user):
        """Test authentication fails for inactive user."""
        # Deactivate the user
        test_user.is_active = False
        db_session.commit()

        user = authenticate_user(db_session, "testuser", "testpassword123")

        assert user is None
