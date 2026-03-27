"""
Partner routes — commission calculation, invoice generation, dashboard
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from ..database import get_db
from ..models import Restaurant, Invoice, PartnerInvoice
from ..schemas import (
    PartnerInvoiceResponse,
    PartnerInvoiceGenerate,
    PartnerDashboardResponse,
    RestaurantResponse,
)
from shared.config.settings import settings
from shared.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("partner-routes-rs")
_security = HTTPBearer()


def _decode_jwt(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def _require_partner_or_admin(partner_id: UUID, payload: dict):
    role = payload.get("role", "")
    if role == "master_admin":
        return
    if role == "partner" and str(payload.get("partner_id")) == str(partner_id):
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _require_admin(payload: dict):
    if payload.get("role") != "master_admin":
        raise HTTPException(status_code=403, detail="Master admin only")


def _calc_commission(revenue: float, commission_type: str, commission_value: float) -> float:
    if commission_type == "percent":
        return round(revenue * commission_value / 100, 2)
    return round(commission_value, 2)  # fixed per restaurant


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/{partner_id}/dashboard", response_model=PartnerDashboardResponse)
async def partner_dashboard(
    partner_id: UUID,
    payload: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
):
    _require_partner_or_admin(partner_id, payload)

    q = select(Restaurant).where(Restaurant.partner_id == partner_id)
    result = await db.execute(q)
    restaurants = result.scalars().all()

    invoices_q = select(PartnerInvoice).where(PartnerInvoice.partner_id == partner_id)
    inv_result = await db.execute(invoices_q)
    invoices = inv_result.scalars().all()

    total_commission = sum(i.total_commission for i in invoices)
    unpaid = sum(i.total_commission for i in invoices if not i.is_paid)

    return PartnerDashboardResponse(
        partner_id=partner_id,
        total_restaurants=len(restaurants),
        active_restaurants=sum(1 for r in restaurants if r.is_active),
        total_invoices=len(invoices),
        total_commission_earned=total_commission,
        unpaid_commission=unpaid,
        restaurants=[
            {
                "id": str(r.id),
                "name": r.name,
                "tier": r.tier,
                "billing_model": r.billing_model,
                "monthly_charge": r.monthly_charge,
                "commission_type": r.commission_type,
                "commission_value": r.commission_value,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat(),
            }
            for r in restaurants
        ],
    )


# ─── Restaurants for a partner ────────────────────────────────────────────────

@router.get("/{partner_id}/restaurants")
async def partner_restaurants(
    partner_id: UUID,
    payload: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
):
    _require_partner_or_admin(partner_id, payload)
    q = select(Restaurant).where(Restaurant.partner_id == partner_id).order_by(Restaurant.created_at.desc())
    result = await db.execute(q)
    restaurants = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "slug": r.slug,
            "tier": r.tier,
            "billing_model": r.billing_model,
            "monthly_charge": r.monthly_charge,
            "commission_type": r.commission_type,
            "commission_value": r.commission_value,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat(),
        }
        for r in restaurants
    ]


# ─── Invoice generation ───────────────────────────────────────────────────────

@router.post("/{partner_id}/invoices/generate", response_model=PartnerInvoiceResponse, status_code=201)
async def generate_partner_invoice(
    partner_id: UUID,
    payload_body: PartnerInvoiceGenerate,
    jwt_payload: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(jwt_payload)

    # Strip timezone from datetimes
    period_start = payload_body.period_start.replace(tzinfo=None) if payload_body.period_start.tzinfo else payload_body.period_start
    period_end = payload_body.period_end.replace(tzinfo=None) if payload_body.period_end.tzinfo else payload_body.period_end

    # Get all restaurants for this partner
    q = select(Restaurant).where(and_(
        Restaurant.partner_id == partner_id,
        Restaurant.is_active == True,
    ))
    result = await db.execute(q)
    restaurants = result.scalars().all()

    if not restaurants:
        raise HTTPException(404, "No active restaurants found for this partner")

    line_items = []
    total_revenue = 0.0
    total_commission = 0.0

    for r in restaurants:
        comm_type = r.commission_type or "percent"
        comm_value = r.commission_value if r.commission_value is not None else 10.0

        if r.billing_model == "monthly":
            revenue = r.monthly_charge
        else:
            # per_booking: sum booking revenue from invoices in period
            inv_q = select(Invoice).where(and_(
                Invoice.restaurant_id == r.id,
                Invoice.period_start >= period_start,
                Invoice.period_end <= period_end,
            ))
            inv_result = await db.execute(inv_q)
            restaurant_invoices = inv_result.scalars().all()
            revenue = sum(i.total_revenue for i in restaurant_invoices)

        commission = _calc_commission(revenue, comm_type, comm_value)
        total_revenue += revenue
        total_commission += commission
        line_items.append({
            "restaurant_id": str(r.id),
            "restaurant_name": r.name,
            "billing_model": r.billing_model,
            "revenue": revenue,
            "commission_type": comm_type,
            "commission_value": comm_value,
            "commission": commission,
        })

    # Generate invoice number
    month_str = period_start.strftime("%Y%m")
    count_q = await db.execute(
        select(func.count()).select_from(PartnerInvoice).where(PartnerInvoice.partner_id == partner_id)
    )
    seq = (count_q.scalar() or 0) + 1
    invoice_number = f"PINV-{str(partner_id)[:8].upper()}-{month_str}-{seq:03d}"

    invoice = PartnerInvoice(
        partner_id=partner_id,
        invoice_number=invoice_number,
        period_start=period_start,
        period_end=period_end,
        restaurants_count=len(restaurants),
        total_revenue=round(total_revenue, 2),
        total_commission=round(total_commission, 2),
        line_items=line_items,
        notes=payload_body.notes,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    logger.info(f"Partner invoice generated: {invoice_number} commission={total_commission}")
    return invoice


# ─── Invoice list & detail ────────────────────────────────────────────────────

@router.get("/{partner_id}/invoices", response_model=List[PartnerInvoiceResponse])
async def list_partner_invoices(
    partner_id: UUID,
    payload: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
):
    _require_partner_or_admin(partner_id, payload)
    q = select(PartnerInvoice).where(PartnerInvoice.partner_id == partner_id).order_by(PartnerInvoice.period_start.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{partner_id}/invoices/{invoice_id}", response_model=PartnerInvoiceResponse)
async def get_partner_invoice(
    partner_id: UUID,
    invoice_id: UUID,
    payload: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
):
    _require_partner_or_admin(partner_id, payload)
    invoice = await db.get(PartnerInvoice, invoice_id)
    if not invoice or invoice.partner_id != partner_id:
        raise HTTPException(404, "Invoice not found")
    return invoice


@router.patch("/{partner_id}/invoices/{invoice_id}/mark-paid", response_model=PartnerInvoiceResponse)
async def mark_invoice_paid(
    partner_id: UUID,
    invoice_id: UUID,
    payload: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(payload)
    invoice = await db.get(PartnerInvoice, invoice_id)
    if not invoice or invoice.partner_id != partner_id:
        raise HTTPException(404, "Invoice not found")
    invoice.is_paid = True
    invoice.paid_at = datetime.utcnow()
    invoice.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(invoice)
    return invoice
