from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database.database import get_session
from app.models.models import User, Product, Category, Order, Review, Coupon
from app.utils.dependencies import require_admin
from datetime import datetime, timezone

router = APIRouter()
templates = Jinja2Templates(directory="app/views")

@router.get("/admin", response_class=HTMLResponse)
def dashboard(
    request: Request,
    admin=Depends(require_admin),
    session: Session = Depends(get_session)
):
    products = session.exec(select(Product)).all()

    orders = session.exec(
        select(Order).order_by(Order.created_at.desc())
    ).all()

    customers = session.exec(
        select(User).where(User.role == "customer")
    ).all()

    # Count pending customer reviews
    pending_reviews = session.exec(
        select(Review).where(Review.is_approved == False)
    ).all()

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "products": products,
            "orders": orders,
            "customers": customers,
            "revenue": sum(
                o.total for o in orders
                if o.status != "Cancelled"
            ),
            "pending_reviews": len(pending_reviews)
        }
    )

@router.get("/admin/products", response_class=HTMLResponse)
def admin_products(request: Request, admin=Depends(require_admin), session: Session=Depends(get_session)):
    return templates.TemplateResponse(request, "admin/products.html",
        {"products": session.exec(select(Product)).all(),
         "categories": session.exec(select(Category)).all()})

@router.post("/admin/products")
def create_product(name: str=Form(...), description: str=Form(...), price: float=Form(...),
                   stock: int=Form(...), category_id: int=Form(...), emoji: str=Form("🍹"),
                   admin=Depends(require_admin), session: Session=Depends(get_session)):
    if price <= 0 or stock < 0:
        return RedirectResponse("/admin/products", status_code=303)
    session.add(Product(name=name, description=description, price=price, original_price=price,
                        stock=stock, category_id=category_id, emoji=emoji))
    session.commit()
    return RedirectResponse("/admin/products", status_code=303)

@router.post("/admin/products/delete/{product_id}")
def delete_product(product_id: int, admin=Depends(require_admin), session: Session=Depends(get_session)):
    product = session.get(Product, product_id)
    if product:
        product.is_active = False
        session.add(product); session.commit()
    return RedirectResponse("/admin/products", status_code=303)

@router.post("/admin/orders/{order_id}/status")
def update_order(order_id: int, status: str=Form(...), admin=Depends(require_admin),
                 session: Session=Depends(get_session)):
    allowed = {"Pending", "Confirmed", "Processing", "Shipped", "Out for Delivery", "Delivered", "Cancelled"}
    order = session.get(Order, order_id)
    if order and status in allowed:
        order.status = status
        session.add(order); session.commit()
    return RedirectResponse("/admin", status_code=303)

# ADMIN REVIEW MANAGEMENT

@router.get("/admin/reviews", response_class=HTMLResponse)
def admin_reviews(
    request: Request,
    admin=Depends(require_admin),
    session: Session = Depends(get_session)
):
    review_rows = session.exec(
        select(Review, User, Product)
        .join(User, Review.user_id == User.id)
        .join(Product, Review.product_id == Product.id)
        .order_by(Review.created_at.desc())
    ).all()

    reviews = [
        {
            "review": review,
            "customer": customer,
            "product": product
        }
        for review, customer, product in review_rows
    ]

    return templates.TemplateResponse(
        request,
        "admin/reviews.html",
        {
            "reviews": reviews
        }
    )


# APPROVE REVIEW

@router.post("/admin/reviews/approve/{review_id}")
def approve_review(
    review_id: int,
    admin=Depends(require_admin),
    session: Session = Depends(get_session)
):
    review = session.get(Review, review_id)

    if review:
        review.is_approved = True
        session.add(review)
        session.commit()

    return RedirectResponse("/admin/reviews", status_code=303)


# DELETE REVIEW

@router.post("/admin/reviews/delete/{review_id}")
def delete_review(
    review_id: int,
    admin=Depends(require_admin),
    session: Session = Depends(get_session)
):
    review = session.get(Review, review_id)

    if review:
        session.delete(review)
        session.commit()

    return RedirectResponse("/admin/reviews", status_code=303)

# ADMIN COUPON MANAGEMENT

@router.get("/admin/coupons", response_class=HTMLResponse)
def admin_coupons(
    request: Request,
    admin=Depends(require_admin),
    session: Session = Depends(get_session)
):
    coupons = session.exec(
        select(Coupon).order_by(Coupon.created_at.desc())
    ).all()

    return templates.TemplateResponse(
        request,
        "admin/coupons.html",
        {
            "coupons": coupons
        }
    )

# CREATE NEW COUPON

@router.post("/admin/coupons/create")
def create_coupon(
    code: str = Form(...),
    discount_type: str = Form(...),
    discount_value: float = Form(...),
    minimum_order: float = Form(0),
    max_discount: float = Form(0),
    usage_limit: int = Form(0),
    expires_at: str = Form(""),
    admin=Depends(require_admin),
    session: Session = Depends(get_session)
):
    code = code.strip().upper()

    # Validate coupon details
    if not code or discount_type not in {"percentage", "fixed"}:
        return RedirectResponse("/admin/coupons", status_code=303)

    if discount_value <= 0:
        return RedirectResponse("/admin/coupons", status_code=303)

    if discount_type == "percentage" and discount_value > 100:
        return RedirectResponse("/admin/coupons", status_code=303)

    if minimum_order < 0 or max_discount < 0:
        return RedirectResponse("/admin/coupons", status_code=303)

    if usage_limit < 0:
        return RedirectResponse("/admin/coupons", status_code=303)

    # Check duplicate coupon code
    existing = session.exec(
        select(Coupon).where(Coupon.code == code)
    ).first()

    if existing:
        return RedirectResponse("/admin/coupons", status_code=303)

    # Convert expiry date
    expiry = None
    if expires_at:
        try:
            expiry = datetime.strptime(
                expires_at, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            return RedirectResponse("/admin/coupons", status_code=303)

    coupon = Coupon(
        code=code,
        discount_type=discount_type,
        discount_value=discount_value,
        minimum_order=minimum_order,
        max_discount=max_discount if max_discount > 0 else None,
        usage_limit=usage_limit if usage_limit > 0 else None,
        used_count=0,
        is_active=True,
        expires_at=expiry
    )

    session.add(coupon)
    session.commit()

    return RedirectResponse("/admin/coupons", status_code=303)

@router.post("/admin/coupons/{coupon_id}/delete")
def delete_coupon(
    coupon_id: int,
    admin=Depends(require_admin),
    session: Session = Depends(get_session)
):
    coupon = session.get(Coupon, coupon_id)

    if coupon:
        session.delete(coupon)
        session.commit()

    return RedirectResponse("/admin/coupons", status_code=303)
