"""
System routes — app announcements (news ticker) and app version management
"""
from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from ..database import get_db
from ..models import AppAnnouncement, AppVersion
from shared.config.settings import settings

router = APIRouter()
_security = HTTPBearer()
_security_optional = HTTPBearer(auto_error=False)


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


def _require_master_admin(payload: dict):
    if payload.get("role") != "master_admin":
        raise HTTPException(status_code=403, detail="Master admin only")


# ── Schemas ──────────────────────────────────────────────────────────────────

class AnnouncementCreate(BaseModel):
    message: str
    is_active: bool = True


class AnnouncementResponse(BaseModel):
    id: str
    message: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AppVersionUpsert(BaseModel):
    version_string: str
    download_url: str
    release_notes: Optional[str] = None


class AppVersionResponse(BaseModel):
    platform: str
    version_string: str
    download_url: str
    release_notes: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Announcement endpoints ────────────────────────────────────────────────────

@router.get("/announcements", response_model=List[AnnouncementResponse])
async def get_announcements(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    """Public — returns active announcements for the news ticker."""
    q = select(AppAnnouncement).order_by(AppAnnouncement.created_at.desc())
    if active_only:
        q = q.where(AppAnnouncement.is_active == True)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/announcements", response_model=AnnouncementResponse)
async def create_announcement(
    data: AnnouncementCreate,
    payload: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
):
    _require_master_admin(payload)
    announcement = AppAnnouncement(
        id=str(uuid.uuid4()),
        message=data.message,
        is_active=data.is_active,
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)
    return announcement


@router.patch("/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def toggle_announcement(
    announcement_id: str,
    data: dict,
    payload: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
):
    _require_master_admin(payload)
    result = await db.execute(select(AppAnnouncement).where(AppAnnouncement.id == announcement_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if "is_active" in data:
        ann.is_active = data["is_active"]
    if "message" in data:
        ann.message = data["message"]
    await db.commit()
    await db.refresh(ann)
    return ann


@router.delete("/announcements/{announcement_id}", status_code=204)
async def delete_announcement(
    announcement_id: str,
    payload: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
):
    _require_master_admin(payload)
    result = await db.execute(select(AppAnnouncement).where(AppAnnouncement.id == announcement_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    await db.delete(ann)
    await db.commit()


# ── App version endpoints ─────────────────────────────────────────────────────

@router.get("/app-versions", response_model=List[AppVersionResponse])
async def get_all_versions(db: AsyncSession = Depends(get_db)):
    """Public — returns latest version info for all platforms."""
    result = await db.execute(select(AppVersion))
    return result.scalars().all()


@router.get("/app-versions/{platform}", response_model=AppVersionResponse)
async def get_version(platform: str, db: AsyncSession = Depends(get_db)):
    """Public — returns latest version for a specific platform."""
    result = await db.execute(select(AppVersion).where(AppVersion.platform == platform))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail=f"No version info for platform '{platform}'")
    return v


@router.put("/app-versions/{platform}", response_model=AppVersionResponse)
async def upsert_version(
    platform: str,
    data: AppVersionUpsert,
    payload: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
):
    _require_master_admin(payload)
    if platform not in ("windows", "android", "ios"):
        raise HTTPException(status_code=400, detail="Platform must be 'windows', 'android', or 'ios'")
    result = await db.execute(select(AppVersion).where(AppVersion.platform == platform))
    v = result.scalar_one_or_none()
    if v:
        v.version_string = data.version_string
        v.download_url = data.download_url
        v.release_notes = data.release_notes
        v.updated_at = datetime.utcnow()
    else:
        v = AppVersion(
            id=str(uuid.uuid4()),
            platform=platform,
            version_string=data.version_string,
            download_url=data.download_url,
            release_notes=data.release_notes,
            updated_at=datetime.utcnow(),
        )
        db.add(v)
    await db.commit()
    await db.refresh(v)
    return v
