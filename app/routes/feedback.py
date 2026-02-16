"""
Customer feedback routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from ..database import get_db
from ..models import Feedback, Restaurant
from ..schemas import FeedbackCreate, FeedbackResponse, MessageResponse
from shared.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("feedback-routes")


@router.post("/{restaurant_id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    restaurant_id: UUID,
    feedback_data: FeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit customer feedback for a restaurant
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

    # Create feedback
    new_feedback = Feedback(
        restaurant_id=restaurant_id,
        table_id=feedback_data.table_id,
        rating=feedback_data.rating,
        comment=feedback_data.comment,
        customer_name=feedback_data.customer_name,
        customer_email=feedback_data.customer_email
    )

    db.add(new_feedback)
    await db.commit()
    await db.refresh(new_feedback)

    logger.info(f"Feedback submitted for restaurant {restaurant_id}: Rating {feedback_data.rating}/5")

    return new_feedback


@router.get("/{restaurant_id}/feedback", response_model=List[FeedbackResponse])
async def list_feedback(
    restaurant_id: UUID,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
    days: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    List all feedback for a restaurant with optional filters
    """
    query = select(Feedback).where(Feedback.restaurant_id == restaurant_id)

    # Apply filters
    if min_rating is not None:
        query = query.where(Feedback.rating >= min_rating)
    if max_rating is not None:
        query = query.where(Feedback.rating <= max_rating)
    if days is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.where(Feedback.created_at >= cutoff_date)

    query = query.order_by(Feedback.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    feedbacks = result.scalars().all()

    return feedbacks


@router.get("/{restaurant_id}/feedback/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    restaurant_id: UUID,
    feedback_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific feedback
    """
    result = await db.execute(
        select(Feedback).where(
            Feedback.id == feedback_id,
            Feedback.restaurant_id == restaurant_id
        )
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    return feedback


@router.delete("/{restaurant_id}/feedback/{feedback_id}", response_model=MessageResponse)
async def delete_feedback(
    restaurant_id: UUID,
    feedback_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete feedback (Admin only)
    """
    result = await db.execute(
        select(Feedback).where(
            Feedback.id == feedback_id,
            Feedback.restaurant_id == restaurant_id
        )
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )

    await db.delete(feedback)
    await db.commit()

    logger.info(f"Feedback deleted: {feedback_id}")

    return MessageResponse(message="Feedback deleted successfully")


@router.get("/{restaurant_id}/feedback/stats/summary")
async def get_feedback_summary(
    restaurant_id: UUID,
    days: Optional[int] = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Get feedback summary statistics
    """
    query = select(Feedback).where(Feedback.restaurant_id == restaurant_id)

    if days is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.where(Feedback.created_at >= cutoff_date)

    result = await db.execute(query)
    feedbacks = result.scalars().all()

    if not feedbacks:
        return {
            "total_feedback": 0,
            "average_rating": 0.0,
            "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "period_days": days
        }

    # Calculate statistics
    total_feedback = len(feedbacks)
    average_rating = sum(f.rating for f in feedbacks) / total_feedback
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for feedback in feedbacks:
        rating_distribution[feedback.rating] += 1

    return {
        "total_feedback": total_feedback,
        "average_rating": round(average_rating, 2),
        "rating_distribution": rating_distribution,
        "period_days": days,
        "five_star_percentage": round((rating_distribution[5] / total_feedback) * 100, 1),
        "four_plus_percentage": round(((rating_distribution[4] + rating_distribution[5]) / total_feedback) * 100, 1)
    }
