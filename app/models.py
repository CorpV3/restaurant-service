"""
Database models for Restaurant Service
"""
from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from shared.models.enums import MenuItemCategory, TableStatus, SubscriptionStatus, PricingPlan, OrderStatus
from .database import Base


class InventoryCategory(str, enum.Enum):
    MEAT = "meat"
    VEGETABLES = "vegetables"
    DAIRY = "dairy"
    BAKERY = "bakery"
    SPICES = "spices"
    BEVERAGES = "beverages"
    SEAFOOD = "seafood"
    FROZEN = "frozen"
    OTHER = "other"


class PreparedFoodStatus(str, enum.Enum):
    ACTIVE = "active"
    OFFER = "offer"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class MovementType(str, enum.Enum):
    STOCK_IN = "stock_in"
    USED = "used"
    WASTE = "waste"
    ADJUSTMENT = "adjustment"
    EXPIRED = "expired"


class MovementItemType(str, enum.Enum):
    INGREDIENT = "ingredient"
    PREPARED = "prepared"


class Restaurant(Base):
    """Restaurant model"""

    __tablename__ = "restaurants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)  # For subdomain routing: pizza-palace
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    theme_color = Column(String(7), default="#000000")  # Hex color

    # Contact information
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)

    # Location & Currency
    country = Column(String(100), nullable=True, default="United States")
    currency_code = Column(String(3), nullable=True, default="USD")  # ISO 4217 currency code
    currency_symbol = Column(String(10), nullable=True, default="$")

    # Billing Configuration
    per_table_booking_fee = Column(Float, nullable=False, default=0.0)
    per_online_booking_fee = Column(Float, nullable=False, default=0.0)
    enable_booking_fees = Column(Boolean, default=False, nullable=False)
    last_invoice_date = Column(DateTime, nullable=True)  # Track when last invoice was generated

    # Subscription
    subscription_status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False)
    pricing_plan = Column(SQLEnum(PricingPlan), default=PricingPlan.BASIC, nullable=False)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)

    # Branding & Marketing
    banner_images = Column(JSONB, default=list)  # List of image URLs
    upcoming_events = Column(JSONB, default=list)  # List of event objects
    advertisements = Column(JSONB, default=list)  # List of ad objects

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    max_tables = Column(Integer, default=10, nullable=False)

    # Delivery Integrations
    uber_enabled = Column(Boolean, default=False, nullable=False)
    uber_store_id = Column(String(255), nullable=True)
    justeat_enabled = Column(Boolean, default=False, nullable=False)
    justeat_restaurant_id = Column(String(255), nullable=True)
    deliveroo_enabled = Column(Boolean, default=False, nullable=False)
    deliveroo_restaurant_id = Column(String(255), nullable=True)

    # Payment Integrations
    tripos_enabled = Column(Boolean, default=False, nullable=False)
    tripos_acceptor_id = Column(String(255), nullable=True)
    tripos_account_id = Column(String(255), nullable=True)
    tripos_account_token = Column(String(500), nullable=True)
    tripos_application_id = Column(String(255), nullable=True)
    tripos_lane_id = Column(Integer, nullable=True)
    tripos_environment = Column(String(10), default='cert', nullable=True)
    stripe_enabled = Column(Boolean, default=False, nullable=False)
    stripe_secret_key = Column(String(500), nullable=True)
    sumup_enabled = Column(Boolean, default=False, nullable=False)
    sumup_api_key = Column(String(500), nullable=True)

    # Partner & Tier
    tier = Column(String(20), default="enterprise", nullable=False)          # basic | enterprise
    billing_model = Column(String(20), default="per_booking", nullable=False) # per_booking | monthly
    monthly_charge = Column(Float, default=0.0, nullable=False)
    partner_id = Column(UUID(as_uuid=True), nullable=True, index=True)       # ref to auth-service Partner
    commission_type = Column(String(20), nullable=True)                      # percent | fixed
    commission_value = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    menu_items = relationship("MenuItem", back_populates="restaurant", cascade="all, delete-orphan")
    tables = relationship("Table", back_populates="restaurant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Restaurant(id={self.id}, name={self.name})>"


class MenuItem(Base):
    """Menu item model"""

    __tablename__ = "menu_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(SQLEnum(MenuItemCategory), nullable=False, index=True)
    price = Column(Float, nullable=False)
    image_url = Column(String(500), nullable=True)

    # Availability
    is_available = Column(Boolean, default=True, nullable=False)
    is_vegetarian = Column(Boolean, default=False, nullable=False)
    is_vegan = Column(Boolean, default=False, nullable=False)
    is_gluten_free = Column(Boolean, default=False, nullable=False)

    # Additional info
    preparation_time = Column(Integer, nullable=True)  # in minutes
    calories = Column(Integer, nullable=True)
    ingredients = Column(JSONB, default=list)  # List of ingredients
    allergens = Column(JSONB, default=list)  # List of allergens

    # Display order
    display_order = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="menu_items")

    def __repr__(self):
        return f"<MenuItem(id={self.id}, name={self.name}, price={self.price})>"


class Table(Base):
    """Table model"""

    __tablename__ = "tables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)

    table_number = Column(String(50), nullable=False)
    seat_count = Column(Integer, nullable=False)
    status = Column(SQLEnum(TableStatus), default=TableStatus.AVAILABLE, nullable=False, index=True)

    # QR Code
    qr_code_url = Column(Text, nullable=True)  # Base64 data URL can be very long
    qr_code_data = Column(Text, nullable=True)  # Unique identifier for table

    # Location (optional)
    floor = Column(String(50), nullable=True)
    section = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="tables")

    def __repr__(self):
        return f"<Table(id={self.id}, number={self.table_number}, seats={self.seat_count})>"


class Feedback(Base):
    """Customer feedback model"""

    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Feedback content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)

    # Customer info (optional)
    customer_name = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Feedback(id={self.id}, restaurant_id={self.restaurant_id}, rating={self.rating})>"


class Order(Base):
    """Order model"""

    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id = Column(UUID(as_uuid=True), ForeignKey("tables.id", ondelete="SET NULL"), nullable=True, index=True)

    # Order details
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)

    # Customer info (optional - for public QR orders)
    customer_name = Column(String(255), nullable=True)
    customer_phone = Column(String(20), nullable=True)

    # Pricing
    subtotal = Column(Float, nullable=False, default=0.0)
    tax = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)

    # Special instructions
    special_instructions = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    restaurant = relationship("Restaurant")
    table = relationship("Table")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, number={self.order_number}, status={self.status})>"


class OrderItem(Base):
    """Order item model - individual items in an order"""

    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True, index=True)

    # Item details (stored at time of order in case menu item changes)
    item_name = Column(String(255), nullable=False)
    item_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    # Special instructions for this item
    special_instructions = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")

    def __repr__(self):
        return f"<OrderItem(id={self.id}, name={self.item_name}, quantity={self.quantity})>"


class Invoice(Base):
    """Invoice model for billing periods"""

    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Invoice details
    invoice_number = Column(String(50), nullable=False, unique=True, index=True)

    # Billing period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)

    # Currency at time of invoice
    currency_code = Column(String(3), nullable=False)
    currency_symbol = Column(String(10), nullable=False)

    # Fees at time of invoice (snapshot)
    per_table_booking_fee = Column(Float, nullable=False)
    per_online_booking_fee = Column(Float, nullable=False)

    # Booking counts for this period
    total_table_bookings = Column(Integer, nullable=False, default=0)
    total_online_bookings = Column(Integer, nullable=False, default=0)

    # Calculated revenue
    table_booking_revenue = Column(Float, nullable=False, default=0.0)
    online_booking_revenue = Column(Float, nullable=False, default=0.0)
    total_revenue = Column(Float, nullable=False, default=0.0)

    # Status
    is_paid = Column(Boolean, default=False, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    restaurant = relationship("Restaurant")

    def __repr__(self):
        return f"<Invoice(id={self.id}, number={self.invoice_number}, total={self.total_revenue})>"


class InventoryItem(Base):
    """Raw ingredient / stock item"""

    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    category = Column(SQLEnum(InventoryCategory), nullable=False, default=InventoryCategory.OTHER, index=True)
    quantity = Column(Float, nullable=False, default=0.0)
    unit = Column(String(20), nullable=False, default="pieces")  # kg, g, L, ml, pieces, portions
    min_threshold = Column(Float, nullable=False, default=0.0)  # alert when below this
    cost_per_unit = Column(Float, nullable=True)
    supplier = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    recipes = relationship("Recipe", back_populates="inventory_item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<InventoryItem(id={self.id}, name={self.name}, qty={self.quantity}{self.unit})>"


class PreparedFood(Base):
    """Prepared / ready-to-sell food with expiry tracking"""

    __tablename__ = "prepared_food"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    batch_number = Column(String(50), nullable=True)
    prepared_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    status = Column(SQLEnum(PreparedFoodStatus), default=PreparedFoodStatus.ACTIVE, nullable=False, index=True)
    offer_discount = Column(Float, nullable=True)   # % discount when status=offer
    offer_price = Column(Float, nullable=True)      # fixed offer price (optional)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    menu_item = relationship("MenuItem")

    def __repr__(self):
        return f"<PreparedFood(id={self.id}, name={self.name}, expires={self.expires_at})>"


class Recipe(Base):
    """Bill of Materials — links menu items to ingredients with required quantities"""

    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)

    quantity_required = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    menu_item = relationship("MenuItem")
    inventory_item = relationship("InventoryItem", back_populates="recipes")

    def __repr__(self):
        return f"<Recipe(menu={self.menu_item_id}, ingredient={self.inventory_item_id}, qty={self.quantity_required})>"


class StockMovement(Base):
    """Audit trail for all inventory changes"""

    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    restaurant_id = Column(UUID(as_uuid=True), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    item_type = Column(SQLEnum(MovementItemType), nullable=False)
    item_name = Column(String(255), nullable=False)
    movement_type = Column(SQLEnum(MovementType), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)
    reason = Column(String(255), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)  # e.g. order_id
    created_by = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<StockMovement(item={self.item_name}, type={self.movement_type}, qty={self.quantity})>"


class PartnerInvoice(Base):
    """Monthly commission invoice for a partner"""

    __tablename__ = "partner_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    partner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    restaurants_count = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    total_commission = Column(Float, default=0.0)
    line_items = Column(JSONB, default=list)  # per-restaurant breakdown
    is_paid = Column(Boolean, default=False, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PartnerInvoice(id={self.id}, partner={self.partner_id}, commission={self.total_commission})>"
