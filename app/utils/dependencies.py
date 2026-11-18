from fastapi import Request, Depends, HTTPException
from sqlmodel import Session
from app.database.database import get_session
from app.models.models import User

def current_user(request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return session.get(User, user_id)

def require_user(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Please log in first.")
    return user

def require_admin(request: Request, session: Session = Depends(get_session)):
    user = require_user(request, session)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user
