"""
Menu item management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import os
import shutil
from pathlib import Path
from datetime import datetime
from ..database import get_db
from ..models import MenuItem, Restaurant
from ..schemas import (
    MenuItemCreate,
    MenuItemUpdate,
    MenuItemResponse,
    MessageResponse
)
from shared.models.enums import MenuItemCategory
from shared.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("menu-item-routes")

# Image upload configuration
UPLOAD_DIR = Path("/app/uploads/menu-items")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".avif", ".svg"}


@router.post("/{restaurant_id}/menu-items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    restaurant_id: UUID,
    item_data: MenuItemCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new menu item for a restaurant
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

    # Create menu item
    new_item = MenuItem(
        restaurant_id=restaurant_id,
        name=item_data.name,
        description=item_data.description,
        category=item_data.category,
        price=item_data.price,
        image_url=item_data.image_url,
        is_vegetarian=item_data.is_vegetarian,
        is_vegan=item_data.is_vegan,
        is_gluten_free=item_data.is_gluten_free,
        preparation_time=item_data.preparation_time,
        calories=item_data.calories,
        ingredients=item_data.ingredients or [],
        allergens=item_data.allergens or [],
        display_order=item_data.display_order,
        is_available=True
    )

    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    logger.info(f"Menu item created: {new_item.name} for restaurant {restaurant_id}")

    return new_item


@router.get("/{restaurant_id}/menu-items", response_model=List[MenuItemResponse])
async def list_menu_items(
    restaurant_id: UUID,
    category: Optional[MenuItemCategory] = Query(None),
    is_available: Optional[bool] = Query(None),
    is_vegetarian: Optional[bool] = Query(None),
    is_vegan: Optional[bool] = Query(None),
    is_gluten_free: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    List all menu items for a restaurant with optional filters
    """
    query = select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)

    # Apply filters
    if category is not None:
        query = query.where(MenuItem.category == category)
    if is_available is not None:
        query = query.where(MenuItem.is_available == is_available)
    if is_vegetarian is not None:
        query = query.where(MenuItem.is_vegetarian == is_vegetarian)
    if is_vegan is not None:
        query = query.where(MenuItem.is_vegan == is_vegan)
    if is_gluten_free is not None:
        query = query.where(MenuItem.is_gluten_free == is_gluten_free)

    query = query.order_by(MenuItem.display_order, MenuItem.name).offset(skip).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    return items


@router.get("/{restaurant_id}/menu-items/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    restaurant_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific menu item
    """
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.restaurant_id == restaurant_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )

    return item


@router.put("/{restaurant_id}/menu-items/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    restaurant_id: UUID,
    item_id: UUID,
    item_data: MenuItemUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a menu item
    """
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.restaurant_id == restaurant_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )

    # Update fields
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(item, field, value)

    await db.commit()
    await db.refresh(item)

    logger.info(f"Menu item updated: {item.name} (ID: {item_id})")

    return item


@router.delete("/{restaurant_id}/menu-items/{item_id}", response_model=MessageResponse)
async def delete_menu_item(
    restaurant_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a menu item
    """
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.restaurant_id == restaurant_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )

    await db.delete(item)
    await db.commit()

    logger.info(f"Menu item deleted: {item.name} (ID: {item_id})")

    return MessageResponse(message="Menu item deleted successfully")


@router.patch("/{restaurant_id}/menu-items/{item_id}/toggle-availability", response_model=MenuItemResponse)
async def toggle_menu_item_availability(
    restaurant_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle menu item availability
    """
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.restaurant_id == restaurant_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )

    item.is_available = not item.is_available
    await db.commit()
    await db.refresh(item)

    logger.info(f"Menu item availability toggled: {item.name} -> {'available' if item.is_available else 'unavailable'}")

    return item


@router.get("/{restaurant_id}/menu-items/category/{category}", response_model=List[MenuItemResponse])
async def get_menu_items_by_category(
    restaurant_id: UUID,
    category: MenuItemCategory,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all menu items in a specific category
    """
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.restaurant_id == restaurant_id,
            MenuItem.category == category,
            MenuItem.is_available == True
        ).order_by(MenuItem.display_order, MenuItem.name)
    )
    items = result.scalars().all()

    return items



@router.post("/{restaurant_id}/menu-items/upload-image")
async def upload_menu_item_image(
    restaurant_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an image for a menu item
    Returns the URL of the uploaded image
    """
    # Verify restaurant exists
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        allowed_types = ", ".join(ALLOWED_EXTENSIONS)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {allowed_types}"
        )

    # Validate file size (max 5MB)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 5MB"
        )

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{restaurant_id}_{timestamp}{file_ext}"
    file_path = UPLOAD_DIR / filename

    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file"
        )

    # Return URL (you can customize this based on how you serve static files)
    image_url = f"/uploads/menu-items/{filename}"

    logger.info(f"Image uploaded: {filename} for restaurant {restaurant_id}")

    return {"image_url": image_url, "filename": filename}

