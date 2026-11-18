from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database.database import get_session
from app.models.models import User
from app.utils.security import hash_password, verify_password

router = APIRouter()
templates = Jinja2Templates(directory="app/views")

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "customer/register.html", {"error": None})

@router.post("/register")
def register(request: Request, name: str = Form(...), email: str = Form(...),
             password: str = Form(...), session: Session = Depends(get_session)):
    email = email.strip().lower()
    if len(password) < 8:
        return templates.TemplateResponse(request, "customer/register.html",
                                           {"error": "Password must contain at least 8 characters."}, status_code=400)
    if session.exec(select(User).where(User.email == email)).first():
        return templates.TemplateResponse(request, "customer/register.html",
                                           {"error": "An account with this email already exists."}, status_code=400)
    user = User(name=name.strip(), email=email, password_hash=hash_password(password))
    session.add(user); session.commit(); session.refresh(user)
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "customer/login.html", {"error": None})

@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...),
          session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == email.strip().lower())).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request, "customer/login.html",
                                           {"error": "Email or password is incorrect."}, status_code=400)
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse("/admin" if user.role == "admin" else "/", status_code=303)

@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
