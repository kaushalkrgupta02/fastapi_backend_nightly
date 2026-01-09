from sqlalchemy.orm import Session
from models.auth import Profile, UserRole, AppRole, StaffProfile
import uuid
from datetime import datetime
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AuthController:
    """Authentication and user management operations"""

    @staticmethod
    def create_user_profile(
        db: Session,
        user_id: str,
        email: str,
        display_name: str = "",
        urole: str = ""
    ) -> Tuple[Dict[str, Any], int]:
        """
        Create a new user profile
        """
        try:
            # Convert string user_id to UUID
            user_uuid = uuid.UUID(user_id)
            
            # Create profile
            profile = Profile(
                user_id=user_uuid,
                display_name=display_name,
                language="en"
            )
            
            db.add(profile)
            db.flush()  # Flush to ensure profile is created before creating role
            
            # Determine the role (default to user)
            role_mapping = {
                "admin": AppRole.admin,
                "venue_manager": AppRole.venue_manager,
                "manager": AppRole.manager,
                "reception": AppRole.reception,
                "kitchen": AppRole.kitchen,
                "waitress": AppRole.waitress,
                "bar": AppRole.bar,
                "guest": AppRole.guest,
            }
            
            app_role = role_mapping.get(urole)
            
            # Create user role with proper enum conversion
            user_role = UserRole(
                user_id=user_uuid,
                role=app_role.value if isinstance(app_role, AppRole) else app_role
            )
            
            db.add(user_role)
            db.commit()
            db.refresh(profile)
            
            logger.info(f"Created profile for user {user_id} with role {app_role}")
            
            return {
                "message": "Profile created successfully",
                "user_id": str(profile.id),
                "display_name": profile.display_name,
                "role": app_role.value if app_role else None
            }, 201
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user profile: {e}")
            return {"error": str(e)}, 400

    @staticmethod
    def get_user_with_role(
        db: Session,
        user_id: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get user profile with role information
        """
        try:
            user_uuid = uuid.UUID(user_id)
            
            # Get profile
            profile = db.query(Profile).filter(Profile.user_id == user_uuid).first()
            
            if not profile:
                logger.warning(f"Profile not found for user {user_id}")
                return {"error": "User profile not found"}, 404
            
            # Get user role
            user_role = db.query(UserRole).filter(UserRole.user_id == user_uuid).first()
            venue_id = db.query(StaffProfile).filter(StaffProfile.user_id == user_uuid).first()
            
            return {
                "user_id": str(profile.user_id),
                "display_name": profile.display_name,
                "phone_number": profile.phone,
                "profile_picture_url": profile.avatar_url,
                "avatar_url": profile.avatar_url,
                "language": profile.language,
                "is_member": profile.is_member,
                "membership_tier": profile.membership_tier,
                "points_balance": profile.points_balance,
                "membership_renews_at": profile.membership_renews_at.isoformat() if (profile.membership_renews_at is not None) else None,
                "role": user_role.role.value if user_role else None,
                "venue_id": str(venue_id.venue_id) if venue_id else None,
                "created_at": profile.created_at.isoformat() if (profile.created_at is not None) else None
            }, 200
            
        except ValueError as e:
            logger.error(f"Invalid user_id format: {e}")
            return {"error": "Invalid user_id format"}, 400
        except Exception as e:
            logger.error(f"Error fetching user profile: {e}")
            return {"error": str(e)}, 500

    @staticmethod
    def get_user_venue(
        db: Session,
        user_id: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get venue associated with the user
        """
        try:
            user_uuid = uuid.UUID(user_id)
            
            # Get staff profile to find venue
            staff_profile = db.query(StaffProfile).filter(StaffProfile.user_id == user_uuid).first()
            
            if not staff_profile:
                logger.warning(f"Staff profile not found for user {user_id}")
                return {"error": "Staff profile not found"}, 404
            
            return {
                "user_id": str(staff_profile.user_id),
                "venue_id": str(staff_profile.venue_id),
                "display_name": staff_profile.display_name,
                "avatar_url": staff_profile.avatar_url,
                "phone": staff_profile.phone,
                "is_active": staff_profile.is_active,
                "created_at": staff_profile.created_at.isoformat() if (staff_profile.created_at is not None) else None
            }, 200
            
        except ValueError as e:
            logger.error(f"Invalid user_id format: {e}")
            return {"error": "Invalid user_id format"}, 400
        except Exception as e:
            logger.error(f"Error fetching staff profile: {e}")
            return {"error": str(e)}, 500
        
        