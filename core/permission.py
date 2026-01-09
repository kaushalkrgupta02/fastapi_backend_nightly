from enum import Enum
from typing import Dict, List


class Permission(str, Enum):
    """Permission definitions for RBAC"""
    
 # Venue Management
    VENUE_CREATE = "venue:create"
    VENUE_READ = "venue:read"
    VENUE_UPDATE = "venue:update"
    VENUE_DELETE = "venue:delete"
    VENUE_ANALYTICS = "venue:analytics"
    VENUE_TYPE_CREATE = "venue_type:create" 
    
    
    # Staff Management
    STAFF_CREATE = "staff:create"
    STAFF_READ = "staff:read"
    STAFF_UPDATE = "staff:update"
    STAFF_DELETE = "staff:delete"
    
    # Bookings
    BOOKING_CREATE = "booking:create"
    BOOKING_READ = "booking:read"
    BOOKING_UPDATE = "booking:update"
    BOOKING_CANCEL = "booking:cancel"
    
    # Orders
    ORDER_CREATE = "order:create"
    ORDER_READ = "order:read"
    ORDER_UPDATE = "order:update"
    ORDER_CANCEL = "order:cancel"
    
    # Payments
    PAYMENT_PROCESS = "payment:process"
    PAYMENT_REFUND = "payment:refund"
    PAYMENT_VIEW = "payment:view"
    
    # Promos
    PROMO_CREATE = "promo:create"
    PROMO_UPDATE = "promo:update"
    PROMO_DELETE = "promo:delete"
    
    # Analytics
    ANALYTICS_VIEW = "analytics:view"
    AI_INSIGHTS_VIEW = "ai:view"


# Role to Permission mapping
ROLE_PERMISSIONS: Dict[str, List[Permission]] = {
    "admin": [p for p in Permission],  # All permissions
    
"venue_manager": [
    Permission.VENUE_READ,
    Permission.VENUE_UPDATE,
    Permission.VENUE_ANALYTICS,
    Permission.VENUE_TYPE_CREATE, 
    Permission.STAFF_CREATE,
    Permission.STAFF_READ,
    Permission.STAFF_UPDATE,
    Permission.STAFF_DELETE,
    Permission.BOOKING_READ,
    Permission.BOOKING_UPDATE,
    Permission.ORDER_READ,
    Permission.PAYMENT_VIEW,
    Permission.PROMO_CREATE,
    Permission.PROMO_UPDATE,
    Permission.PROMO_DELETE,
    Permission.ANALYTICS_VIEW,
    Permission.AI_INSIGHTS_VIEW,
],
    
    "manager": [
        Permission.VENUE_READ,
        Permission.BOOKING_READ,
        Permission.BOOKING_UPDATE,
        Permission.ORDER_CREATE,
        Permission.ORDER_READ,
        Permission.ORDER_UPDATE,
        Permission.PAYMENT_PROCESS,
        Permission.PAYMENT_VIEW,
        Permission.ANALYTICS_VIEW,
    ],
    
    "reception": [
        Permission.BOOKING_CREATE,
        Permission.BOOKING_READ,
        Permission.BOOKING_UPDATE,
        Permission.VENUE_READ,
    ],
    
    "waitress": [
        Permission.BOOKING_READ,
        Permission.ORDER_CREATE,
        Permission.ORDER_READ,
        Permission.ORDER_UPDATE,
        Permission.VENUE_READ,
    ],
    
    "kitchen": [
        Permission.ORDER_READ,
        Permission.ORDER_UPDATE,
    ],
    
    "bar": [
        Permission.ORDER_READ,
        Permission.ORDER_UPDATE,
    ],
    
    "user": [
        Permission.VENUE_READ,
        Permission.BOOKING_CREATE,
        Permission.BOOKING_READ,
        Permission.ORDER_CREATE,
        Permission.ORDER_READ,
    ],
}


def has_permission(user_role: str, permission: Permission) -> bool:
    """Check if role has specific permission"""
    return permission in ROLE_PERMISSIONS.get(user_role, [])
