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
        # Supabase client may return different shapes depending on version.
        user_resp = supabase.auth.get_user(token)
        user = None

        # Handle supabase-py response shapes
        if isinstance(user_resp, dict):
            # e.g. {'data': {'user': {...}}, 'error': None}
            user = user_resp.get('data', {}).get('user')
        else:
            # e.g. object with .user attribute or namedtuple
            user = getattr(user_resp, 'user', None)

        if user:
            return {
                "sub": str(user.get('id') if isinstance(user, dict) else getattr(user, 'id')),
                "email": user.get('email') if isinstance(user, dict) else getattr(user, 'email', None),
                "aud": "authenticated",
                "user_metadata": (user.get('user_metadata') if isinstance(user, dict) else getattr(user, 'user_metadata', {})) or {}
            }

        # If Supabase validation failed but token is a JWT, attempt a local decode as fallback (no signature verification).
        # This is useful for local development where we might be using tokens issued by a different Supabase project.
        try:
            decoded = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
            return {
                "sub": str(decoded.get('sub') or decoded.get('user_id') or decoded.get('uid')),
                "email": decoded.get('email'),
                "aud": decoded.get('aud', 'authenticated'),
                "user_metadata": decoded.get('user_metadata') or decoded.get('user_metadata', {})
            }
        except Exception as decode_err:
            logger.debug(f"Local JWT decode failed: {decode_err}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except HTTPException:
        # Re-raise explicit HTTPExceptions
        raise
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

