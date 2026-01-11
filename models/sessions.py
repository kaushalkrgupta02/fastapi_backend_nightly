from sqlalchemy import Column, Text, DateTime, Integer, Numeric, Boolean, ForeignKey, JSON, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.get_db import Base
from sqlalchemy import func
import uuid


class TableSession(Base):
    __tablename__ = "table_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), nullable=False)
    table_id = Column(UUID(as_uuid=True), ForeignKey("venue_tables.id", ondelete="SET NULL"), nullable=True)
    booking_id = Column(UUID(as_uuid=True), nullable=True)
    package_purchase_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Text, nullable=False, default="open")  # open, billing, paid, closed, cancelled
    guest_count = Column(Integer, nullable=False, default=1)
    guest_name = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    opened_by = Column(UUID(as_uuid=True), nullable=True)
    closed_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    table = relationship("VenueTable")
    orders = relationship("SessionOrder", back_populates="session", cascade="all, delete-orphan")
    invoice = relationship("SessionInvoice", back_populates="session", cascade="all, delete-orphan", uselist=False)


class SessionOrder(Base):
    __tablename__ = "session_orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("table_sessions.id", ondelete="CASCADE"), nullable=False)
    order_number = Column(Integer, nullable=False, default=1)
    status = Column(Text, nullable=False, default="pending")  # pending, confirmed, preparing, ready, served, cancelled
    notes = Column(Text, nullable=True)
    ordered_by = Column(UUID(as_uuid=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    session = relationship("TableSession", back_populates="orders")
    items = relationship("SessionOrderItem", back_populates="order", cascade="all, delete-orphan")


class SessionOrderItem(Base):
    __tablename__ = "session_order_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_order_id = Column(UUID(as_uuid=True), ForeignKey("session_orders.id", ondelete="CASCADE"), nullable=False)
    menu_item_id = Column(UUID(as_uuid=True), nullable=True)
    item_name = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric, nullable=False, default=0)
    modifiers = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")  # pending, preparing, ready, served, cancelled
    destination = Column(Text, nullable=True)  # e.g., 'bar', 'kitchen'
    served_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    order = relationship("SessionOrder", back_populates="items")


class SessionInvoice(Base):
    __tablename__ = "session_invoices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("table_sessions.id", ondelete="CASCADE"), nullable=False)
    invoice_number = Column(Text, nullable=False)
    subtotal = Column(Numeric, nullable=False, default=0)
    tax_amount = Column(Numeric, nullable=False, default=0)
    service_charge = Column(Numeric, nullable=False, default=0)
    discount_amount = Column(Numeric, nullable=False, default=0)
    discount_reason = Column(Text, nullable=True)
    deposit_credit = Column(Numeric, nullable=False, default=0)
    total_amount = Column(Numeric, nullable=False, default=0)
    amount_paid = Column(Numeric, nullable=False, default=0)
    status = Column(Text, nullable=False, default="draft")  # draft, pending, paid, partially_paid, void
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("TableSession", back_populates="invoice")
    payments = relationship("SessionPayment", back_populates="invoice", cascade="all, delete-orphan")


class SessionPayment(Base):
    __tablename__ = "session_payments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("session_invoices.id", ondelete="CASCADE"), nullable=False)
    payment_method = Column(Text, nullable=False)
    amount = Column(Numeric, nullable=False)
    reference_number = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="completed")
    processed_by = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    invoice = relationship("SessionInvoice", back_populates="payments")


# --- Menus / POS settings (for menu lookups) ---
class Menu(Base):
    __tablename__ = "menus"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class MenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_id = Column(UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric, nullable=True)
    category = Column(Text, nullable=True)
    is_available = Column(Boolean, nullable=False, default=True)
    dietary_tags = Column(ARRAY(Text), nullable=True, default=list)
    image_url = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class VenuePOSSettings(Base):
    __tablename__ = "venue_pos_settings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), nullable=False)
    tax_rate = Column(Numeric, nullable=False, default=0)
    service_charge_rate = Column(Numeric, nullable=False, default=0)
    currency = Column(Text, nullable=False, default='IDR')
    auto_print_kitchen = Column(Boolean, nullable=True, default=False)
    auto_print_bar = Column(Boolean, nullable=True, default=False)
    require_table_for_orders = Column(Boolean, nullable=True, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
