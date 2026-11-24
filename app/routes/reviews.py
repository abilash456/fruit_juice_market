
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database.database import get_session
from app.models.models import Review, Product
from app.utils.dependencies import require_user


router = APIRouter()
templates = Jinja2Templates(directory="app/views")


@router.post("/reviews/{product_id}")
def add_review(
    product_id: int,
    request: Request,
    rating: int = Form(...),
    comment: str = Form(...),
    session: Session = Depends(get_session),
    user=Depends(require_user)
):
    # Check rating
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5.")

    # Check comment
    comment = comment.strip()

    if not comment:
        raise HTTPException(status_code=400, detail="Please write a review.")

    # Check product
    product = session.get(Product, product_id)

    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found.")

    # Prevent duplicate reviews by the same customer
    existing_review = session.exec(
        select(Review).where(
            Review.user_id == user.id,
            Review.product_id == product_id
        )
    ).first()

    if existing_review:
        existing_review.rating = rating
        existing_review.comment = comment

        # Require admin approval again after editing
        existing_review.is_approved = False

        session.add(existing_review)
        session.commit()

        return RedirectResponse(
            f"/product/{product_id}?review=updated",
            status_code=303
        )

    # Save review
    review = Review(
        user_id=user.id,
        product_id=product_id,
        rating=rating,
        comment=comment,
        is_approved=False,
        created_at=datetime.now(timezone.utc)
    )

    session.add(review)
    session.commit()

    return RedirectResponse(
        f"/product/{product_id}?review=success",
        status_code=303
    )
