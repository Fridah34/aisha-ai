# ==============================================================================
# AUTHENTICATION ROUTER MODULE
# ==============================================================================
# This module controls the web entry gates for the application. It receives
# incoming requests for user registration, logins, and token management,
# coordinates with the database workers, and returns the secure responses.
# ==============================================================================

import os

from app.auth.dependencies import get_current_user
from app.auth.utils import (
    create_access_token,
    hash_password,
    refresh_access_token,
    verify_access_token,
    verify_password,
)
from app.crud import get_user_by_email
from app.database import get_db
from app.models import BusinessType as ModelBusinessType
from app.models import User
from app.schema import (
    UserGoogleRegister,
    UserLogin,
    UserRegister,
    UserResponse,
)
from fastapi import APIRouter, Depends, HTTPException,Request, Response, status
from sqlalchemy.orm import Session

# ===================ENVIRONMENT CONFIG====================
# Cookies marked `secure=True` are only stored/sent by browsers over HTTPS.
# Local dev runs on plain HTTP (localhost:5173 / localhost:8000), so `secure`
# must be False there or the browser silently drops the cookie entirely.
# Set ENVIRONMENT=production in your deployment's .env once real HTTPS is in place.
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"

# ===================ROUTER INITIALIZATION====================

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        400: {"description": "Bad Request - Invalid Input"},
        401: {"description": "Unauthorized - Invalid credentials"},
        409: {"description": "Conflict - Email already exists"},
        500: {"description": "Internal Server Error"},
    },
)

# ==============REGISTER ENDPOINT====================


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register new Business Owner",
    description="Create new business account with email and password",
)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # check if email already exist
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered. Use a different email or login with your existing account.",
            headers={"X-Error-Code": "EMAIL_ALREADY_EXISTS"},
        )
    try:
        # create temporary user object with hashed password for validation
        new_user = User(
            email=user_data.email,
            name=user_data.name,
            business_name=user_data.business_name,
            business_type=ModelBusinessType(user_data.business_type.value),
            hashed_password=hash_password(user_data.password),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"user": UserResponse.model_validate(new_user)}

    except Exception as e:
        db.rollback()
        print("\n ACTUAL REGISTRATION ERROR:", str(e))
        import traceback

        traceback.print_exc()
        print("===========================\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account .Please try again",
        )


# ==============GOOGLE REGISTER ENDPOINT====================


@router.post(
    "/register/google",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register with Google OAuth",
    description="Create account using Google OAuth credentials",
)
def register_google(user_data: UserGoogleRegister, db: Session = Depends(get_db)):
    # check if email already exist
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered. Use a different email or login with your existing account.",
            headers={"X-Error-Code": "EMAIL_ALREADY_EXISTS"},
        )
    try:
        # create new user object without password since its Google OAuth

        new_user = User(
            email=user_data.email,
            name=user_data.name,
            business_name=user_data.business_name,
            google_id=user_data.google_id,
            hashed_password=None,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user
    except Exception as e:
        db.rollback()  # undo any changes made during the creation process
        print("\n ACTUAL REGISTRATION ERROR:", str(e))
        import traceback

        traceback.print_exc()
        print("=========================================\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account .Please try again",
        )


# ============LOGIN ENDPOINT==========


@router.post(
    "/login",
    summary="Loginwith email & Password",
    description="Authenticate and receive JWT access token",
)
def login(
    credentials: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    # Step 1: Find User by email
    user = get_user_by_email(db, credentials.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"X-Error-Code": "INVALID_CREDENTIALS"},
        )
    # Step 2: Verify Password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"X-Error-Code": "INVALID_CREDENTIALS"},
        )

    # Step 3: Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
            headers={"X-Error-Code": "ACCOUNT_NOT_ACTIVE"},
        )

    # Step 4: Create Access Token
    access_token = create_access_token(data={"sub": user.email})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=60 * 60 * 3 ,
    )
    
    refresh_token = refresh_access_token(data={"sub": user.email})
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=60 * 60 * 24,  # 24hours , matches refresh_access_token()
)
    return {"user": UserResponse.model_validate(user)}


# =============GET ME ENDPOINT====================


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Retrieve authenticated users information",
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# =============LOGOUT ENDPOINT====================


@router.post(
    "/logout",
    summary="Logout User",
    description="Logout and Invalidate session",
)
def logout(response: Response, current_user: User = Depends(get_current_user)):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
    )
    return {"message": "Logged out successfully"}


# ==========VERIFY TOKEN ENDPOINT====================


@router.post(
    "/verify-token",
    summary="Verify Token",
    description="Check if JWT token is valid",
)
def verify_token(current_user: User = Depends(get_current_user)):
    return {
        "is_valid": True,
        "user": UserResponse.model_validate(current_user),
        "message": "Token is valid",
    }


# auth/router.py — refresh token endpoint
@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    token_data = verify_access_token(refresh_token)
    if token_data is None or token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = get_user_by_email(db, token_data["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    new_access_token = create_access_token(data={"sub": user.email})
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=1800,
    )
    return {"message": "Token refreshed"}