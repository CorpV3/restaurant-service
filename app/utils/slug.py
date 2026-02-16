"""
Slug generation utilities for multi-tenant SaaS
"""
import re
import unicodedata
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional


def generate_slug(text: str) -> str:
    """
    Generate a URL-friendly slug from text

    Examples:
        "Pizza Palace" -> "pizza-palace"
        "Joe's Café & Grill" -> "joes-cafe-grill"
        "The Best Restaurant!!" -> "the-best-restaurant"
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Convert to lowercase
    text = text.lower()

    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)

    # Remove leading/trailing hyphens
    text = text.strip('-')

    return text


async def generate_unique_slug(
    db: AsyncSession,
    restaurant_model,
    base_name: str,
    restaurant_id: Optional[str] = None
) -> str:
    """
    Generate a unique slug by appending numbers if needed

    Args:
        db: Database session
        restaurant_model: Restaurant SQLAlchemy model class
        base_name: Restaurant name to slugify
        restaurant_id: Current restaurant ID (for updates)

    Returns:
        Unique slug string

    Examples:
        "Pizza Palace" -> "pizza-palace"
        "Pizza Palace" (if exists) -> "pizza-palace-2"
        "Pizza Palace" (if 2 exists) -> "pizza-palace-3"
    """
    base_slug = generate_slug(base_name)
    slug = base_slug
    counter = 1

    while True:
        # Check if slug exists
        stmt = select(restaurant_model).where(restaurant_model.slug == slug)

        # Exclude current restaurant when updating
        if restaurant_id:
            stmt = stmt.where(restaurant_model.id != restaurant_id)

        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            return slug

        # Slug exists, try with number suffix
        counter += 1
        slug = f"{base_slug}-{counter}"
