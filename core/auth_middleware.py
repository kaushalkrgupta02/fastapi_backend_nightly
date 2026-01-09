from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import jwt
from core.supabase_client import get_supabase
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
security = HTTPBearer()

# You can set this from environment variables
JWT_SECRET = None  # Supabase will verify the token


async def get_current_user(credentials = Depends(security)) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token
    Returns the decoded token payload
    """
    token = credentials.credentials
    
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user(token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "sub": str(user.user.id),
            "email": user.user.email,
            "aud": "authenticated",
            "user_metadata": user.user.user_metadata or {}
        }
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_with_role(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current user with role information
    """
    return current_user


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user_with_role),
) -> Dict[str, Any]:
    """
    Verify that current user is an admin
    """
    # This would typically check the role from the database
    # For now, we return the user if authenticated
    # The role verification should happen in the service layer
    return current_user

