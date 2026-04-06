from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import UUID
from app.database import get_db
from app.models.question import Question
from app.models.response import Response
from app.schemas.question import QuestionResponse
from app.schemas.response import ResponseCreate, ResponseModel
from app.api.auth import get_current_user
from app.models.user import User
import json
import google.generativeai as genai
from typing import List
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()

genai.configure(api_key=settings.GEMINI_API_KEY)
def enforce_daily_limit(user: User, db: Session):
    # Enforce 230-question reset at UTC midnight
    now_utc = datetime.now(timezone.utc)
    start_of_day_utc = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    
    responses_today = db.query(Response).filter(
        Response.user_id == user.id,
        Response.created_at >= start_of_day_utc.replace(tzinfo=None) # Assuming DB stores naiive UTC timestamps like default
    ).count()

    if responses_today >= 230:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily question limit of 230 reached. Resets at UTC midnight."
        )

@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(question_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.post("/answer", response_model=ResponseModel)
def submit_answer(
    response_in: ResponseCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    enforce_daily_limit(current_user, db)
    
    question = db.query(Question).filter(Question.id == response_in.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Evaluation Logic: strict exact matching of submitted technical data vs correct technical data
    is_correct = (response_in.submitted_technical_data == question.correct_answer_technical_data)

    new_response = Response(
        user_id=current_user.id,
        session_id=response_in.session_id,
        question_id=response_in.question_id,
        submitted_technical_data=response_in.submitted_technical_data,
        is_correct=is_correct,
        created_at=datetime.utcnow()
    )
    
    db.add(new_response)
    db.commit()
    db.refresh(new_response)
    return new_response

class GenerateQuestionResponse(BaseModel):
    vignette: str
    options: List[str]
    correctAnswer: str
    explanation: str

@router.post("/generate", response_model=GenerateQuestionResponse)
def generate_question(current_user: User = Depends(get_current_user)):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    You are an expert medical educator writing questions for Canadian medical licensing exams (MCCQE Part 1 / TDM).
    Generate a challenging, high-quality clinical vignette at this difficulty level. 
    It must include:
    - A detailed patient presentation, history, and relevant lab/imaging findings.
    - 5 plausible multiple-choice options (A to E) assessing diagnosis, next step in management, or underlying pathophysiology.
    - The correct answer.
    - A thorough explanation of why the correct answer is right and why the distractors are wrong.
    
    You MUST output ONLY valid, raw JSON with absolutely NO markdown formatting, NO html formatting, NO code blocks, and NO extra text.
    The JSON must strictly match this exact schema:
    {
      "vignette": "The clinical scenario...",
      "options": [
        "A. Option one",
        "B. Option two",
        "C. Option three",
        "D. Option four",
        "E. Option five"
      ],
      "correctAnswer": "A",
      "explanation": "The clinical rationale for the correct answer."
    }
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        question_data = json.loads(response.text)
        return question_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate medical vignette: {str(e)}"
        )
