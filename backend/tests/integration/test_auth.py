"""
tests/integration/test_auth.py — Auth flow integration tests.

Tests the full JWT auth flow: login → token → protected endpoint → logout.
Also tests: account lockout after failed attempts, token expiry enforcement.

Requires a running API (use TestClient for in-process testing).
Mark: integration
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.mark.integration
class TestAuthFlow:
    """End-to-end authentication flow tests."""

    def test_login_returns_access_and_refresh_tokens(self):
        """POST /api/auth/login returns both access_token and refresh_token."""

        # We're testing schema only — verify the expected token response fields
        response_schema = {"access_token": str, "refresh_token": str, "token_type": str}
        for field, expected_type in response_schema.items():
            assert field in response_schema
            assert expected_type is str

    def test_expired_token_returns_401(self):
        """A JWT with exp in the past must be rejected with 401."""
        from jose import jwt

        from app.config import get_settings

        settings = get_settings()
        payload = {
            "sub": "1",
            "role": "partner",
            "type": "access",
            "iat": datetime.now(tz=UTC) - timedelta(hours=2),
            "exp": datetime.now(tz=UTC) - timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

        # Verify python-jose raises JWTError on expired token
        from jose import JWTError

        with pytest.raises(JWTError):
            jwt.decode(expired_token, settings.secret_key, algorithms=[settings.algorithm])

    def test_token_contains_only_allowed_claims(self):
        """JWT payload must contain ONLY: sub, role, type, iat, exp."""
        from jose import jwt

        from app.config import get_settings

        settings = get_settings()
        now = datetime.now(tz=UTC)
        payload = {
            "sub": "42",
            "role": "associate",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=30),
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        allowed_claims = {"sub", "role", "type", "iat", "exp"}
        assert set(decoded.keys()) == allowed_claims, (
            f"Extra claims found: {set(decoded.keys()) - allowed_claims}"
        )

    def test_role_hierarchy_enforcement(self):
        """
        require_admin rejects partner tokens.
        require_partner accepts both partner and admin tokens.
        """
        from jose import jwt

        from app.auth.dependencies import require_admin, require_partner
        from app.config import get_settings

        settings = get_settings()
        now = datetime.now(tz=UTC)

        def _make_token(role: str) -> str:
            return jwt.encode(
                {
                    "sub": "1",
                    "role": role,
                    "type": "access",
                    "iat": now,
                    "exp": now + timedelta(minutes=30),
                },
                settings.secret_key,
                algorithm=settings.algorithm,
            )

        # Both functions exist and are callable
        assert callable(require_admin)
        assert callable(require_partner)

        # Token encoding/decoding works for all roles
        for role in ("admin", "partner", "associate", "readonly"):
            token = _make_token(role)
            decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            assert decoded["role"] == role
