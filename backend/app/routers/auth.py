"""
Authentication routes for login and user management.
Implements JWT-based authentication with rate limiting.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import LoginRequest, TokenResponse, UserResponse
from app.auth import authenticate_user, create_access_token, create_refresh_token, get_current_user
from app.models import User
from app.redis_client import check_rate_limit, reset_rate_limit
from app.config import settings
from app.services.cache import cache_service
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.

    Rate-limited to prevent brute-force attacks (max 5 attempts per minute per IP).

    Args:
        login_data: Username and password
        request: FastAPI request object (for IP address)
        db: Database session

    Returns:
        Access and refresh JWT tokens

    Raises:
        HTTPException 429: Too many login attempts
        HTTPException 401: Invalid credentials
    """
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"login:{client_ip}"

    # Check rate limit
    if not check_rate_limit(rate_limit_key, settings.login_rate_limit, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please try again in 1 minute."
        )

    # Authenticate user
    user = authenticate_user(db, login_data.username, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset rate limit on successful login
    reset_rate_limit(rate_limit_key)

    # Create tokens
    token_data = {"user_id": user.id, "username": user.username, "is_admin": user.is_admin}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        User information
    """
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout user by blacklisting their JWT token.

    The token will be blacklisted for the remaining time until it expires.
    After logout, the token cannot be used for authentication.

    Args:
        credentials: Bearer token to blacklist
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException 401: Invalid or expired token
        HTTPException 500: Failed to blacklist token
    """
    token = credentials.credentials

    # Validate token by getting current user (will raise exception if invalid)
    try:
        current_user = get_current_user(credentials, db)
    except HTTPException:
        # Re-raise authentication errors
        raise

    # Blacklist the token (will expire automatically after token TTL)
    success = cache_service.blacklist_token(token, ttl=settings.access_token_expire_minutes * 60)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout. Please try again."
        )

    return {
        "message": "Successfully logged out",
        "detail": "Token has been revoked and can no longer be used",
        "user": current_user.username
    }
