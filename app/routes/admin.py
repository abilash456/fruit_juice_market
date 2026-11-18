from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database.database import get_session
from app.models.models import User, Product, Category, Order
from app.utils.dependencies import require_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/views")

@router.get("/admin", response_class=HTMLResponse)
def dashboard(request: Request, admin=Depends(require_admin), session: Session=Depends(get_session)):
    products = session.exec(select(Product)).all()
    orders = session.exec(select(Order).order_by(Order.created_at.desc())).all()
    customers = session.exec(select(User).where(User.role == "customer")).all()
    return templates.TemplateResponse(request, "admin/dashboard.html",
        {"products": products, "orders": orders, "customers": customers,
         "revenue": sum(o.total for o in orders if o.status != "Cancelled")})

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
