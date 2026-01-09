from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime, date, timezone
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from core.get_db import get_db
from core.auth_middleware import get_current_user
from models.venue import Venue, VenueTable,VenueGuestProfile
from models.auth import Profile, UserRole, StaffProfile, AppRole
from models.venue import Venue, VenueTable, VenueGuestProfile, VenuePackage, PackageItem, LineSkipPass
import uuid as uuid_module
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/venues", tags=["Venues"])

# --- Pydantic Schemas ---

class VenueCreate(BaseModel):
    name: str
    venue_type_id: Optional[UUID] = None
    status: Optional[str] = "perfect"
    has_cover: Optional[bool] = False
    supports_booking: Optional[bool] = False
    booking_mode: Optional[str] = "none"
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    opening_hours: Optional[dict] = None
    cover_image_url: Optional[str] = None
    amenities: Optional[List[str]] = []
    venue_notes: Optional[str] = None
    min_spend: Optional[str] = None
    crowd_trend: Optional[str] = "steady"
    line_skip_enabled: Optional[bool] = False
    line_skip_price: Optional[float] = None
    line_skip_daily_limit: Optional[int] = None
    line_skip_valid_until: Optional[str] = None
    external_id: Optional[str] = None
    external_source: Optional[str] = "manual"
    has_promo: Optional[bool] = False
    promo_type: Optional[str] = None
    promo_description: Optional[str] = None
    promo_valid_until: Optional[datetime] = None
    show_arrival_window: Optional[bool] = True
    allow_special_requests: Optional[bool] = True
    min_party_size: Optional[int] = 1
    max_party_size: Optional[int] = 20
    max_bookings_per_night: Optional[int] = None
    total_tables: Optional[int] = 10
    seats_per_table: Optional[int] = 4
    total_capacity: Optional[int] = 40
    entry_pass_enabled: Optional[bool] = False
    entry_pass_price: Optional[float] = None
    entry_pass_daily_limit: Optional[int] = None
    vip_pass_enabled: Optional[bool] = False
    vip_pass_price: Optional[float] = None
    vip_pass_daily_limit: Optional[int] = None
    vip_pass_free_item: Optional[str] = None
    stripe_account_id: Optional[str] = None
    payout_enabled: Optional[bool] = False
    deposit_enabled: Optional[bool] = False
    deposit_amount: Optional[float] = 0
    deposit_percentage: Optional[float] = 0
    no_show_charge_enabled: Optional[bool] = False
    reminder_enabled: Optional[bool] = True
    reminder_24h_enabled: Optional[bool] = True
    reminder_2h_enabled: Optional[bool] = True
    logo_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class VenueTableCreate(BaseModel):
    table_number: str
    seats: int
    status: str
    location_zone: Optional[str] = None
    minimum_spend: Optional[float] = None
    notes: Optional[str] = None
    special_features: Optional[List[str]] = []
    is_active: Optional[bool] = True
    sort_order: Optional[int] = None

class VenueTableResponse(BaseModel):
    id: UUID
    venue_id: UUID
    table_number: str
    seats: int
    status: str
    location_zone: Optional[str]
    minimum_spend: Optional[float]
    notes: Optional[str]
    special_features: Optional[List[str]]
    is_active: bool
    sort_order: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



class StaffProfileCreate(BaseModel):
    user_id: UUID
    venue_id: UUID
    display_name: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = True
    role: Optional[str] = None  # Role to assign: reception, kitchen, waitress, bar

class StaffProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

class StaffProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    venue_id: UUID
    display_name: str
    avatar_url: Optional[str]
    phone: Optional[str]
    is_active: bool
    role: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VenueGuestProfileCreate(BaseModel):
    venue_id: UUID
    user_id: Optional[UUID] = None  # Optional for walk-in guests
    guest_name: str  # Required field from form
    guest_phone: str  # Required field from form
    guest_email: str  # Required field from form
    vip_status: Optional[str] = "regular"
    tags: Optional[List[str]] = []
    dietary_restrictions: Optional[List[str]] = []
    preferences: Optional[dict] = {}
    # total_visits: Optional[int] = 0
    # total_spend: Optional[float] = 0
    # last_visit_at: Optional[datetime] = None

    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        if v == "":
            return None
        return v

class VenueGuestProfileUpdate(BaseModel):
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    vip_status: Optional[str] = None
    tags: Optional[List[str]] = None
    dietary_restrictions: Optional[List[str]] = None
    preferences: Optional[dict] = None
    # total_visits: Optional[int] = None
    # total_spend: Optional[float] = None
    # last_visit_at: Optional[datetime] = None

class VenueGuestProfileResponse(BaseModel):
    id: UUID
    venue_id: UUID
    user_id: Optional[UUID]
    guest_name: Optional[str]
    guest_phone: Optional[str]
    guest_email: Optional[str]
    dietary_restrictions: Optional[List[str]]
    preferences: Optional[dict]
    tags: Optional[List[str]]
    vip_status: Optional[str]
    total_visits: Optional[int]
    total_spend: Optional[float]
    last_visit_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
        
class VenueTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None

class VenueTypeResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class VenueResponse(BaseModel):
    id: UUID
    name: str
    cover_image_url: Optional[str]
    venue_type_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True        
        
        
        
# --- Packages / Package Items schemas ---
class VenuePackageCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    availability_start: Optional[str] = None
    availability_end: Optional[str] = None
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0
    package_type: Optional[str] = "custom"
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_quantity: Optional[int] = None
    image_url: Optional[str] = None
    guest_count: Optional[int] = 1

class VenuePackageResponse(VenuePackageCreate):
    id: UUID
    venue_id: UUID
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class PackageItemCreate(BaseModel):
    item_type: Optional[str] = "other"
    item_name: str
    quantity: Optional[int] = 1
    redemption_rule: Optional[str] = "once"
    sort_order: Optional[int] = 0
    notes: Optional[str] = None

class PackageItemResponse(PackageItemCreate):
    id: UUID
    package_id: UUID
    created_at: datetime
    class Config:
        from_attributes = True


# --- Passes schemas ---
class LineSkipPassCreate(BaseModel):
    user_id: Optional[UUID] = None
    purchase_date: Optional[date] = None
    status: Optional[str] = "active"
    price: Optional[float] = None
    pass_type: Optional[str] = "entry"
    free_item_claimed: Optional[bool] = False

class LineSkipPassResponse(LineSkipPassCreate):
    id: UUID
    venue_id: UUID
    created_at: datetime
    class Config:
        from_attributes = True
        
        


# --- STAFF MANAGEMENT ENDPOINTS ---
@router.post("/staff", response_model=StaffProfileResponse)
def create_staff_profile(
    staff_data: StaffProfileCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new staff profile for a user at a venue
    Current user must be admin or venue manager for this venue
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        
        # Check if venue exists
        venue = db.query(Venue).filter(Venue.id == staff_data.venue_id).first()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        
        # Check authorization - user must be admin OR venue manager for this venue
        current_user_role = db.query(UserRole).filter(UserRole.user_id == current_user_uuid).first()
        is_admin = current_user_role and current_user_role.role == AppRole.admin
        
        is_venue_manager = db.query(StaffProfile).filter(
            StaffProfile.user_id == current_user_uuid,
            StaffProfile.venue_id == staff_data.venue_id
        ).first() is not None
        
        if not (is_admin or is_venue_manager):
            raise HTTPException(
                status_code=403, 
                detail="You must be admin or venue manager to create staff profiles"
            )
        
        # Check if user exists in profiles table
        user_profile = db.query(Profile).filter(Profile.user_id == staff_data.user_id).first()
        if not user_profile:
            raise HTTPException(status_code=404, detail="User not found in profiles")
        
        # Check if staff profile already exists for this user at this venue
        existing_staff = db.query(StaffProfile).filter(
            StaffProfile.user_id == staff_data.user_id,
            StaffProfile.venue_id == staff_data.venue_id
        ).first()
        
        if existing_staff:
            raise HTTPException(
                status_code=400, 
                detail="Staff profile already exists for this user at this venue"
            )
        
        # Determine role - default to "reception"
        role_to_assign = staff_data.role if staff_data.role else " "
        
        # Validate role
        valid_roles = [r.value for r in AppRole]
        if role_to_assign not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        
        # Create staff profile
        staff_profile = StaffProfile(
            user_id=staff_data.user_id,
            venue_id=staff_data.venue_id,
            display_name=staff_data.display_name,
            avatar_url=staff_data.avatar_url,
            phone=staff_data.phone,
            is_active=staff_data.is_active
        )
        db.add(staff_profile)
        
        # Create or update user role
        user_role = db.query(UserRole).filter(UserRole.user_id == staff_data.user_id).first()
        
        if user_role:
            # Update existing role
            user_role.role = AppRole(role_to_assign)
        else:
            # Create new role
            user_role = UserRole(
                user_id=staff_data.user_id,
                role=AppRole(role_to_assign)
            )
            db.add(user_role)
        
        db.commit()
        db.refresh(staff_profile)
        
        return {
            **staff_profile.__dict__,
            "role": role_to_assign
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create staff profile error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    

@router.get("/staff/{venue_id}", response_model=List[StaffProfileResponse])
def get_venue_staff(
    venue_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all staff members working at a specific venue
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        
        # Check if venue exists
        venue = db.query(Venue).filter(Venue.id == venue_id).first()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        
        # Check authorization - user must be venue manager or admin
        user_role = db.query(UserRole).filter(UserRole.user_id == current_user_uuid).first()
        
        is_admin = user_role and user_role.role == AppRole.admin
        is_venue_manager = db.query(StaffProfile).filter(
            StaffProfile.user_id == current_user_uuid,
            StaffProfile.venue_id == venue_id
        ).first() is not None
        
        if not (is_admin or is_venue_manager):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view staff for this venue"
            )
        
        # Get all staff at venue with their roles
        staff_list = db.query(StaffProfile).filter(
            StaffProfile.venue_id == venue_id
        ).all()
        
        result = []
        for staff in staff_list:
            user_role = db.query(UserRole).filter(UserRole.user_id == staff.user_id).first()
            result.append({
                **staff.__dict__,
                "role": user_role.role.value if user_role else None
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get venue staff error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# @router.patch("/staff/{staff_id}", response_model=StaffProfileResponse)
# def update_staff_profile(
#     staff_id: UUID,
#     update_data: StaffProfileUpdate,
#     current_user = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Update staff profile details and role
#     """
#     try:
#         current_user_uuid = uuid_module.UUID(current_user["sub"])
        
#         # Get staff profile
#         staff = db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
#         if not staff:
#             raise HTTPException(status_code=404, detail="Staff profile not found")
        
#         # Check authorization
#         user_role = db.query(UserRole).filter(UserRole.user_id == current_user_uuid).first()
#         is_admin = user_role and user_role.role == AppRole.admin
#         is_manager = db.query(StaffProfile).filter(
#             StaffProfile.user_id == current_user_uuid,
#             StaffProfile.venue_id == staff.venue_id
#         ).first() is not None
        
#         if not (is_admin or is_manager):
#             raise HTTPException(status_code=403, detail="Not authorized to update this staff")
        
#         # Update fields
#         if update_data.display_name:
#             staff.display_name = update_data.display_name
#         if update_data.avatar_url:
#             staff.avatar_url = update_data.avatar_url
#         if update_data.phone:
#             staff.phone = update_data.phone
#         if update_data.is_active is not None:
#             staff.is_active = update_data.is_active
        
#         # Update role if provided
#         if update_data.role:
#             valid_roles = [r.value for r in AppRole]
#             if update_data.role not in valid_roles:
#                 raise HTTPException(status_code=400, detail=f"Invalid role: {update_data.role}")
            
#             user_role = db.query(UserRole).filter(UserRole.user_id == staff.user_id).first()
#             if user_role:
#                 user_role.role = AppRole(update_data.role)
#             else:
#                 user_role = UserRole(
#                     user_id=staff.user_id,
#                     role=AppRole(update_data.role)
#                 )
#                 db.add(user_role)
        
#         db.commit()
#         db.refresh(staff)
        
#         user_role = db.query(UserRole).filter(UserRole.user_id == staff.user_id).first()
#         return {
#             **staff.__dict__,
#             "role": user_role.role.value if user_role else None
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Update staff error: {e}")
#         raise HTTPException(status_code=400, detail=str(e))


@router.delete("/staff/{staff_id}")
def delete_staff_profile(
    staff_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove staff profile (venue manager only)
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        
        staff = db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff profile not found")
        
        # Check authorization
        user_role = db.query(UserRole).filter(UserRole.user_id == current_user_uuid).first()
        is_admin = user_role and user_role.role == AppRole.admin
        is_manager = db.query(StaffProfile).filter(
            StaffProfile.user_id == current_user_uuid,
            StaffProfile.venue_id == staff.venue_id
        ).first() is not None
        
        if not (is_admin or is_manager):
            raise HTTPException(status_code=403, detail="Not authorized to delete this staff")
        
        db.delete(staff)
        db.commit()
        
        return {"message": "Staff profile deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Delete staff error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# --- VENUE GUEST PROFILE ENDPOINTS ---
@router.post("/guests", response_model=VenueGuestProfileResponse)
def create_venue_guest_profile(
    guest_data: VenueGuestProfileCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a new guest profile to a venue for booking purposes
    Matches the form: Name*, Phone*, Email*, VIP Status, Tags, Dietary Restrictions
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        
        # Check if venue exists
        venue = db.query(Venue).filter(Venue.id == guest_data.venue_id).first()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        
        # Check authorization - must be venue staff or admin
        user_role = db.query(UserRole).filter(UserRole.user_id == current_user_uuid).first()
        is_admin = user_role and user_role.role == AppRole.admin
        
        is_venue_staff = db.query(StaffProfile).filter(
            StaffProfile.user_id == current_user_uuid,
            StaffProfile.venue_id == guest_data.venue_id
        ).first() is not None
        
        if not (is_admin or is_venue_staff):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to create guest profiles for this venue"
            )
        
        # Check for existing guest profile (unique constraints)
        if guest_data.user_id:
            existing_guest = db.query(VenueGuestProfile).filter(
                VenueGuestProfile.venue_id == guest_data.venue_id,
                VenueGuestProfile.user_id == guest_data.user_id
            ).first()
            if existing_guest:
                raise HTTPException(
                    status_code=400,
                    detail="Guest profile already exists for this user at this venue"
                )
        
        # Check for existing guest by phone (unique constraint)
        existing_guest = db.query(VenueGuestProfile).filter(
            VenueGuestProfile.venue_id == guest_data.venue_id,
            VenueGuestProfile.guest_phone == guest_data.guest_phone
        ).first()
        if existing_guest:
            raise HTTPException(
                status_code=400,
                detail="Guest profile already exists with this phone number at this venue"
            )
        
        # Create guest profile with form fields
        guest_profile = VenueGuestProfile(
            venue_id=guest_data.venue_id,
            user_id=guest_data.user_id,
            guest_name=guest_data.guest_name,
            guest_phone=guest_data.guest_phone,
            guest_email=guest_data.guest_email,
            vip_status=guest_data.vip_status,
            tags=guest_data.tags,
            dietary_restrictions=guest_data.dietary_restrictions,
            preferences=guest_data.preferences)
    

        db.add(guest_profile)
        db.commit()
        db.refresh(guest_profile)
        
        return guest_profile
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create guest profile error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    


 
#helper function
def assert_venue_access(
    db: Session,
    user_id: UUID,
    venue_id: UUID,
    error_message: str
):
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id
    ).one_or_none()

    is_admin = user_role and user_role.role == AppRole.admin

    is_venue_staff = db.query(StaffProfile).filter(
        StaffProfile.user_id == user_id,
        StaffProfile.venue_id == venue_id
    ).first() is not None

    if not (is_admin or is_venue_staff):
        raise HTTPException(status_code=403, detail=error_message)


@router.get("/guests/venue/{venue_id}/guest/{guest_id}",response_model=VenueGuestProfileResponse)
def get_guest_profile(
    venue_id: UUID,
    guest_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific guest profile for a venue
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        assert_venue_access(
            db,
            current_user_uuid,
            venue_id,
            "Not authorized to view this guest profile"
        )

        guest = db.query(VenueGuestProfile).filter(
            VenueGuestProfile.id == guest_id,
            VenueGuestProfile.venue_id == venue_id
        ).one_or_none()

        if not guest:
            raise HTTPException(status_code=404, detail="Guest profile not found")

        return guest

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get guest profile error: {e}")
        raise HTTPException(status_code=400, detail=str(e))




@router.get(
    "/guests/venue/{venue_id}",
    response_model=List[VenueGuestProfileResponse]
)
def get_venue_guests(
    venue_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all guest profiles for a venue
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        venue = db.query(Venue).filter(
            Venue.id == venue_id
        ).one_or_none()

        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        assert_venue_access(
            db,
            current_user_uuid,
            venue_id,
            "Not authorized to view guests for this venue"
        )

        guests = (
            db.query(VenueGuestProfile)
            .filter(VenueGuestProfile.venue_id == venue_id)
            .order_by(VenueGuestProfile.created_at.desc())
            .all()
        )

        return guests

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get venue guests error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/guests/venue/{venue_id}/search", response_model=List[VenueGuestProfileResponse])
def search_guests_by_name(
    venue_id: UUID,
    name: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search guest profiles by name (partial, case-insensitive) within a venue.
    """
    try:
        if not name or name.strip() == "":
            raise HTTPException(status_code=400, detail="Query parameter 'name' is required")

        current_user_uuid = uuid_module.UUID(current_user["sub"])

        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        assert_venue_access(
            db,
            current_user_uuid,
            venue_id,
            "Not authorized to search guests for this venue"
        )

        pattern = f"%{name}%"
        guests = (
            db.query(VenueGuestProfile)
            .filter(VenueGuestProfile.venue_id == venue_id)
            .filter(VenueGuestProfile.guest_name.ilike(pattern))
            .order_by(VenueGuestProfile.created_at.desc())
            .all()
        )

        return guests

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search guests by name error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/guests/{guest_id}",
    response_model=VenueGuestProfileResponse
)
def update_venue_guest_profile(
    guest_id: UUID,
    update_data: VenueGuestProfileUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update guest profile information
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        guest = db.query(VenueGuestProfile).filter(
            VenueGuestProfile.id == guest_id
        ).one_or_none()

        if not guest:
            raise HTTPException(status_code=404, detail="Guest profile not found")

        assert_venue_access(
            db,
            current_user_uuid,
            guest.venue_id,
            "Not authorized to update this guest"
        )

        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(guest, field, value)

        db.commit()
        db.refresh(guest)

        return guest

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Update guest profile error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tables/venue/{venue_id}", response_model=VenueTableResponse)
def create_table_at_venue(
    venue_id: UUID,
    table_data: VenueTableCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new table at a venue (admin or venue manager)
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        # Ensure venue exists
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        # Authorization
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to create tables for this venue")

        # Prevent duplicate table_number for the same venue
        existing = db.query(VenueTable).filter(
            VenueTable.venue_id == venue_id,
            VenueTable.table_number == table_data.table_number
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Table with this number already exists at this venue")

        now = datetime.now(timezone.utc)
        table = VenueTable(
            venue_id=venue_id,
            table_number=table_data.table_number,
            seats=table_data.seats,
            status=table_data.status,
            location_zone=table_data.location_zone,
            minimum_spend=table_data.minimum_spend,
            notes=table_data.notes,
            special_features=table_data.special_features,
            is_active=table_data.is_active if table_data.is_active is not None else True,
            sort_order=table_data.sort_order,
            created_at=now,
            updated_at=now
        )

        db.add(table)
        db.commit()
        db.refresh(table)
        return table

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create table error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    
@router.get("/tables/venue/{venue_id}", response_model=List[VenueTableResponse])
def get_tables_at_venue(
    venue_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all tables for a venue (admin or venue staff)
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        # Ensure venue exists
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        # Authorization
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to view tables for this venue")

        tables = (
            db.query(VenueTable)
            .filter(VenueTable.venue_id == venue_id)
            .order_by(VenueTable.sort_order.asc().nulls_last(), VenueTable.table_number.asc())
            .all()
        )
        return tables

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tables error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# --- Packages endpoints ---
@router.post("/packages/venue/{venue_id}", response_model=VenuePackageResponse)
def create_package_at_venue(venue_id: UUID, payload: VenuePackageCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to create packages for this venue")
        existing = db.query(VenuePackage).filter(VenuePackage.venue_id == venue_id, VenuePackage.name == payload.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Package with this name already exists at this venue")
        now = datetime.now(timezone.utc)
        pkg = VenuePackage(
            venue_id=venue_id,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            availability_start=payload.availability_start,
            availability_end=payload.availability_end,
            is_active=payload.is_active,
            sort_order=payload.sort_order,
            created_at=now,
            updated_at=now,
            package_type=payload.package_type,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            max_quantity=payload.max_quantity,
            image_url=payload.image_url,
            guest_count=payload.guest_count
        )
        db.add(pkg)
        db.commit()
        db.refresh(pkg)
        return pkg
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create package error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/packages/venue/{venue_id}", response_model=List[VenuePackageResponse])
def get_packages_at_venue(venue_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to view packages for this venue")
        packages = db.query(VenuePackage).filter(VenuePackage.venue_id == venue_id).order_by(VenuePackage.sort_order.asc().nulls_last()).all()
        return packages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get packages error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/packages/{package_id}/items", response_model=PackageItemResponse)
def create_package_item(package_id: UUID, payload: PackageItemCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        pkg = db.query(VenuePackage).filter(VenuePackage.id == package_id).one_or_none()
        if not pkg:
            raise HTTPException(status_code=404, detail="Package not found")
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        assert_venue_access(db, current_user_uuid, pkg.venue_id, "Not authorized to create package items for this package")
        now = datetime.now(timezone.utc)
        item = PackageItem(
            package_id=package_id,
            item_type=payload.item_type,
            item_name=payload.item_name,
            quantity=payload.quantity,
            redemption_rule=payload.redemption_rule,
            sort_order=payload.sort_order,
            notes=payload.notes,
            created_at=now
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create package item error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/packages/{package_id}/items", response_model=List[PackageItemResponse])
def get_package_items(package_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        pkg = db.query(VenuePackage).filter(VenuePackage.id == package_id).one_or_none()
        if not pkg:
            raise HTTPException(status_code=404, detail="Package not found")
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        assert_venue_access(db, current_user_uuid, pkg.venue_id, "Not authorized to view package items for this package")
        items = db.query(PackageItem).filter(PackageItem.package_id == package_id).order_by(PackageItem.sort_order.asc()).all()
        return items
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get package items error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# --- Passes endpoints ---
@router.post("/passes/venue/{venue_id}", response_model=LineSkipPassResponse)
def create_pass_at_venue(venue_id: UUID, payload: LineSkipPassCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to create passes for this venue")
        user_id = payload.user_id or current_user_uuid
        now = datetime.now(timezone.utc)
        purchase_date = payload.purchase_date or now.date()
        p = LineSkipPass(
            user_id=user_id,
            venue_id=venue_id,
            purchase_date=purchase_date,
            status=payload.status,
            price=payload.price,
            created_at=now,
            pass_type=payload.pass_type,
            free_item_claimed=payload.free_item_claimed or False
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create pass error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/passes/venue/{venue_id}", response_model=List[LineSkipPassResponse])
def get_passes_at_venue(venue_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to view passes for this venue")
        passes = db.query(LineSkipPass).filter(LineSkipPass.venue_id == venue_id).order_by(LineSkipPass.created_at.desc()).all()
        return passes
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get passes error: {e}")
        raise HTTPException(status_code=400, detail=str(e))