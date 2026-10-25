from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, List
import jwt
from app.core.config import settings
from app.core.exceptions import AuthenticationError


def create_access_token(
    user_id: str,
    email: str,
    roles: List[str],
    institution_id: Optional[str] = None,
    assigned_region: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "roles": roles,
        "institution_id": institution_id,
        "assigned_region": assigned_region,
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Session token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid authentication credentials.")
