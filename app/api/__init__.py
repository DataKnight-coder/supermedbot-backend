from fastapi import APIRouter
from . import auth, questions

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
