from sqlalchemy import Column, String, Text, JSON, DateTime, Date, Boolean, Integer, ForeignKey, Numeric, ARRAY, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.get_db import Base
from sqlalchemy import func
import uuid

class Venue(Base):
    __tablename__ = "venues"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    venue_type_id = Column(UUID(as_uuid=True), ForeignKey("venue_types.id"), nullable=True)
    status = Column(Text, nullable=False, default="perfect")
    has_cover = Column(Boolean, nullable=False, default=False)
    supports_booking = Column(Boolean, nullable=False, default=False)
    booking_mode = Column(Text, nullable=False, default="none")
    description = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    whatsapp = Column(Text, nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    opening_hours = Column(Text, nullable=True)  # JSONB, use Text for now
    cover_image_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    amenities = Column(ARRAY(Text), nullable=True, default=[])
    venue_notes = Column(Text, nullable=True)
    min_spend = Column(Text, nullable=True)
    crowd_trend = Column(Text, nullable=True, default="steady")
    line_skip_enabled = Column(Boolean, nullable=False, default=False)
    line_skip_price = Column(Numeric, nullable=True)
    line_skip_daily_limit = Column(Integer, nullable=True)
    line_skip_sold_count = Column(Integer, nullable=False, default=0)
    line_skip_valid_until = Column(Text, nullable=True)
    external_id = Column(Text, nullable=True)
    external_source = Column(Text, nullable=True, default="manual")
    has_promo = Column(Boolean, nullable=False, default=False)
    promo_type = Column(Text, nullable=True)
    promo_description = Column(Text, nullable=True)
    promo_valid_until = Column(DateTime(timezone=True), nullable=True)
    show_arrival_window = Column(Boolean, nullable=False, default=True)
    allow_special_requests = Column(Boolean, nullable=False, default=True)
    min_party_size = Column(Integer, nullable=True, default=1)
    max_party_size = Column(Integer, nullable=True, default=20)
    max_bookings_per_night = Column(Integer, nullable=True)
    total_tables = Column(Integer, nullable=True, default=10)
    seats_per_table = Column(Integer, nullable=True, default=4)
    total_capacity = Column(Integer, nullable=True, default=40)
    entry_pass_enabled = Column(Boolean, nullable=False, default=False)
    entry_pass_price = Column(Numeric, nullable=True)
    entry_pass_daily_limit = Column(Integer, nullable=True)
    entry_pass_sold_count = Column(Integer, nullable=False, default=0)
    vip_pass_enabled = Column(Boolean, nullable=False, default=False)
    vip_pass_price = Column(Numeric, nullable=True)
    vip_pass_daily_limit = Column(Integer, nullable=True)
    vip_pass_sold_count = Column(Integer, nullable=False, default=0)
    vip_pass_free_item = Column(Text, nullable=True)
    stripe_account_id = Column(Text, nullable=True)
    payout_enabled = Column(Boolean, nullable=True, default=False)
    deposit_enabled = Column(Boolean, nullable=True, default=False)
    deposit_amount = Column(Numeric, nullable=True, default=0)
    deposit_percentage = Column(Numeric, nullable=True, default=0)
    no_show_charge_enabled = Column(Boolean, nullable=True, default=False)
    reminder_enabled = Column(Boolean, nullable=True, default=True)
    reminder_24h_enabled = Column(Boolean, nullable=True, default=True)
    reminder_2h_enabled = Column(Boolean, nullable=True, default=True)
    logo_url = Column(Text, nullable=True)

class VenueTable(Base):
    __tablename__ = "venue_tables"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False)
    table_number = Column(Text, nullable=False)
    seats = Column(Integer, nullable=False)
    status = Column(Text, nullable=False)
    location_zone = Column(Text, nullable=True)
    minimum_spend = Column(Numeric, nullable=True)
    notes = Column(Text, nullable=True)
    special_features = Column(ARRAY(Text), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

class VenueType(Base):
    __tablename__ = "venue_types"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<VenueType(id={self.id}, name={self.name})>"


class VenueGuestProfile(Base):
    __tablename__ = "venue_guest_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.user_id"), nullable=True)  # Changed to profiles.user_id
    guest_phone = Column(Text, nullable=True)
    guest_name = Column(Text, nullable=True)
    guest_email = Column(Text, nullable=True)
    dietary_restrictions = Column(ARRAY(Text), nullable=True, default=[])
    preferences = Column(JSON, nullable=True, default={})
    tags = Column(ARRAY(Text), nullable=True, default=[])
    vip_status = Column(Text, nullable=True, default="regular")
    total_visits = Column(Integer, default=0)
    total_spend = Column(Numeric, default=0)
    last_visit_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    def __repr__(self):
        return f"<VenueGuestProfile(id={self.id}, venue_id={self.venue_id}, guest_name={self.guest_name})>"

# --- Packages & Package Items ---
class VenuePackage(Base):
    __tablename__ = "venue_packages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric, nullable=True)
    availability_start = Column(Text, nullable=True)
    availability_end = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    package_type = Column(Text, nullable=False, default="custom")
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    max_quantity = Column(Integer, nullable=True)
    sold_count = Column(Integer, nullable=False, default=0)
    image_url = Column(Text, nullable=True)
    guest_count = Column(Integer, nullable=False, default=1)


class PackageItem(Base):
    __tablename__ = "package_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(UUID(as_uuid=True), ForeignKey("venue_packages.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(Text, nullable=False, default="other")
    item_name = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    redemption_rule = Column(Text, nullable=False, default="once")
    sort_order = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# --- Line skip passes ---
class LineSkipPass(Base):
    __tablename__ = "line_skip_passes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False)
    purchase_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(Text, nullable=False, default="active")
    price = Column(Numeric, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    pass_type = Column(Text, nullable=False, default="entry")
    free_item_claimed = Column(Boolean, nullable=False, default=False)


# --- Package purchases ---
class PackagePurchase(Base):
    __tablename__ = "package_purchases"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(UUID(as_uuid=True), ForeignKey("venue_packages.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    venue_id = Column(UUID(as_uuid=True), nullable=False)
    qr_code = Column(Text, nullable=False, unique=True)
    status = Column(Text, nullable=False, default="active")
    purchased_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    guest_name = Column(Text, nullable=True)
    guest_phone = Column(Text, nullable=True)
    guest_count = Column(Integer, nullable=True, default=1)
    total_paid = Column(Numeric, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PackageRedemption(Base):
    __tablename__ = "package_redemptions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_id = Column(UUID(as_uuid=True), ForeignKey("package_purchases.id"), nullable=False)
    package_item_id = Column(UUID(as_uuid=True), ForeignKey("package_items.id"), nullable=False)
    quantity_redeemed = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# --- Promos & Promo Analytics ---
class Promo(Base):
    __tablename__ = "promos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    subtitle = Column(Text, nullable=True)
    image_url = Column(Text, nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ends_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    deep_link = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=True)

    # Additional metadata fields from Supabase schema
    promo_category = Column(Text, nullable=True, server_default=text("'general'::text"))
    discount_type = Column(Text, nullable=True)
    discount_value = Column(Numeric, nullable=True)
    target_audience = Column(Text, nullable=True, server_default=text("'all'::text"))
    ai_generated = Column(Boolean, nullable=True, server_default=text('false'))
    predicted_impact = Column(JSON, nullable=True, server_default=text("'{}'::jsonb"))
    min_party_size = Column(Integer, nullable=True)
    max_redemptions = Column(Integer, nullable=True)
    current_redemptions = Column(Integer, nullable=True, default=0)
    promo_code = Column(Text, nullable=True)
    terms_conditions = Column(Text, nullable=True)
    target_segments = Column(ARRAY(Text), nullable=True, default=list)
    promo_tier = Column(Text, nullable=True, server_default=text("'basic'::text"))
    created_by_role = Column(Text, nullable=True)
    commission_rate = Column(Numeric, nullable=True, server_default=text('0.15'))
    boost_spend = Column(Numeric, nullable=True, server_default=text('0'))
    published_platforms = Column(ARRAY(Text), nullable=True, default=lambda: ['app'])

    def __repr__(self):
        return f"<Promo(id={self.id}, title={self.title})>"


class PromoAnalytics(Base):
    __tablename__ = "promo_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    promo_id = Column(UUID(as_uuid=True), ForeignKey("promos.id"), nullable=False)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=True)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    redemptions = Column(Integer, nullable=False, default=0)
    revenue_generated = Column(Numeric, nullable=True, server_default=text('0'))

    # Note: conversion_rate is generated by Supabase/DATABASE as a stored column; do not define it here to avoid overwriting DB behavior.
    recorded_date = Column(Date, nullable=False, server_default=text('CURRENT_DATE'))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<PromoAnalytics(id={self.id}, promo_id={self.promo_id}, recorded_date={self.recorded_date})>"