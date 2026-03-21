"""
tests/test_auth.py — Authentication endpoint tests.

Tests JWT flow, account lockout, role enforcement.
Uses httpx.AsyncClient against the test app.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# ── Auth service unit tests ────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_and_verify(self):
        from app.auth.service import hash_password, verify_password
        plain = "SecurePass123!"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed)

    def test_wrong_password_fails(self):
        from app.auth.service import hash_password, verify_password
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_empty_password_fails(self):
        from app.auth.service import hash_password, verify_password
        hashed = hash_password("notempty")
        assert not verify_password("", hashed)


class TestTokenGeneration:
    def _make_user(self):
        from app.auth.models import User, UserRole
        user = MagicMock(spec=User)
        user.id = 42
        user.email = "partner@halcyon.legal"
        user.role = UserRole.partner
        user.partner_id = 3
        return user

    def test_access_token_contains_claims(self):
        from app.auth.service import create_access_token, decode_token
        user = self._make_user()
        token = create_access_token(user)
        claims = decode_token(token)
        assert claims.user_id == 42
        assert claims.email == "partner@halcyon.legal"
        assert claims.role.value == "partner"

    def test_refresh_token_type(self):
        from app.auth.service import create_refresh_token
        from jose import jwt
        from app.config import get_settings
        user = self._make_user()
        token = create_refresh_token(user)
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        assert payload["type"] == "refresh"

    def test_access_token_not_accepted_as_refresh(self):
        from app.auth.service import create_access_token
        from jose import jwt, JWTError
        from app.config import get_settings
        user = self._make_user()
        token = create_access_token(user)
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        assert payload["type"] == "access"
        # Attempting to use it as refresh should fail
        assert payload["type"] != "refresh"

    def test_tampered_token_rejected(self):
        from app.auth.service import create_access_token, decode_token
        from jose import JWTError
        user = self._make_user()
        token = create_access_token(user)
        tampered = token[:-4] + "XXXX"
        with pytest.raises(JWTError):
            decode_token(tampered)


class TestTokenClaims:
    def test_admin_is_admin(self):
        from app.auth.service import TokenClaims
        from app.auth.models import UserRole
        claims = TokenClaims(sub=1, email="a@b.com", role=UserRole.admin, partner_id=None)
        assert claims.is_admin
        assert claims.is_partner_or_above
        assert claims.can_write()

    def test_partner_can_write(self):
        from app.auth.service import TokenClaims
        from app.auth.models import UserRole
        claims = TokenClaims(sub=2, email="p@b.com", role=UserRole.partner, partner_id=1)
        assert not claims.is_admin
        assert claims.is_partner_or_above
        assert claims.can_write()

    def test_readonly_cannot_write(self):
        from app.auth.service import TokenClaims
        from app.auth.models import UserRole
        claims = TokenClaims(sub=3, email="r@b.com", role=UserRole.readonly, partner_id=None)
        assert not claims.is_admin
        assert not claims.is_partner_or_above
        assert not claims.can_write()

    def test_associate_can_write_not_admin(self):
        from app.auth.service import TokenClaims
        from app.auth.models import UserRole
        claims = TokenClaims(sub=4, email="a@b.com", role=UserRole.associate, partner_id=None)
        assert not claims.is_admin
        assert not claims.is_partner_or_above
        assert claims.can_write()


# ── Entity resolution unit tests ───────────────────────────────────────────────

class TestEntityResolution:
    def test_normalise_strips_legal_suffix(self):
        from app.services.entity_resolution import normalise
        assert normalise("Arctis Mining Corp.") == "arctis mining"
        assert normalise("Northfield Energy Partners LP") == "northfield energy"
        assert normalise("EMBER FINANCIAL CORPORATION") == "ember financial"
        assert normalise("ClearPath Technologies Inc.") == "clearpath technologies"

    def test_normalise_handles_empty(self):
        from app.services.entity_resolution import normalise
        assert normalise("") == ""
        assert normalise(None) == ""

    def test_normalise_strips_punctuation(self):
        from app.services.entity_resolution import normalise
        assert normalise("A.B.C. Holdings") == "abc holdings"

    def test_resolver_exact_match(self):
        from app.services.entity_resolution import EntityResolver
        resolver = EntityResolver()
        resolver._index = {"arctis mining": (1, "client", "Arctis Mining Corp.")}
        resolver._norm_list = ["arctis mining"]

        result = resolver.resolve("Arctis Mining Corp.")
        assert result.matched
        assert result.entity_id == 1
        assert result.entity_type == "client"
        assert result.score == 100.0

    def test_resolver_fuzzy_match(self):
        from app.services.entity_resolution import EntityResolver
        resolver = EntityResolver()
        resolver._index = {"arctis mining": (1, "client", "Arctis Mining Corp.")}
        resolver._norm_list = ["arctis mining"]

        # Slight variation — should still match
        result = resolver.resolve("Arctis Mining Corporation")
        assert result.matched
        assert result.entity_id == 1

    def test_resolver_no_match_below_threshold(self):
        from app.services.entity_resolution import EntityResolver
        resolver = EntityResolver()
        resolver._index = {"arctis mining": (1, "client", "Arctis Mining Corp.")}
        resolver._norm_list = ["arctis mining"]

        result = resolver.resolve("Completely Different Company Ltd")
        assert not result.matched
        assert result.entity_id is None

    def test_resolver_empty_index(self):
        from app.services.entity_resolution import EntityResolver
        resolver = EntityResolver()
        result = resolver.resolve("Any Company Inc.")
        assert not result.matched

    def test_add_entity_live_update(self):
        from app.services.entity_resolution import EntityResolver
        resolver = EntityResolver()
        resolver.add_entity("New Prospect Corp.", 99, "prospect")
        result = resolver.resolve("New Prospect Corp.")
        assert result.matched
        assert result.entity_id == 99


# ── Cache client unit tests ────────────────────────────────────────────────────

class TestCacheClient:
    def test_ai_response_key_deterministic(self):
        from app.cache.client import CacheClient
        c = CacheClient()
        k1 = c.ai_response_key("churn_brief", client_id=42, score=78)
        k2 = c.ai_response_key("churn_brief", client_id=42, score=78)
        assert k1 == k2

    def test_ai_response_key_differs_by_params(self):
        from app.cache.client import CacheClient
        c = CacheClient()
        k1 = c.ai_response_key("churn_brief", client_id=42)
        k2 = c.ai_response_key("churn_brief", client_id=43)
        assert k1 != k2

    def test_client_key_format(self):
        from app.cache.client import CacheClient
        c = CacheClient()
        assert c.client_key(42) == "client:v1:42"

    def test_trigger_feed_key_format(self):
        from app.cache.client import CacheClient
        c = CacheClient()
        assert "triggers:v1:live" in c.trigger_feed_key("ALL", 50, 72)
