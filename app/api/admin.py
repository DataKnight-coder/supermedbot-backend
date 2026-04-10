from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from uuid import UUID

router = APIRouter()

def verify_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

@router.post("/approve-user/{user_id}", dependencies=[Depends(verify_admin)])
def approve_user(user_id: UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_approved = True
    db.commit()
    
    return {"message": f"User {user.email} successfully approved."}
