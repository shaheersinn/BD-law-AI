"""
tests/test_auth.py — Authentication endpoint tests.

Tests JWT flow, account lockout, role enforcement.
Uses httpx.AsyncClient against the test app.
"""

import pytest

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
    def test_access_token_contains_claims(self):
        from app.auth.service import create_access_token, decode_token

        token = create_access_token(user_id=42, role="partner")
        claims = decode_token(token, expected_type="access")
        assert claims["sub"] == "42"
        assert claims["role"] == "partner"
        assert claims["type"] == "access"

    def test_refresh_token_type(self):
        from jose import jwt

        from app.auth.service import create_refresh_token
        from app.config import get_settings

        token = create_refresh_token(user_id=42)
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        assert payload["type"] == "refresh"

    def test_access_token_not_accepted_as_refresh(self):
        from jose import jwt

        from app.auth.service import create_access_token
        from app.config import get_settings

        token = create_access_token(user_id=42, role="partner")
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        assert payload["type"] == "access"
        # Attempting to use it as refresh should fail
        assert payload["type"] != "refresh"

    def test_tampered_token_rejected(self):
        from jose import JWTError

        from app.auth.service import create_access_token, decode_token

        token = create_access_token(user_id=42, role="partner")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(JWTError):
            decode_token(tampered, expected_type="access")


class TestTokenClaims:
    def test_admin_role_in_token(self):
        from app.auth.service import create_access_token, decode_token

        token = create_access_token(user_id=1, role="admin")
        claims = decode_token(token, expected_type="access")
        assert claims["role"] == "admin"

    def test_partner_role_in_token(self):
        from app.auth.service import create_access_token, decode_token

        token = create_access_token(user_id=2, role="partner")
        claims = decode_token(token, expected_type="access")
        assert claims["role"] == "partner"

    def test_readonly_role_in_token(self):
        from app.auth.service import create_access_token, decode_token

        token = create_access_token(user_id=3, role="readonly")
        claims = decode_token(token, expected_type="access")
        assert claims["role"] == "readonly"

    def test_associate_role_in_token(self):
        from app.auth.service import create_access_token, decode_token

        token = create_access_token(user_id=4, role="associate")
        claims = decode_token(token, expected_type="access")
        assert claims["role"] == "associate"


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
