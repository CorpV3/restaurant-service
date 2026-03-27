"""
Pydantic schemas for Restaurant Service
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, UUID4, HttpUrl
from shared.models.enums import MenuItemCategory, TableStatus, SubscriptionStatus, PricingPlan, OrderStatus
from .models import InventoryCategory, PreparedFoodStatus, MovementType, MovementItemType


# Restaurant Schemas
class RestaurantBase(BaseModel):
    """Base restaurant schema"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=3, max_length=255, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[HttpUrl] = None
    theme_color: str = Field(default="#000000", pattern="^#[0-9A-Fa-f]{6}$")
    country: Optional[str] = Field(default="United States", max_length=100)
    currency_code: Optional[str] = Field(default="USD", min_length=3, max_length=3)
    currency_symbol: Optional[str] = Field(default="$", max_length=10)


class RestaurantCreate(RestaurantBase):
    """Schema for restaurant creation"""
    pricing_plan: PricingPlan = PricingPlan.BASIC
    max_tables: int = Field(default=10, ge=1, le=1000)
    per_table_booking_fee: float = Field(default=0.0, ge=0)
    per_online_booking_fee: float = Field(default=0.0, ge=0)
    enable_booking_fees: bool = False
    # Partner & Tier
    tier: Optional[str] = Field(default="enterprise", pattern="^(basic|enterprise)$")
    billing_model: Optional[str] = Field(default="per_booking", pattern="^(per_booking|monthly)$")
    monthly_charge: Optional[float] = Field(default=0.0, ge=0)
    partner_id: Optional[UUID4] = None
    commission_type: Optional[str] = Field(None, pattern="^(percent|fixed)$")
    commission_value: Optional[float] = Field(None, ge=0)


class RestaurantUpdate(BaseModel):
    """Schema for restaurant update"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[HttpUrl] = None
    theme_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    country: Optional[str] = Field(None, max_length=100)
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)
    currency_symbol: Optional[str] = Field(None, max_length=10)
    max_tables: Optional[int] = Field(None, ge=1, le=1000)
    per_table_booking_fee: Optional[float] = Field(None, ge=0)
    per_online_booking_fee: Optional[float] = Field(None, ge=0)
    enable_booking_fees: Optional[bool] = None
    uber_enabled: Optional[bool] = None
    uber_store_id: Optional[str] = Field(None, max_length=255)
    justeat_enabled: Optional[bool] = None
    justeat_restaurant_id: Optional[str] = Field(None, max_length=255)
    deliveroo_enabled: Optional[bool] = None
    deliveroo_restaurant_id: Optional[str] = Field(None, max_length=255)
    tripos_enabled: Optional[bool] = None
    tripos_acceptor_id: Optional[str] = Field(None, max_length=255)
    tripos_account_id: Optional[str] = Field(None, max_length=255)
    tripos_account_token: Optional[str] = Field(None, max_length=500)
    tripos_application_id: Optional[str] = Field(None, max_length=255)
    tripos_lane_id: Optional[int] = None
    tripos_environment: Optional[str] = Field(None, pattern='^(cert|prod)$')
    stripe_enabled: Optional[bool] = None
    stripe_secret_key: Optional[str] = Field(None, max_length=500)
    sumup_enabled: Optional[bool] = None
    sumup_api_key: Optional[str] = Field(None, max_length=500)
    # Partner & Tier
    tier: Optional[str] = Field(None, pattern="^(basic|enterprise)$")
    billing_model: Optional[str] = Field(None, pattern="^(per_booking|monthly)$")
    monthly_charge: Optional[float] = Field(None, ge=0)
    partner_id: Optional[UUID4] = None
    commission_type: Optional[str] = Field(None, pattern="^(percent|fixed)$")
    commission_value: Optional[float] = Field(None, ge=0)


class RestaurantBranding(BaseModel):
    """Schema for restaurant branding updates"""
    logo_url: Optional[str] = None
    theme_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    banner_images: Optional[List[str]] = None
    upcoming_events: Optional[List[Dict[str, Any]]] = None
    advertisements: Optional[List[Dict[str, Any]]] = None


class RestaurantResponse(RestaurantBase):
    """Schema for restaurant response"""
    id: UUID4
    slug: str
    logo_url: Optional[str] = None
    subscription_status: SubscriptionStatus
    pricing_plan: PricingPlan
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    banner_images: List[str] = []
    upcoming_events: List[Dict[str, Any]] = []
    advertisements: List[Dict[str, Any]] = []
    is_active: bool
    max_tables: int
    per_table_booking_fee: float
    per_online_booking_fee: float
    enable_booking_fees: bool
    uber_enabled: bool = False
    uber_store_id: Optional[str] = None
    justeat_enabled: bool = False
    justeat_restaurant_id: Optional[str] = None
    deliveroo_enabled: bool = False
    deliveroo_restaurant_id: Optional[str] = None
    tripos_enabled: bool = False
    tripos_acceptor_id: Optional[str] = None
    tripos_account_id: Optional[str] = None
    tripos_account_token: Optional[str] = None
    tripos_application_id: Optional[str] = None
    tripos_lane_id: Optional[int] = None
    tripos_environment: Optional[str] = None
    stripe_enabled: bool = False
    stripe_secret_key: Optional[str] = None
    sumup_enabled: bool = False
    sumup_api_key: Optional[str] = None
    # Partner & Tier
    tier: str = "enterprise"
    billing_model: str = "per_booking"
    monthly_charge: float = 0.0
    partner_id: Optional[UUID4] = None
    commission_type: Optional[str] = None
    commission_value: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Menu Item Schemas
class MenuItemBase(BaseModel):
    """Base menu item schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: MenuItemCategory
    price: float = Field(..., gt=0)
    image_url: Optional[str] = None
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False
    preparation_time: Optional[int] = Field(None, ge=0)  # minutes
    calories: Optional[int] = Field(None, ge=0)


class MenuItemCreate(MenuItemBase):
    """Schema for menu item creation"""
    ingredients: Optional[List[str]] = []
    allergens: Optional[List[str]] = []
    display_order: int = Field(default=0, ge=0)


class MenuItemUpdate(BaseModel):
    """Schema for menu item update"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[MenuItemCategory] = None
    price: Optional[float] = Field(None, gt=0)
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    is_vegetarian: Optional[bool] = None
    is_vegan: Optional[bool] = None
    is_gluten_free: Optional[bool] = None
    preparation_time: Optional[int] = Field(None, ge=0)
    calories: Optional[int] = Field(None, ge=0)
    ingredients: Optional[List[str]] = None
    allergens: Optional[List[str]] = None
    display_order: Optional[int] = Field(None, ge=0)


class MenuItemResponse(MenuItemBase):
    """Schema for menu item response"""
    id: UUID4
    restaurant_id: UUID4
    is_available: bool
    ingredients: List[str]
    allergens: List[str]
    display_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Table Schemas
class TableBase(BaseModel):
    """Base table schema"""
    table_number: str = Field(..., min_length=1, max_length=50)
    seat_count: int = Field(..., ge=1, le=50)
    floor: Optional[str] = Field(None, max_length=50)
    section: Optional[str] = Field(None, max_length=50)


class TableCreate(TableBase):
    """Schema for table creation"""
    pass


class TableUpdate(BaseModel):
    """Schema for table update"""
    table_number: Optional[str] = Field(None, min_length=1, max_length=50)
    seat_count: Optional[int] = Field(None, ge=1, le=50)
    status: Optional[TableStatus] = None
    floor: Optional[str] = Field(None, max_length=50)
    section: Optional[str] = Field(None, max_length=50)


class TableResponse(TableBase):
    """Schema for table response"""
    id: UUID4
    restaurant_id: UUID4
    status: TableStatus
    qr_code_url: Optional[str] = None
    qr_code_data: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Feedback Schemas
class FeedbackCreate(BaseModel):
    """Schema for feedback creation"""
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    table_id: Optional[UUID4] = None


class FeedbackResponse(BaseModel):
    """Schema for feedback response"""
    id: UUID4
    restaurant_id: UUID4
    table_id: Optional[UUID4] = None
    rating: int
    comment: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# QR Code Schema
class QRCodeResponse(BaseModel):
    """Schema for QR code response"""
    table_id: UUID4
    table_number: str
    qr_code_url: str
    qr_code_data: str


# Order Schemas
class OrderItemCreate(BaseModel):
    """Schema for creating an order item"""
    menu_item_id: UUID4
    quantity: int = Field(..., ge=1, le=100)
    special_instructions: Optional[str] = None


class OrderItemResponse(BaseModel):
    """Schema for order item response"""
    id: UUID4
    order_id: UUID4
    menu_item_id: Optional[UUID4] = None
    item_name: str
    item_price: float
    quantity: int
    special_instructions: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    """Schema for creating an order (public - no auth required)"""
    table_id: UUID4
    items: List[OrderItemCreate] = Field(..., min_length=1)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=20)
    special_instructions: Optional[str] = None


class OrderUpdateStatus(BaseModel):
    """Schema for updating order status (chef/admin only)"""
    status: OrderStatus


class OrderResponse(BaseModel):
    """Schema for order response"""
    id: UUID4
    restaurant_id: UUID4
    table_id: Optional[UUID4] = None
    order_number: str
    status: OrderStatus
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    subtotal: float
    tax: float
    total: float
    special_instructions: Optional[str] = None
    items: List[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Analytics Schemas
class RestaurantAnalytics(BaseModel):
    """Schema for restaurant analytics"""
    total_menu_items: int
    total_tables: int
    available_tables: int
    occupied_tables: int
    total_feedback: int
    average_rating: float
    menu_items_by_category: Dict[str, int]


class RestaurantBilling(BaseModel):
    """Schema for restaurant billing response"""
    restaurant_id: UUID4
    restaurant_name: str
    currency_symbol: str
    enable_booking_fees: bool
    per_table_booking_fee: float
    per_online_booking_fee: float
    total_table_bookings: int
    total_online_bookings: int
    table_booking_revenue: float
    online_booking_revenue: float
    total_revenue: float


# Generic Response
class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    status_code: int


# Invoice Schemas
class InvoiceResponse(BaseModel):
    """Schema for invoice response"""
    id: UUID4
    restaurant_id: UUID4
    invoice_number: str
    period_start: datetime
    period_end: datetime
    currency_code: str
    currency_symbol: str
    per_table_booking_fee: float
    per_online_booking_fee: float
    total_table_bookings: int
    total_online_bookings: int
    table_booking_revenue: float
    online_booking_revenue: float
    total_revenue: float
    is_paid: bool
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    """Schema for generating an invoice"""
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# ─── Inventory Schemas ────────────────────────────────────────────────────────

class InventoryItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: InventoryCategory = InventoryCategory.OTHER
    quantity: float = Field(default=0.0, ge=0)
    unit: str = Field(default="pieces", max_length=20)
    min_threshold: float = Field(default=0.0, ge=0)
    cost_per_unit: Optional[float] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[InventoryCategory] = None
    unit: Optional[str] = None
    min_threshold: Optional[float] = None
    cost_per_unit: Optional[float] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None


class InventoryItemResponse(BaseModel):
    id: UUID4
    restaurant_id: UUID4
    name: str
    category: InventoryCategory
    quantity: float
    unit: str
    min_threshold: float
    cost_per_unit: Optional[float] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StockAdjustRequest(BaseModel):
    delta: float  # positive = add, negative = remove
    movement_type: Optional[str] = "adjustment"  # "waste" | "adjustment" | "stock_in"
    reason: Optional[str] = None
    created_by: Optional[str] = None


class PreparedFoodCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    menu_item_id: Optional[UUID4] = None
    quantity: int = Field(..., ge=1)
    batch_number: Optional[str] = None
    prepared_at: Optional[datetime] = None
    expires_at: datetime
    notes: Optional[str] = None


class PreparedFoodUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    expires_at: Optional[datetime] = None
    status: Optional[PreparedFoodStatus] = None
    offer_discount: Optional[float] = None
    offer_price: Optional[float] = None
    notes: Optional[str] = None


class PreparedFoodResponse(BaseModel):
    id: UUID4
    restaurant_id: UUID4
    menu_item_id: Optional[UUID4] = None
    name: str
    quantity: int
    batch_number: Optional[str] = None
    prepared_at: datetime
    expires_at: datetime
    status: PreparedFoodStatus
    offer_discount: Optional[float] = None
    offer_price: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecipeCreate(BaseModel):
    menu_item_id: UUID4
    inventory_item_id: UUID4
    quantity_required: float = Field(..., gt=0)
    unit: str = Field(..., max_length=20)


class RecipeResponse(BaseModel):
    id: UUID4
    restaurant_id: UUID4
    menu_item_id: UUID4
    inventory_item_id: UUID4
    quantity_required: float
    unit: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StockMovementResponse(BaseModel):
    id: UUID4
    restaurant_id: UUID4
    item_id: UUID4
    item_type: MovementItemType
    item_name: str
    movement_type: MovementType
    quantity: float
    unit: Optional[str] = None
    reason: Optional[str] = None
    reference_id: Optional[UUID4] = None
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryAlertItem(BaseModel):
    id: UUID4
    name: str
    quantity: float
    unit: str
    min_threshold: float


class InventoryAlertsResponse(BaseModel):
    low_stock: List[InventoryAlertItem]
    expiring_soon: List[Dict]
    expired: List[Dict]


# ─── Partner Invoice Schemas ──────────────────────────────────────────────────

class PartnerInvoiceResponse(BaseModel):
    id: UUID4
    partner_id: UUID4
    invoice_number: str
    period_start: datetime
    period_end: datetime
    restaurants_count: int
    total_revenue: float
    total_commission: float
    line_items: List[Dict]
    is_paid: bool
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PartnerInvoiceGenerate(BaseModel):
    period_start: datetime
    period_end: datetime
    notes: Optional[str] = None


class PartnerDashboardResponse(BaseModel):
    partner_id: UUID4
    total_restaurants: int
    active_restaurants: int
    total_invoices: int
    total_commission_earned: float
    unpaid_commission: float
    restaurants: List[Dict]
