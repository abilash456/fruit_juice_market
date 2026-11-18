from uuid import uuid4
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database.database import get_session
from app.models.models import Product, Category, Order, OrderItem, WishlistItem
from app.utils.dependencies import require_user

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
def product_detail(request: Request, product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(404, "Product not found")
    return templates.TemplateResponse(request, "customer/product.html", {"product": product})

def get_cart(request: Request):
    return request.session.setdefault("cart", {})

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
    items, total = [], 0
    for pid, qty in cart.items():
        product = session.get(Product, int(pid))
        if product and product.is_active:
            line = product.price * int(qty)
            items.append({"product": product, "quantity": int(qty), "line_total": line})
            total += line
    return templates.TemplateResponse(request, "customer/cart.html", {"items": items, "total": total})

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
def checkout(request: Request, address: str = Form(...), phone: str = Form(...),
             user=Depends(require_user), session: Session=Depends(get_session)):
    cart = request.session.get("cart", {})
    if not cart:
        return RedirectResponse("/shop", status_code=303)
    products, total = [], 0
    for pid, qty in cart.items():
        product = session.get(Product, int(pid))
        qty = int(qty)
        if not product or not product.is_active or qty < 1 or qty > product.stock:
            raise HTTPException(400, "Cart contains an unavailable quantity. Please update it.")
        products.append((product, qty)); total += product.price * qty
    order = Order(order_number="FJM-" + uuid4().hex[:8].upper(), user_id=user.id,
                  customer_name=user.name, address=address, phone=phone, total=total)
    session.add(order); session.commit(); session.refresh(order)
    for product, qty in products:
        product.stock -= qty
        session.add(OrderItem(order_id=order.id, product_id=product.id,
                              product_name=product.name, quantity=qty, unit_price=product.price))
    session.commit()
    request.session["cart"] = {}
    return RedirectResponse("/orders", status_code=303)

@router.get("/orders", response_class=HTMLResponse)
def orders_page(request: Request, user=Depends(require_user), session: Session=Depends(get_session)):
    orders = session.exec(select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())).all()
    return templates.TemplateResponse(request, "customer/orders.html", {"orders": orders})
