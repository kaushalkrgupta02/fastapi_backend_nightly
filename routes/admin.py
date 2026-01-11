# routes/admin.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
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
        if not (is_admin(db, current_user_uuid)):
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


# --- Admin bookings endpoints (replace edge functions) ---
class AdminBookingResponse(BaseModel):
    id: UUID
    user_id: UUID
    venue_id: UUID
    booking_date: str
    booking_reference: str | None = None
    party_size: int
    arrival_window: str | None = None
    special_requests: str | None = None
    status: str
    created_at: str
    venue: dict | None = None


@router.get("/bookings", response_model=List[AdminBookingResponse])
def get_admin_bookings(venue_id: UUID | None = None, start_date: str | None = None, end_date: str | None = None, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """List bookings for admin or venue manager. If venue_id is not provided, only admins can call this."""
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        # If no venue_id, require admin
        if not venue_id and not is_admin(db, current_user_uuid):
            raise HTTPException(status_code=403, detail="Only admins can view all bookings")

        # If venue_id provided, allow admin or venue manager
        if venue_id and not (is_admin(db, current_user_uuid) or is_venue_manager(db, current_user_uuid, venue_id)):
            raise HTTPException(status_code=403, detail="Not authorized to view bookings for this venue")

        # Build query
        sql = """
            SELECT b.id, b.user_id, b.venue_id, b.booking_date, b.booking_reference, b.party_size, b.arrival_window, b.special_requests, b.status, b.created_at, v.id as venue_id, v.name as venue_name
            FROM bookings b
            LEFT JOIN venues v ON b.venue_id = v.id
            WHERE 1=1
        """
        params = {}
        if venue_id:
            sql += " AND b.venue_id = :venue_id"
            params["venue_id"] = str(venue_id)
        if start_date:
            sql += " AND b.booking_date::date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            sql += " AND b.booking_date::date <= :end_date"
            params["end_date"] = end_date

        sql += " ORDER BY b.booking_date DESC, b.created_at DESC"

        result = db.execute(text(sql), params)
        rows = result.fetchall()

        bookings = []
        for r in rows:
            venue = {"id": r[10], "name": r[11]} if r[10] else None
            bookings.append({
                "id": r[0],
                "user_id": r[1],
                "venue_id": r[2],
                "booking_date": r[3].isoformat() if hasattr(r[3], 'isoformat') else str(r[3]),
                "booking_reference": r[4],
                "party_size": r[5],
                "arrival_window": r[6],
                "special_requests": r[7],
                "status": r[8],
                "created_at": r[9].isoformat() if hasattr(r[9], 'isoformat') else str(r[9]),
                "venue": venue
            })

        return bookings

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get admin bookings error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


class UpdateBookingStatusPayload(BaseModel):
    status: str


@router.post("/bookings/{booking_id}/status")
def update_booking_status(booking_id: UUID, payload: UpdateBookingStatusPayload, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update booking status (admin or venue manager for that booking's venue)"""
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        # fetch booking to find venue
        row = db.execute("SELECT venue_id FROM bookings WHERE id = :id", {"id": str(booking_id)}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Booking not found")
        booking_venue_id = row[0]

        if not (is_admin(db, current_user_uuid) or is_venue_manager(db, current_user_uuid, booking_venue_id)):
            raise HTTPException(status_code=403, detail="Not authorized to update booking status")

        db.execute("UPDATE bookings SET status = :status WHERE id = :id", {"status": payload.status, "id": str(booking_id)})
        db.commit()

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Update booking status error: {e}")
        raise HTTPException(status_code=400, detail=str(e))