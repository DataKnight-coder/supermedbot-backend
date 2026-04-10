from fastapi import APIRouter
from . import auth, questions, admin

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
