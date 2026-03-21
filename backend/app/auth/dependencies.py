"""
app/auth/dependencies.py — FastAPI dependency injection for authentication.

Usage:
    @router.get("/protected")
    async def endpoint(claims: TokenClaims = Depends(require_auth)):
        ...

    @router.delete("/admin-only")
    async def admin_endpoint(claims: TokenClaims = Depends(require_admin)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.auth.models import UserRole
from app.auth.service import TokenClaims, decode_token

_bearer = HTTPBearer(auto_error=False)


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — provide Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def require_auth(token: str = Depends(_extract_token)) -> TokenClaims:
    """Any authenticated user."""
    try:
        return decode_token(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_partner(claims: TokenClaims = Depends(require_auth)) -> TokenClaims:
    """Partners and admins only."""
    if not claims.is_partner_or_above:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner or admin role required",
        )
    return claims


def require_admin(claims: TokenClaims = Depends(require_auth)) -> TokenClaims:
    """Admins only."""
    if not claims.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return claims


def require_write(claims: TokenClaims = Depends(require_auth)) -> TokenClaims:
    """Partners, associates, and admins (not readonly)."""
    if not claims.can_write():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required",
        )
    return claims


# ── Optional auth (for endpoints that work with or without auth) ───────────────

def optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TokenClaims | None:
    """Returns claims if authenticated, None otherwise."""
    if not credentials:
        return None
    try:
        return decode_token(credentials.credentials)
    except JWTError:
        return None
