import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

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
    directly in our Neon PostgreSQL database.
    """
    if not credentials or not credentials.credentials:
        return None

    token = credentials.credentials.strip()
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

        return AuthenticatedUser(
            id=str(row[0]),
            email=row[1],
            name=row[2],
            role=row[3]
        )
    except Exception as e:
        logger.error(f"Error verifying Neon Auth session: {e}")
        return None
    finally:
        db.close()

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
