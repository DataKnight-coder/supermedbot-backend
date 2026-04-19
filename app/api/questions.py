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
from openai import OpenAI, AsyncOpenAI
import os
import asyncio
import re
from typing import List
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()
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

class GenerateRequest(BaseModel):
    category: str
    mode: str = "practice"
    count: int = 1

class GenerateQuestionResponse(BaseModel):
    text: str = ""
    options: List[str]
    correctAnswer: str = "A"
    explanation: str = ""

@router.post("/generate", response_model=List[GenerateQuestionResponse])
async def generate_question(request: GenerateRequest):
    tutor_logic = ""
    sprint_logic = ""
    tdm_logic = ""
    batch_mode_logic = ""
    mode_lower = request.mode.lower()
    cat_lower = request.category.lower()
    
    if mode_lower == "tutor":
        tutor_logic = "- Mention specific Canadian guidelines where applicable (e.g., SOGC, CPS, PHAC, Choosing Wisely Canada)."
        
    if mode_lower == "timed sprint":
        sprint_logic = "- Sprint Format: Keep the vignette highly concise (max 150 words). Focus strictly on 'Key Findings' and 'Next Best Step'. Avoid any unnecessary filler data to allow rapid 30-minute block processing.\n"
        
    persona = "a Chief Examiner for the Therapeutic Decision-Making (TDM) and MCCQE1 boards"
    if cat_lower == "emergency":
        persona = "an ER Chief Examiner for the Therapeutic Decision-Making (TDM) and MCCQE1 boards"
    elif cat_lower == "cleo":
        persona = "a Medical Ethicist, Legal Consultant, and Chief Examiner for the Therapeutic Decision-Making (TDM) and MCCQE1 boards"
    elif cat_lower == "public health":
        persona = "a Medical Officer of Health and Chief Examiner for the Therapeutic Decision-Making (TDM) and MCCQE1 boards"

    if cat_lower == "tdm":
        tdm_logic = "\n- TDM Specificity: Force high-complexity therapeutic scenarios. Include contraindications (e.g., prescribing in renal failure or pregnancy), drug-drug interactions, and side-effect management. Use Canadian brand names alongside generics (e.g., 'paliperidone palmitate (Invega)')."
        batch_mode_logic = "This session represents a 140-question high-difficulty therapeutic focus sprint."
    else:
        batch_mode_logic = "This session represents a 40-question clinical focus sprint."

    async def fetch_chunk(chunk_size: int):
        prompt = f"""
1. Role & Context:
Act as {persona}. Your goal is to generate high-fidelity, high-yield clinical vignettes for the MCCQE Part I and TDM exams. {batch_mode_logic}
You MUST generate EXACTLY {chunk_size} distinctly different clinical vignettes matching the criteria below.

2. Content Standards:
- Units: Strictly use SI Units (e.g., mmol/L for glucose, g/L for protein, μmol/L for creatinine).
- Structure: Every vignette must include Patient Age/Sex, Chief Complaint, HPI (Duration/Quality), relevant Physical Exam findings (Vitals/Signs), and Laboratory/Imaging results. Keep vignettes concise but loaded with 'distractor' clinical data (comorbidities, current medications).
{sprint_logic}- Category Logic: The requested category is '{request.category}'. Strictly constrain the scenario to this domain. For 'CLEO', focus on consent, capacity, and legal disclosure.{tdm_logic}

3. Question Difficulty & Requirements:
- Prohibit simple recall. Every question must require clinical analysis or management decisions. Focus on: 'Next best step,' 'Initial investigation of choice,' and 'Most appropriate pharmacotherapy.'
- Provide 5 distinct options (A through E). Ensure distractors are plausible but incorrect.

4. Explanations:
- The 'Explanation' must be exactly two sentences: The first sentence explains the correct physiological/clinical path; the second explains why the most tempting distractor was wrong.
{tutor_logic}

5. Response Format (CRITICAL):
Return ONLY a valid JSON object. No markdown, no extra text, no code block fences.
Use exactly this schema:
{{
  "questions": [
    {{
      "text": "Concise clinical vignette + question here.",
      "options": [
        "Administer X",
        "Order Y",
        "Prescribe Z",
        "Refer to W",
        "Observe and reassess"
      ],
      "correctAnswer": "A",
      "explanation": "One sentence why correct. One sentence why top distractor is wrong."
    }}
  ]
}}
"""
        
        client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        system_message = (
            'You are a fast, precise medical examiner generating MCCQE1 and TDM exam questions. '
            'Prioritize Clinical Reasoning and Next Best Step questions. Keep vignettes concise (under 120 words). '
            'Return ONLY a valid JSON object with a single key "questions" containing a list. '
            'Each item must have: "text" (string), "options" (list of exactly 5 plain strings WITHOUT A/B/C/D/E prefixes), '
            '"correctAnswer" (single uppercase letter A-E only), and "explanation" (two sentences max). '
            'No markdown, no code fences, no extra commentary.'
        )
        
        messages = [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            chat_completion = await client.chat.completions.create(
                messages=messages,
                model="gpt-4o-mini",
                response_format={"type": "json_object"}
            )
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                print(f"Rate limit hit on gpt-4o-mini. Retrying with a short delay...")
                await asyncio.sleep(2)
                chat_completion = await client.chat.completions.create(
                    messages=messages,
                    model="gpt-4o-mini",
                    response_format={"type": "json_object"}
                )
            else:
                raise e
        
        
        raw_text = chat_completion.choices[0].message.content
        print(f"RAW AI RESPONSE: {raw_text}")
        
        try:
            match = re.search(r'(\[.*\]|\{.*\})', raw_text, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                json_str = raw_text
                
            parsed_json = json.loads(json_str)
            if isinstance(parsed_json, list):
                qs = parsed_json
            else:
                qs = parsed_json.get("questions", [])
            final_list = []
            for q in qs:
                text_val = q.get("text", q.get("question_text", ""))
                correct_ans = q.get("correctAnswer", q.get("correct_answer", "A"))
                
                # Cleanup logic: If correctAnswer says "Option A" or "A.", strip it down to just "A"
                correct_ans = correct_ans.replace("Option", "").replace(".", "").strip()
                
                # Cleanup logic: Strip 'A. ', 'B) ' prefixes from options
                clean_opts = []
                if "options" in q and isinstance(q["options"], list):
                    for opt in q["options"]:
                        clean_opt = re.sub(r'^(Option\s+)?[A-E][.\)]\s*', '', str(opt).strip(), flags=re.IGNORECASE)
                        clean_opts.append(clean_opt)
                elif "options" in q:
                    clean_opts = q["options"]
                    
                final_q = {
                    "text": text_val,
                    "options": clean_opts,
                    "correctAnswer": correct_ans,
                    "explanation": q.get("explanation", "")
                }
                final_list.append(final_q)
                    
            return final_list
        except Exception as e:
            print(f"Failed to parse JSON chunk: {e}")
            raise Exception(f"JSON Parsing Error. Could not parse AI response: {str(e)}. Raw output: {raw_text[:200]}...")

    try:
        max_chunk = 10  # 8b-instant handles larger chunks comfortably
        chunks = [max_chunk] * (request.count // max_chunk)
        if request.count % max_chunk > 0:
            chunks.append(request.count % max_chunk)
            
        tasks = [fetch_chunk(size) for size in chunks]
        results = await asyncio.gather(*tasks)
        
        all_questions = []
        for res in results:
            all_questions.extend(res)
            
        if all_questions:
            print(f"OUTGOING DATA TO UI: {all_questions[0]}")
            
        return all_questions

    except Exception as e:
        print(f"OpenAI API Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate medical vignette: {str(e)}"
        )

class MissedQuestion(BaseModel):
    category: str
    question_text: str | None = None

class SessionSummaryRequest(BaseModel):
    missed_questions: List[MissedQuestion]

class SessionSummaryResponse(BaseModel):
    feedback: str

@router.post("/session-summary", response_model=SessionSummaryResponse)
def generate_session_summary(request: SessionSummaryRequest):
    prompt = f"""
    You are a Senior Canadian Medical Educator acting as a Consultant.
    The user has just finished a challenging MCCQE1 exam sprint.
    Here is the data on the questions they missed (categories and vignettes):
    {request.model_dump_json()}
    
    Generate a precise, 3-sentence 'Consultant's Feedback' summarizing their performance based on these gaps.
    Point out their weaknesses specifically by referencing the missed categories. Give actionable advice (e.g., if they missed CLEO, tell them to review CMPA guidelines).
    
    Example of the tone: 'You demonstrated strong diagnostic skills overall, but your management of legal consent (CLEO) requires review of the CMPA guidelines. Focus more on capacity assessments.'
    
    You MUST output ONLY valid, raw JSON exactly matching this schema:
    {{
        "feedback": "Your 3-sentence feedback here."
    }}
    """
    
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You must output valid JSON only, exactly matching the requested schema."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="gpt-4o-mini",
            response_format={"type": "json_object"}
        )
        
        raw_text = chat_completion.choices[0].message.content
        summary_data = json.loads(raw_text)
        return summary_data

    except Exception as e:
        print(f"OpenAI API Summary Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate session summary: {str(e)}"
        )
