from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database.database import get_session
from app.models.models import SupportTicket
from app.utils.dependencies import require_user

router = APIRouter()
templates = Jinja2Templates(directory="app/views")

@router.get("/support", response_class=HTMLResponse)
def support_page(request: Request, user=Depends(require_user), session: Session=Depends(get_session)):
    tickets = session.exec(select(SupportTicket).where(SupportTicket.user_id == user.id)
                           .order_by(SupportTicket.created_at.desc())).all()
    return templates.TemplateResponse(request, "customer/support.html", {"tickets": tickets, "error": None})

@router.post("/support")
def create_ticket(request: Request, subject: str=Form(...), category: str=Form(...),
                  message: str=Form(...), user=Depends(require_user), session: Session=Depends(get_session)):
    session.add(SupportTicket(user_id=user.id, subject=subject, category=category, message=message))
    session.commit()
    return RedirectResponse("/support", status_code=303)
