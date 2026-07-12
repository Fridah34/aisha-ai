#=================================================================================================
#UTILITY OPERATIONS: Security, cryptography and Token management
#=================================================================================================

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt
from passlib.context import CryptContext

#==========PASSWORD HASHING CONTEXT===========

# ==============================================================================
# NOTE: Passlib uses a double underscore ('__') to target scheme-specific parameters.
# 'bcrypt__min_rounds' forces a cryptographically secure baseline hashing difficulty 
# factor of 12. Do not change to a single underscore, or it will trigger a KeyError.
# ==============================================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__min_rounds=12,
)

#==========JWT CONFIGURATION==============

SECRET_KEY = os.getenv("SECRET_KEY","change-me-in-production-super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

#=========PASSWORD HASHING FUNCTIONS=======

def hash_password(password:str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str,hashed_password: str) -> bool:
    return pwd_context.verify(plain_password,hashed_password)

#==========JWT TOKEN FUNCTIONS=========

def create_access_token(
        data: Dict,
        expires_delta: Optional[timedelta] = None
)-> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    
#=========TOKEN REFRESH FUNCTIONS========

def refresh_access_token(data: Dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": int(expire.timestamp()), "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

#=========PASSWORD VALIDATION=============

def is_password_strong(password: str)-> bool:
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):  # c stands for character
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~" for c in password):
        return False
    return True
