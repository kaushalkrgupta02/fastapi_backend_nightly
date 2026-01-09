from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from pydantic import BaseModel, EmailStr
from typing import Optional
from core.get_db import get_db
from core.auth_middleware import get_current_user, get_current_user_with_role, require_admin
from core.supabase_client import get_supabase
from services.auth import AuthController
from models.auth import Profile, UserRole, StaffProfile
from models.venue import Venue

import logging
import uuid as uuid_module

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Request/Response Models
class SignUpRequest(BaseModel):
    display_name: Optional[str] = None
    email: EmailStr
    password: str
    role: Optional[str] = None

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[str] = None
    role: Optional[str] = None  
    venue_id: Optional[str] = None  
    

class ProfileResponse(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    language: Optional[str] = None
    is_member: Optional[bool] = None
    membership_tier: Optional[str] = None
    points_balance: Optional[int] = None
    membership_renews_at: Optional[str] = None

class SessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class SignInResponse(BaseModel):
    user: UserResponse
    session: SessionResponse

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class UpdatePasswordRequest(BaseModel):
    new_password: str

class UpdateRoleRequest(BaseModel):
    user_id: str
    role: str

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    language: Optional[str] = None

class staffProfileUpdateRequest(BaseModel):
    user_id: str
    venue_id: str


# Auth Endpoints
@router.post("/signup", response_model=dict)
async def signup(
    signup_data: SignUpRequest,
    db: Session = Depends(get_db)
):
    print("Signup endpoint called",signup_data)

    valid_roles = ["admin", "venue_manager",'manager', "reception", "kitchen", "waitress", "bar", "guest","user"]
    if signup_data.role and signup_data.role not in valid_roles:
        print(123)
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    print("abd")

    print("Signup data received:", signup_data)
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_up({
            "email": signup_data.email,
            "password": signup_data.password,
            "options": {
                "data": {
                    "display_name": signup_data.display_name
                }
            }
        })
        
        print("signup response:", signup_data.role) 
        
        if response.user:
            result, status_code = AuthController.create_user_profile(
                db,
                user_id=str(response.user.id),
                email=signup_data.email,
                display_name=signup_data.display_name or "",
                urole=signup_data.role or ""
            )
            print("Profile creation result:", result)
            return {
                "message": "Profile created successfully. Please check your email for verification.",
                "user": {
                    "id": str(response.user.id),
                    "email": signup_data.email,
                    "display_name": signup_data.display_name,
                    "role": signup_data.role or ""
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to create user")
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/signin", response_model=SignInResponse)
async def signin(
    signin_data: SignInRequest,
    db: Session = Depends(get_db)
):
    """
    Sign in with email and password
    """
    try:
        supabase = get_supabase()
        
        response = supabase.auth.sign_in_with_password({
            "email": signin_data.email,
            "password": signin_data.password
        })
        
        if response.session and response.user:
            result, status_code = AuthController.get_user_with_role(
                db, str(response.user.id) 
            )
            
            logger.info(f"User signed in: {str(response.user.id)}")

            # Get created_at from Supabase user
            created_at = response.user.created_at if hasattr(response.user, 'created_at') else None

            return {
                "user": {
                    "user_id": str(response.user.id),
                    "email": response.user.email or "",
                    "display_name": result.get("display_name") if status_code == 200 else None,
                    "avatar_url": result.get("avatar_url") if status_code == 200 else None,
                    "phone": result.get("phone_number") if status_code == 200 else None,
                    "created_at": str(created_at) if created_at else None,
                    "role": result.get("role") if status_code == 200 else None,
                    "venue_id": result.get("venue_id") if status_code == 200 else None
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "token_type": "bearer",
                    "expires_in": response.session.expires_in
                }
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        logger.error(f"Signin error: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
        
@router.post("/reset-password")
async def reset_password(reset_data: ResetPasswordRequest):
    """
    Send password reset email
    """
    try:
        supabase = get_supabase()
        
        response = supabase.auth.reset_password_email(reset_data.email)
        
        return {"message": "Password reset email sent"}
        
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/update-password")
async def update_password(
    password_data: UpdatePasswordRequest,
    current_user = Depends(get_current_user)
):
    """
    Update user password (requires authentication)
    """
    try:
        supabase = get_supabase()
        
        response = supabase.auth.update_user({
            "password": password_data.new_password
        })
        
        return {"message": "Password updated successfully"}
        
    except Exception as e:
        logger.error(f"Update password error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
async def get_me(
    current_user = Depends(get_current_user_with_role),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user with role
    """
    user_id = current_user["sub"]
    logger.info(f"Fetching profile for user: {user_id}")

    try:
        # Convert string to UUID for database query
        user_uuid = uuid_module.UUID(user_id)
        
        profile = db.query(Profile).filter(Profile.user_id == user_uuid).first()
        
        if not profile:
            logger.warning(f"Profile not found for user {user_id}, returning minimal info")
            # Return minimal user info from token if profile doesn't exist
            return {
                "user_id": user_id,
                "email": current_user.get("email"),
                "display_name": None,
                "phone": None,
                "avatar_url": None,
                "language": "en",
                "role": None,
                "venue_id": None,
                "profile_exists": False
            }
            
        user_role = db.query(UserRole).filter(UserRole.user_id == user_uuid).first()
        
        return {
            "user_id": str(profile.user_id),
            "display_name": profile.display_name,
            "phone": profile.phone,
            "avatar_url": profile.avatar_url,
            "language": profile.language or "en",
            "is_member": profile.is_member,
            "membership_tier": profile.membership_tier,
            "points_balance": profile.points_balance,
            "membership_renews_at": profile.membership_renews_at.isoformat() if (profile.membership_renews_at is not None) else None,
            "role": user_role.role.value if user_role else None,
            "email": current_user.get("email"),
            "profile_exists": True
        }
    except Exception as e:
        logger.error(f"Get user profile error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch user profile: {str(e)}")



@router.post("/refresh-token")
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token
    """
    try:
        supabase = get_supabase()
        
        response = supabase.auth.refresh_session(refresh_token)
        
        if response.session:
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_in": response.session.expires_in
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
    except Exception as e:
        logger.error(f"Refresh token error: {e}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")



@router.patch("/profile")
async def update_profile(
    update_data: UpdateProfileRequest = Body(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile details (membership fields cannot be patched by user)
    """
    user_id = current_user["sub"]

    try:
        user_uuid = uuid_module.UUID(user_id)
        profile = db.query(Profile).filter(Profile.user_id == user_uuid).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Only update allowed fields
        allowed_fields = {"display_name", "phone", "avatar_url", "language"}
        for field, value in update_data.dict(exclude_unset=True).items():
            if field in allowed_fields and value is not None:
                setattr(profile, field, value)

        db.commit()
        db.refresh(profile)

        return {
            "message": "Profile updated successfully",
            "profile": {
                "user_id": str(profile.user_id),
                "display_name": profile.display_name,
                "phone": profile.phone,
                "avatar_url": profile.avatar_url,
                "language": profile.language,
                "is_member": profile.is_member,
                "membership_tier": profile.membership_tier,
                "points_balance": profile.points_balance,
                "membership_renews_at": profile.membership_renews_at.isoformat() if (profile.membership_renews_at is not None) else None,
            }
        }
    except ValueError as e:
        logger.error(f"Invalid user_id format: {e}")
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as e:
        db.rollback()
        logger.error(f"Update profile error: {e}")
        raise HTTPException(status_code=400, detail=str(e))    
    
    
@router.post("/admin/map-user-venue", dependencies=[Depends(require_admin)])
def map_user_to_venue(
    mapping_data: staffProfileUpdateRequest,
    db: Session = Depends(get_db)
):
    try:
        user_uuid = uuid_module.UUID(mapping_data.user_id)
        venue_uuid = uuid_module.UUID(mapping_data.venue_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # Check if user exists
    user_profile = db.query(Profile).filter(Profile.user_id == user_uuid).first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if venue exists
    venue = db.query(Venue).filter(Venue.id == venue_uuid).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    # Create or update StaffProfile
    staff_profile = db.query(StaffProfile).filter(StaffProfile.user_id == user_uuid).first()
    if staff_profile:
        staff_profile.venue_id = str(venue_uuid)
        staff_profile.display_name = user_profile.display_name
        staff_profile.phone = user_profile.phone
        staff_profile.avatar_url = user_profile.avatar_url
    else:
        staff_profile = StaffProfile(
            user_id=str(user_uuid),
            venue_id=str(venue_uuid),
            display_name=user_profile.display_name,
            phone=user_profile.phone,
            avatar_url=user_profile.avatar_url
        )
        db.add(staff_profile)
    
    db.commit()
    return {"message": "User mapped to venue successfully"}
  