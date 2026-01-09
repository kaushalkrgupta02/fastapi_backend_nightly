# routes/admin.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import UUID
import uuid as uuid_module
import logging

from core.get_db import get_db
from core.auth_middleware import get_current_user
from models.venue import Venue, VenueType
from models.auth import UserRole, StaffProfile, AppRole
from routes.venue import VenueTypeCreate, VenueTypeResponse, VenueResponse, VenueCreate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# --- Helpers ---
def is_admin(db: Session, user_uuid: UUID) -> bool:
    ur = db.query(UserRole).filter(UserRole.user_id == user_uuid).one_or_none()
    return ur and ur.role == AppRole.admin


def is_venue_manager(db: Session, user_uuid: UUID, venue_id: UUID) -> bool:
    return db.query(StaffProfile).filter(
        StaffProfile.user_id == user_uuid, StaffProfile.venue_id == venue_id
    ).one_or_none() is not None


# --- Endpoints ---
@router.get("/venues", response_model=List[VenueResponse])
def get_all_venues(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        # print(current_user)
        if not (is_admin(db, current_user_uuid) or db.query(StaffProfile).filter(StaffProfile.user_id == current_user_uuid).one_or_none()):
            raise HTTPException(status_code=403, detail="Only admins/venue_manager can view all venues")

        venues = db.query(Venue).all()
        return venues

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get all venues error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    
    
@router.get("/venues_by_id/{venue_id}", response_model=VenueCreate)
def get_all_venues_by_id(venue_id: UUID, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    #Get venue by ID (admin only)

    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        if not is_admin(db, current_user_uuid):
            raise HTTPException(status_code=403, detail="Only admins can view venue by ID")

        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        return venue

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get venue by ID error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/venue_types", response_model=VenueTypeResponse)
def create_venue_type(payload: VenueTypeCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create a venue type (admin only)
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        if not is_admin(db, current_user_uuid):
            raise HTTPException(status_code=403, detail="Only admins can create venue types")

        exists = db.query(VenueType).filter(VenueType.name == payload.name).one_or_none()
        if exists:
            raise HTTPException(status_code=400, detail="Venue type name already exists")

        vt = VenueType(name=payload.name, description=payload.description)
        db.add(vt)
        db.commit()
        db.refresh(vt)
        return vt

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create venue type error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/venue_types", response_model=List[VenueTypeResponse])
def list_venue_types(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    List venue types (admin only)
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        if not is_admin(db, current_user_uuid):
            raise HTTPException(status_code=403, detail="Only admins can list venue types")

        return db.query(VenueType).order_by(VenueType.created_at.desc()).all()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List venue types error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


class AssignVenueTypePayload(BaseModel):
    venue_id: UUID
    venue_type_id: UUID


@router.post("/assign_venue_type", response_model=VenueResponse)
def assign_venue_type(payload: AssignVenueTypePayload, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Assign a venue type to a venue (admin or venue manager)
    """
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        if not (is_admin(db, current_user_uuid) or is_venue_manager(db, current_user_uuid, payload.venue_id)):
            raise HTTPException(status_code=403, detail="Not authorized to assign venue type")

        venue = db.query(Venue).filter(Venue.id == payload.venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        vt = db.query(VenueType).filter(VenueType.id == payload.venue_type_id).one_or_none()
        if not vt:
            raise HTTPException(status_code=404, detail="Venue type not found")

        venue.venue_type_id = payload.venue_type_id
        db.commit()
        db.refresh(venue)
        return venue

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Assign venue type error: {e}")
        raise HTTPException(status_code=400, detail=str(e))