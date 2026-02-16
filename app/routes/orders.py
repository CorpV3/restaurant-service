"""
Order management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import secrets
from ..database import get_db
from ..models import Order, OrderItem, MenuItem, Table, Restaurant
from ..schemas import (
    OrderCreate,
    OrderResponse,
    OrderUpdateStatus,
    MessageResponse
)
from shared.models.enums import OrderStatus
from shared.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("order-routes")


def generate_order_number() -> str:
    """Generate a unique order number"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_suffix = secrets.token_hex(3).upper()
    return f"ORD-{timestamp}-{random_suffix}"


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new order (PUBLIC - no authentication required)
    Customers scan QR code and place orders directly
    """
    # Verify table exists and get restaurant_id
    result = await db.execute(
        select(Table).where(Table.id == order_data.table_id)
    )
    table = result.scalar_one_or_none()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    # Calculate order totals
    subtotal = 0.0
    order_items_data = []

    for item in order_data.items:
        # Get menu item details
        result = await db.execute(
            select(MenuItem).where(MenuItem.id == item.menu_item_id)
        )
        menu_item = result.scalar_one_or_none()

        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu item {item.menu_item_id} not found"
            )

        if not menu_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item '{menu_item.name}' is not available"
            )

        item_total = menu_item.price * item.quantity
        subtotal += item_total

        order_items_data.append({
            "menu_item_id": menu_item.id,
            "item_name": menu_item.name,
            "item_price": menu_item.price,
            "quantity": item.quantity,
            "special_instructions": item.special_instructions
        })

    # Calculate tax (10% for now - can be configurable per restaurant)
    tax = subtotal * 0.10
    total = subtotal + tax

    # Create order
    new_order = Order(
        restaurant_id=table.restaurant_id,
        table_id=order_data.table_id,
        order_number=generate_order_number(),
        status=OrderStatus.PENDING,
        customer_name=order_data.customer_name,
        customer_phone=order_data.customer_phone,
        special_instructions=order_data.special_instructions,
        subtotal=subtotal,
        tax=tax,
        total=total
    )

    db.add(new_order)
    await db.flush()  # Get order ID before adding items

    # Add order items
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=new_order.id,
            **item_data
        )
        db.add(order_item)

    await db.commit()
    await db.refresh(new_order)

    # Load items relationship
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == new_order.id)
    )
    order_with_items = result.scalar_one()

    logger.info(f"Order created: {new_order.order_number} for table {table.table_number}")

    return order_with_items


@router.get("/restaurants/{restaurant_id}/orders", response_model=List[OrderResponse])
async def list_orders(
    restaurant_id: UUID,
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    table_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    List all orders for a restaurant (CHEF/ADMIN)
    Filterable by status and table
    """
    # Build query
    query = select(Order).options(selectinload(Order.items)).where(
        Order.restaurant_id == restaurant_id
    )

    if status_filter:
        query = query.where(Order.status == status_filter)

    if table_id:
        query = query.where(Order.table_id == table_id)

    # Order by creation time (newest first)
    query = query.order_by(Order.created_at.desc()).limit(limit)

    result = await db.execute(query)
    orders = result.scalars().all()

    return orders


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific order by ID (PUBLIC - for order tracking)
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return order


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    status_update: OrderUpdateStatus,
    db: AsyncSession = Depends(get_db)
):
    """
    Update order status (CHEF/ADMIN only)
    Status flow: PENDING → CONFIRMED → PREPARING → READY → SERVED → COMPLETED
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Update status
    order.status = status_update.status

    # If order is completed or cancelled, set completed_at
    if status_update.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
        order.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(order)

    logger.info(f"Order {order.order_number} status updated to {status_update.status}")

    return order


@router.delete("/orders/{order_id}", response_model=MessageResponse)
async def cancel_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel an order (mark as CANCELLED)
    """
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status in [OrderStatus.COMPLETED, OrderStatus.SERVED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed or served order"
        )

    order.status = OrderStatus.CANCELLED
    order.completed_at = datetime.utcnow()

    await db.commit()

    logger.info(f"Order {order.order_number} cancelled")

    return MessageResponse(message="Order cancelled successfully")
