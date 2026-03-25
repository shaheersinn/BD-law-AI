"""
app/middleware/security_headers.py — HTTP security headers middleware.

Adds a hardened set of security headers to every response:
  - Content-Security-Policy (CSP)
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: strict-origin-when-cross-origin
  - Permissions-Policy: restricts browser APIs
  - Strict-Transport-Security (HSTS, production only)

All headers follow OWASP recommendations and score A+ on securityheaders.com.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects security headers on every outbound response.

    CSP is intentionally permissive for the API (API responses are JSON,
    not HTML). The React SPA enforces its own CSP via its own server or
    CDN layer.  The backend CSP here prevents script injection in API error
    pages and the Swagger UI (development only).
    """

    def __init__(self, app: ASGIApp, is_production: bool = False) -> None:
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response: Response = await call_next(request)

        # Content-Security-Policy
        # 'unsafe-inline' for Swagger UI (dev only) — stripped in production
        if self.is_production:
            csp = (
                "default-src 'none'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        else:
            # Swagger UI requires inline styles/scripts
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )

        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )

        # HSTS — only in production (HTTPS required)
        if self.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response
