from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, model_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from core.get_db import get_db
from core.auth_middleware import get_current_user
from models.venue import Venue, VenueTable, VenueGuestProfile
from models.sessions import TableSession, SessionOrder, SessionOrderItem, SessionInvoice, Menu, MenuItem, VenuePOSSettings
from models.auth import UserRole, StaffProfile, AppRole
import uuid as uuid_module
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Sessions"])


class CheckInPayload(BaseModel):
    table_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None
    package_purchase_id: Optional[UUID] = None
    guest_profile_id: Optional[UUID] = None  # optional reference to existing VenueGuestProfile
    guest_count: int
    guest_name: Optional[str] = None
    notes: Optional[str] = None


class CreateOrderItem(BaseModel):
    menu_item_id: Optional[UUID] = None
    item_name: str
    quantity: int = 1
    unit_price: float = 0.0
    modifiers: Optional[dict] = None
    notes: Optional[str] = None
    destination: Optional[str] = None  # 'bar' or 'kitchen' or other


class CreateOrderPayload(BaseModel):
    items: List[CreateOrderItem]
    notes: Optional[str] = None


class PaymentPayload(BaseModel):
    invoice_id: UUID
    amount: Optional[float] = None
    total_amount: Optional[float] = None
    method: Optional[str] = None
    reference: Optional[str] = None  # can be idempotency key or payment reference

    @model_validator(mode="after")
    def ensure_amount(cls, values):
        # map legacy `total_amount` to `amount` when provided by clients
        if values.amount is None and values.total_amount is not None:
            values.amount = values.total_amount
        if values.amount is None:
            raise ValueError("'amount' is required (or provide 'total_amount')")
        return values


def _apply_payment(invoice, amount: float, method: Optional[str], reference: Optional[str], processed_by: UUID, db: Session):
    # idempotency: if a payment with same reference and invoice exists, return it
    existing_payment = None
    if reference:
        existing_payment = db.query(SessionPayment).filter(
            SessionPayment.invoice_id == invoice.id,
            SessionPayment.reference_number == reference
        ).one_or_none()
        if existing_payment:
            logger.info(f"Idempotent payment detected for invoice={invoice.id} reference={reference} returning existing payment={existing_payment.id}")
            return existing_payment

    payment = SessionPayment(
        invoice_id=invoice.id,
        payment_method=method or 'unknown',
        amount=amount,
        reference_number=reference,
        status='completed',
        processed_by=processed_by
    )
    db.add(payment)
    db.flush()

    # update invoice totals
    invoice.amount_paid = float(invoice.amount_paid or 0) + float(amount)
    if invoice.amount_paid >= float(invoice.total_amount):
        invoice.status = 'paid'
        invoice.paid_at = datetime.now(timezone.utc)
    else:
        invoice.status = 'partially_paid'

    db.add(invoice)

    # if all invoices for the session are paid -> close session and free table
    session = db.query(TableSession).filter(TableSession.id == invoice.session_id).one_or_none()
    if session:
        unpaid = db.query(SessionInvoice).filter(SessionInvoice.session_id == session.id).filter(SessionInvoice.status != 'paid').count()
        if unpaid == 0:
            session.status = 'closed'
            session.closed_at = datetime.now(timezone.utc)
            # closed_by will be set by caller
            if session.table_id:
                t = db.query(VenueTable).filter(VenueTable.id == session.table_id).one_or_none()
                if t:
                    t.status = 'available'
                    db.add(t)
            db.add(session)

    db.commit()

    # refresh to get timestamps and DB-generated values
    try:
        db.refresh(payment)
    except Exception:
        pass
    try:
        db.refresh(invoice)
    except Exception:
        pass

    logger.info(
        f"Payment recorded: invoice={invoice.id} payment={payment.id} amount={payment.amount} method={payment.payment_method} reference={payment.reference_number} by={processed_by}"
    )

    return payment


# helper

def assert_venue_access(db: Session, user_id: UUID, venue_id: UUID, error_message: str):
    user_role = db.query(UserRole).filter(UserRole.user_id == user_id).one_or_none()
    is_admin = user_role and user_role.role == AppRole.admin
    is_venue_staff = db.query(StaffProfile).filter(
        StaffProfile.user_id == user_id,
        StaffProfile.venue_id == venue_id
    ).first() is not None
    if not (is_admin or is_venue_staff):
        raise HTTPException(status_code=403, detail=error_message)


def staff_has_role(db: Session, user_id: UUID, venue_id: UUID, role: str) -> bool:
    sp = db.query(StaffProfile).filter(
        StaffProfile.user_id == user_id,
        StaffProfile.venue_id == venue_id,
        StaffProfile.role == role
    ).first()
    if sp:
        return True
    # admins can act as any role
    ur = db.query(UserRole).filter(UserRole.user_id == user_id).one_or_none()
    return ur and ur.role == AppRole.admin


@router.post("/venue/{venue_id}/checkin", response_model=dict)
def checkin(venue_id: UUID, payload: CheckInPayload, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Open a table session (requires `table_id`; auto-assignment is disabled).
    Table status becomes 'reserved'."""
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to open sessions for this venue")

        # table must be provided (auto-assignment disabled)
        if not payload.table_id:
            raise HTTPException(status_code=400, detail="table_id is required; auto-assignment is disabled")

        table = db.query(VenueTable).filter(VenueTable.id == payload.table_id, VenueTable.venue_id == venue_id).one_or_none()
        if not table:
            raise HTTPException(status_code=404, detail="Table not found for this venue")
        if table.status and table.status != 'available':
            raise HTTPException(status_code=400, detail=f"Table not available (status={table.status})")
        # verify capacity
        if table.seats < payload.guest_count:
            raise HTTPException(status_code=400, detail="Table seats are less than guest count")

        now = datetime.now(timezone.utc)

        # coerce empty booking/package ids to None
        booking_id = payload.booking_id or None
        package_purchase_id = payload.package_purchase_id or None

        # handle guest profile if provided
        guest_profile = None
        guest_name_to_use = payload.guest_name
        if payload.guest_profile_id:
            guest_profile = db.query(VenueGuestProfile).filter(
                VenueGuestProfile.id == payload.guest_profile_id,
                VenueGuestProfile.venue_id == venue_id
            ).one_or_none()
            if not guest_profile:
                raise HTTPException(status_code=404, detail="Guest profile not found for this venue")
            # prefer provided guest_name, otherwise use profile name
            if not guest_name_to_use and guest_profile.guest_name:
                guest_name_to_use = guest_profile.guest_name
            # update guest visit stats
            guest_profile.total_visits = (guest_profile.total_visits or 0) + 1
            guest_profile.last_visit_at = now
            db.add(guest_profile)

        session = TableSession(
            venue_id=venue_id,
            table_id=table.id if table else None,
            booking_id=booking_id,
            package_purchase_id=package_purchase_id,
            status='open',
            guest_count=payload.guest_count,
            guest_name=guest_name_to_use,
            notes=payload.notes,
            opened_at=now,
            opened_by=current_user_uuid
        )

        db.add(session)
        # mark table reserved
        if table:
            table.status = 'reserved'
            db.add(table)

        db.commit()
        db.refresh(session)

        return {"session_id": str(session.id)}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Checkin error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/venue/{venue_id}/active", response_model=List[dict])
def get_active_sessions(venue_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to view sessions for this venue")

        sessions = db.query(TableSession).filter(TableSession.venue_id == venue_id).filter(TableSession.status.in_(['open', 'billing'])).all()
        result = []
        for s in sessions:
            result.append({
                "id": str(s.id),
                "table_id": str(s.table_id) if s.table_id else None,
                "status": s.status,
                "guest_count": s.guest_count,
                "guest_name": s.guest_name,
                "opened_at": s.opened_at.isoformat() if s.opened_at else None
            })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get active sessions error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}", response_model=dict)
def get_session(session_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Return a single session with its orders, items, and invoice."""
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        session = db.query(TableSession).filter(TableSession.id == session_id).one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        assert_venue_access(db, current_user_uuid, session.venue_id, "Not authorized to view this session")

        table = None
        if session.table_id:
            table = db.query(VenueTable).filter(VenueTable.id == session.table_id).one_or_none()

        orders_q = db.query(SessionOrder).filter(SessionOrder.session_id == session_id).order_by(SessionOrder.order_number.asc()).all()
        orders = []
        for o in orders_q:
            items_q = db.query(SessionOrderItem).filter(SessionOrderItem.session_order_id == o.id).order_by(SessionOrderItem.created_at.asc()).all()
            items_list = []
            for it in items_q:
                items_list.append({
                    "id": str(it.id),
                    "menu_item_id": str(it.menu_item_id) if it.menu_item_id else None,
                    "item_name": it.item_name,
                    "quantity": it.quantity,
                    "unit_price": float(it.unit_price),
                    "modifiers": it.modifiers,
                    "notes": it.notes,
                    "status": it.status,
                    "destination": it.destination,
                    "served_at": it.served_at.isoformat() if it.served_at else None,
                    "created_at": it.created_at.isoformat() if it.created_at else None
                })
            orders.append({
                "id": str(o.id),
                "order_number": o.order_number,
                "status": o.status,
                "notes": o.notes,
                "ordered_by": str(o.ordered_by) if o.ordered_by else None,
                "confirmed_at": o.confirmed_at.isoformat() if o.confirmed_at else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "items": items_list
            })

        invoice = db.query(SessionInvoice).filter(SessionInvoice.session_id == session_id).one_or_none()
        invoice_obj = None
        if invoice:
            invoice_obj = {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "subtotal": float(invoice.subtotal),
                "tax_amount": float(invoice.tax_amount),
                "service_charge": float(invoice.service_charge),
                "discount_amount": float(invoice.discount_amount),
                "deposit_credit": float(invoice.deposit_credit),
                "total_amount": float(invoice.total_amount),
                "amount_paid": float(invoice.amount_paid),
                "status": invoice.status,
                "generated_at": invoice.generated_at.isoformat() if invoice.generated_at else None,
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None
            }

        result = {
            "id": str(session.id),
            "venue_id": str(session.venue_id),
            "table_id": str(session.table_id) if session.table_id else None,
            "table_number": table.table_number if table else None,
            "status": session.status,
            "guest_count": session.guest_count,
            "guest_name": session.guest_name,
            "notes": session.notes,
            "opened_at": session.opened_at.isoformat() if session.opened_at else None,
            "closed_at": session.closed_at.isoformat() if session.closed_at else None,
            "orders": orders,
            "invoice": invoice_obj
        }
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/orders", response_model=dict)
def create_session_order(session_id: UUID, payload: CreateOrderPayload, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        session = db.query(TableSession).filter(TableSession.id == session_id).one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        assert_venue_access(db, current_user_uuid, session.venue_id, "Not authorized to add orders for this session")

        # respect venue POS settings (require table for orders)
        pos_settings = db.query(VenuePOSSettings).filter(VenuePOSSettings.venue_id == session.venue_id).one_or_none()
        if pos_settings and pos_settings.require_table_for_orders and not session.table_id:
            raise HTTPException(status_code=400, detail="This venue requires a table assignment before creating orders")

        # determine next order number
        last_order = db.query(SessionOrder).filter(SessionOrder.session_id == session_id).order_by(SessionOrder.order_number.desc()).first()
        next_number = (last_order.order_number + 1) if last_order else 1

        order = SessionOrder(
            session_id=session_id,
            order_number=next_number,
            status='pending',
            notes=payload.notes,
            ordered_by=current_user_uuid
        )
        db.add(order)
        db.flush()

        items_created = []
        for it in payload.items:
            # If menu_item_id supplied, fetch menu item and populate details
            if it.menu_item_id:
                menu_item = db.query(MenuItem).filter(MenuItem.id == it.menu_item_id).one_or_none()
                if not menu_item:
                    raise HTTPException(status_code=404, detail=f"Menu item {it.menu_item_id} not found")
                menu = db.query(Menu).filter(Menu.id == menu_item.menu_id).one_or_none()
                if not menu or menu.venue_id != session.venue_id:
                    raise HTTPException(status_code=400, detail="Menu item does not belong to this venue")

                item_name = menu_item.name
                unit_price = float(menu_item.price) if menu_item.price is not None else 0.0
                # map categories to destinations (simple rule)
                category = (menu_item.category or '').lower()
                default_destination = 'bar' if category in ('drink', 'bar', 'beverage') else 'kitchen'
                destination = it.destination or default_destination
                menu_item_id_val = it.menu_item_id
            else:
                if not it.item_name:
                    raise HTTPException(status_code=400, detail="item_name is required when menu_item_id is not provided")
                item_name = it.item_name
                unit_price = float(it.unit_price or 0)
                destination = it.destination or 'kitchen'
                menu_item_id_val = None

            item = SessionOrderItem(
                session_order_id=order.id,
                menu_item_id=menu_item_id_val,
                item_name=item_name,
                quantity=it.quantity,
                unit_price=unit_price,
                modifiers=it.modifiers,
                notes=it.notes,
                status='pending',
                destination=destination
            )
            db.add(item)
            items_created.append(item)

        # set session status to open if not already
        if session.status != 'open':
            session.status = 'open'
            db.add(session)

        db.commit()
        db.refresh(order)

        # fetch created items to return their IDs
        created_items = db.query(SessionOrderItem).filter(SessionOrderItem.session_order_id == order.id).all()
        item_ids = [str(i.id) for i in created_items]

        return {"order_id": str(order.id), "order_number": order.order_number, "item_ids": item_ids}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create order error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/destination/{destination}", response_model=List[dict])
def get_orders_for_destination(destination: str, venue_id: Optional[UUID] = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch items for a given destination (e.g., 'bar' or 'kitchen'). If venue_id provided, filter by venue."""
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        # if venue provided we check access
        if venue_id:
            assert_venue_access(db, current_user_uuid, venue_id, "Not authorized to view orders for this venue")

        # if staff has role matching destination or admin
        # skip strict role checks if venue_id not provided
        if venue_id and not staff_has_role(db, current_user_uuid, venue_id, destination):
            raise HTTPException(status_code=403, detail="Not authorized as this destination role")

        q = db.query(SessionOrderItem).join(SessionOrder).join(TableSession).filter(SessionOrderItem.destination == destination).filter(SessionOrderItem.status.in_(['pending', 'preparing']))
        if venue_id:
            q = q.filter(TableSession.venue_id == venue_id)

        items = q.order_by(SessionOrderItem.created_at.asc()).all()

        result = []
        for it in items:
            result.append({
                "id": str(it.id),
                "order_id": str(it.session_order_id),
                "session_id": str(it.order.session_id),
                "item_name": it.item_name,
                "quantity": it.quantity,
                "status": it.status,
                "destination": it.destination,
                "created_at": it.created_at.isoformat() if it.created_at else None,
                "menu_item_id": str(it.menu_item_id) if it.menu_item_id else None
            })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get orders for destination error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# --- Menus endpoints ---
@router.get("/venue/{venue_id}/menus", response_model=List[dict])
def get_menus_for_venue(venue_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # Anyone can view active menus for venue (but we check venue exists)
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        menus = db.query(Menu).filter(Menu.venue_id == venue_id, Menu.is_active == True).order_by(Menu.sort_order.asc()).all()
        return [{"id": str(m.id), "name": m.name, "description": m.description} for m in menus]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get menus error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/invoices/{invoice_id}/pay", response_model=dict)
def pay_invoice_by_id(invoice_id: UUID, payload: PaymentPayload, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Pay a specific invoice and record a session payment. Returns the payment record."""
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        invoice = db.query(SessionInvoice).filter(SessionInvoice.id == invoice_id).one_or_none()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        session = db.query(TableSession).filter(TableSession.id == invoice.session_id).one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found for invoice")

        assert_venue_access(db, current_user_uuid, session.venue_id, "Not authorized to process payments for this invoice")

        # apply payment
        payment = _apply_payment(invoice, float(payload.amount), payload.method, payload.reference, current_user_uuid, db)

        # set closed_by if session closed
        if session.status == 'closed':
            session.closed_by = current_user_uuid
            db.add(session)
            db.commit()

        response = {
            "payment_id": str(payment.id),
            "invoice_id": str(invoice.id),
            "amount": float(payment.amount),
            "method": payment.payment_method,
            "reference": payment.reference_number,
            "status": payment.status,
            "processed_by": str(payment.processed_by) if payment.processed_by else None,
            "created_at": payment.created_at.isoformat() if getattr(payment, 'created_at', None) else None,
            "invoice_total": float(invoice.total_amount),
            "invoice_amount_paid": float(invoice.amount_paid),
            "invoice_status": invoice.status
        }

        return response
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Pay invoice by id error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


class AdminForcePayload(BaseModel):
    mark_orders_served: Optional[bool] = True
    mark_invoices_paid: Optional[bool] = True
    payment_method: Optional[str] = "admin_offline"
    payment_reference: Optional[str] = None
    close_session: Optional[bool] = True
    note: Optional[str] = None


@router.post("/{session_id}/admin/force-close", response_model=dict)
def admin_force_close(session_id: UUID, payload: AdminForcePayload, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Admin-only: force-mark orders as served, mark invoices paid (creates payments), and close session.
    Used when offline/manual verification is done from POS."""
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        user_role = db.query(UserRole).filter(UserRole.user_id == current_user_uuid).one_or_none()
        if not (user_role and user_role.role == AppRole.admin):
            raise HTTPException(status_code=403, detail="Admin privileges required")

        session = db.query(TableSession).filter(TableSession.id == session_id).one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        result = {"orders_updated": 0, "invoices_paid": 0, "payments": []}

        # mark order items as served
        if payload.mark_orders_served:
            items_q = db.query(SessionOrderItem).join(SessionOrder).filter(SessionOrder.session_id == session_id).filter(SessionOrderItem.status != 'served').all()
            for it in items_q:
                it.status = 'served'
                it.served_at = datetime.now(timezone.utc)
                db.add(it)
            db.commit()

            # update parent orders
            orders = db.query(SessionOrder).filter(SessionOrder.session_id == session_id).all()
            for o in orders:
                statuses = set(i.status for i in o.items)
                if all(s == 'served' for s in statuses):
                    o.status = 'served'
                    db.add(o)
            db.commit()

            result['orders_updated'] = len(items_q)

        # mark invoices paid by creating payments for remaining amounts
        if payload.mark_invoices_paid:
            invoices = db.query(SessionInvoice).filter(SessionInvoice.session_id == session_id).filter(SessionInvoice.status != 'paid').filter(SessionInvoice.status != 'void').all()
            for inv in invoices:
                remaining = float(inv.total_amount) - float(inv.amount_paid or 0)
                if remaining > 0:
                    payment = _apply_payment(inv, remaining, payload.payment_method, payload.payment_reference, current_user_uuid, db)
                    result['payments'].append(str(payment.id))
                    result['invoices_paid'] += 1
                else:
                    # mark already-covered invoices as paid
                    if float(inv.amount_paid or 0) >= float(inv.total_amount):
                        inv.status = 'paid'
                        inv.paid_at = datetime.now(timezone.utc)
                        db.add(inv)
                        db.commit()
                        result['invoices_paid'] += 1

        # optionally close session and free table
        if payload.close_session:
            session.status = 'closed'
            session.closed_at = datetime.now(timezone.utc)
            session.closed_by = current_user_uuid
            db.add(session)
            if session.table_id:
                t = db.query(VenueTable).filter(VenueTable.id == session.table_id).one_or_none()
                if t:
                    t.status = 'available'
                    db.add(t)
            db.commit()

        # log
        logger.info(f"Admin force-close by {current_user_uuid} on session {session_id}: {result}")

        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Admin force-close error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/menus/{menu_id}/items", response_model=List[dict])
def get_menu_items(menu_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        menu = db.query(Menu).filter(Menu.id == menu_id).one_or_none()
        if not menu:
            raise HTTPException(status_code=404, detail="Menu not found")

        items = db.query(MenuItem).filter(MenuItem.menu_id == menu_id, MenuItem.is_available == True).order_by(MenuItem.sort_order.asc()).all()
        return [{"id": str(i.id), "name": i.name, "price": float(i.price) if i.price is not None else None, "category": i.category, "image_url": i.image_url} for i in items]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get menu items error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/venue/{venue_id}/menu-items", response_model=List[dict])
def search_menu_items(venue_id: UUID, name: Optional[str] = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        venue = db.query(Venue).filter(Venue.id == venue_id).one_or_none()
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")

        q = db.query(MenuItem).join(Menu).filter(Menu.venue_id == venue_id, MenuItem.is_available == True)
        if name and name.strip():
            pattern = f"%{name}%"
            q = q.filter(MenuItem.name.ilike(pattern))

        items = q.order_by(MenuItem.sort_order.asc()).all()
        return [{"id": str(i.id), "name": i.name, "price": float(i.price) if i.price is not None else None, "category": i.category, "menu_id": str(i.menu_id)} for i in items]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search menu items error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/order-items/{item_id}/status", response_model=dict)
def update_order_item_status(item_id: UUID, status: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])

        item = db.query(SessionOrderItem).filter(SessionOrderItem.id == item_id).one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Order item not found")

        session = db.query(TableSession).filter(TableSession.id == item.order.session_id).one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found for this item")

        # staff either bar/kitchen or admin/venue staff
        if not staff_has_role(db, current_user_uuid, session.venue_id, item.destination):
            # allow admin or venue manager to update any
            assert_venue_access(db, current_user_uuid, session.venue_id, "Not authorized to update order item status")

        item.status = status
        if status == 'served':
            item.served_at = datetime.now(timezone.utc)
        db.add(item)
        db.commit()
        db.refresh(item)

        # update parent order status based on child items
        order = db.query(SessionOrder).filter(SessionOrder.id == item.session_order_id).one_or_none()
        if order:
            statuses = set(i.status for i in order.items)
            if 'pending' in statuses or 'preparing' in statuses:
                order.status = 'preparing'
            elif all(s == 'served' for s in statuses):
                order.status = 'served'
            db.add(order)
            db.commit()

        return {"item_id": str(item.id), "status": item.status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Update order item status error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/create-invoice", response_model=dict)
def create_invoice(session_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        session = db.query(TableSession).filter(TableSession.id == session_id).one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        assert_venue_access(db, current_user_uuid, session.venue_id, "Not authorized to create invoice for this session")

        # compute totals from orders/items
        items = db.query(SessionOrderItem).join(SessionOrder).filter(SessionOrder.session_id == session_id).all()
        subtotal = sum((float(i.unit_price) * i.quantity) for i in items)

        # use venue POS settings for tax/service rates
        pos_settings = db.query(VenuePOSSettings).filter(VenuePOSSettings.venue_id == session.venue_id).one_or_none()
        tax_rate = float(pos_settings.tax_rate) if pos_settings else 0.1
        service_rate = float(pos_settings.service_charge_rate) if pos_settings else 0.05

        tax = round(subtotal * tax_rate, 2)
        service = round(subtotal * service_rate, 2)
        total = subtotal + tax + service

        # Check for an existing non-void, non-paid invoice for this session
        existing = db.query(SessionInvoice).filter(
            SessionInvoice.session_id == session_id,
            SessionInvoice.status != 'void',
            SessionInvoice.status != 'paid'
        ).order_by(SessionInvoice.created_at.desc()).first()

        if existing:
            # Update the existing invoice totals instead of creating a duplicate
            existing.subtotal = subtotal
            existing.tax_amount = tax
            existing.service_charge = service
            existing.total_amount = total
            # ensure status is pending (re-open billing)
            existing.status = 'pending'
            db.add(existing)
            session.status = 'billing'
            db.add(session)
            db.commit()
            db.refresh(existing)
            return {"invoice_id": str(existing.id), "total_amount": float(existing.total_amount), "updated": True}

        invoice = SessionInvoice(
            session_id=session_id,
            invoice_number=str(uuid_module.uuid4())[:8],
            subtotal=subtotal,
            tax_amount=tax,
            service_charge=service,
            total_amount=total,
            amount_paid=0,
            status='pending'
        )
        db.add(invoice)
        session.status = 'billing'
        db.add(session)
        db.commit()
        db.refresh(invoice)

        return {"invoice_id": str(invoice.id), "total_amount": float(invoice.total_amount), "created": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create invoice error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/pay", response_model=dict)
def pay_invoice(session_id: UUID, payload: PaymentPayload, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Backward-compatible session-level pay (keeps existing behaviour but records session_payments). Prefer `/invoices/{invoice_id}/pay`."""
    try:
        current_user_uuid = uuid_module.UUID(current_user["sub"])
        session = db.query(TableSession).filter(TableSession.id == session_id).one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        assert_venue_access(db, current_user_uuid, session.venue_id, "Not authorized to process payments for this session")

        invoice = db.query(SessionInvoice).filter(SessionInvoice.id == payload.invoice_id, SessionInvoice.session_id == session_id).one_or_none()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # create payment and update invoice/session via helper
        payment = _apply_payment(invoice, float(payload.amount), payload.method, payload.reference, current_user_uuid, db)
        # set closed_by if session closed
        if session.status == 'closed':
            session.closed_by = current_user_uuid
            db.add(session)
            db.commit()

        response = {
            "payment_id": str(payment.id),
            "invoice_id": str(invoice.id),
            "amount": float(payment.amount),
            "method": payment.payment_method,
            "reference": payment.reference_number,
            "status": payment.status,
            "processed_by": str(payment.processed_by) if payment.processed_by else None,
            "created_at": payment.created_at.isoformat() if getattr(payment, 'created_at', None) else None,
            "invoice_total": float(invoice.total_amount),
            "invoice_amount_paid": float(invoice.amount_paid),
            "invoice_status": invoice.status
        }

        return response
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Pay invoice error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
