"""
Restaurant management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from uuid import UUID
from ..database import get_db
from ..models import Restaurant, MenuItem, Table, Feedback, Invoice, Order
from ..schemas import (
    RestaurantCreate,
    RestaurantUpdate,
    RestaurantResponse,
    RestaurantBranding,
    RestaurantAnalytics,
    RestaurantBilling,
    InvoiceCreate,
    InvoiceResponse,
    MessageResponse
)
from ..utils.slug import generate_unique_slug
from shared.models.enums import UserRole, TableStatus
from shared.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("restaurant-routes")


@router.post("", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
async def create_restaurant(
    restaurant_data: RestaurantCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new restaurant (Master Admin only)
    Automatically generates unique slug for subdomain: pizza-palace.yourapp.com
    """
    # Generate unique slug from restaurant name
    slug = restaurant_data.slug or await generate_unique_slug(db, Restaurant, restaurant_data.name)

    # Create new restaurant
    new_restaurant = Restaurant(
        name=restaurant_data.name,
        slug=slug,
        description=restaurant_data.description,
        email=restaurant_data.email,
        phone=restaurant_data.phone,
        address=restaurant_data.address,
        website=str(restaurant_data.website) if restaurant_data.website else None,
        theme_color=restaurant_data.theme_color,
        country=restaurant_data.country,
        currency_code=restaurant_data.currency_code,
        currency_symbol=restaurant_data.currency_symbol,
        pricing_plan=restaurant_data.pricing_plan,
        max_tables=restaurant_data.max_tables,
        per_table_booking_fee=restaurant_data.per_table_booking_fee,
        per_online_booking_fee=restaurant_data.per_online_booking_fee,
        enable_booking_fees=restaurant_data.enable_booking_fees,
        is_active=True
    )

    db.add(new_restaurant)
    await db.commit()
    await db.refresh(new_restaurant)

    logger.info(f"Restaurant created: {new_restaurant.name} (Slug: {slug}, ID: {new_restaurant.id})")

    return new_restaurant


@router.get("", response_model=List[RestaurantResponse])
async def list_restaurants(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all restaurants (Master Admin only)
    """
    query = select(Restaurant)

    if is_active is not None:
        query = query.where(Restaurant.is_active == is_active)

    query = query.offset(skip).limit(limit).order_by(Restaurant.created_at.desc())

    result = await db.execute(query)
    restaurants = result.scalars().all()

    return restaurants


@router.get("/slug/{slug}", response_model=RestaurantResponse)
async def get_restaurant_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get restaurant by slug (for tenant resolution)
    Used for subdomain routing: pizza-palace.yourapp.com
    """
    result = await db.execute(
        select(Restaurant).where(
            Restaurant.slug == slug,
            Restaurant.is_active == True
        )
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Restaurant with slug '{slug}' not found or inactive"
        )

    return restaurant


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant(
    restaurant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get restaurant by ID
    """
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    return restaurant


@router.put("/{restaurant_id}", response_model=RestaurantResponse)
async def update_restaurant(
    restaurant_id: UUID,
    restaurant_data: RestaurantUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update restaurant details (Restaurant Admin or Master Admin)
    """
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Update fields
    update_data = restaurant_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if field == "website" and value:
                setattr(restaurant, field, str(value))
            else:
                setattr(restaurant, field, value)

    await db.commit()
    await db.refresh(restaurant)

    logger.info(f"Restaurant updated: {restaurant.name} (ID: {restaurant_id})")

    return restaurant


@router.patch("/{restaurant_id}/branding", response_model=RestaurantResponse)
async def update_restaurant_branding(
    restaurant_id: UUID,
    branding_data: RestaurantBranding,
    db: AsyncSession = Depends(get_db)
):
    """
    Update restaurant branding (logo, theme, banners, events, ads)
    """
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Update branding fields
    if branding_data.logo_url is not None:
        restaurant.logo_url = branding_data.logo_url
    if branding_data.theme_color is not None:
        restaurant.theme_color = branding_data.theme_color
    if branding_data.banner_images is not None:
        restaurant.banner_images = branding_data.banner_images
    if branding_data.upcoming_events is not None:
        restaurant.upcoming_events = branding_data.upcoming_events
    if branding_data.advertisements is not None:
        restaurant.advertisements = branding_data.advertisements

    await db.commit()
    await db.refresh(restaurant)

    logger.info(f"Restaurant branding updated: {restaurant.name}")

    return restaurant


@router.delete("/{restaurant_id}", response_model=MessageResponse)
async def delete_restaurant(
    restaurant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete restaurant (Master Admin only)
    """
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    await db.delete(restaurant)
    await db.commit()

    logger.info(f"Restaurant deleted: {restaurant.name} (ID: {restaurant_id})")

    return MessageResponse(message="Restaurant deleted successfully")


@router.patch("/{restaurant_id}/toggle-status", response_model=RestaurantResponse)
async def toggle_restaurant_status(
    restaurant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle restaurant active status (Master Admin only)
    """
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    restaurant.is_active = not restaurant.is_active
    await db.commit()
    await db.refresh(restaurant)

    logger.info(f"Restaurant status toggled: {restaurant.name} -> {'active' if restaurant.is_active else 'inactive'}")

    return restaurant


@router.get("/{restaurant_id}/analytics", response_model=RestaurantAnalytics)
async def get_restaurant_analytics(
    restaurant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get restaurant analytics
    """
    # Check if restaurant exists
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Count menu items
    menu_count_result = await db.execute(
        select(func.count(MenuItem.id)).where(MenuItem.restaurant_id == restaurant_id)
    )
    total_menu_items = menu_count_result.scalar() or 0

    # Count tables by status
    tables_result = await db.execute(
        select(Table).where(Table.restaurant_id == restaurant_id)
    )
    tables = tables_result.scalars().all()
    total_tables = len(tables)
    available_tables = sum(1 for t in tables if t.status == TableStatus.AVAILABLE)
    occupied_tables = sum(1 for t in tables if t.status == TableStatus.OCCUPIED)

    # Count feedback and average rating
    feedback_result = await db.execute(
        select(Feedback).where(Feedback.restaurant_id == restaurant_id)
    )
    feedbacks = feedback_result.scalars().all()
    total_feedback = len(feedbacks)
    average_rating = sum(f.rating for f in feedbacks) / total_feedback if total_feedback > 0 else 0.0

    # Menu items by category
    menu_items_result = await db.execute(
        select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)
    )
    menu_items = menu_items_result.scalars().all()
    menu_items_by_category = {}
    for item in menu_items:
        category = item.category.value
        menu_items_by_category[category] = menu_items_by_category.get(category, 0) + 1

    return RestaurantAnalytics(
        total_menu_items=total_menu_items,
        total_tables=total_tables,
        available_tables=available_tables,
        occupied_tables=occupied_tables,
        total_feedback=total_feedback,
        average_rating=round(average_rating, 2),
        menu_items_by_category=menu_items_by_category
    )


@router.get("/{restaurant_id}/billing", response_model=RestaurantBilling)
async def get_restaurant_billing(
    restaurant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get restaurant billing information and revenue from booking fees
    Returns billing configuration and calculated revenue based on order counts
    """
    # Check if restaurant exists
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Query actual order counts since last invoice (or restaurant creation)
    # Table bookings: orders with table_id NOT NULL
    # Online bookings: orders with table_id IS NULL
    period_start = restaurant.last_invoice_date or restaurant.created_at

    order_counts_query = await db.execute(
        select(
            func.count().filter(Order.table_id.isnot(None)).label('table_bookings'),
            func.count().filter(Order.table_id.is_(None)).label('online_bookings')
        ).where(
            Order.restaurant_id == restaurant.id,
            Order.created_at >= period_start
        )
    )
    order_counts = order_counts_query.first()
    total_table_bookings = order_counts.table_bookings if order_counts else 0
    total_online_bookings = order_counts.online_bookings if order_counts else 0

    # Calculate revenue based on configured fees
    table_booking_revenue = total_table_bookings * restaurant.per_table_booking_fee if restaurant.enable_booking_fees else 0.0
    online_booking_revenue = total_online_bookings * restaurant.per_online_booking_fee if restaurant.enable_booking_fees else 0.0
    total_revenue = table_booking_revenue + online_booking_revenue

    return RestaurantBilling(
        restaurant_id=restaurant.id,
        restaurant_name=restaurant.name,
        currency_symbol=restaurant.currency_symbol,
        enable_booking_fees=restaurant.enable_booking_fees,
        per_table_booking_fee=restaurant.per_table_booking_fee,
        per_online_booking_fee=restaurant.per_online_booking_fee,
        total_table_bookings=total_table_bookings,
        total_online_bookings=total_online_bookings,
        table_booking_revenue=table_booking_revenue,
        online_booking_revenue=online_booking_revenue,
        total_revenue=total_revenue
    )


@router.post("/{restaurant_id}/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def generate_invoice(
    restaurant_id: UUID,
    invoice_data: InvoiceCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate invoice for a restaurant billing period
    - Counts orders since last invoice (or restaurant creation)
    - Creates invoice with billing data
    - Updates restaurant.last_invoice_date to reset billing period
    """
    from datetime import datetime

    # Check if restaurant exists
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Determine billing period
    period_start = invoice_data.period_start or restaurant.last_invoice_date or restaurant.created_at
    period_end = invoice_data.period_end or datetime.utcnow()

    # Query actual order counts for the billing period
    # Table bookings: orders with table_id NOT NULL
    # Online bookings: orders with table_id IS NULL
    order_counts_query = await db.execute(
        select(
            func.count().filter(Order.table_id.isnot(None)).label('table_bookings'),
            func.count().filter(Order.table_id.is_(None)).label('online_bookings')
        ).where(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= period_start,
            Order.created_at <= period_end
        )
    )
    order_counts = order_counts_query.first()
    total_table_bookings = order_counts.table_bookings if order_counts else 0
    total_online_bookings = order_counts.online_bookings if order_counts else 0

    # Calculate revenue
    table_booking_revenue = total_table_bookings * restaurant.per_table_booking_fee if restaurant.enable_booking_fees else 0.0
    online_booking_revenue = total_online_bookings * restaurant.per_online_booking_fee if restaurant.enable_booking_fees else 0.0
    total_revenue = table_booking_revenue + online_booking_revenue

    # Generate invoice number
    invoice_count = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.restaurant_id == restaurant_id)
    )
    count = invoice_count.scalar() or 0
    invoice_number = f"INV-{restaurant.slug.upper()}-{count + 1:05d}"

    # Create invoice
    new_invoice = Invoice(
        restaurant_id=restaurant_id,
        invoice_number=invoice_number,
        period_start=period_start,
        period_end=period_end,
        currency_code=restaurant.currency_code,
        currency_symbol=restaurant.currency_symbol,
        per_table_booking_fee=restaurant.per_table_booking_fee,
        per_online_booking_fee=restaurant.per_online_booking_fee,
        total_table_bookings=total_table_bookings,
        total_online_bookings=total_online_bookings,
        table_booking_revenue=table_booking_revenue,
        online_booking_revenue=online_booking_revenue,
        total_revenue=total_revenue
    )

    db.add(new_invoice)

    # Update restaurant's last invoice date to reset billing period
    restaurant.last_invoice_date = period_end

    await db.commit()
    await db.refresh(new_invoice)

    logger.info(f"Invoice generated: {invoice_number} for {restaurant.name}, Total: {restaurant.currency_symbol}{total_revenue:.2f}")

    return new_invoice


@router.get("/{restaurant_id}/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    restaurant_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    List all invoices for a restaurant
    """
    # Check if restaurant exists
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Fetch invoices
    query = select(Invoice).where(Invoice.restaurant_id == restaurant_id)
    query = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit)

    invoices_result = await db.execute(query)
    invoices = invoices_result.scalars().all()

    return invoices


@router.get("/{restaurant_id}/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    restaurant_id: UUID,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific invoice by ID
    """
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.restaurant_id == restaurant_id
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    return invoice
