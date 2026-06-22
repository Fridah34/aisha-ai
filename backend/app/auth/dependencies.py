#================================================================================================
#DEPENDENCIES OPERATIONS:Route protection, Database  Hooks & Authentication Guard
#================================================================================================

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
from app.models import User
from app.auth.utils import verify_token
from database import get_db
from typing import Optional

#===========HTTP BEARER SCHEME================

security = HTTPBearer(
    description="Enter your JWT token to access this endpoint from the auth/login endpoint",
    auto_error=True
)
#===========AUTHENTICATION DEPENDENCY================

async def get_current_user(
    credentials:HTTPAuthCredentials = Depends(Security),
    db:Session = Depends(get_db),   
)-> User:
    token =credentials.credentials
    token_data = verify_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},

        )
    email = token_data.get("email")
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        
        )
    #Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return user


#===========OPTIONAL AUTHENTICATION DEPENDENCY================

async def get_optional_current_user(
    credentials:HTTPAuthCredentials = Depends(Security),
    db:Session = Depends(get_db),
) -> Optional[User]:
    if credentials is None:
        return None
    
    token = credentials.credentials
    token_data = verify_token(token)
    if token_data is None:
        return None

    email = token_data.get("email")
    user = db.query(User).filter(User.email == email).first()

    if user and user.is_active:
        return user

    return None





