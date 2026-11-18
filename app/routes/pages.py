from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database.database import get_session
from app.models.models import Product, Category, User

router = APIRouter()
templates = Jinja2Templates(directory="app/views")

@router.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    products = session.exec(select(Product).where(Product.is_active == True)).all()
    categories = session.exec(select(Category)).all()
    user = session.get(User, request.session.get("user_id")) if request.session.get("user_id") else None
    return templates.TemplateResponse(request, "customer/home.html",
                                      {"products": products, "categories": categories, "user": user})

@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse(request, "customer/about.html", {})

@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse(request, "customer/contact.html", {})
