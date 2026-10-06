from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.config import settings

import hashlib
import time
import threading

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# Thread-safe in-memory token cache (60s TTL) to prevent hammering Neon Postgres on every request
_AUTH_CACHE: Dict[str, tuple[AuthenticatedUser, float]] = {}
_AUTH_CACHE_LOCK = threading.Lock()
_AUTH_CACHE_TTL_SECONDS = 60.0

def clear_auth_cache() -> None:
    """Clears the token cache (primarily for tests and token revocation)."""
    with _AUTH_CACHE_LOCK:
        _AUTH_CACHE.clear()

def _clean_expired_cache(now: float) -> None:
    """Evicts expired token cache entries if cache size exceeds threshold."""
    if len(_AUTH_CACHE) > 512:
        expired_keys = [k for k, (_, exp) in _AUTH_CACHE.items() if exp <= now]
        for k in expired_keys:
            _AUTH_CACHE.pop(k, None)

class AuthenticatedUser:
    """Represents a validated user from Neon Auth (Better Auth)."""
    def __init__(self, id: str, email: str, name: Optional[str] = None, role: Optional[str] = None):
        self.id = id
        self.email = email
        self.name = name or email.split("@")[0]
        self.role = role or "user"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role
        }

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[AuthenticatedUser]:
    """
    Validates the session token from Better Auth against neon_auth.session
    directly in our Neon PostgreSQL database, with a 60s thread-safe in-memory cache.
    """
    if not credentials or not credentials.credentials:
        return None

    token = credentials.credentials.strip()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = time.monotonic()

    # Fast path: check in-memory TTL cache
    with _AUTH_CACHE_LOCK:
        cached = _AUTH_CACHE.get(token_hash)
        if cached:
            user, expires_at = cached
            if now < expires_at:
                return user
            else:
                _AUTH_CACHE.pop(token_hash, None)

    # Slow path: query Neon PostgreSQL
    db = SessionLocal()
    try:
        query = text("""
            SELECT u.id, u.email, u.name, u.role, s."expiresAt"
            FROM neon_auth.session s
            JOIN neon_auth."user" u ON s."userId" = u.id
            WHERE s.token = :token AND s."expiresAt" > NOW()
            LIMIT 1;
        """)
        row = db.execute(query, {"token": token}).fetchone()
        if not row:
            return None

        user = AuthenticatedUser(
            id=str(row[0]),
            email=row[1],
            name=row[2],
            role=row[3]
        )

        with _AUTH_CACHE_LOCK:
            _clean_expired_cache(now)
            _AUTH_CACHE[token_hash] = (user, now + _AUTH_CACHE_TTL_SECONDS)

        return user
    except Exception as e:
        # Infrastructure failure must NOT be reported as "anonymous": doing so
        # silently downgrades every authenticated request during a DB outage.
        # Distinguish a genuine infrastructure error from an invalid session.
        logger.error("Error verifying Neon Auth session (treating as infra failure): %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication backend is unavailable. Please retry.",
        ) from e
    finally:
        db.close()


def require_role(*roles: str):
    """Dependency factory enforcing that the caller holds one of ``roles``."""
    allowed = {r.strip().lower() for r in roles}

    def _dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if allowed and user.role.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the following roles: {', '.join(sorted(allowed))}.",
            )
        return user

    return _dependency

def get_current_user(
    user: Optional[AuthenticatedUser] = Depends(get_current_user_optional)
) -> AuthenticatedUser:
    """Enforces authentication for protected endpoints."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in via Neon Auth.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user
