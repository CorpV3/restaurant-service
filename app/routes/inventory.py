"""
Inventory management routes — ingredients, prepared food, recipes, stock movements
"""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update

from ..database import get_db
from ..models import (
    InventoryItem, PreparedFood, Recipe, StockMovement,
    InventoryCategory, PreparedFoodStatus, MovementType, MovementItemType,
    MenuItem, Restaurant
)
from ..schemas import (
    InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse,
    PreparedFoodCreate, PreparedFoodUpdate, PreparedFoodResponse,
    RecipeCreate, RecipeResponse,
    StockMovementResponse, StockAdjustRequest,
    InventoryAlertsResponse, InventoryAlertItem,
)

router = APIRouter()


# ─── helpers ──────────────────────────────────────────────────────────────────

async def _get_restaurant(restaurant_id: UUID, db: AsyncSession):
    r = await db.get(Restaurant, restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return r


async def _log_movement(db, restaurant_id, item_id, item_type, item_name,
                        movement_type, quantity, unit=None, reason=None,
                        reference_id=None, created_by=None):
    mv = StockMovement(
        restaurant_id=restaurant_id, item_id=item_id, item_type=item_type,
        item_name=item_name, movement_type=movement_type, quantity=quantity,
        unit=unit, reason=reason, reference_id=reference_id, created_by=created_by
    )
    db.add(mv)


# ─── inventory items (ingredients) ────────────────────────────────────────────

@router.post("/{restaurant_id}/inventory/items", response_model=InventoryItemResponse, status_code=201)
async def create_inventory_item(restaurant_id: UUID, payload: InventoryItemCreate, db: AsyncSession = Depends(get_db)):
    await _get_restaurant(restaurant_id, db)
    item = InventoryItem(restaurant_id=restaurant_id, **payload.model_dump())
    db.add(item)
    await db.flush()
    await _log_movement(db, restaurant_id, item.id, MovementItemType.INGREDIENT,
                        item.name, MovementType.STOCK_IN, payload.quantity, payload.unit,
                        reason="Initial stock entry")
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/{restaurant_id}/inventory/items", response_model=List[InventoryItemResponse])
async def list_inventory_items(
    restaurant_id: UUID,
    category: Optional[InventoryCategory] = None,
    low_stock: bool = False,
    db: AsyncSession = Depends(get_db)
):
    await _get_restaurant(restaurant_id, db)
    q = select(InventoryItem).where(InventoryItem.restaurant_id == restaurant_id)
    if category:
        q = q.where(InventoryItem.category == category)
    if low_stock:
        q = q.where(InventoryItem.quantity <= InventoryItem.min_threshold)
    q = q.order_by(InventoryItem.name)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{restaurant_id}/inventory/items/{item_id}", response_model=InventoryItemResponse)
async def get_inventory_item(restaurant_id: UUID, item_id: UUID, db: AsyncSession = Depends(get_db)):
    item = await db.get(InventoryItem, item_id)
    if not item or item.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.patch("/{restaurant_id}/inventory/items/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(restaurant_id: UUID, item_id: UUID, payload: InventoryItemUpdate, db: AsyncSession = Depends(get_db)):
    item = await db.get(InventoryItem, item_id)
    if not item or item.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{restaurant_id}/inventory/items/{item_id}", status_code=204)
async def delete_inventory_item(restaurant_id: UUID, item_id: UUID, db: AsyncSession = Depends(get_db)):
    item = await db.get(InventoryItem, item_id)
    if not item or item.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    await db.delete(item)
    await db.commit()


@router.post("/{restaurant_id}/inventory/items/{item_id}/adjust", response_model=InventoryItemResponse)
async def adjust_stock(restaurant_id: UUID, item_id: UUID, payload: StockAdjustRequest, db: AsyncSession = Depends(get_db)):
    item = await db.get(InventoryItem, item_id)
    if not item or item.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    item.quantity = max(0.0, item.quantity + payload.delta)
    item.updated_at = datetime.utcnow()
    mtype = MovementType.STOCK_IN if payload.delta > 0 else (
        MovementType.WASTE if payload.movement_type == "waste" else MovementType.ADJUSTMENT
    )
    await _log_movement(db, restaurant_id, item.id, MovementItemType.INGREDIENT,
                        item.name, mtype, abs(payload.delta), item.unit,
                        reason=payload.reason, created_by=payload.created_by)
    await db.commit()
    await db.refresh(item)
    return item


# ─── prepared food ─────────────────────────────────────────────────────────────

@router.post("/{restaurant_id}/inventory/prepared", response_model=PreparedFoodResponse, status_code=201)
async def create_prepared_food(restaurant_id: UUID, payload: PreparedFoodCreate, db: AsyncSession = Depends(get_db)):
    await _get_restaurant(restaurant_id, db)
    food = PreparedFood(restaurant_id=restaurant_id, **payload.model_dump())
    db.add(food)
    await db.flush()
    await _log_movement(db, restaurant_id, food.id, MovementItemType.PREPARED,
                        food.name, MovementType.STOCK_IN, payload.quantity,
                        reason="Prepared batch")
    await db.commit()
    await db.refresh(food)
    return food


@router.get("/{restaurant_id}/inventory/prepared", response_model=List[PreparedFoodResponse])
async def list_prepared_food(
    restaurant_id: UUID,
    status: Optional[PreparedFoodStatus] = None,
    expiring_within_hours: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    await _get_restaurant(restaurant_id, db)
    # Auto-expire items past their expiry date
    now = datetime.utcnow()
    await db.execute(
        update(PreparedFood)
        .where(and_(
            PreparedFood.restaurant_id == restaurant_id,
            PreparedFood.expires_at <= now,
            PreparedFood.status.in_([PreparedFoodStatus.ACTIVE, PreparedFoodStatus.OFFER])
        ))
        .values(status=PreparedFoodStatus.EXPIRED, updated_at=now)
    )
    await db.commit()

    q = select(PreparedFood).where(PreparedFood.restaurant_id == restaurant_id)
    if status:
        q = q.where(PreparedFood.status == status)
    if expiring_within_hours:
        cutoff = now + timedelta(hours=expiring_within_hours)
        q = q.where(and_(
            PreparedFood.expires_at <= cutoff,
            PreparedFood.expires_at > now,
            PreparedFood.status == PreparedFoodStatus.ACTIVE
        ))
    q = q.order_by(PreparedFood.expires_at)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{restaurant_id}/inventory/prepared/{food_id}", response_model=PreparedFoodResponse)
async def get_prepared_food(restaurant_id: UUID, food_id: UUID, db: AsyncSession = Depends(get_db)):
    food = await db.get(PreparedFood, food_id)
    if not food or food.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Prepared food not found")
    return food


@router.patch("/{restaurant_id}/inventory/prepared/{food_id}", response_model=PreparedFoodResponse)
async def update_prepared_food(restaurant_id: UUID, food_id: UUID, payload: PreparedFoodUpdate, db: AsyncSession = Depends(get_db)):
    food = await db.get(PreparedFood, food_id)
    if not food or food.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Prepared food not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(food, k, v)
    food.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(food)
    return food


@router.post("/{restaurant_id}/inventory/prepared/{food_id}/offer", response_model=PreparedFoodResponse)
async def convert_to_offer(restaurant_id: UUID, food_id: UUID, discount: float = Query(..., ge=1, le=99), db: AsyncSession = Depends(get_db)):
    food = await db.get(PreparedFood, food_id)
    if not food or food.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Prepared food not found")
    if food.status not in (PreparedFoodStatus.ACTIVE,):
        raise HTTPException(status_code=400, detail=f"Cannot convert {food.status.value} item to offer")
    food.status = PreparedFoodStatus.OFFER
    food.offer_discount = discount
    food.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(food)
    return food


@router.delete("/{restaurant_id}/inventory/prepared/{food_id}", status_code=204)
async def delete_prepared_food(restaurant_id: UUID, food_id: UUID, db: AsyncSession = Depends(get_db)):
    food = await db.get(PreparedFood, food_id)
    if not food or food.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Prepared food not found")
    await db.delete(food)
    await db.commit()


# ─── recipes (BOM) ─────────────────────────────────────────────────────────────

@router.post("/{restaurant_id}/inventory/recipes", response_model=RecipeResponse, status_code=201)
async def create_recipe(restaurant_id: UUID, payload: RecipeCreate, db: AsyncSession = Depends(get_db)):
    await _get_restaurant(restaurant_id, db)
    mi = await db.get(MenuItem, payload.menu_item_id)
    if not mi or mi.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Menu item not found")
    inv = await db.get(InventoryItem, payload.inventory_item_id)
    if not inv or inv.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    recipe = Recipe(restaurant_id=restaurant_id, **payload.model_dump())
    db.add(recipe)
    await db.commit()
    await db.refresh(recipe)
    return recipe


@router.get("/{restaurant_id}/inventory/recipes", response_model=List[RecipeResponse])
async def list_recipes(restaurant_id: UUID, menu_item_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    await _get_restaurant(restaurant_id, db)
    q = select(Recipe).where(Recipe.restaurant_id == restaurant_id)
    if menu_item_id:
        q = q.where(Recipe.menu_item_id == menu_item_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.delete("/{restaurant_id}/inventory/recipes/{recipe_id}", status_code=204)
async def delete_recipe(restaurant_id: UUID, recipe_id: UUID, db: AsyncSession = Depends(get_db)):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe or recipe.restaurant_id != restaurant_id:
        raise HTTPException(status_code=404, detail="Recipe not found")
    await db.delete(recipe)
    await db.commit()


# ─── stock movements ────────────────────────────────────────────────────────────

@router.get("/{restaurant_id}/inventory/movements", response_model=List[StockMovementResponse])
async def list_movements(
    restaurant_id: UUID,
    item_id: Optional[UUID] = None,
    movement_type: Optional[MovementType] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db)
):
    await _get_restaurant(restaurant_id, db)
    q = select(StockMovement).where(StockMovement.restaurant_id == restaurant_id)
    if item_id:
        q = q.where(StockMovement.item_id == item_id)
    if movement_type:
        q = q.where(StockMovement.movement_type == movement_type)
    q = q.order_by(StockMovement.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# ─── alerts ─────────────────────────────────────────────────────────────────────

@router.get("/{restaurant_id}/inventory/alerts", response_model=InventoryAlertsResponse)
async def get_alerts(restaurant_id: UUID, db: AsyncSession = Depends(get_db)):
    await _get_restaurant(restaurant_id, db)
    now = datetime.utcnow()

    # Low stock ingredients
    low_q = select(InventoryItem).where(and_(
        InventoryItem.restaurant_id == restaurant_id,
        InventoryItem.quantity <= InventoryItem.min_threshold,
        InventoryItem.min_threshold > 0
    ))
    low_result = await db.execute(low_q)
    low_items = low_result.scalars().all()

    # Expiring within 24h
    cutoff_24h = now + timedelta(hours=24)
    exp_q = select(PreparedFood).where(and_(
        PreparedFood.restaurant_id == restaurant_id,
        PreparedFood.expires_at <= cutoff_24h,
        PreparedFood.expires_at > now,
        PreparedFood.status == PreparedFoodStatus.ACTIVE
    ))
    exp_result = await db.execute(exp_q)
    expiring = exp_result.scalars().all()

    # Already expired but not yet marked
    expired_q = select(PreparedFood).where(and_(
        PreparedFood.restaurant_id == restaurant_id,
        PreparedFood.expires_at <= now,
        PreparedFood.status.in_([PreparedFoodStatus.ACTIVE, PreparedFoodStatus.OFFER])
    ))
    expired_result = await db.execute(expired_q)
    expired = expired_result.scalars().all()

    return InventoryAlertsResponse(
        low_stock=[InventoryAlertItem(id=i.id, name=i.name, quantity=i.quantity, unit=i.unit, min_threshold=i.min_threshold) for i in low_items],
        expiring_soon=[{"id": str(f.id), "name": f.name, "quantity": f.quantity, "expires_at": f.expires_at.isoformat(), "hours_left": round((f.expires_at - now).total_seconds() / 3600, 1)} for f in expiring],
        expired=[{"id": str(f.id), "name": f.name, "quantity": f.quantity, "expired_at": f.expires_at.isoformat()} for f in expired],
    )
