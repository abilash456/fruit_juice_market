from uuid import uuid4
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database.database import get_session
from app.models.models import (Product, Category, Order, OrderItem, WishlistItem, Review, User, Coupon)
from app.utils.dependencies import require_user, current_user
from datetime import datetime, timezone

router = APIRouter()
templates = Jinja2Templates(directory="app/views")

@router.get("/shop", response_class=HTMLResponse)
def shop(request: Request, q: str = "", category: int = 0, session: Session = Depends(get_session)):
    statement = select(Product).where(Product.is_active == True)
    if q.strip():
        statement = statement.where(Product.name.contains(q.strip()))
    if category:
        statement = statement.where(Product.category_id == category)
    products = session.exec(statement).all()
    categories = session.exec(select(Category)).all()
    return templates.TemplateResponse(request, "customer/shop.html",
                                      {"products": products, "categories": categories, "q": q, "category": category})


@router.get("/product/{product_id}", response_class=HTMLResponse)
def product_detail(
    request: Request,
    product_id: int,
    session: Session = Depends(get_session),
    user=Depends(current_user)
):
    product = session.get(Product, product_id)

    if not product or not product.is_active:
        raise HTTPException(404, "Product not found")

    review_rows = session.exec(
        select(Review, User)
        .join(User, Review.user_id == User.id)
        .where(
            Review.product_id == product_id,
            Review.is_approved == True
        )
        .order_by(Review.created_at.desc())
    ).all()

    reviews = [
        {
            "review": review,
            "user_name": customer.name
        }
        for review, customer in review_rows
    ]

    total_reviews = len(reviews)

    average_rating = (
        sum(item["review"].rating for item in reviews) / total_reviews
        if total_reviews > 0 else 0
    )

    return templates.TemplateResponse(
        request,
        "customer/product.html",
        {
            "product": product,
            "reviews": reviews,
            "total_reviews": total_reviews,
            "average_rating": round(average_rating, 1),
            "user": user,
            "review_status": request.query_params.get("review"),
        }
    )


def get_cart(request: Request):
    return request.session.setdefault("cart", {})

def calculate_coupon_discount(coupon, subtotal):
    if subtotal < coupon.minimum_order:
        return 0

    if coupon.discount_type == "percentage":
        discount = subtotal * coupon.discount_value / 100
    else:
        discount = coupon.discount_value

    if coupon.max_discount is not None:
        discount = min(discount, coupon.max_discount)

    return round(min(discount, subtotal), 2)

@router.post("/cart/add/{product_id}")
def add_to_cart(request: Request, product_id: int, quantity: int = Form(1),
                session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product or not product.is_active or quantity < 1 or quantity > product.stock:
        raise HTTPException(400, "Invalid product or quantity.")
    cart = get_cart(request)
    cart[str(product_id)] = min(product.stock, int(cart.get(str(product_id), 0)) + quantity)
    request.session["cart"] = cart
    return RedirectResponse("/cart", status_code=303)

@router.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request, session: Session = Depends(get_session)):
    cart = request.session.get("cart", {})
    items = []
    total = 0

    for pid, qty in cart.items():
        product = session.get(Product, int(pid))

        if product and product.is_active:
            line = product.price * int(qty)
            items.append({
                "product": product,
                "quantity": int(qty),
                "line_total": line
            })
            total += line

    discount_amount = 0
    coupon = None
    coupon_code = request.session.get("coupon_code")

    if coupon_code:
        coupon = session.exec(
            select(Coupon).where(Coupon.code == coupon_code)
        ).first()

        if coupon and coupon.is_active:
            expired = False

            if coupon.expires_at:
                expiry = coupon.expires_at
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                expired = expiry < datetime.now(timezone.utc)

            usage_exhausted = (
                coupon.usage_limit is not None
                and coupon.used_count >= coupon.usage_limit
            )

            if not expired and not usage_exhausted:
                discount_amount = calculate_coupon_discount(
                    coupon, total
                )
            else:
                request.session.pop("coupon_code", None)
                request.session["coupon_message"] = (
                    "Your coupon is no longer valid."
                )
        else:
            request.session.pop("coupon_code", None)
            request.session["coupon_message"] = "Invalid coupon code."

    final_total = round(total - discount_amount, 2)

    coupon_message = request.session.pop("coupon_message", None)

    return templates.TemplateResponse(request, "customer/cart.html", {
        "items": items,
        "total": round(total, 2),
        "discount_amount": discount_amount,
        "final_total": final_total,
        "coupon_message": coupon_message,
        "coupon_code": coupon.code if coupon and discount_amount > 0 else None
    })

@router.post("/cart/update/{product_id}")
def update_cart(request: Request, product_id: int, quantity: int = Form(...),
                session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    cart = request.session.get("cart", {})
    if not product or quantity < 1 or quantity > product.stock:
        raise HTTPException(400, "Quantity is outside available stock.")
    cart[str(product_id)] = quantity
    request.session["cart"] = cart
    return RedirectResponse("/cart", status_code=303)

@router.post("/cart/remove/{product_id}")
def remove_cart(request: Request, product_id: int):
    cart = request.session.get("cart", {})
    cart.pop(str(product_id), None)
    request.session["cart"] = cart
    return RedirectResponse("/cart", status_code=303)

@router.post("/wishlist/add/{product_id}")
def wishlist_add(product_id: int, user=Depends(require_user), session: Session=Depends(get_session)):
    exists = session.exec(select(WishlistItem).where(WishlistItem.user_id == user.id,
                                                     WishlistItem.product_id == product_id)).first()
    if not exists and session.get(Product, product_id):
        session.add(WishlistItem(user_id=user.id, product_id=product_id)); session.commit()
    return RedirectResponse("/wishlist", status_code=303)

@router.get("/wishlist", response_class=HTMLResponse)
def wishlist_page(request: Request, user=Depends(require_user), session: Session=Depends(get_session)):
    rows = session.exec(select(WishlistItem).where(WishlistItem.user_id == user.id)).all()
    products = [session.get(Product, row.product_id) for row in rows]
    return templates.TemplateResponse(request, "customer/wishlist.html", {"products": [p for p in products if p]})

@router.post("/wishlist/remove/{product_id}")
def wishlist_remove(product_id: int, user=Depends(require_user), session: Session=Depends(get_session)):
    row = session.exec(select(WishlistItem).where(WishlistItem.user_id == user.id,
                                                  WishlistItem.product_id == product_id)).first()
    if row:
        session.delete(row); session.commit()
    return RedirectResponse("/wishlist", status_code=303)

@router.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request, user=Depends(require_user)):
    if not request.session.get("cart"):
        return RedirectResponse("/shop", status_code=303)
    return templates.TemplateResponse(request, "customer/checkout.html", {"user": user, "error": None})

@router.post("/checkout")
def checkout(
    request: Request,
    address: str = Form(...),
    phone: str = Form(...),
    user=Depends(require_user),
    session: Session = Depends(get_session)
):
    cart = request.session.get("cart", {})

    if not cart:
        return RedirectResponse("/shop", status_code=303)

    products = []
    subtotal = 0

    # Calculate cart subtotal
    for pid, qty in cart.items():
        product = session.get(Product, int(pid))
        qty = int(qty)

        if not product or not product.is_active or qty < 1 or qty > product.stock:
            raise HTTPException(
                400,
                "Cart contains an unavailable quantity. Please update it."
            )

        products.append((product, qty))
        subtotal += product.price * qty

    # Validate the applied coupon again
    discount_amount = 0
    coupon = None
    coupon_code = request.session.get("coupon_code")

    if coupon_code:
        coupon = session.exec(
            select(Coupon).where(Coupon.code == coupon_code)
        ).first()

        if not coupon or not coupon.is_active:
            request.session["coupon_message"] = "Invalid coupon. Please apply another coupon."
            request.session.pop("coupon_code", None)
            return RedirectResponse("/cart", status_code=303)

        if coupon.expires_at:
            expiry = coupon.expires_at

            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            if expiry < datetime.now(timezone.utc):
                request.session["coupon_message"] = "Coupon has expired."
                request.session.pop("coupon_code", None)
                return RedirectResponse("/cart", status_code=303)

        if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
            request.session["coupon_message"] = "Coupon usage limit reached."
            request.session.pop("coupon_code", None)
            return RedirectResponse("/cart", status_code=303)

        if subtotal < coupon.minimum_order:
            request.session["coupon_message"] = "Minimum order amount not reached."
            request.session.pop("coupon_code", None)
            return RedirectResponse("/cart", status_code=303)

        discount_amount = calculate_coupon_discount(coupon, subtotal)

    # Calculate final order amount
    final_total = round(subtotal - discount_amount, 2)

    # Create order with discounted total

    order = Order(
        order_number="FJM-" + uuid4().hex[:8].upper(),
        user_id=user.id,
        customer_name=user.name,
        address=address,
        phone=phone,
        total=final_total
    )

    session.add(order)
    session.flush()

    for product, qty in products:
        product.stock -= qty

        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=qty,
                unit_price=product.price
            )
        )

    if coupon:
        coupon.used_count += 1
        session.add(coupon)

    session.commit()

    # Clear cart and applied coupon
    request.session["cart"] = {}
    request.session.pop("coupon_code", None)
    request.session.pop("coupon_message", None)

    return RedirectResponse("/orders", status_code=303)

@router.get("/orders", response_class=HTMLResponse)
def orders_page(request: Request, user=Depends(require_user), session: Session=Depends(get_session)):
    orders = session.exec(select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())).all()
    return templates.TemplateResponse(request, "customer/orders.html", {"orders": orders})

@router.post("/cart/apply-coupon")
def apply_coupon(
    request: Request,
    coupon_code: str = Form(...),
    session: Session = Depends(get_session)
):
    code = coupon_code.strip().upper()

    cart = request.session.get("cart", {})
    if not cart:
        return RedirectResponse("/cart", status_code=303)

    coupon = session.exec(
        select(Coupon).where(Coupon.code == code)
    ).first()

    if not coupon or not coupon.is_active:
        request.session["coupon_message"] = "Invalid coupon code."
        request.session.pop("coupon_code", None)
        return RedirectResponse("/cart", status_code=303)

    if coupon.expires_at:
        expiry = coupon.expires_at

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if expiry < datetime.now(timezone.utc):
            request.session["coupon_message"] = "This coupon has expired."
            request.session.pop("coupon_code", None)
            return RedirectResponse("/cart", status_code=303)

    if coupon.usage_limit is not None:
        if coupon.used_count >= coupon.usage_limit:
            request.session["coupon_message"] = "Coupon usage limit reached."
            request.session.pop("coupon_code", None)
            return RedirectResponse("/cart", status_code=303)

    subtotal = 0

    for pid, qty in cart.items():
        product = session.get(Product, int(pid))

        if product and product.is_active:
            subtotal += product.price * int(qty)

    if subtotal < coupon.minimum_order:
        request.session["coupon_message"] = (
            f"Minimum order amount is ₹{coupon.minimum_order:.2f}."
        )
        request.session.pop("coupon_code", None)
        return RedirectResponse("/cart", status_code=303)

    request.session["coupon_code"] = coupon.code
    request.session["coupon_message"] = "Coupon applied successfully!"

    return RedirectResponse("/cart", status_code=303)

@router.post("/cart/remove-coupon")
def remove_coupon(request: Request):
    request.session.pop("coupon_code", None)
    request.session["coupon_message"] = "Coupon removed successfully."

    return RedirectResponse("/cart", status_code=303)
