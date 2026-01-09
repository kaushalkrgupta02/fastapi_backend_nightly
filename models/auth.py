from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.get_db import Base
import uuid
import enum
from datetime import datetime


class AppRole(str, enum.Enum):
    """User roles in the application"""
    admin = "admin"
    venue_manager = "venue_manager"
    manager = "manager"
    reception = "reception"
    kitchen = "kitchen"
    waitress = "waitress"
    bar = "bar"
    guest = "guest"
    user = 'user'
    


class Profile(Base):
    """User profile information"""
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    phone = Column(Text, nullable=True)
    display_name = Column(Text, nullable=True)
    avatar_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    language = Column(String(5), nullable=True, default="en")
    is_member = Column(Boolean, nullable=False, default=False)
    membership_tier = Column(String(50), nullable=False, default="Member")
    points_balance = Column(Integer, nullable=False, default=0)
    membership_renews_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships - join on user_id
    user_roles = relationship("UserRole", foreign_keys="UserRole.user_id", primaryjoin="Profile.user_id == UserRole.user_id", back_populates="profile")

    def __repr__(self):
        return f"<Profile(id={self.id}, user_id={self.user_id}, display_name={self.display_name})>"


class UserRole(Base):
    """User roles mapping"""
    __tablename__ = "user_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(Enum(AppRole), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    profile = relationship("Profile", foreign_keys="UserRole.user_id", primaryjoin="Profile.user_id == UserRole.user_id", back_populates="user_roles")

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role={self.role})>"
    
class StaffProfile(Base):
    """Staff profile information"""
    __tablename__ = "staff_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id"), nullable=False, unique=True)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False)
    display_name = Column(Text, nullable=False)
    avatar_url = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<StaffProfile(id={self.id}, user_id={self.user_id}, venue_id={self.venue_id}, display_name={self.display_name})>"
