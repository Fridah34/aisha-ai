# ================================================================================================
# DEPENDENCIES OPERATIONS:Route protection, Database  Hooks & Authentication Guard
# ================================================================================================

from typing import Optional

from app.auth.utils import verify_access_token
from app.database import get_db
from app.models import User
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

# ===========HTTP BEARER SCHEME================

security = HTTPBearer(
    description="Enter your JWT token to access this endpoint from the auth/login endpoint",
    auto_error=False,
)


def _get_token_from_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    if credentials is not None:
        return credentials.credentials

    return None


# ===========AUTHENTICATION DEPENDENCY================


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = _get_token_from_request(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = verify_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = token_data.get("email") or token_data.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return user


# ===========OPTIONAL AUTHENTICATION DEPENDENCY================


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = _get_token_from_request(request, credentials)
    if token is None:
        return None

    token_data = verify_access_token(token)
    if token_data is None:
        return None

    email = token_data.get("email") or token_data.get("sub")
    user = db.query(User).filter(User.email == email).first()

    if user and user.is_active:
        return user

    return None
