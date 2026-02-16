"""
Table management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from ..database import get_db
from ..models import Table, Restaurant
from ..schemas import (
    TableCreate,
    TableUpdate,
    TableResponse,
    QRCodeResponse,
    MessageResponse
)
from ..qr_generator import generate_qr_code, regenerate_qr_code
from shared.models.enums import TableStatus
from shared.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("table-routes")


@router.post("/{restaurant_id}/tables", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    restaurant_id: UUID,
    table_data: TableCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new table for a restaurant
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

    # Check if table number already exists
    existing_table = await db.execute(
        select(Table).where(
            Table.restaurant_id == restaurant_id,
            Table.table_number == table_data.table_number
        )
    )
    if existing_table.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Table {table_data.table_number} already exists"
        )

    # Check max tables limit
    tables_count = await db.execute(
        select(Table).where(Table.restaurant_id == restaurant_id)
    )
    if len(tables_count.scalars().all()) >= restaurant.max_tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum tables limit ({restaurant.max_tables}) reached"
        )

    # Create table
    new_table = Table(
        restaurant_id=restaurant_id,
        table_number=table_data.table_number,
        seat_count=table_data.seat_count,
        floor=table_data.floor,
        section=table_data.section,
        status=TableStatus.AVAILABLE
    )

    db.add(new_table)
    await db.flush()  # Get the ID before generating QR code

    # Generate QR code
    qr_code_image, qr_url, qr_token = generate_qr_code(
        new_table.id,
        restaurant_id,
        table_data.table_number
    )

    new_table.qr_code_data = qr_code_image  # Base64 image for display
    new_table.qr_code_url = qr_url  # Actual URL that QR points to

    await db.commit()
    await db.refresh(new_table)

    logger.info(f"Table created: {new_table.table_number} for restaurant {restaurant_id}")

    return new_table


@router.get("/{restaurant_id}/tables", response_model=List[TableResponse])
async def list_tables(
    restaurant_id: UUID,
    status_filter: Optional[TableStatus] = Query(None, alias="status"),
    floor: Optional[str] = None,
    section: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    List all tables for a restaurant with optional filters
    """
    query = select(Table).where(Table.restaurant_id == restaurant_id)

    # Apply filters
    if status_filter is not None:
        query = query.where(Table.status == status_filter)
    if floor is not None:
        query = query.where(Table.floor == floor)
    if section is not None:
        query = query.where(Table.section == section)

    query = query.order_by(Table.table_number).offset(skip).limit(limit)

    result = await db.execute(query)
    tables = result.scalars().all()

    return tables


@router.get("/{restaurant_id}/tables/{table_id}", response_model=TableResponse)
async def get_table(
    restaurant_id: UUID,
    table_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific table
    """
    result = await db.execute(
        select(Table).where(
            Table.id == table_id,
            Table.restaurant_id == restaurant_id
        )
    )
    table = result.scalar_one_or_none()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    return table


@router.put("/{restaurant_id}/tables/{table_id}", response_model=TableResponse)
async def update_table(
    restaurant_id: UUID,
    table_id: UUID,
    table_data: TableUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update table details
    """
    result = await db.execute(
        select(Table).where(
            Table.id == table_id,
            Table.restaurant_id == restaurant_id
        )
    )
    table = result.scalar_one_or_none()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    # Check if new table number already exists (if changing)
    if table_data.table_number and table_data.table_number != table.table_number:
        existing = await db.execute(
            select(Table).where(
                Table.restaurant_id == restaurant_id,
                Table.table_number == table_data.table_number,
                Table.id != table_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table {table_data.table_number} already exists"
            )

    # Update fields
    update_data = table_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(table, field, value)

    await db.commit()
    await db.refresh(table)

    logger.info(f"Table updated: {table.table_number} (ID: {table_id})")

    return table


@router.delete("/{restaurant_id}/tables/{table_id}", response_model=MessageResponse)
async def delete_table(
    restaurant_id: UUID,
    table_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a table
    """
    result = await db.execute(
        select(Table).where(
            Table.id == table_id,
            Table.restaurant_id == restaurant_id
        )
    )
    table = result.scalar_one_or_none()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    await db.delete(table)
    await db.commit()

    logger.info(f"Table deleted: {table.table_number} (ID: {table_id})")

    return MessageResponse(message="Table deleted successfully")


@router.patch("/{restaurant_id}/tables/{table_id}/status", response_model=TableResponse)
async def update_table_status(
    restaurant_id: UUID,
    table_id: UUID,
    new_status: TableStatus,
    db: AsyncSession = Depends(get_db)
):
    """
    Update table status
    """
    result = await db.execute(
        select(Table).where(
            Table.id == table_id,
            Table.restaurant_id == restaurant_id
        )
    )
    table = result.scalar_one_or_none()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    table.status = new_status
    await db.commit()
    await db.refresh(table)

    logger.info(f"Table status updated: {table.table_number} -> {new_status.value}")

    return table


@router.post("/{restaurant_id}/tables/{table_id}/regenerate-qr", response_model=QRCodeResponse)
async def regenerate_table_qr_code(
    restaurant_id: UUID,
    table_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate QR code for a table
    """
    result = await db.execute(
        select(Table).where(
            Table.id == table_id,
            Table.restaurant_id == restaurant_id
        )
    )
    table = result.scalar_one_or_none()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    # Regenerate QR code
    qr_code_image, qr_url, qr_token = regenerate_qr_code(
        table.id,
        restaurant_id,
        table.table_number
    )

    table.qr_code_data = qr_code_image  # Base64 image for display
    table.qr_code_url = qr_url  # Actual URL that QR points to

    await db.commit()
    await db.refresh(table)

    logger.info(f"QR code regenerated for table: {table.table_number}")

    return QRCodeResponse(
        table_id=table.id,
        table_number=table.table_number,
        qr_code_url=qr_url,
        qr_code_data=qr_code_image
    )


@router.get("/{restaurant_id}/tables/{table_id}/qr-code", response_model=QRCodeResponse)
async def get_table_qr_code(
    restaurant_id: UUID,
    table_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get QR code for a table
    """
    result = await db.execute(
        select(Table).where(
            Table.id == table_id,
            Table.restaurant_id == restaurant_id
        )
    )
    table = result.scalar_one_or_none()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )

    if not table.qr_code_url:
        # Generate QR code if not exists
        qr_code_image, qr_url, qr_token = generate_qr_code(
            table.id,
            restaurant_id,
            table.table_number
        )
        table.qr_code_data = qr_code_image
        table.qr_code_url = qr_url
        await db.commit()

    return QRCodeResponse(
        table_id=table.id,
        table_number=table.table_number,
        qr_code_url=table.qr_code_url,
        qr_code_data=table.qr_code_data
    )
