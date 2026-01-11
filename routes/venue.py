from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from datetime import datetime, date, timezone
from sqlalchemy.orm import Session
from sqlalchemy import cast, String, func, or_
import re
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from core.get_db import get_db
from core.auth_middleware import get_current_user
from core.supabase_client import get_supabase
from models.venue import Venue, VenueTable,VenueGuestProfile
from models.auth import Profile, UserRole, StaffProfile, AppRole
from models.venue import Venue, VenueTable, VenueGuestProfile, VenuePackage, PackageItem, LineSkipPass, PackagePurchase, PackageRedemption, Promo, PromoAnalytics
import uuid as uuid_module
import logging
import os

# Allow overriding the Supabase bucket name via environment variable
SUPABASE_BUCKET_NAME = os.getenv('SUPABASE_BUCKET_NAME', 'venue_logo')

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/venues", tags=["Venues"])
logger.info("Venue router loaded")


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
        


class LogoUploadResponse(BaseModel):
    file_url: str


@router.post("/{venue_id}/logo", response_model=LogoUploadResponse)
async def upload_venue_logo(
    venue_id: UUID,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload venue logo to Supabase storage and update venue cover_image_url and logo_url
    """
    try:
        # Auth check: only admins or staff for this venue may upload
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        venue = db.query(Venue).filter(Venue.id == venue_id).first()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        user_role = db.query(UserRole).filter(UserRole.user_id == current_user_uuid).first()
        is_admin = (user_role.role == AppRole.admin) if user_role else False
        is_venue_manager = db.query(StaffProfile).filter(
            StaffProfile.user_id == current_user_uuid,
            StaffProfile.venue_id == venue_id
        ).first() is not None

        if not (is_admin or is_venue_manager):
            raise HTTPException(status_code=403, detail="Not authorized to update venue logo")

        # Validate file
        logger.debug(f"Using Supabase bucket: {SUPABASE_BUCKET_NAME}")
        if not (file.content_type and file.content_type.startswith("image/")):
            raise HTTPException(status_code=400, detail="File must be an image")

        contents = await file.read()
        if len(contents) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File must be under 2MB")

        # Prefer admin client for storage operations when available
        admin_supabase = None
        try:
            from core.supabase_client import get_supabase_admin
            admin_supabase = get_supabase_admin()
        except Exception:
            admin_supabase = None

        supabase = admin_supabase or get_supabase()
        if not admin_supabase:
            logger.warning("No SUPABASE_SERVICE_ROLE_KEY set; storage operations may be blocked by row-level security policies")

        file_ext = (file.filename.split('.')[-1] if file.filename and '.' in file.filename else 'jpg')
        file_name = f"{venue_id}-logo-{int(datetime.now().timestamp()*1000)}.{file_ext}"

        try:
            # upload - handle different client response shapes
            upload_resp = supabase.storage.from_(SUPABASE_BUCKET_NAME).upload(file_name, contents)
            logger.debug(f"Supabase upload response: {upload_resp}")
            # check response for an error key (some clients return dict with 'error')
            if isinstance(upload_resp, dict) and upload_resp.get('error'):
                logger.error(f"Supabase returned error during upload: {upload_resp.get('error')}")
                raise HTTPException(status_code=500, detail="Failed to upload file")
        except Exception as e:
            logger.error(f"Supabase upload error: {e}")
            # Try to detect RLS / unauthorized errors and provide actionable message
            msg = str(e)
            if (isinstance(e, dict) and e.get('statusCode') == 403) or 'row-level' in msg.lower() or 'unauthorized' in msg.lower():
                logger.error("Upload blocked by row-level security or unauthorized. Ensure we have a service role key or correct bucket policies.")
                raise HTTPException(status_code=403, detail=(f"Upload blocked by storage row-level security or unauthorized access. "
                                                              f"Please set SUPABASE_SERVICE_ROLE_KEY in the server environment or update the bucket '{SUPABASE_BUCKET_NAME}' policies to allow authenticated inserts."))

            # Try to detect a missing bucket and attempt to create it if possible
            if 'Bucket not found' in msg or 'bucket not found' in msg.lower():
                logger.info(f"Bucket '{SUPABASE_BUCKET_NAME}' missing. Attempting to create it.")
                try:
                    # Some clients expose create_bucket directly
                    if hasattr(supabase.storage, 'create_bucket'):
                        create_resp = None
                        try:
                            # Try simple signature first
                            create_resp = supabase.storage.create_bucket(SUPABASE_BUCKET_NAME)
                        except TypeError as te:
                            logger.debug(f"create_bucket TypeError (simple): {te}, trying alternate signatures")
                            try:
                                # Some client versions accept an options dict
                                create_resp = supabase.storage.create_bucket(SUPABASE_BUCKET_NAME, {'public': True})
                            except TypeError as te2:
                                logger.debug(f"create_bucket TypeError (options dict): {te2}, trying is_public kwarg")
                                try:
                                    # Other clients may accept is_public kwarg
                                    create_resp = supabase.storage.create_bucket(SUPABASE_BUCKET_NAME, is_public=True)
                                except Exception as ex:
                                    logger.debug(f"Alternate create_bucket attempts failed: {ex}")
                                    raise
                        except Exception as e_create:
                            logger.debug(f"create_bucket threw: {e_create}")
                            raise

                        logger.debug(f"Create bucket response: {create_resp}")
                        if isinstance(create_resp, dict) and create_resp.get('error'):
                            logger.error(f"Create bucket returned error: {create_resp}")
                            raise Exception("Create bucket failed")
                    else:
                        # If method not available, attempt REST call via client
                        try:
                            create_resp = supabase.post('/storage/v1/bucket', json={'id': SUPABASE_BUCKET_NAME, 'public': True})
                            logger.debug(f"Create bucket via REST response: {create_resp}")
                        except Exception as re:
                            logger.debug(f"REST-based create bucket attempt failed: {re}")
                            raise

                    # Retry upload once after creating bucket
                    upload_resp = supabase.storage.from_(SUPABASE_BUCKET_NAME).upload(file_name, contents)
                    logger.debug(f"Supabase upload response after create: {upload_resp}")
                    if isinstance(upload_resp, dict) and upload_resp.get('error'):
                        logger.error(f"Supabase returned error during upload after create: {upload_resp.get('error')}")
                        raise HTTPException(status_code=500, detail="Failed to upload file after creating bucket")
                except HTTPException:
                    raise
                except Exception as e2:
                    logger.error(f"Failed to create bucket or upload after create: {e2}")
                    raise HTTPException(status_code=500, detail=f"Bucket '{SUPABASE_BUCKET_NAME}' not found and automatic creation failed; please create it in Supabase or provide a service role key with bucket management permissions")
            else:
                raise HTTPException(status_code=500, detail="Failed to upload file")

        # try to get public url
        public_url = None
        try:
            public_resp = supabase.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(file_name)
            # parse common response shapes
            if isinstance(public_resp, dict):
                public_url = public_resp.get('data', {}).get('publicUrl') or public_resp.get('data', {}).get('public_url') or public_resp.get('data', {}).get('publicURL') or public_resp.get('public_url') or public_resp.get('publicUrl') or public_resp.get('publicURL')
            else:
                data = getattr(public_resp, 'data', None)
                if isinstance(data, dict):
                    public_url = data.get('publicUrl') or data.get('public_url') or data.get('publicURL')
                else:
                    public_url = getattr(public_resp, 'public_url', None) or getattr(public_resp, 'publicUrl', None) or getattr(public_resp, 'publicURL', None)

            # If no public url returned, try creating a signed URL with admin client (if available)
            if not public_url:
                logger.debug("get_public_url returned no url; attempting to generate a signed URL via admin client")
                try:
                    admin_supabase = get_supabase_admin()
                except Exception:
                    admin_supabase = None

                if admin_supabase:
                    try:
                        # try common signatures for create_signed_url
                        signed_resp = None
                        try:
                            signed_resp = admin_supabase.storage.from_(SUPABASE_BUCKET_NAME).create_signed_url(file_name, 60*60*24*7)
                        except TypeError:
                            signed_resp = admin_supabase.storage.from_(SUPABASE_BUCKET_NAME).create_signed_url(file_name, expires_in=60*60*24*7)

                        logger.debug(f"Signed URL response: {signed_resp}")
                        if isinstance(signed_resp, dict):
                            public_url = (signed_resp.get('data') or {}).get('signedUrl') or (signed_resp.get('data') or {}).get('signed_url') or signed_resp.get('signed_url') or signed_resp.get('signedUrl')
                        else:
                            data = getattr(signed_resp, 'data', None)
                            if isinstance(data, dict):
                                public_url = data.get('signedUrl') or data.get('signed_url')
                            else:
                                public_url = getattr(signed_resp, 'signed_url', None) or getattr(signed_resp, 'signedUrl', None)

                    except Exception as e:
                        logger.debug(f"create_signed_url failed: {e}")

                # fallback to constructed public url if we can guess base url
                if not public_url:
                    base_url = getattr(supabase, '_url', None)
                    if base_url:
                        public_url = f"{base_url}/storage/v1/object/public/{SUPABASE_BUCKET_NAME}/{file_name}"
        except Exception as e:
            logger.error(f"Supabase get public url error: {e}")

        if not public_url:
            raise HTTPException(status_code=500, detail=(f"Failed to get public URL for uploaded file. Ensure bucket '{SUPABASE_BUCKET_NAME}' is public or set SUPABASE_SERVICE_ROLE_KEY to generate signed URLs."))

        # Update venue record
        venue.cover_image_url = public_url
        venue.logo_url = public_url
        db.add(venue)
        db.commit()

        return {"file_url": public_url}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Upload venue logo error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


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


# --- Package purchases schemas ---
class PackagePurchaseCreate(BaseModel):
    user_id: Optional[UUID] = None
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_count: Optional[int] = 1
    expires_at: Optional[datetime] = None
    total_paid: Optional[float] = None
    status: Optional[str] = None

class PackagePurchaseResponse(PackagePurchaseCreate):
    id: UUID
    package_id: UUID
    venue_id: UUID
    qr_code: str
    status: str
    purchased_at: datetime
    created_at: datetime
    updated_at: datetime
    package: Optional[VenuePackageCreate] = None
    items: Optional[list] = None

    class Config:
        from_attributes = True


# --- Promo schemas ---
class PromoResponse(BaseModel):
    id: UUID
    venue_id: UUID
    title: str
    subtitle: Optional[str] = None
    promo_code: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    current_redemptions: Optional[int] = None
    max_redemptions: Optional[int] = None
    ends_at: Optional[datetime] = None
    image_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PromoAnalyticsResponse(BaseModel):
    id: UUID
    promo_id: UUID
    venue_id: UUID
    recorded_date: datetime
    impressions: int = 0
    clicks: int = 0
    redemptions: int = 0
    revenue_generated: Optional[float] = None
    details: Optional[dict] = None
    promo: Optional[dict] = None  # nested promo: {id, title, is_active}

    class Config:
        from_attributes = True


def generate_qr_code() -> str:
    # Simple QR code generator (PKG-XXXXXXXX)
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    code = 'PKG-'
    import random
    for i in range(8):
        code += random.choice(chars)
    return code


# --- Passes schemas ---
class VenueShort(BaseModel):
    id: UUID
    name: Optional[str] = None
    cover_image_url: Optional[str] = None
    vip_pass_free_item: Optional[str] = None

    class Config:
        from_attributes = True

class ProfileShort(BaseModel):
    display_name: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True

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
    venue: Optional[VenueShort] = None
    profile: Optional[ProfileShort] = None

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
        if not _can_manage_staff(db, current_user_uuid, staff_data.venue_id):
            raise HTTPException(
                status_code=403,
                detail="You must be admin or venue manager to create staff profiles"
            )

        
        # Check if user exists in profiles table
        user_profile = db.query(Profile).filter(Profile.user_id == staff_data.user_id).first()
        if not user_profile:
            raise HTTPException(status_code=404, detail="User not found in profiles")
        
        # Check if staff profile already exists for this user (any venue)
        existing_staff_any = db.query(StaffProfile).filter(StaffProfile.user_id == staff_data.user_id).first()
        if existing_staff_any:
            # If it's the same venue, it's a duplicate; if different, prevent reassignment through this endpoint
            if existing_staff_any.venue_id == staff_data.venue_id:
                raise HTTPException(status_code=400, detail="Staff profile already exists for this user at this venue")
            else:
                raise HTTPException(status_code=400, detail="User already assigned as staff to another venue")

        # Determine role - default to "reception"
        role_to_assign = staff_data.role if staff_data.role else "reception"

        # Validate role
        valid_roles = [r.value for r in AppRole]
        if role_to_assign not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")

        # Only admins can assign 'admin' or 'venue_manager' roles
        if role_to_assign in [AppRole.admin.value, AppRole.venue_manager.value] and not _is_admin(current_user_uuid, db):
            raise HTTPException(status_code=403, detail="Only admins can assign admin or venue_manager roles")
        
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
            # Update existing role (only change to permitted roles by admin)
            user_role.role = AppRole(role_to_assign)
        else:
            # Create new role
            user_role = UserRole(
                user_id=staff_data.user_id,
                role=AppRole(role_to_assign)
            )
            db.add(user_role)

        db.add(staff_profile)
        db.commit()
        db.refresh(staff_profile)

        return {
            **staff_profile.__dict__,
            "role": user_role.role.value if user_role else None
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
        
        is_admin = (user_role.role == AppRole.admin) if user_role else False
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


@router.patch("/staff/{staff_id}", response_model=StaffProfileResponse)
def update_staff_profile(
    staff_id: UUID,
    update_data: StaffProfileUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update staff profile details and role
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        staff = db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff profile not found")

        # Authorization: admin or venue_manager for this venue
        if not _can_manage_staff(db, current_user_uuid, staff.venue_id):
            raise HTTPException(status_code=403, detail="Not authorized to update this staff")

        # Update fields
        if update_data.display_name:
            staff.display_name = update_data.display_name
        if update_data.avatar_url:
            staff.avatar_url = update_data.avatar_url
        if update_data.phone:
            staff.phone = update_data.phone
        if update_data.is_active is not None:
            staff.is_active = update_data.is_active

        # Update role if provided
        if update_data.role:
            valid_roles = [r.value for r in AppRole]
            if update_data.role not in valid_roles:
                raise HTTPException(status_code=400, detail=f"Invalid role: {update_data.role}")

            # Only admins can assign 'admin' or 'venue_manager'
            if update_data.role in [AppRole.admin.value, AppRole.venue_manager.value] and not _is_admin(current_user_uuid, db):
                raise HTTPException(status_code=403, detail="Only admins can assign admin or venue_manager roles")

            user_role = db.query(UserRole).filter(UserRole.user_id == staff.user_id).first()
            if user_role:
                user_role.role = AppRole(update_data.role)
            else:
                user_role = UserRole(
                    user_id=staff.user_id,
                    role=AppRole(update_data.role)
                )
                db.add(user_role)

        db.commit()
        db.refresh(staff)

        user_role = db.query(UserRole).filter(UserRole.user_id == staff.user_id).first()
        return {
            **staff.__dict__,
            "role": user_role.role.value if user_role else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Update staff error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


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
        
        # Authorization: admin or venue_manager for this venue
        if not _can_manage_staff(db, current_user_uuid, staff.venue_id):
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
        is_admin = (user_role.role == AppRole.admin) if user_role else False
        
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

    is_admin = (user_role.role == AppRole.admin) if user_role else False

    # User is venue staff for the requested venue
    is_venue_staff = db.query(StaffProfile).filter(
        StaffProfile.user_id == user_id,
        StaffProfile.venue_id == venue_id
    ).first() is not None

    # User has a global venue_manager role and a staff profile for this venue
    is_venue_manager = False
    if user_role and user_role.role == AppRole.venue_manager:
        # ensure they are assigned to this venue as staff
        is_venue_manager = is_venue_staff

    if not (is_admin or is_venue_staff or is_venue_manager):
        raise HTTPException(status_code=403, detail=error_message)


# Helper to check admin
def _is_admin(user_id: UUID, db: Session) -> bool:
    user_role = db.query(UserRole).filter(UserRole.user_id == user_id).one_or_none()
    return True if (user_role and user_role.role == AppRole.admin) else False


# Helper to check venue manager for a specific venue
def _is_venue_manager_for(db: Session, user_id: UUID, venue_id: UUID) -> bool:
    user_role = db.query(UserRole).filter(UserRole.user_id == user_id).one_or_none()
    if not user_role or user_role.role != AppRole.venue_manager:
        return False
    staff = db.query(StaffProfile).filter(StaffProfile.user_id == user_id, StaffProfile.venue_id == venue_id).one_or_none()
    return staff is not None


def _can_manage_staff(db: Session, current_user_id: UUID, venue_id: UUID) -> bool:
    return _is_admin(current_user_id, db) or _is_venue_manager_for(db, current_user_id, venue_id)


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

        # Attach items for each package
        for pkg in packages:
            items = db.query(PackageItem).filter(PackageItem.package_id == pkg.id).order_by(PackageItem.sort_order.asc()).all()
            setattr(pkg, 'items', items)

        return packages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get packages error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# --- Promo endpoints ---
@router.get("/promos/venue/{venue_id}", response_model=List[PromoResponse])
def get_promos_at_venue(venue_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to view promos for this venue")
        promos = db.query(Promo).filter(Promo.venue_id == venue_id).order_by(Promo.created_at.desc()).all()
        logger.debug("get_promos_at_venue: venue=%s count=%d", str(venue_id), len(promos))
        return promos
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get promos error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/promos/search", response_model=List[PromoResponse])
def search_promos(term: Optional[str] = None, venue_id: Optional[UUID] = None, is_active: Optional[bool] = None, ends_at_gte: Optional[datetime] = None, limit: Optional[int] = 50, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Search promos with filters similar to Supabase: term matches promo_code (ilike) or id, filter by venue_id, is_active and ends_at >="""
    try:
        # If venue_id provided, verify access
        if venue_id:
            current_user_uuid = uuid_module.UUID(current_user["sub"])
            venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
            if not venue:
                raise HTTPException(status_code=404, detail="Venue not found")
            assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to search promos for this venue")

        query = db.query(Promo)

        if venue_id:
            query = query.filter(Promo.venue_id == venue_id)
        if is_active is not None:
            query = query.filter(Promo.is_active == is_active)
        if ends_at_gte is not None:
            query = query.filter(Promo.ends_at >= ends_at_gte)

        if term:
            t_like = f"%{term}%"
            # try interpret term as uuid
            try:
                term_uuid = uuid_module.UUID(term)
                query = query.filter(or_(Promo.promo_code.ilike(t_like), Promo.id == term_uuid))
            except Exception:
                query = query.filter(or_(Promo.promo_code.ilike(t_like), Promo.title.ilike(t_like), Promo.subtitle.ilike(t_like)))

        promos = query.order_by(Promo.created_at.desc()).limit(limit).all()
        logger.debug("search_promos: venue=%s term=%s is_active=%s ends_at_gte=%s count=%d", str(venue_id), term, str(is_active), str(ends_at_gte), len(promos))
        return promos
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search promos error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get('/promos/{promo_id}', response_model=PromoResponse)
def get_promo(promo_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        p = db.query(Promo).filter(Promo.id == promo_id).one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail='Promo not found')
        current_user_uuid = uuid_module.UUID(current_user['sub'])
        assert_venue_access(db, current_user_uuid, p.venue_id, 'Not authorized to view this promo')
        return p
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get promo error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/promo-analytics/venue/{venue_id}", response_model=List[PromoAnalyticsResponse])
def get_promo_analytics_at_venue(venue_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to view promo analytics for this venue")

        rows = db.query(PromoAnalytics).filter(PromoAnalytics.venue_id == venue_id).order_by(PromoAnalytics.recorded_date.desc()).all()
        logger.debug("get_promo_analytics_at_venue: venue=%s count=%d", str(venue_id), len(rows))

        result = []
        for r in rows:
            promo = db.query(Promo).filter(Promo.id == r.promo_id).one_or_none()
            promo_obj = None
            if promo:
                promo_obj = {
                    'id': promo.id,
                    'title': promo.title,
                    'is_active': promo.is_active
                }
            setattr(r, 'promo', promo_obj)
            result.append(r)

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get promo analytics error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# --- Package purchases endpoints ---
@router.get("/packages/purchases/venue/{venue_id}", response_model=List[PackagePurchaseResponse])
def get_package_purchases_at_venue(venue_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None, preset: Optional[str] = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to view package purchases for this venue")

        # If a preset (today|week|month|year|all) is provided and explicit start/end are not, compute them server-side
        if preset and not start_date and not end_date:
            from datetime import timedelta
            today = datetime.now(timezone.utc).date()
            p = preset.lower()
            if p == 'today':
                start_date = today
                end_date = today
            elif p == 'week':
                start_of_week = today - timedelta(days=today.weekday())  # week starts on Monday
                end_of_week = start_of_week + timedelta(days=6)
                start_date = start_of_week
                end_date = end_of_week
            elif p == 'month':
                start_of_month = today.replace(day=1)
                next_month = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)
                last_day = next_month - timedelta(days=1)
                start_date = start_of_month
                end_date = last_day
            elif p == 'year':
                start_date = today.replace(month=1, day=1)
                end_date = today.replace(month=12, day=31)
            elif p == 'all':
                start_date = None
                end_date = None
            else:
                raise HTTPException(status_code=400, detail="Invalid preset value. Supported: today, week, month, year, all")

        query = db.query(PackagePurchase).filter(PackagePurchase.venue_id == venue_id)

        if start_date:
            start_dt = datetime.combine(start_date, __import__('datetime').time.min).replace(tzinfo=timezone.utc)
            query = query.filter(PackagePurchase.purchased_at >= start_dt)
        if end_date:
            end_dt = datetime.combine(end_date, __import__('datetime').time.max).replace(tzinfo=timezone.utc)
            query = query.filter(PackagePurchase.purchased_at <= end_dt)

        purchases = query.order_by(PackagePurchase.purchased_at.desc()).all()

        # Debug log: show filter params, preset and returned count
        logger.debug("get_package_purchases_at_venue: venue=%s preset=%s start=%s end=%s count=%d", str(venue_id), str(preset), str(start_date), str(end_date), len(purchases))

        # Attach package and items with redemption counts for frontend
        result = []
        for p in purchases:
            pkg = db.query(VenuePackage).filter(VenuePackage.id == p.package_id).one_or_none()
            setattr(p, 'package', pkg)

            # Get package items and any redemptions for this purchase
            items = db.query(PackageItem).filter(PackageItem.package_id == p.package_id).order_by(PackageItem.sort_order.asc()).all()
            redemptions = db.query(PackageRedemption).filter(PackageRedemption.purchase_id == p.id).all()
            redemption_map = {}
            for r in redemptions:
                redemption_map.setdefault(str(r.package_item_id), 0)
                redemption_map[str(r.package_item_id)] += r.quantity_redeemed

            items_with_redemptions = []
            for item in items:
                items_with_redemptions.append({
                    'id': item.id,
                    'item_type': item.item_type,
                    'item_name': item.item_name,
                    'quantity': item.quantity,
                    'redemption_rule': item.redemption_rule,
                    'redeemed_count': redemption_map.get(str(item.id), 0),
                })

            setattr(p, 'items', items_with_redemptions)
            result.append(p)

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get package purchases error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/packages/{package_id}/purchases", response_model=PackagePurchaseResponse)
def create_package_purchase(package_id: UUID, payload: PackagePurchaseCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        pkg = db.query(VenuePackage).filter(VenuePackage.id == package_id).one_or_none()
        if not pkg:
            raise HTTPException(status_code=404, detail="Package not found")
        assert_venue_access(db, current_user_uuid, pkg.venue_id, "Not authorized to create purchases for this package")

        # Generate QR code
        qr_code = generate_qr_code() if 'generate_qr_code' in globals() else f"PKG-{uuid_module.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)
        purchase = PackagePurchase(
            package_id=package_id,
            user_id=payload.user_id or None,
            venue_id=pkg.venue_id,
            qr_code=qr_code,
            status='active',
            purchased_at=now,
            expires_at=payload.expires_at,
            guest_name=payload.guest_name,
            guest_phone=payload.guest_phone,
            guest_count=payload.guest_count or 1,
            total_paid=payload.total_paid,
            created_at=now,
            updated_at=now
        )
        db.add(purchase)
        # increment sold_count on package
        pkg.sold_count = (pkg.sold_count or 0) + 1
        db.add(pkg)
        db.commit()
        db.refresh(purchase)

        # attach package and items (serialize items for response)
        setattr(purchase, 'package', pkg)
        items = db.query(PackageItem).filter(PackageItem.package_id == package_id).order_by(PackageItem.sort_order.asc()).all()
        items_with_redemptions = []
        for item in items:
            items_with_redemptions.append({
                'id': item.id,
                'item_type': item.item_type,
                'item_name': item.item_name,
                'quantity': item.quantity,
                'redemption_rule': item.redemption_rule,
                'redeemed_count': 0,
            })
        setattr(purchase, 'items', items_with_redemptions)

        return purchase
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create package purchase error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/packages/purchases/{purchase_id}", response_model=PackagePurchaseResponse)
def update_package_purchase_status(purchase_id: UUID, payload: PackagePurchaseCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        p = db.query(PackagePurchase).filter(PackagePurchase.id == purchase_id).one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Purchase not found")
        assert_venue_access(db, current_user_uuid, p.venue_id, "Not authorized to update this purchase")
        # allow updating status and free fields
        if payload.total_paid is not None:
            p.total_paid = payload.total_paid
        if payload.expires_at is not None:
            p.expires_at = payload.expires_at
        if payload.guest_name is not None:
            p.guest_name = payload.guest_name
        if payload.guest_phone is not None:
            p.guest_phone = payload.guest_phone
        if payload.guest_count is not None:
            p.guest_count = payload.guest_count
        # For status update, client should set status in payload.status but schema doesn't include it; support via optional attr
        if hasattr(payload, 'status') and getattr(payload, 'status') is not None:
            p.status = getattr(payload, 'status')
        db.add(p)
        db.commit()
        db.refresh(p)
        pkg = db.query(VenuePackage).filter(VenuePackage.id == p.package_id).one_or_none()
        if pkg:
            setattr(p, 'package', pkg)
        items = db.query(PackageItem).filter(PackageItem.package_id == p.package_id).order_by(PackageItem.sort_order.asc()).all()
        redemptions = db.query(PackageRedemption).filter(PackageRedemption.purchase_id == p.id).all()
        redemption_map = {}
        for r in redemptions:
            redemption_map.setdefault(str(r.package_item_id), 0)
            redemption_map[str(r.package_item_id)] += r.quantity_redeemed

        items_with_redemptions = []
        for item in items:
            items_with_redemptions.append({
                'id': item.id,
                'item_type': item.item_type,
                'item_name': item.item_name,
                'quantity': item.quantity,
                'redemption_rule': item.redemption_rule,
                'redeemed_count': redemption_map.get(str(item.id), 0),
            })
        setattr(p, 'items', items_with_redemptions)
        return p
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Update package purchase error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/packages/purchases/qr/{qr_code}", response_model=PackagePurchaseResponse)
def find_purchase_by_qr(qr_code: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        qr_clean = qr_code.strip().upper()
        logger.debug("find_purchase_by_qr: lookup qr_raw=%s normalized=%s", qr_code, qr_clean)

        # Prefer normalized exact match (trim + uppercase)
        p = db.query(PackagePurchase).filter(func.upper(func.trim(PackagePurchase.qr_code)) == qr_clean).one_or_none()

        # If not found, try case-insensitive exact (ilike) candidates and pick first
        if not p:
            p_candidates = db.query(PackagePurchase).filter(PackagePurchase.qr_code.ilike(qr_clean)).limit(10).all()
            logger.debug("find_purchase_by_qr: purchase exact candidates for qr %s -> %s", qr_clean, [str(pc.id) + '@' + str(pc.qr_code) for pc in p_candidates])
            p = p_candidates[0] if p_candidates else None

        if not p:
            # If no purchase found, try to resolve PKG-<prefix> codes to a package (fallback)
            m = re.match(r'^PKG-([A-Za-z0-9\-]+)$', qr_clean)
            if m:
                prefix = m.group(1)
                logger.debug("find_purchase_by_qr: no purchase found for qr=%s, trying package fallback with prefix=%s", qr_clean, prefix)

                # Try matching strategies across package.id (start-with, dashless start-with, contains)
                candidates = db.query(VenuePackage).filter(cast(VenuePackage.id, String).ilike(f"{prefix}%")).limit(10).all()
                if not candidates:
                    candidates = db.query(VenuePackage).filter(func.replace(cast(VenuePackage.id, String), '-', '').ilike(f"{prefix}%")).limit(10).all()
                if not candidates:
                    candidates = db.query(VenuePackage).filter(cast(VenuePackage.id, String).ilike(f"%{prefix}%")).limit(10).all()

                logger.debug("find_purchase_by_qr: package candidates for prefix %s -> %s", prefix, [str(c.id) for c in candidates])

                pkg = None
                if candidates:
                    # Prefer package whose id (dashless) starts with the prefix
                    for c in candidates:
                        if str(c.id).lower().replace('-', '').startswith(prefix.lower()):
                            pkg = c
                            break
                    if not pkg:
                        pkg = candidates[0]

                # If no package found by id heuristics, try to find a purchase with qr substring
                if not pkg:
                    current_user_uuid = uuid_module.UUID(current_user["sub"])
                    purchase_candidates = db.query(PackagePurchase).filter(PackagePurchase.qr_code.ilike(f"%{prefix}%")).limit(10).all()
                    logger.debug("find_purchase_by_qr: purchase candidates for prefix %s -> %s", prefix, [str(pc.id) + '@' + str(pc.qr_code) for pc in purchase_candidates])
                    for pc in purchase_candidates:
                        # ensure user has access to that purchase's venue
                        try:
                            assert_venue_access(db, current_user_uuid, pc.venue_id, "Not authorized to view this purchase")
                            # attach package and items then return
                            pkg_for_pc = db.query(VenuePackage).filter(VenuePackage.id == pc.package_id).one_or_none()
                            if pkg_for_pc:
                                setattr(pc, 'package', pkg_for_pc)
                            items = db.query(PackageItem).filter(PackageItem.package_id == pc.package_id).order_by(PackageItem.sort_order.asc()).all()
                            redemptions = db.query(PackageRedemption).filter(PackageRedemption.purchase_id == pc.id).all()
                            redemption_map = {}
                            for r in redemptions:
                                redemption_map.setdefault(str(r.package_item_id), 0)
                                redemption_map[str(r.package_item_id)] += r.quantity_redeemed
                            items_with_redemptions = []
                            for item in items:
                                items_with_redemptions.append({
                                    'id': item.id,
                                    'item_type': item.item_type,
                                    'item_name': item.item_name,
                                    'quantity': item.quantity,
                                    'redemption_rule': item.redemption_rule,
                                    'redeemed_count': redemption_map.get(str(item.id), 0),
                                })
                            setattr(pc, 'items', items_with_redemptions)
                            logger.debug("find_purchase_by_qr: returning purchase candidate %s for qr=%s", str(pc.id), qr_clean)
                            return pc
                        except HTTPException:
                            continue

                # If still not found, try package name contains (use more human-friendly matching)
                if not pkg:
                    name_candidates = db.query(VenuePackage).filter(VenuePackage.name.ilike(f"%{prefix.replace('-', ' ')}%")).limit(10).all()
                    logger.debug("find_purchase_by_qr: package name candidates for prefix %s -> %s", prefix, [str(c.id) + ':' + (c.name or '') for c in name_candidates])
                    if name_candidates:
                        # choose first authorized package
                        current_user_uuid = uuid_module.UUID(current_user["sub"])
                        for npkg in name_candidates:
                            try:
                                assert_venue_access(db, current_user_uuid, npkg.venue_id, "Not authorized to view this purchase")
                                pkg = npkg
                                break
                            except HTTPException:
                                continue

                if pkg:
                    logger.debug("find_purchase_by_qr: returning fallback package %s for qr=%s", str(pkg.id), qr_clean)
                    # enforce access
                    current_user_uuid = uuid_module.UUID(current_user["sub"])
                    assert_venue_access(db, current_user_uuid, pkg.venue_id, "Not authorized to view this purchase")

                    # Build a lightweight purchase-like response based on the package
                    now = datetime.now(timezone.utc)
                    items = db.query(PackageItem).filter(PackageItem.package_id == pkg.id).order_by(PackageItem.sort_order.asc()).all()
                    items_with_redemptions = []
                    for item in items:
                        items_with_redemptions.append({
                            'id': item.id,
                            'item_type': item.item_type,
                            'item_name': item.item_name,
                            'quantity': item.quantity,
                            'redemption_rule': item.redemption_rule,
                            'redeemed_count': 0,
                        })

                    return {
                        'id': pkg.id,  # use package id as a stable id for the fallback
                        'package_id': pkg.id,
                        'venue_id': pkg.venue_id,
                        'qr_code': qr_clean,
                        'status': 'active' if (pkg.sold_count and pkg.sold_count > 0) else 'fully_redeemed',
                        'purchased_at': now,
                        'created_at': pkg.created_at,
                        'updated_at': pkg.updated_at,
                        'package': {
                            'id': pkg.id,
                            'name': pkg.name,
                            'description': pkg.description,
                            'price': pkg.price,
                            'package_type': pkg.package_type,
                        },
                        'items': items_with_redemptions,
                    }
            logger.debug("find_purchase_by_qr: no package matched for qr=%s", qr_clean)
            raise HTTPException(status_code=404, detail="Package purchase not found")
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        assert_venue_access(db, current_user_uuid, p.venue_id, "Not authorized to view this purchase")

        pkg = db.query(VenuePackage).filter(VenuePackage.id == p.package_id).one_or_none()
        setattr(p, 'package', pkg)

        # Get package items and redemptions
        items = db.query(PackageItem).filter(PackageItem.package_id == p.package_id).order_by(PackageItem.sort_order.asc()).all()
        redemptions = db.query(PackageRedemption).filter(PackageRedemption.purchase_id == p.id).all()
        redemption_map = {}
        for r in redemptions:
            redemption_map.setdefault(str(r.package_item_id), 0)
            redemption_map[str(r.package_item_id)] += r.quantity_redeemed

        items_with_redemptions = []
        for item in items:
            items_with_redemptions.append({
                'id': item.id,
                'item_type': item.item_type,
                'item_name': item.item_name,
                'quantity': item.quantity,
                'redemption_rule': item.redemption_rule,
                'redeemed_count': redemption_map.get(str(item.id), 0),
            })

        setattr(p, 'items', items_with_redemptions)
        return p
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Find purchase by QR error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


class PackageRedemptionCreate(BaseModel):
    package_item_id: UUID
    quantity_redeemed: int = 1
    notes: Optional[str] = None


@router.post("/packages/purchases/{purchase_id}/redemptions")
def create_package_redemption(purchase_id: UUID, payload: List[PackageRedemptionCreate], current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Create one or more redemptions for a purchase and update purchase status accordingly"""
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        purchase = db.query(PackagePurchase).filter(PackagePurchase.id == purchase_id).one_or_none()
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")
        assert_venue_access(db, current_user_uuid, purchase.venue_id, "Not authorized to redeem items for this purchase")

        created = []
        now = datetime.now(timezone.utc)
        for item_payload in payload:
            pr = PackageRedemption(
                purchase_id=purchase_id,
                package_item_id=item_payload.package_item_id,
                quantity_redeemed=item_payload.quantity_redeemed,
                created_at=now
            )
            db.add(pr)
            created.append(pr)

        db.commit()

        # After creating redemptions, recalculate purchase status
        _recalculate_purchase_status(purchase_id, db)

        return { 'success': True, 'created': len(created) }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create package redemption error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/packages/purchases/{purchase_id}/redemptions")
def list_package_redemptions(purchase_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        purchase = db.query(PackagePurchase).filter(PackagePurchase.id == purchase_id).one_or_none()
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        assert_venue_access(db, current_user_uuid, purchase.venue_id, "Not authorized to view redemptions for this purchase")
        redemptions = db.query(PackageRedemption).filter(PackageRedemption.purchase_id == purchase_id).order_by(PackageRedemption.created_at.desc()).all()
        return redemptions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List redemptions error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# helper to recalculate purchase status
def _recalculate_purchase_status(purchase_id: UUID, db: Session):
    try:
        purchase = db.query(PackagePurchase).filter(PackagePurchase.id == purchase_id).one_or_none()
        if not purchase:
            return
        items = db.query(PackageItem).filter(PackageItem.package_id == purchase.package_id).all()
        if not items:
            return
        redemptions = db.query(PackageRedemption).filter(PackageRedemption.purchase_id == purchase_id).all()
        redemption_map = {}
        for r in redemptions:
            redemption_map.setdefault(str(r.package_item_id), 0)
            redemption_map[str(r.package_item_id)] += r.quantity_redeemed

        hasPartialRedemption = False
        allFullyRedeemed = True
        for item in items:
            if item.redemption_rule == 'unlimited':
                continue
            redeemed = redemption_map.get(str(item.id), 0)
            if redeemed > 0 and redeemed < item.quantity:
                hasPartialRedemption = True
                allFullyRedeemed = False
            elif redeemed < item.quantity:
                allFullyRedeemed = False

        newStatus = 'active'
        if allFullyRedeemed:
            newStatus = 'fully_redeemed'
        elif hasPartialRedemption or len(redemptions) > 0:
            newStatus = 'partially_redeemed'

        purchase.status = newStatus
        db.add(purchase)
        db.commit()
    except Exception as e:
        logger.error(f"Error recalculating purchase status: {e}")
        db.rollback()


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
def get_passes_at_venue(venue_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to view passes for this venue")

        # Base query
        query = db.query(LineSkipPass).filter(LineSkipPass.venue_id == venue_id)

        # Optional date range filters (purchase_date is a DateTime)
        if start_date:
            start_dt = datetime.combine(start_date, __import__('datetime').time.min).replace(tzinfo=timezone.utc)
            query = query.filter(LineSkipPass.purchase_date >= start_dt)
        if end_date:
            end_dt = datetime.combine(end_date, __import__('datetime').time.max).replace(tzinfo=timezone.utc)
            query = query.filter(LineSkipPass.purchase_date <= end_dt)

        passes = query.order_by(LineSkipPass.created_at.desc()).all()

        # Attach venue and profile info for frontend compatibility
        result = []
        for p in passes:
            prof = None
            if p.user_id:
                prof = db.query(Profile).filter(Profile.user_id == p.user_id).one_or_none()
            v = db.query(Venue).filter(Venue.id == p.venue_id).one_or_none()
            if v:
                setattr(p, 'venue', v)
            if prof:
                setattr(p, 'profile', prof)
            result.append(p)

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get passes error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/passes/{pass_id}", response_model=LineSkipPassResponse)
def get_pass_by_id(pass_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        p = db.query(LineSkipPass).filter(LineSkipPass.id == pass_id).one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Pass not found")
        assert_venue_access(db, current_user_uuid, p.venue_id, "Not authorized to view this pass")

        prof = None
        if p.user_id:
            prof = db.query(Profile).filter(Profile.user_id == p.user_id).one_or_none()
        v = db.query(Venue).filter(Venue.id == p.venue_id).one_or_none()
        if v:
            setattr(p, 'venue', v)
        if prof:
            setattr(p, 'profile', prof)

        return p
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get pass by id error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/passes/{pass_id}/redeem", response_model=LineSkipPassResponse)
def redeem_pass(pass_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        p = db.query(LineSkipPass).filter(LineSkipPass.id == pass_id).one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Pass not found")
        assert_venue_access(db, current_user_uuid, p.venue_id, "Not authorized to redeem this pass")
        p.status = 'used'
        db.add(p)
        db.commit()
        db.refresh(p)

        prof = None
        if p.user_id:
            prof = db.query(Profile).filter(Profile.user_id == p.user_id).one_or_none()
        v = db.query(Venue).filter(Venue.id == p.venue_id).one_or_none()
        if v:
            setattr(p, 'venue', v)
        if prof:
            setattr(p, 'profile', prof)

        return p
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Redeem pass error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/passes/{pass_id}/claim-free-item", response_model=LineSkipPassResponse)
def claim_free_item(pass_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        p = db.query(LineSkipPass).filter(LineSkipPass.id == pass_id).one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Pass not found")
        assert_venue_access(db, current_user_uuid, p.venue_id, "Not authorized to claim free item for this pass")
        p.free_item_claimed = True
        db.add(p)
        db.commit()
        db.refresh(p)

        prof = None
        if p.user_id:
            prof = db.query(Profile).filter(Profile.user_id == p.user_id).one_or_none()
        v = db.query(Venue).filter(Venue.id == p.venue_id).one_or_none()
        if v:
            setattr(p, 'venue', v)
        if prof:
            setattr(p, 'profile', prof)

        return p
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Claim free item error: {e}")
        raise HTTPException(status_code=400, detail=str(e))